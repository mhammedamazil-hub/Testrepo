use axum::{
    body::Body,
    http::{Request, StatusCode},
    routing::post,
    Json, Router,
};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use sourcebook::{App, Config};
use tower::ServiceExt;

const TOKEN: &str = "integration-test-token-12345";
async fn request(
    router: &Router,
    method: &str,
    path: &str,
    body: Option<Value>,
    auth: bool,
) -> (StatusCode, Value) {
    let mut builder = Request::builder()
        .method(method)
        .uri(path)
        .header("content-type", "application/json");
    if auth {
        builder = builder.header("authorization", format!("Bearer {TOKEN}"));
    }
    let response = router
        .clone()
        .oneshot(
            builder
                .body(Body::from(body.map(|v| v.to_string()).unwrap_or_default()))
                .unwrap(),
        )
        .await
        .unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap())
}
async fn setup(base_url: String) -> (App, Router, std::path::PathBuf) {
    let path = std::env::temp_dir().join(format!("sourcebook-{}.json", uuid::Uuid::new_v4()));
    let a = App::open(Config {
        data: path.clone(),
        token: TOKEN.into(),
        base_url,
        model: "mock-model".into(),
        api_key: "private-key".into(),
    })
    .await
    .unwrap();
    let router = sourcebook::router(a.clone());
    (a, router, path)
}
#[tokio::test]
async fn auth_crud_and_persistence() {
    let (app, router, path) = setup("http://127.0.0.1:1/v1".into()).await;
    assert_eq!(
        request(&router, "GET", "/api/notebooks", None, false)
            .await
            .0,
        StatusCode::UNAUTHORIZED
    );
    let (status, n) = request(
        &router,
        "POST",
        "/api/notebooks",
        Some(json!({"title":"Research"})),
        true,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    let id = n["id"].as_str().unwrap();
    let base = format!("/api/notebooks/{id}");
    assert_eq!(
        request(
            &router,
            "POST",
            &format!("{base}/sources"),
            Some(json!({"title":"Paper","content":"Plants use sunlight for photosynthesis"})),
            true
        )
        .await
        .0,
        StatusCode::OK
    );
    assert_eq!(
        request(
            &router,
            "POST",
            &format!("{base}/notes"),
            Some(json!({"title":"Idea","content":"Explore sunlight"})),
            true
        )
        .await
        .0,
        StatusCode::OK
    );
    let (_, export) = request(&router, "GET", &format!("{base}/export"), None, true).await;
    assert_eq!(export["sources"].as_array().unwrap().len(), 1);
    assert_eq!(export["notes"].as_array().unwrap().len(), 1);
    let reopened = App::open(app.config.clone()).await.unwrap();
    assert_eq!(reopened.db.read().await.notebooks.len(), 1);
    let (_, config) = request(&router, "GET", "/api/config", None, true).await;
    assert!(!config.to_string().contains("private-key"));
    assert_eq!(
        request(&router, "DELETE", &base, None, true).await.0,
        StatusCode::OK
    );
    assert_eq!(
        request(&router, "GET", &base, None, true).await.0,
        StatusCode::NOT_FOUND
    );
    std::fs::remove_file(path).unwrap();
}
#[tokio::test]
async fn chat_and_artifact_with_mock_provider() {
    let mock = Router::new().route(
        "/v1/chat/completions",
        post(|Json(body): Json<Value>| async move {
            assert_eq!(body["model"], "mock-model");
            assert!(body["messages"][0]["content"]
                .as_str()
                .unwrap()
                .contains("UNTRUSTED DATA"));
            Json(json!({"choices":[{"message":{"content":"Plants use sunlight [1]."}}]}))
        }),
    );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let server = tokio::spawn(async move {
        axum::serve(listener, mock).await.unwrap();
    });
    let (_, router, path) = setup(format!("http://{addr}/v1")).await;
    let (_, n) = request(
        &router,
        "POST",
        "/api/notebooks",
        Some(json!({"title":"Botany"})),
        true,
    )
    .await;
    let base = format!("/api/notebooks/{}", n["id"].as_str().unwrap());
    assert_eq!(
        request(
            &router,
            "POST",
            &format!("{base}/chat"),
            Some(json!({"question":"Sunlight?"})),
            true
        )
        .await
        .0,
        StatusCode::BAD_REQUEST
    );
    request(
        &router,
        "POST",
        &format!("{base}/sources"),
        Some(json!({"title":"Science","content":"Plants use sunlight."})),
        true,
    )
    .await;
    let (status, reply) = request(
        &router,
        "POST",
        &format!("{base}/chat"),
        Some(json!({"question":"How do plants grow?"})),
        true,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(reply["evidence"][0]["title"], "Science");
    let (status, artifact) = request(
        &router,
        "POST",
        &format!("{base}/generate"),
        Some(json!({"kind":"summary"})),
        true,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(artifact["kind"], "summary");
    let (_, n) = request(&router, "GET", &base, None, true).await;
    assert_eq!(n["messages"].as_array().unwrap().len(), 2);
    assert_eq!(n["artifacts"].as_array().unwrap().len(), 1);
    assert_eq!(
        request(
            &router,
            "POST",
            &format!("{base}/generate"),
            Some(json!({"kind":"video"})),
            true
        )
        .await
        .0,
        StatusCode::BAD_REQUEST
    );
    server.abort();
    std::fs::remove_file(path).unwrap();
}
#[tokio::test]
async fn source_validation() {
    let (_, router, path) = setup("http://127.0.0.1:1/v1".into()).await;
    let (_, n) = request(
        &router,
        "POST",
        "/api/notebooks",
        Some(json!({"title":"Test"})),
        true,
    )
    .await;
    let base = format!("/api/notebooks/{}/sources", n["id"].as_str().unwrap());
    for value in [
        json!({"title":"Invalid","content":""}),
        json!({"title":"Bad PDF","kind":"pdf","content":"bm90IHBkZg=="}),
        json!({"title":"Local","kind":"url","url":"http://127.0.0.1/secret"}),
        json!({"title":"Scheme","kind":"url","url":"file:///etc/passwd"}),
    ] {
        assert_eq!(
            request(&router, "POST", &base, Some(value), true).await.0,
            StatusCode::BAD_REQUEST
        );
    }
    std::fs::remove_file(path).unwrap();
}

#[tokio::test]
async fn interactive_study_restore_sharing_and_editing() {
    let mock = Router::new().route("/v1/chat/completions", post(|Json(body):Json<Value>|async move {
        let prompt=body["messages"].as_array().unwrap().last().unwrap()["content"].as_str().unwrap();
        let content=if prompt.contains("Create a flashcards") {r#"{"type":"flashcards","cards":[{"front":"What do plants use?","back":"Sunlight [1]"}]}"#}
        else if prompt.contains("Create a quiz") {r#"{"type":"quiz","questions":[{"question":"Plants use?","options":["Sunlight","Steel"],"answer":0,"explanation":"Sunlight [1]"}]}"#}
        else if prompt.contains("Create a data-table") {r#"{"type":"data-table","columns":["A","B"],"rows":[["=danger()","Fact [1]"]]}"#}
        else {"Source guide: plants use sunlight [1]."};
        Json(json!({"choices":[{"message":{"content":content}}]}))
    }));
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let server = tokio::spawn(async move {
        axum::serve(listener, mock).await.unwrap();
    });
    let (_, router, path) = setup(format!("http://{addr}/v1")).await;
    let (_, book) = request(
        &router,
        "POST",
        "/api/notebooks",
        Some(json!({"title":"Study"})),
        true,
    )
    .await;
    let base = format!("/api/notebooks/{}", book["id"].as_str().unwrap());
    let (_, source) = request(
        &router,
        "POST",
        &format!("{base}/sources"),
        Some(json!({"title":"Plant facts","content":"Plants use sunlight."})),
        true,
    )
    .await;
    let sid = source["id"].as_str().unwrap();
    assert_eq!(
        request(
            &router,
            "PATCH",
            &format!("{base}/sources/{sid}"),
            Some(json!({"title":"Plants","content":"Plants use sunlight for photosynthesis."})),
            true
        )
        .await
        .0,
        StatusCode::OK
    );
    for kind in ["flashcards", "quiz", "data-table"] {
        let (status, art) = request(
            &router,
            "POST",
            &format!("{base}/generate"),
            Some(json!({"kind":kind})),
            true,
        )
        .await;
        assert_eq!(status, StatusCode::OK, "{art}");
        assert_eq!(art["data"]["type"], kind);
        let artbase = format!("{base}/artifacts/{}", art["id"].as_str().unwrap());
        if kind == "flashcards" {
            let (s, review) = request(
                &router,
                "POST",
                &format!("{artbase}/review"),
                Some(json!({"card":0,"known":true})),
                true,
            )
            .await;
            assert_eq!(s, StatusCode::OK);
            assert_eq!(review["known"][0], true);
        }
        if kind == "quiz" {
            let (_, review) = request(
                &router,
                "POST",
                &format!("{artbase}/review"),
                Some(json!({"answers":[0]})),
                true,
            )
            .await;
            assert_eq!(review["score"], 1);
            assert_eq!(
                request(
                    &router,
                    "POST",
                    &format!("{artbase}/review"),
                    Some(json!({"answers":[4]})),
                    true
                )
                .await
                .0,
                StatusCode::BAD_REQUEST
            );
        }
        if kind == "data-table" {
            let response = router
                .clone()
                .oneshot(
                    Request::builder()
                        .uri(format!("{artbase}/download"))
                        .header("authorization", format!("Bearer {TOKEN}"))
                        .body(Body::empty())
                        .unwrap(),
                )
                .await
                .unwrap();
            assert_eq!(response.status(), StatusCode::OK);
            let bytes = response.into_body().collect().await.unwrap().to_bytes();
            assert!(String::from_utf8_lossy(&bytes).contains("'=danger()"));
        }
    }
    assert_eq!(
        request(
            &router,
            "POST",
            &format!("{base}/sources/{sid}/guide"),
            Some(json!({})),
            true
        )
        .await
        .0,
        StatusCode::OK
    );
    let (_, note) = request(
        &router,
        "POST",
        &format!("{base}/notes"),
        Some(json!({"title":"Note","content":"Old"})),
        true,
    )
    .await;
    assert_eq!(
        request(
            &router,
            "PATCH",
            &format!("{base}/notes/{}", note["id"].as_str().unwrap()),
            Some(json!({"title":"Updated","content":"New"})),
            true
        )
        .await
        .0,
        StatusCode::OK
    );
    let (_, share) = request(
        &router,
        "POST",
        &format!("{base}/share"),
        Some(json!({})),
        true,
    )
    .await;
    let shared = format!("/api/share/{}", share["token"].as_str().unwrap());
    let (status, view) = request(&router, "GET", &shared, None, false).await;
    assert_eq!(status, StatusCode::OK);
    assert!(view["share_token"].is_null());
    assert_eq!(view["notes"][0]["content"], "New");
    let (_, export) = request(&router, "GET", &format!("{base}/export"), None, true).await;
    let (status, restored) =
        request(&router, "POST", "/api/notebooks/import", Some(export), true).await;
    assert_eq!(status, StatusCode::OK);
    assert_ne!(restored["id"], book["id"]);
    assert_ne!(restored["sources"][0]["id"], source["id"]);
    assert!(restored["share_token"].is_null());
    request(&router, "DELETE", &format!("{base}/share"), None, true).await;
    assert_eq!(
        request(&router, "GET", &shared, None, false).await.0,
        StatusCode::NOT_FOUND
    );
    server.abort();
    std::fs::remove_file(path).unwrap();
}

#[tokio::test]
async fn real_media_protocol_with_mock_provider() {
    let mock=Router::new()
        .route("/v1/chat/completions",post(||async{Json(json!({"choices":[{"message":{"content":"Plants use sunlight. This is a short audio overview."}}]}))}))
        .route("/v1/audio/speech",post(|Json(p):Json<Value>|async move{assert_eq!(p["model"],"mock-tts");assert_eq!(p["response_format"],"mp3");([( "content-type","audio/mpeg")],b"ID3mock-audio-bytes".to_vec())}))
        .route("/v1/audio/transcriptions",post(|headers:axum::http::HeaderMap|async move{assert!(headers["content-type"].to_str().unwrap().contains("multipart/form-data"));Json(json!({"text":"A transcribed lecture about plants."}))}));
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let server = tokio::spawn(async move {
        axum::serve(listener, mock).await.unwrap();
    });
    let (mut app, _, path) = setup(format!("http://{addr}/v1")).await;
    app.media = std::sync::Arc::new(sourcebook::MediaConfig {
        tts_model: "mock-tts".into(),
        voice: "alloy".into(),
        transcription_model: "mock-whisper".into(),
    });
    let router = sourcebook::router(app);
    let (_, book) = request(
        &router,
        "POST",
        "/api/notebooks",
        Some(json!({"title":"Audio"})),
        true,
    )
    .await;
    let base = format!("/api/notebooks/{}", book["id"].as_str().unwrap());
    let (status, source) = request(
        &router,
        "POST",
        &format!("{base}/transcribe"),
        Some(json!({"title":"Lecture","filename":"lecture.mp3","content":"SUQzYXVkaW8="})),
        true,
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{source}");
    assert_eq!(source["kind"], "transcript");
    let (status, art) = request(
        &router,
        "POST",
        &format!("{base}/generate"),
        Some(json!({"kind":"audio-overview"})),
        true,
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{art}");
    assert_eq!(art["media"], true);
    let media = format!("{base}/artifacts/{}/media", art["id"].as_str().unwrap());
    assert_eq!(
        request(&router, "GET", &media, None, false).await.0,
        StatusCode::UNAUTHORIZED
    );
    let response = router
        .clone()
        .oneshot(
            Request::builder()
                .uri(&media)
                .header("authorization", format!("Bearer {TOKEN}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(response.headers()["content-type"], "audio/mpeg");
    request(&router, "DELETE", &base, None, true).await;
    assert_eq!(
        std::fs::read_dir(path.with_extension("media"))
            .unwrap()
            .count(),
        0
    );
    std::fs::remove_dir(path.with_extension("media")).unwrap();
    std::fs::remove_file(path).unwrap();
    server.abort();
}

#[tokio::test]
async fn docx_extracts_text_and_rejects_invalid_archives() {
    use base64::Engine;
    use std::io::Write;
    let (_, router, path) = setup("http://127.0.0.1:1/v1".into()).await;
    let (_, book) = request(
        &router,
        "POST",
        "/api/notebooks",
        Some(json!({"title":"Documents"})),
        true,
    )
    .await;
    let base = format!("/api/notebooks/{}/sources", book["id"].as_str().unwrap());
    let mut archive = zip::ZipWriter::new(std::io::Cursor::new(Vec::new()));
    archive
        .start_file(
            "word/document.xml",
            zip::write::SimpleFileOptions::default(),
        )
        .unwrap();
    archive.write_all(br#"<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello &amp; Rust</w:t></w:r></w:p></w:body></w:document>"#).unwrap();
    let bytes = archive.finish().unwrap().into_inner();
    let (status,source)=request(&router,"POST",&base,Some(json!({"title":"Document","kind":"docx","content":base64::engine::general_purpose::STANDARD.encode(bytes)})),true).await;
    assert_eq!(status, StatusCode::OK, "{source}");
    assert_eq!(source["content"], "Hello & Rust");
    assert_eq!(
        request(
            &router,
            "POST",
            &base,
            Some(json!({"title":"Bad","kind":"docx","content":"bm90IGEgemlw"})),
            true
        )
        .await
        .0,
        StatusCode::BAD_REQUEST
    );
    std::fs::remove_file(path).unwrap();
}

#[tokio::test]
async fn offline_storage_and_network_boundaries_without_socket_server() {
    let (mut app, _, path) = setup("http://127.0.0.1:1/disabled".into()).await;
    app.offline = true;
    let router = sourcebook::router(app);
    let (_, book) = request(
        &router,
        "POST",
        "/api/notebooks",
        Some(json!({"title":"On phone"})),
        true,
    )
    .await;
    let base = format!("/api/notebooks/{}", book["id"].as_str().unwrap());
    assert_eq!(
        request(
            &router,
            "POST",
            &format!("{base}/sources"),
            Some(json!({"title":"Local","content":"On-device source"})),
            true
        )
        .await
        .0,
        StatusCode::OK
    );
    let (status, error) = request(
        &router,
        "POST",
        &format!("{base}/sources"),
        Some(json!({"title":"Web","kind":"url","url":"https://example.com"})),
        true,
    )
    .await;
    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(error["error"].as_str().unwrap().contains("offline"));
    assert_eq!(
        request(
            &router,
            "POST",
            &format!("{base}/share"),
            Some(json!({})),
            true
        )
        .await
        .0,
        StatusCode::BAD_REQUEST
    );
    let (_, config) = request(&router, "GET", "/api/config", None, true).await;
    assert_eq!(config["offline"], true);
    std::fs::remove_file(path).unwrap();
}

#[tokio::test]
async fn provider_keys_are_redacted_persisted_and_task_routing_is_applied() {
    let called = std::sync::Arc::new(tokio::sync::Mutex::new(String::new()));
    let capture = called.clone();
    let mock = Router::new().route(
        "/v1/chat/completions",
        post(move |Json(p): Json<Value>| {
            let capture = capture.clone();
            async move {
                *capture.lock().await = p["model"].as_str().unwrap_or("").into();
                Json(json!({"choices":[{"message":{"content":"Grounded answer [1]"}}]}))
            }
        }),
    );
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let base = format!("http://{}/v1", listener.local_addr().unwrap());
    let server = tokio::spawn(async move { axum::serve(listener, mock).await.unwrap() });
    let (_, router, path) = setup(base.clone()).await;
    let pid = uuid::Uuid::new_v4().to_string();
    assert_eq!(
        request(&router, "GET", "/api/ai", None, false).await.0,
        StatusCode::UNAUTHORIZED
    );
    let payload = json!({"providers":[{"id":pid,"name":"Task AI","kind":"openai","base_url":base,"model":"specific-chat-model","api_key":"not-a-real-secret"}],"assignments":{"chat":pid}});
    let (status, saved) = request(&router, "PUT", "/api/ai", Some(payload.clone()), true).await;
    assert_eq!(status, StatusCode::OK, "{saved}");
    assert_eq!(saved["providers"][0]["key_set"], true);
    assert!(!saved.to_string().contains("not-a-real-secret"));
    let (_, settings) = request(&router, "GET", "/api/ai", None, true).await;
    assert!(!settings.to_string().contains("not-a-real-secret"));
    let (_, book) = request(
        &router,
        "POST",
        "/api/notebooks",
        Some(json!({"title":"Routing"})),
        true,
    )
    .await;
    let notebook = format!("/api/notebooks/{}", book["id"].as_str().unwrap());
    let (_, source) = request(
        &router,
        "POST",
        &format!("{notebook}/sources"),
        Some(json!({"title":"Facts","content":"Rust is a programming language."})),
        true,
    )
    .await;
    let (status, answer) = request(
        &router,
        "POST",
        &format!("{notebook}/chat"),
        Some(json!({"question":"What is Rust?","source_ids":[source["id"]]})),
        true,
    )
    .await;
    assert_eq!(status, StatusCode::OK, "{answer}");
    assert_eq!(&*called.lock().await, "specific-chat-model");
    let mut preserve = payload.clone();
    preserve["providers"][0]
        .as_object_mut()
        .unwrap()
        .remove("api_key");
    assert_eq!(
        request(&router, "PUT", "/api/ai", Some(preserve.clone()), true)
            .await
            .1["providers"][0]["key_set"],
        true
    );
    preserve["providers"][0]["clear_key"] = json!(true);
    assert_eq!(
        request(&router, "PUT", "/api/ai", Some(preserve), true)
            .await
            .1["providers"][0]["key_set"],
        false
    );
    let mut invalid = payload;
    invalid["assignments"]["quiz"] = json!("unknown-provider");
    assert_eq!(
        request(&router, "PUT", "/api/ai", Some(invalid), true)
            .await
            .0,
        StatusCode::BAD_REQUEST
    );
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        assert_eq!(
            std::fs::metadata(path.with_extension("ai.json"))
                .unwrap()
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
    }
    std::fs::remove_file(path.with_extension("ai.json")).unwrap();
    std::fs::remove_file(path).unwrap();
    server.abort();
}

#[tokio::test]
async fn gemini_discovery_and_connection_use_native_schema_and_redact_errors() {
    use axum::http::HeaderMap;
    let mock=Router::new()
      .route("/v1beta/models",axum::routing::get(|h:HeaderMap|async move{assert_eq!(h["x-goog-api-key"],"secret-for-test");Json(json!({"models":[{"name":"models/available-flash","supportedGenerationMethods":["generateContent"]},{"name":"models/embed-only","supportedGenerationMethods":["embedContent"]}]}))}))
      .route("/v1beta/models/{model}",post(|axum::extract::Path(model):axum::extract::Path<String>,h:HeaderMap,Json(p):Json<Value>|async move{
          assert_eq!(h["x-goog-api-key"],"secret-for-test");
          if model=="bad:generateContent" {return (StatusCode::BAD_REQUEST,Json(json!({"error":{"message":"Invalid model. Credential secret-for-test key=AIzaExampleMustNotLeak"}})));}
          assert_eq!(model,"available-flash:generateContent");assert!(p.get("messages").is_none());assert_eq!(p["contents"][0]["role"],"user");assert_eq!(p["contents"][0]["parts"][0]["text"],"Reply with OK.");assert_eq!(p["systemInstruction"]["parts"][0]["text"],"Connection check. Reply briefly.");
          (StatusCode::OK,Json(json!({"candidates":[{"content":{"parts":[{"text":"private thinking","thought":true},{"text":"OK"}]}}]})))
      }));
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let base = format!("http://{}/v1beta", listener.local_addr().unwrap());
    let server = tokio::spawn(async move { axum::serve(listener, mock).await.unwrap() });
    let (_, router, path) = setup(base.clone()).await;
    let mut p = json!({"id":uuid::Uuid::new_v4().to_string(),"name":"Gemini","kind":"gemini","base_url":base,"model":"models/available-flash","api_key":"secret-for-test"});
    assert_eq!(
        request(&router, "POST", "/api/ai/test", Some(p.clone()), false)
            .await
            .0,
        StatusCode::UNAUTHORIZED
    );
    let (status, models) = request(&router, "POST", "/api/ai/models", Some(p.clone()), true).await;
    assert_eq!(status, StatusCode::OK, "{models}");
    assert_eq!(models["models"], json!(["available-flash"]));
    let (status, test) = request(&router, "POST", "/api/ai/test", Some(p.clone()), true).await;
    assert_eq!(status, StatusCode::OK, "{test}");
    assert_eq!(test["ok"], true);
    assert!(!test.to_string().contains("private thinking"));
    p["model"] = json!("bad");
    let (status, error) = request(&router, "POST", "/api/ai/test", Some(p), true).await;
    assert_eq!(status, StatusCode::BAD_GATEWAY);
    assert!(error["error"].as_str().unwrap().contains("Invalid model"));
    assert!(!error.to_string().contains("secret-for-test"));
    assert!(!error.to_string().contains("AIzaExample"));
    assert_eq!(
        request(&router, "GET", "/api/ai", None, true).await.1["providers"],
        json!([]),
        "Tests must not silently save configuration"
    );
    if path.exists() {
        std::fs::remove_file(path).unwrap();
    }
    server.abort();
}
