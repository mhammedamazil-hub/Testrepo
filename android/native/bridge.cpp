#include "llama.h"
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>
#include <string>
#include <vector>
#include <algorithm>

static std::mutex model_mutex;
static llama_model * model = nullptr;
static std::atomic<bool> cancelled{false}, loaded{false};
static std::chrono::steady_clock::time_point deadline;
static thread_local std::string error_text;
static bool abort_inference(void *) {return cancelled.load() || std::chrono::steady_clock::now() > deadline;}
extern "C" {
struct SbMessage {const char *role; const char *content;};
const char *sb_error(){return error_text.c_str();}
bool sb_loaded(){return loaded.load();}
void sb_cancel(){cancelled.store(true);}
void sb_free(char *p){std::free(p);}
int sb_load(const char *path){
 std::lock_guard<std::mutex> lock(model_mutex);
 try {
  static std::once_flag init;std::call_once(init,[]{llama_backend_init();});
  if(model){llama_model_free(model);model=nullptr;loaded.store(false);}
  cancelled.store(false);
  auto params=llama_model_default_params();params.n_gpu_layers=0;
  model=llama_model_load_from_file(path,params);
  if(!model){error_text="Could not load GGUF. The file may be unsupported, incomplete, or too large for available RAM.";return -1;}
  if(!llama_model_has_decoder(model)||llama_model_has_encoder(model)){llama_model_free(model);model=nullptr;error_text="Use a decoder-only text instruct GGUF model.";return -1;}
  loaded.store(true);return 0;
 }catch(const std::exception &e){error_text=e.what();return -1;}catch(...){error_text="Native model load failed";return -1;}
}
char *sb_complete(const SbMessage *messages,size_t count){
 std::lock_guard<std::mutex> lock(model_mutex);
 try {
  if(!model){error_text="Import a compatible text-instruct GGUF using the Model button first.";return nullptr;}
  cancelled.store(false);deadline=std::chrono::steady_clock::now()+std::chrono::minutes(5);
  std::vector<llama_chat_message> chat;for(size_t i=0;i<count;++i)chat.push_back({messages[i].role,messages[i].content});
  const char *tmpl=llama_model_chat_template(model,nullptr);
  if(!tmpl){error_text="This GGUF has no chat template. Use an instruct model with an embedded supported template.";return nullptr;}
  int size=llama_chat_apply_template(tmpl,chat.data(),chat.size(),true,nullptr,0);
  if(size<=0||size>100000){error_text="Unsupported chat template or oversized prompt.";return nullptr;}
  std::vector<char> formatted(size+1);
  size=llama_chat_apply_template(tmpl,chat.data(),chat.size(),true,formatted.data(),size);
  const llama_vocab *vocab=llama_model_get_vocab(model);
  int nt=-llama_tokenize(vocab,formatted.data(),size,nullptr,0,true,true);
  if(nt<=0||nt>3000){error_text="Prompt exceeds the offline context budget (3000 input tokens). Shorten your question or choose fewer sources.";return nullptr;}
  std::vector<llama_token> tokens(nt);if(llama_tokenize(vocab,formatted.data(),size,tokens.data(),nt,true,true)<0){error_text="Tokenization failed";return nullptr;}
  auto params=llama_context_default_params();params.n_ctx=4096;params.n_batch=256;params.n_ubatch=128;params.n_threads=4;params.n_threads_batch=4;params.abort_callback=abort_inference;
  std::unique_ptr<llama_context,decltype(&llama_free)> ctx(llama_init_from_model(model,params),llama_free);
  if(!ctx){error_text="Could not allocate the 4096-token context. Free RAM or use a smaller model.";return nullptr;}
  for(int i=0;i<nt;i+=256){auto batch=llama_batch_get_one(tokens.data()+i,std::min(256,nt-i));if(llama_decode(ctx.get(),batch)!=0){error_text="Prefill cancelled, timed out, or failed.";return nullptr;}}
  std::unique_ptr<llama_sampler,decltype(&llama_sampler_free)> sampler(llama_sampler_init_greedy(),llama_sampler_free);
  std::string out;bool ended=false;
  for(int i=0;i<1024;++i){
   if(abort_inference(nullptr)){error_text="Generation cancelled or exceeded the five-minute limit.";return nullptr;}
   llama_token token=llama_sampler_sample(sampler.get(),ctx.get(),-1);llama_sampler_accept(sampler.get(),token);
   if(llama_vocab_is_eog(vocab,token)){ended=true;break;}
   char small[256];int len=llama_token_to_piece(vocab,token,small,sizeof(small),0,false);
   if(len<0){std::vector<char> big(-len);len=llama_token_to_piece(vocab,token,big.data(),big.size(),0,false);if(len>0)out.append(big.data(),len);}else if(len>0)out.append(small,len);
   auto batch=llama_batch_get_one(&token,1);if(llama_decode(ctx.get(),batch)!=0){error_text="Decode cancelled, timed out, or failed.";return nullptr;}
  }
  if(!ended){error_text="Output exceeded 1024 tokens. Request a shorter answer or fewer study items.";return nullptr;}
  if(out.empty()){error_text="The model produced no text.";return nullptr;}
  // Some reasoning models expose a thinking preamble. Keep only the final answer when closed.
  auto close=out.find("</think>");if(close!=std::string::npos)out=out.substr(close+8);
  char *result=static_cast<char*>(std::malloc(out.size()+1));if(!result){error_text="Out of memory";return nullptr;}std::memcpy(result,out.c_str(),out.size()+1);return result;
 }catch(const std::exception &e){error_text=e.what();return nullptr;}catch(...){error_text="Native inference failed";return nullptr;}
}
}
