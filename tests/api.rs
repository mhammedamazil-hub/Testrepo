use axum::{body::Body, http::{Request,StatusCode}, routing::post, Json, Router};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use sourcebook::{App, Config};
use tower::ServiceExt;

const TOKEN:&str="integration-test-token-12345";
async fn request(router:&Router,method:&str,path:&str,body:Option<Value>,auth:bool)->(StatusCode,Value){
    let mut builder=Request::builder().method(method).uri(path).header("content-type","application/json");
    if auth{builder=builder.header("authorization",format!("Bearer {TOKEN}"));}
    let response=router.clone().oneshot(builder.body(Body::from(body.map(|v|v.to_string()).unwrap_or_default())).unwrap()).await.unwrap();
    let status=response.status();let bytes=response.into_body().collect().await.unwrap().to_bytes();
    (status,serde_json::from_slice(&bytes).unwrap())
}
async fn setup(base_url:String)->(App,Router,std::path::PathBuf){
    let path=std::env::temp_dir().join(format!("sourcebook-{}.json",uuid::Uuid::new_v4()));
    let a=App::open(Config{data:path.clone(),token:TOKEN.into(),base_url,model:"mock-model".into(),api_key:"private-key".into()}).await.unwrap();
    let router=sourcebook::router(a.clone());(a,router,path)
}
#[tokio::test]
async fn auth_crud_and_persistence(){
    let (app,router,path)=setup("http://127.0.0.1:1/v1".into()).await;
    assert_eq!(request(&router,"GET","/api/notebooks",None,false).await.0,StatusCode::UNAUTHORIZED);
    let (status,n)=request(&router,"POST","/api/notebooks",Some(json!({"title":"Research"})),true).await;assert_eq!(status,StatusCode::OK);
    let id=n["id"].as_str().unwrap();let base=format!("/api/notebooks/{id}");
    assert_eq!(request(&router,"POST",&format!("{base}/sources"),Some(json!({"title":"Paper","content":"Plants use sunlight for photosynthesis"})),true).await.0,StatusCode::OK);
    assert_eq!(request(&router,"POST",&format!("{base}/notes"),Some(json!({"title":"Idea","content":"Explore sunlight"})),true).await.0,StatusCode::OK);
    let (_,export)=request(&router,"GET",&format!("{base}/export"),None,true).await;assert_eq!(export["sources"].as_array().unwrap().len(),1);assert_eq!(export["notes"].as_array().unwrap().len(),1);
    let reopened=App::open(app.config.clone()).await.unwrap();assert_eq!(reopened.db.read().await.notebooks.len(),1);
    let (_,config)=request(&router,"GET","/api/config",None,true).await;assert!(!config.to_string().contains("private-key"));
    assert_eq!(request(&router,"DELETE",&base,None,true).await.0,StatusCode::OK);
    assert_eq!(request(&router,"GET",&base,None,true).await.0,StatusCode::NOT_FOUND);
    std::fs::remove_file(path).unwrap();
}
#[tokio::test]
async fn chat_and_artifact_with_mock_provider(){
    let mock=Router::new().route("/v1/chat/completions",post(|Json(body):Json<Value>|async move{
        assert_eq!(body["model"],"mock-model");assert!(body["messages"][0]["content"].as_str().unwrap().contains("UNTRUSTED DATA"));
        Json(json!({"choices":[{"message":{"content":"Plants use sunlight [1]."}}]}))
    }));
    let listener=tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();let addr=listener.local_addr().unwrap();
    let server=tokio::spawn(async move{axum::serve(listener,mock).await.unwrap();});
    let (_,router,path)=setup(format!("http://{addr}/v1")).await;
    let (_,n)=request(&router,"POST","/api/notebooks",Some(json!({"title":"Botany"})),true).await;
    let base=format!("/api/notebooks/{}",n["id"].as_str().unwrap());
    assert_eq!(request(&router,"POST",&format!("{base}/chat"),Some(json!({"question":"Sunlight?"})),true).await.0,StatusCode::BAD_REQUEST);
    request(&router,"POST",&format!("{base}/sources"),Some(json!({"title":"Science","content":"Plants use sunlight."})),true).await;
    let (status,reply)=request(&router,"POST",&format!("{base}/chat"),Some(json!({"question":"How do plants grow?"})),true).await;
    assert_eq!(status,StatusCode::OK);assert_eq!(reply["evidence"][0]["title"],"Science");
    let (status,artifact)=request(&router,"POST",&format!("{base}/generate"),Some(json!({"kind":"summary"})),true).await;assert_eq!(status,StatusCode::OK);assert_eq!(artifact["kind"],"summary");
    let (_,n)=request(&router,"GET",&base,None,true).await;assert_eq!(n["messages"].as_array().unwrap().len(),2);assert_eq!(n["artifacts"].as_array().unwrap().len(),1);
    assert_eq!(request(&router,"POST",&format!("{base}/generate"),Some(json!({"kind":"video"})),true).await.0,StatusCode::BAD_REQUEST);
    server.abort();std::fs::remove_file(path).unwrap();
}
#[tokio::test]
async fn source_validation(){
    let (_,router,path)=setup("http://127.0.0.1:1/v1".into()).await;
    let (_,n)=request(&router,"POST","/api/notebooks",Some(json!({"title":"Test"})),true).await;
    let base=format!("/api/notebooks/{}/sources",n["id"].as_str().unwrap());
    for value in [json!({"title":"Invalid","content":""}),json!({"title":"Bad PDF","kind":"pdf","content":"bm90IHBkZg=="}),json!({"title":"Local","kind":"url","url":"http://127.0.0.1/secret"}),json!({"title":"Scheme","kind":"url","url":"file:///etc/passwd"})]{assert_eq!(request(&router,"POST",&base,Some(value),true).await.0,StatusCode::BAD_REQUEST);}
    std::fs::remove_file(path).unwrap();
}
