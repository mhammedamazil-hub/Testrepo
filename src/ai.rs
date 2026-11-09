//! Owner-configured providers and task routing. Secrets never appear in GET responses.
use super::*;
use std::collections::BTreeMap;
#[derive(Clone, Serialize, Deserialize)]
pub struct Provider {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub base_url: String,
    pub model: String,
    #[serde(default)]
    pub api_key: String,
}
#[derive(Clone, Serialize, Deserialize, Default)]
pub struct Settings {
    pub providers: Vec<Provider>,
    pub assignments: BTreeMap<String, String>,
}
#[derive(Deserialize)]
pub(super) struct SaveInput {
    pub providers: Vec<ProviderInput>,
    pub assignments: BTreeMap<String, String>,
}
#[derive(Deserialize)]
pub(super) struct ProviderInput {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub base_url: String,
    pub model: String,
    pub api_key: Option<String>,
    #[serde(default)]
    pub clear_key: bool,
}
pub(super) fn validate(p: &Provider) -> Result<()> {
    text(&p.name, "Provider name", 100)?;
    text(&p.model, "Model", 200)?;
    if !["openai", "anthropic", "gemini", "native"].contains(&p.kind.as_str()) {
        return Err(bad("Unsupported API protocol"));
    }
    if p.kind == "native" {
        return Ok(());
    }
    let url = reqwest::Url::parse(&p.base_url).map_err(|_| bad("Invalid provider base URL"))?;
    if !url.username().is_empty()
        || url.password().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
    {
        return Err(bad(
            "Provider URL must not contain credentials, query or fragment",
        ));
    }
    if url.scheme() != "https"
        && !(url.scheme() == "http"
            && matches!(url.host_str(), Some("localhost" | "127.0.0.1" | "[::1]")))
    {
        return Err(bad("Use HTTPS for APIs; HTTP is allowed only for an explicit on-device/localhost model endpoint"));
    }
    if p.api_key.len() > 8000 {
        return Err(bad("API key too long"));
    }
    Ok(())
}
pub(super) async fn get(State(a): State<App>, h: HeaderMap) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    Ok(Json(redact(&*a.ai.read().await)))
}
fn redact(s: &Settings) -> Value {
    json!({"providers":s.providers.iter().map(|p|json!({"id":p.id,"name":p.name,"kind":p.kind,"base_url":p.base_url,"model":p.model,"key_set":!p.api_key.is_empty()})).collect::<Vec<_>>(),"assignments":s.assignments,"tasks":tasks(),"key_storage":"Keys are saved in app-private/local configuration with restricted file permissions; they are not encrypted by this application."})
}
pub(super) fn tasks() -> Vec<&'static str> {
    let mut v = vec![
        "default",
        "chat",
        "source-guide",
        "vision",
        "speech",
        "transcription",
    ];
    v.extend_from_slice(KINDS);
    v
}
pub(super) async fn save(
    State(a): State<App>,
    h: HeaderMap,
    Json(p): Json<SaveInput>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    if p.providers.len() > 20 {
        return Err(bad("Maximum 20 providers"));
    }
    let mut guard = a.ai.write().await;
    let mut next = Settings::default();
    let mut ids = HashSet::new();
    for input in p.providers {
        if Uuid::parse_str(&input.id).is_err() || !ids.insert(input.id.clone()) {
            return Err(bad("Provider IDs must be unique UUIDs"));
        }
        let old = guard.providers.iter().find(|x| x.id == input.id);
        let key = if input.clear_key {
            String::new()
        } else if let Some(key) = input.api_key {
            key
        } else {
            old.map(|p| p.api_key.clone()).unwrap_or_default()
        };
        let provider = Provider {
            id: input.id,
            name: text(&input.name, "Provider name", 100)?,
            kind: input.kind,
            base_url: input.base_url.trim().trim_end_matches('/').into(),
            model: input.model.trim().trim_start_matches("models/").into(),
            api_key: key,
        };
        validate(&provider)?;
        next.providers.push(provider);
    }
    for (task, pid) in p.assignments {
        if !tasks().contains(&task.as_str()) || (!pid.is_empty() && !ids.contains(&pid)) {
            return Err(bad("Invalid task assignment"));
        }
        if !pid.is_empty() {
            next.assignments.insert(task, pid);
        }
    }
    let path = a.config.data.with_extension("ai.json");
    if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
        tokio::fs::create_dir_all(parent).await.map_err(internal)?;
    }
    let temp = path.with_extension("ai.tmp");
    let mut options = tokio::fs::OpenOptions::new();
    options.create(true).write(true).truncate(true);
    #[cfg(unix)]
    options.mode(0o600);
    use tokio::io::AsyncWriteExt;
    let mut file = options.open(&temp).await.map_err(internal)?;
    file.write_all(&serde_json::to_vec(&next).map_err(internal)?)
        .await
        .map_err(internal)?;
    file.sync_all().await.map_err(internal)?;
    drop(file);
    tokio::fs::rename(&temp, &path).await.map_err(internal)?;
    *guard = next;
    Ok(Json(redact(&guard)))
}
pub(super) async fn resolve(a: &App, task: &str) -> Provider {
    let settings = a.ai.read().await;
    let selected = settings
        .assignments
        .get(task)
        .or_else(|| settings.assignments.get("default"))
        .and_then(|id| settings.providers.iter().find(|p| &p.id == id));
    if let Some(p) = selected {
        return p.clone();
    }
    Provider {
        id: "environment".into(),
        name: "Default".into(),
        kind: if cfg!(all(feature = "android-offline", target_os = "android")) {
            "native"
        } else {
            "openai"
        }
        .into(),
        base_url: a.config.base_url.clone(),
        model: a.config.model.clone(),
        api_key: a.config.api_key.clone(),
    }
}
/// Convert multimodal OpenAI-style content for native Gemini/Anthropic APIs.
fn parts(content: &Value, kind: &str) -> Value {
    let items = if let Some(s) = content.as_str() {
        vec![json!({"type":"text","text":s})]
    } else {
        content.as_array().cloned().unwrap_or_default()
    };
    Value::Array(items.into_iter().filter_map(|p|{if p["type"]=="text"{Some(if kind=="gemini"{json!({"text":p["text"]})}else{p})}else if p["type"]=="image_url"{let raw=p["image_url"]["url"].as_str()?;let (head,data)=raw.strip_prefix("data:")?.split_once(";base64,")?;Some(if kind=="gemini"{json!({"inlineData":{"mimeType":head,"data":data}})}else{json!({"type":"image","source":{"type":"base64","media_type":head,"data":data}})})}else{None}}).collect())
}
pub(super) async fn request(a: &App, p: &Provider, messages: Vec<Value>) -> Result<String> {
    if p.kind == "native" {
        #[cfg(all(feature = "android-offline", target_os = "android"))]
        {
            return android_offline::complete(messages).await;
        }
        #[cfg(not(all(feature = "android-offline", target_os = "android")))]
        {
            return Err(bad("The native on-device engine is available only in the standalone Android build. Configure a localhost OpenAI-compatible endpoint on desktop."));
        }
    }
    if a.offline {
        return Err(bad("Cloud AI is disabled in offline mode"));
    }
    let base = p.base_url.trim_end_matches('/');
    let system = messages
        .first()
        .and_then(|v| v["content"].as_str())
        .unwrap_or("");
    let mut req=match p.kind.as_str(){
  "anthropic"=>a.client.post(format!("{base}/messages")).header("x-api-key",&p.api_key).header("anthropic-version","2023-06-01").json(&json!({"model":p.model,"max_tokens":4096,"system":system,"messages":messages.iter().skip(1).map(|m|json!({"role":m["role"],"content":parts(&m["content"],"anthropic")})).collect::<Vec<_>>()})),
  "gemini"=>{let mut url=reqwest::Url::parse(&format!("{base}/models/")).map_err(|_|bad("Invalid Gemini base URL"))?;url.path_segments_mut().map_err(|_|bad("Invalid provider path"))?.pop_if_empty().push(&format!("{}:generateContent",p.model.trim_start_matches("models/")));a.client.post(url).header("x-goog-api-key",&p.api_key).json(&json!({"systemInstruction":{"parts":[{"text":system}]},"contents":messages.iter().skip(1).map(|m|json!({"role":if m["role"]=="assistant"{"model"}else{"user"},"parts":parts(&m["content"],"gemini")})).collect::<Vec<_>>(),"generationConfig":{"maxOutputTokens":4096}}))},
  _=>a.client.post(format!("{base}/chat/completions")).json(&json!({"model":p.model,"messages":messages,"max_tokens":4096})),
 };
    if p.kind == "openai" && !p.api_key.is_empty() {
        req = req.bearer_auth(&p.api_key);
    }
    let mut response = req.send().await.map_err(|_| {
        Error(
            StatusCode::BAD_GATEWAY,
            "AI connection failed. Check network access, base URL and provider configuration."
                .into(),
        )
    })?;
    if !response.status().is_success() {
        return Err(provider_error(response, p).await);
    }
    let mut bytes = Vec::new();
    while let Some(c) = response
        .chunk()
        .await
        .map_err(|_| bad("AI response interrupted"))?
    {
        if bytes.len() + c.len() > MAX_TEXT {
            return Err(bad("AI response exceeds 2 MB"));
        }
        bytes.extend_from_slice(&c);
    }
    let v: Value = serde_json::from_slice(&bytes).map_err(|_| bad("Invalid provider JSON"))?;
    let answer = match p.kind.as_str() {
        "gemini" => v["candidates"][0]["content"]["parts"].as_array().map(|p| {
            p.iter()
                .filter(|x| x["thought"] != true)
                .filter_map(|x| x["text"].as_str())
                .collect::<Vec<_>>()
                .join("\n")
        }),
        "anthropic" => v["content"].as_array().map(|p| {
            p.iter()
                .filter_map(|x| x["text"].as_str())
                .collect::<Vec<_>>()
                .join("\n")
        }),
        _ => v["choices"][0]["message"]["content"]
            .as_str()
            .map(str::to_owned),
    };
    answer
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| bad("Provider returned no usable text"))
}

pub(super) async fn media_provider(a: &App, task: &str) -> Result<Provider> {
    let settings = a.ai.read().await;
    let selected = settings
        .assignments
        .get(task)
        .and_then(|id| settings.providers.iter().find(|p| &p.id == id))
        .cloned();
    drop(settings);
    let mut provider = if let Some(p) = selected {
        p
    } else {
        let mut p = resolve(a, "default").await;
        p.model = if task == "speech" {
            a.media.tts_model.clone()
        } else {
            a.media.transcription_model.clone()
        };
        p
    };
    provider.model=text(&provider.model,"Assign a speech/transcription model in Settings (or set AI_TTS_MODEL / AI_TRANSCRIPTION_MODEL)",200)?;
    if provider.kind != "openai" {
        return Err(bad("Speech/transcription currently require an OpenAI-compatible audio API, not Gemini/Anthropic text protocols or the native text engine"));
    }
    Ok(provider)
}

/// Only structured, bounded provider messages are shown; never raw HTTP bodies/headers.
async fn provider_error(mut response: reqwest::Response, p: &Provider) -> Error {
    let status = response.status();
    let mut bytes = Vec::new();
    while let Ok(Some(chunk)) = response.chunk().await {
        if bytes.len() + chunk.len() > 16384 {
            break;
        }
        bytes.extend_from_slice(&chunk);
    }
    let value: Value = serde_json::from_slice(&bytes).unwrap_or(Value::Null);
    let raw = value["error"]["message"]
        .as_str()
        .or_else(|| value["message"].as_str())
        .unwrap_or("");
    let mut message = raw.to_string();
    if !p.api_key.is_empty() {
        message = message.replace(&p.api_key, "[redacted]");
    }
    // Strip tokens even when a provider echoes a fragment/URL-encoded credential.
    message = message
        .split_whitespace()
        .map(|word| {
            if word.contains("AIza") || word.contains("sk-") || word.contains("key=") {
                "[redacted]"
            } else {
                word
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
        .filter(|c| !c.is_control())
        .take(600)
        .collect();
    let hint=match status.as_u16(){400=>"Check the exact model ID, API key restrictions and request support. Use Load models and Test connection in Settings.",401|403=>"Check API key validity, project permissions, region restrictions and billing.",404=>"This model or endpoint was not found. Load models in Settings and choose an available model.",429=>"Provider quota or rate limit reached. Check billing/quota, then retry later.",_=>"Check provider availability and configuration."};
    Error(
        StatusCode::BAD_GATEWAY,
        format!(
            "{} returned HTTP {}. {} {}",
            p.name,
            status.as_u16(),
            message,
            hint
        ),
    )
}
async fn draft(a: &App, input: ProviderInput, require_model: bool) -> Result<Provider> {
    let guard = a.ai.read().await;
    let old = guard.providers.iter().find(|p| p.id == input.id);
    let api_key = if input.clear_key {
        String::new()
    } else {
        input
            .api_key
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| old.map(|p| p.api_key.clone()).unwrap_or_default())
    };
    let mut p = Provider {
        id: input.id,
        name: input.name,
        kind: input.kind,
        base_url: input.base_url.trim().trim_end_matches('/').into(),
        model: input.model.trim().trim_start_matches("models/").into(),
        api_key,
    };
    if !require_model && p.model.is_empty() {
        p.model = "discovery".into();
    }
    validate(&p)?;
    Ok(p)
}
pub(super) async fn test_connection(
    State(a): State<App>,
    h: HeaderMap,
    Json(input): Json<ProviderInput>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    let p = draft(&a, input, true).await?;
    let _slot = a
        .ai_slots
        .try_acquire()
        .map_err(|_| bad("Another AI job is running; retry shortly"))?;
    let start = std::time::Instant::now();
    tokio::time::timeout(
        Duration::from_secs(60),
        request(
            &a,
            &p,
            vec![
                json!({"role":"system","content":"Connection check. Reply briefly."}),
                json!({"role":"user","content":"Reply with OK."}),
            ],
        ),
    )
    .await
    .map_err(|_| bad("Connection test timed out after 60 seconds"))??;
    Ok(Json(
        json!({"ok":true,"model":p.model,"latency_ms":start.elapsed().as_millis(),"message":"Model responded successfully. Settings are not saved until you press Save."}),
    ))
}
pub(super) async fn models(
    State(a): State<App>,
    h: HeaderMap,
    Json(input): Json<ProviderInput>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    if a.offline {
        return Err(bad("Model discovery requires a network"));
    }
    let p = draft(&a, input, false).await?;
    if p.kind == "native" {
        return Err(bad("Use Local AI in Settings to import compatible weights. This runtime has no remote model list."));
    }
    let _slot = a
        .ai_slots
        .try_acquire()
        .map_err(|_| bad("Another AI job is running; retry shortly"))?;
    let base = p.base_url.trim_end_matches('/');
    let mut request = a
        .client
        .get(format!("{base}/models"))
        .timeout(Duration::from_secs(30));
    if p.kind == "gemini" {
        request = request
            .header("x-goog-api-key", &p.api_key)
            .query(&[("pageSize", "1000")]);
    } else if p.kind == "anthropic" {
        request = request
            .header("x-api-key", &p.api_key)
            .header("anthropic-version", "2023-06-01");
    } else if !p.api_key.is_empty() {
        request = request.bearer_auth(&p.api_key);
    }
    let mut response = request
        .send()
        .await
        .map_err(|_| bad("Could not fetch models. Check the base URL, network and API key."))?;
    if !response.status().is_success() {
        return Err(provider_error(response, &p).await);
    }
    let mut bytes = Vec::new();
    while let Some(c) = response
        .chunk()
        .await
        .map_err(|_| bad("Model list interrupted"))?
    {
        if bytes.len() + c.len() > MAX_TEXT {
            return Err(bad("Model list too large"));
        }
        bytes.extend_from_slice(&c);
    }
    let v: Value = serde_json::from_slice(&bytes).map_err(|_| bad("Invalid model list JSON"))?;
    let mut models: Vec<String> = if p.kind == "gemini" {
        v["models"]
            .as_array()
            .into_iter()
            .flatten()
            .filter(|m| {
                m["supportedGenerationMethods"]
                    .as_array()
                    .is_some_and(|a| a.iter().any(|x| x == "generateContent"))
            })
            .filter_map(|m| m["name"].as_str())
            .map(|s| s.trim_start_matches("models/").to_string())
            .collect()
    } else {
        v["data"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(|m| m["id"].as_str())
            .map(str::to_string)
            .collect()
    };
    models.sort();
    models.dedup();
    models.truncate(1000);
    Ok(Json(
        json!({"models":models,"note":"Models advertised by this endpoint. Availability and task support depend on your account; use Test connection. Listing may be limited to the first page."}),
    ))
}
