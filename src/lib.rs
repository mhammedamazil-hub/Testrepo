mod ai;
#[cfg(all(feature = "android-offline", target_os = "android"))]
mod android_offline;
mod discovery;
mod nie;
mod studio;
mod video;
use axum::{
    extract::{DefaultBodyLimit, Path, State},
    http::{HeaderMap, StatusCode},
    response::{Html, IntoResponse, Response},
    routing::{delete, get, post},
    Json, Router,
};
use base64::Engine;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{collections::HashSet, net::IpAddr, path::PathBuf, sync::Arc, time::Duration};
pub use studio::MediaConfig;
use tokio::sync::RwLock;
use uuid::Uuid;

pub const MAX_TEXT: usize = 2_000_000;
fn id() -> String {
    Uuid::new_v4().to_string()
}
fn now() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Source {
    #[serde(default)]
    pub frames: Vec<video::Frame>,
    pub id: String,
    pub title: String,
    pub content: String,
    pub kind: String,
    pub url: Option<String>,
    pub created: u64,
}
#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Evidence {
    pub number: usize,
    pub source_id: String,
    pub title: String,
    pub excerpt: String,
}
#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Message {
    pub id: String,
    pub role: String,
    pub content: String,
    pub evidence: Vec<Evidence>,
    pub created: u64,
}
#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Note {
    pub id: String,
    pub title: String,
    pub content: String,
    pub created: u64,
}
#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Artifact {
    #[serde(default)]
    pub data: Option<Value>,
    #[serde(default)]
    pub progress: Value,
    #[serde(default)]
    pub media: bool,
    pub id: String,
    pub kind: String,
    pub title: String,
    pub content: String,
    pub evidence: Vec<Evidence>,
    pub created: u64,
}
#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Notebook {
    #[serde(default)]
    pub share_token: Option<String>,
    pub id: String,
    pub title: String,
    pub description: String,
    pub sources: Vec<Source>,
    pub messages: Vec<Message>,
    pub notes: Vec<Note>,
    pub artifacts: Vec<Artifact>,
    pub created: u64,
    pub updated: u64,
}
impl Notebook {
    pub fn new(title: String) -> Self {
        Self {
            share_token: None,
            id: id(),
            title,
            description: String::new(),
            sources: vec![],
            messages: vec![],
            notes: vec![],
            artifacts: vec![],
            created: now(),
            updated: now(),
        }
    }
}
#[derive(Clone, Serialize, Deserialize, Default)]
pub struct Database {
    pub notebooks: Vec<Notebook>,
}
#[derive(Clone)]
pub struct Config {
    pub data: PathBuf,
    pub token: String,
    pub base_url: String,
    pub model: String,
    pub api_key: String,
}
#[derive(Clone)]
pub struct App {
    pub ai: Arc<RwLock<ai::Settings>>,
    pub offline: bool,
    pub db: Arc<RwLock<Database>>,
    pub config: Config,
    pub client: reqwest::Client,
    pub ai_slots: Arc<tokio::sync::Semaphore>,
    pub media: Arc<MediaConfig>,
}
#[derive(Debug)]
pub struct Error(pub StatusCode, pub String);
impl IntoResponse for Error {
    fn into_response(self) -> Response {
        (self.0, Json(json!({"error":self.1}))).into_response()
    }
}
type Result<T> = std::result::Result<T, Error>;
fn bad(s: impl Into<String>) -> Error {
    Error(StatusCode::BAD_REQUEST, s.into())
}
fn missing() -> Error {
    Error(StatusCode::NOT_FOUND, "Notebook or item not found".into())
}
fn internal(e: impl std::fmt::Display) -> Error {
    eprintln!("Storage/runtime error: {e}");
    Error(
        StatusCode::INTERNAL_SERVER_ERROR,
        "Storage or runtime operation failed".into(),
    )
}
fn authorized(headers: &HeaderMap, app: &App) -> Result<()> {
    let received = headers
        .get("authorization")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    // Fixed-work byte comparison avoids early-exit comparisons of the secret.
    let wanted = format!("Bearer {}", app.config.token);
    let mut diff = received.len() ^ wanted.len();
    for (i, b) in wanted.bytes().enumerate() {
        diff |= (b ^ received.as_bytes().get(i).copied().unwrap_or(0)) as usize;
    }
    if diff != 0 {
        return Err(Error(
            StatusCode::UNAUTHORIZED,
            "Enter the server access token to continue".into(),
        ));
    }
    Ok(())
}
impl App {
    pub async fn open(config: Config) -> std::result::Result<Self, Box<dyn std::error::Error>> {
        if config.token.len() < 16 {
            return Err("SOURCEBOOK_TOKEN must contain at least 16 characters".into());
        }
        let db = match tokio::fs::read(&config.data).await {
            Ok(b) => serde_json::from_slice(&b)?,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Database::default(),
            Err(e) => return Err(e.into()),
        };
        let client = reqwest::Client::builder()
            .redirect(reqwest::redirect::Policy::none())
            .timeout(Duration::from_secs(120))
            .build()?;
        let ai_path = config.data.with_extension("ai.json");
        let settings = match tokio::fs::read(ai_path).await {
            Ok(bytes) => serde_json::from_slice(&bytes)?,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => ai::Settings::default(),
            Err(e) => return Err(e.into()),
        };
        Ok(Self {
            ai: Arc::new(RwLock::new(settings)),
            offline: cfg!(all(feature = "android-offline", target_os = "android")),
            db: Arc::new(RwLock::new(db)),
            config,
            client,
            ai_slots: Arc::new(tokio::sync::Semaphore::new(2)),
            media: Arc::new(MediaConfig::from_env()),
        })
    }
    async fn mutate<T>(&self, f: impl FnOnce(&mut Database) -> Result<T>) -> Result<T> {
        let mut guard = self.db.write().await;
        let mut candidate = guard.clone();
        let result = f(&mut candidate)?;
        let bytes = serde_json::to_vec(&candidate).map_err(internal)?;
        if let Some(parent) = self
            .config
            .data
            .parent()
            .filter(|p| !p.as_os_str().is_empty())
        {
            tokio::fs::create_dir_all(parent).await.map_err(internal)?;
        }
        let tmp = self.config.data.with_extension("json.tmp");
        let mut options = tokio::fs::OpenOptions::new();
        options.write(true).create(true).truncate(true);
        #[cfg(unix)]
        options.mode(0o600);
        let mut file = options.open(&tmp).await.map_err(internal)?;
        use tokio::io::AsyncWriteExt;
        file.write_all(&bytes).await.map_err(internal)?;
        file.sync_all().await.map_err(internal)?;
        drop(file);
        tokio::fs::rename(&tmp, &self.config.data)
            .await
            .map_err(internal)?;
        *guard = candidate;
        Ok(result)
    }
    async fn notebook(&self, nid: &str) -> Result<Notebook> {
        self.db
            .read()
            .await
            .notebooks
            .iter()
            .find(|n| n.id == nid)
            .cloned()
            .ok_or_else(missing)
    }
}
fn notebook_mut<'a>(db: &'a mut Database, nid: &str) -> Result<&'a mut Notebook> {
    db.notebooks
        .iter_mut()
        .find(|n| n.id == nid)
        .ok_or_else(missing)
}
fn text(value: &str, name: &str, max: usize) -> Result<String> {
    let s = value.trim();
    if s.is_empty() || s.len() > max {
        return Err(bad(format!("{name} must contain 1–{max} bytes")));
    }
    Ok(s.into())
}

pub fn router(app: App) -> Router {
    Router::new()
        .route(
            "/",
            get(|| async { Html(include_str!("../web/index.html")) }),
        )
        .route(
            "/app.js",
            get(|| async {
                (
                    [("content-type", "text/javascript; charset=utf-8")],
                    include_str!("../web/app.js"),
                )
            }),
        )
        .route(
            "/offline.js",
            get(|| async {
                (
                    [("content-type", "text/javascript; charset=utf-8")],
                    include_str!("../web/offline.js"),
                )
            }),
        )
        .route(
            "/style.css",
            get(|| async {
                (
                    [("content-type", "text/css; charset=utf-8")],
                    include_str!("../web/style.css"),
                )
            }),
        )
        .route(
            "/health",
            get(|| async { Json(json!({"status":"ok","version":env!("CARGO_PKG_VERSION")})) }),
        )
        .route("/api/config", get(config))
        .route("/api/ai", get(ai::get).put(ai::save))
        .route("/api/ai/test", post(ai::test_connection))
        .route("/api/ai/models", post(ai::models))
        .route("/api/notebooks/{id}/video", post(video::ingest))
        .route(
            "/api/notebooks/{id}/video-frames",
            post(video::ingest_frames),
        )
        .route(
            "/api/notebooks/{id}/recommendations",
            get(discovery::recommendations),
        )
        .route("/api/share/{token}", get(studio::shared))
        .route("/api/share/{token}/media/{item}", get(studio::shared_media))
        .route(
            "/api/notebooks/{id}/share",
            post(studio::enable_share).delete(studio::disable_share),
        )
        .route("/api/notebooks", get(list).post(create))
        .route("/api/notebooks/import", post(studio::restore))
        .route("/api/notebooks/{id}/transcribe", post(studio::transcribe))
        .route(
            "/api/notebooks/{id}/sources/{item}/guide",
            post(studio::source_guide),
        )
        .route(
            "/api/notebooks/{id}/artifacts/{item}/review",
            post(studio::review),
        )
        .route(
            "/api/notebooks/{id}/artifacts/{item}/media",
            get(studio::media_file),
        )
        .route(
            "/api/notebooks/{id}/artifacts/{item}/download",
            get(studio::download),
        )
        .route(
            "/api/notebooks/{id}",
            get(read).patch(rename).delete(remove),
        )
        .route("/api/notebooks/{id}/export", get(export))
        .route("/api/notebooks/{id}/sources", post(add_source))
        .route(
            "/api/notebooks/{id}/sources/{item}",
            delete(remove_source).patch(studio::edit_source),
        )
        .route("/api/notebooks/{id}/chat", post(chat).delete(clear_chat))
        .route("/api/notebooks/{id}/notes", post(add_note))
        .route(
            "/api/notebooks/{id}/notes/{item}",
            delete(remove_note).patch(studio::edit_note),
        )
        .route("/api/notebooks/{id}/generate", post(generate))
        .route(
            "/api/notebooks/{id}/artifacts/{item}",
            delete(remove_artifact),
        )
        .layer(axum::middleware::from_fn(
            |request: axum::extract::Request, next: axum::middleware::Next| async move {
                let mut response = next.run(request).await;
                response.headers_mut().insert(
                    "cache-control",
                    axum::http::HeaderValue::from_static("no-store"),
                );
                response.headers_mut().insert(
                    "referrer-policy",
                    axum::http::HeaderValue::from_static("no-referrer"),
                );
                response.headers_mut().insert(
                    "x-content-type-options",
                    axum::http::HeaderValue::from_static("nosniff"),
                );
                response
            },
        ))
        .layer(DefaultBodyLimit::max(16 * 1024 * 1024))
        .with_state(app)
}
async fn config(State(a): State<App>, h: HeaderMap) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    let active = ai::resolve(&a, "chat").await;
    let configured = !active.model.is_empty();
    #[cfg(all(feature = "android-offline", target_os = "android"))]
    let configured = configured && (active.kind != "native" || android_offline::model_loaded());
    Ok(Json(
        json!({"model":active.model,"configured":configured,"standalone":cfg!(all(feature="android-offline",target_os="android")),"offline":a.offline,"api_key_set":!active.api_key.is_empty(),"formats":["text","markdown","pdf","url","docx"],"generators":KINDS,"audio_configured":ai::media_provider(&a,"speech").await.is_ok(),"transcription_configured":ai::media_provider(&a,"transcription").await.is_ok()}),
    ))
}
async fn list(State(a): State<App>, h: HeaderMap) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    let db = a.db.read().await;
    Ok(Json(json!(db.notebooks.iter().map(|n|json!({"id":n.id,"title":n.title,"description":n.description,"created":n.created,"updated":n.updated,"source_count":n.sources.len(),"note_count":n.notes.len()})).collect::<Vec<_>>())))
}
#[derive(Deserialize)]
struct Title {
    title: String,
    #[serde(default)]
    description: String,
}
async fn create(
    State(a): State<App>,
    h: HeaderMap,
    Json(p): Json<Title>,
) -> Result<Json<Notebook>> {
    authorized(&h, &a)?;
    let mut n = Notebook::new(text(&p.title, "Title", 200)?);
    n.description = p.description.chars().take(2000).collect();
    let result = a
        .mutate(|d| {
            d.notebooks.push(n.clone());
            Ok(n)
        })
        .await?;
    Ok(Json(result))
}
async fn read(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
) -> Result<Json<Notebook>> {
    authorized(&h, &a)?;
    Ok(Json(a.notebook(&nid).await?))
}
async fn rename(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
    Json(p): Json<Title>,
) -> Result<Json<Notebook>> {
    authorized(&h, &a)?;
    let title = text(&p.title, "Title", 200)?;
    Ok(Json(
        a.mutate(|d| {
            let n = notebook_mut(d, &nid)?;
            n.title = title;
            n.description = p.description.chars().take(2000).collect();
            n.updated = now();
            Ok(n.clone())
        })
        .await?,
    ))
}
async fn remove(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    let old = a.notebook(&nid).await?;
    a.mutate(|d| {
        let i = d
            .notebooks
            .iter()
            .position(|n| n.id == nid)
            .ok_or_else(missing)?;
        d.notebooks.remove(i);
        Ok(())
    })
    .await?;
    for item in old.artifacts.iter().filter(|i| i.media) {
        studio::cleanup_media(&a, &nid, &item.id).await;
    }
    Ok(Json(json!({"deleted":true})))
}
async fn export(State(a): State<App>, h: HeaderMap, Path(nid): Path<String>) -> Result<Response> {
    authorized(&h, &a)?;
    let n = a.notebook(&nid).await?;
    Ok((
        [
            ("content-type", "application/json"),
            ("content-disposition", "attachment; filename=notebook.json"),
        ],
        Json(n),
    )
        .into_response())
}

#[derive(Deserialize)]
struct SourceInput {
    title: String,
    #[serde(default)]
    content: String,
    #[serde(default = "default_kind")]
    kind: String,
    url: Option<String>,
}
fn default_kind() -> String {
    "text".into()
}
pub fn public_ip(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(v) => {
            let o = v.octets();
            !(v.is_loopback()
                || v.is_private()
                || v.is_link_local()
                || v.is_multicast()
                || v.is_unspecified()
                || v.is_broadcast()
                || o[0] == 0
                || o[0] >= 224
                || (o[0] == 100 && (64..=127).contains(&o[1]))
                || (o[0] == 192 && o[1] == 0)
                || (o[0] == 198 && (o[1] == 18 || o[1] == 19)))
        }
        IpAddr::V6(v) => {
            let s = v.segments();
            !v.is_loopback()
                && !v.is_unspecified()
                && ((s[0] & 0xe000) == 0x2000)
                && !(s[0] == 0x2001 && (s[1] == 0 || s[1] == 2 || s[1] == 0xdb8))
        }
    }
}
async fn import_url(raw: &str) -> Result<String> {
    let url = reqwest::Url::parse(raw).map_err(|_| bad("Invalid URL"))?;
    if !["http", "https"].contains(&url.scheme())
        || !url.username().is_empty()
        || url.password().is_some()
    {
        return Err(bad(
            "Only public HTTP(S) URLs without credentials are allowed",
        ));
    }
    let host = url.host_str().ok_or_else(|| bad("Missing host"))?;
    let port = url
        .port_or_known_default()
        .ok_or_else(|| bad("Missing port"))?;
    if port != 80 && port != 443 {
        return Err(bad("URL imports allow only ports 80 and 443"));
    }
    let addresses: Vec<_> = tokio::net::lookup_host((host, port))
        .await
        .map_err(|_| bad("Could not resolve URL host"))?
        .collect();
    if addresses.is_empty() || addresses.iter().any(|s| !public_ip(s.ip())) {
        return Err(bad(
            "Private, local and reserved network destinations are blocked",
        ));
    }
    // Pin validated DNS results; no proxy or redirects to avoid SSRF/rebinding.
    let client = reqwest::Client::builder()
        .no_proxy()
        .resolve_to_addrs(host, &addresses)
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(internal)?;
    let mut response = client
        .get(url)
        .header(
            "User-Agent",
            "Sourcebook/0.1 (user-requested source import)",
        )
        .send()
        .await
        .map_err(|_| bad("Could not fetch URL; check network policy"))?;
    if !response.status().is_success() {
        return Err(bad(format!("Source returned HTTP {}; redirects are not followed. Paste the final public URL or source text.",response.status())));
    }
    let ct = response
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();
    if !ct.starts_with("text/") && !ct.contains("json") {
        return Err(bad(
            "URL must return text or HTML. Upload PDF files directly.",
        ));
    }
    let mut bytes = Vec::new();
    while let Some(chunk) = response
        .chunk()
        .await
        .map_err(|_| bad("Failed reading URL"))?
    {
        if bytes.len() + chunk.len() > MAX_TEXT {
            return Err(bad("URL response exceeds 2 MB"));
        }
        bytes.extend_from_slice(&chunk);
    }
    let raw = String::from_utf8_lossy(&bytes);
    if ct.contains("html") {
        let html = scraper::Html::parse_document(&raw);
        let selector = scraper::Selector::parse("body").map_err(internal)?;
        let mut parts = Vec::new();
        for body in html.select(&selector) {
            for node in body.descendants() {
                if let Some(t) = node.value().as_text() {
                    if !node.ancestors().any(|p| {
                        p.value()
                            .as_element()
                            .map(|e| {
                                matches!(
                                    e.name(),
                                    "script" | "style" | "noscript" | "nav" | "footer"
                                )
                            })
                            .unwrap_or(false)
                    }) {
                        parts.push(t.to_string());
                    }
                }
            }
        }
        Ok(parts
            .join(" ")
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" "))
    } else {
        Ok(raw.into_owned())
    }
}
async fn add_source(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
    Json(p): Json<SourceInput>,
) -> Result<Json<Source>> {
    authorized(&h, &a)?;
    if a.offline && p.kind == "url" {
        return Err(bad(
            "Webpage import needs a network. Paste or upload the article text in this offline app.",
        ));
    }
    a.notebook(&nid).await?;
    let title = text(&p.title, "Source title", 300)?;
    let content = match p.kind.as_str() {
        "docx" => studio::docx(&p.content)?,
        "text" | "markdown" => p.content,
        "url" => import_url(p.url.as_deref().ok_or_else(|| bad("URL is required"))?).await?,
        "pdf" => {
            let bytes = base64::engine::general_purpose::STANDARD
                .decode(&p.content)
                .map_err(|_| bad("PDF content must be base64"))?;
            if bytes.len() > 10 * 1024 * 1024 {
                return Err(bad("PDF exceeds 10 MB"));
            }
            if !bytes.starts_with(b"%PDF-") {
                return Err(bad("Not a PDF file"));
            }
            let _slot = a.ai_slots.try_acquire().map_err(|_| {
                Error(
                    StatusCode::TOO_MANY_REQUESTS,
                    "Server busy; retry shortly".into(),
                )
            })?;
            tokio::task::spawn_blocking(move||pdf_extract::extract_text_from_mem(&bytes)).await.map_err(internal)?.map_err(|_|bad("Could not extract PDF text; encrypted and scanned PDFs need conversion/OCR first"))?
        }
        _ => return Err(bad("Supported kinds: text, markdown, pdf, url")),
    };
    let content = text(&content, "Extracted source text", MAX_TEXT)?;
    let source = Source {
        frames: vec![],
        id: id(),
        title,
        content,
        kind: p.kind,
        url: p.url,
        created: now(),
    };
    Ok(Json(
        a.mutate(|db| {
            let n = notebook_mut(db, &nid)?;
            if n.sources.len() >= 100 {
                return Err(bad("Limit: 100 sources per notebook"));
            }
            n.sources.push(source.clone());
            n.updated = now();
            Ok(source)
        })
        .await?,
    ))
}
async fn remove_source(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, sid)): Path<(String, String)>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    a.mutate(|d| {
        let n = notebook_mut(d, &nid)?;
        let i = n
            .sources
            .iter()
            .position(|s| s.id == sid)
            .ok_or_else(missing)?;
        n.sources.remove(i);
        n.updated = now();
        Ok(())
    })
    .await?;
    Ok(Json(json!({"deleted":true})))
}

pub fn chunks(content: &str) -> Vec<String> {
    let chars: Vec<char> = content.chars().collect();
    let mut result = vec![];
    let mut i = 0;
    while i < chars.len() {
        let end = (i + 1200).min(chars.len());
        result.push(chars[i..end].iter().collect());
        if end == chars.len() {
            break;
        }
        i = end - 150;
    }
    result
}
fn tokens(s: &str) -> HashSet<String> {
    s.split(|c: char| !c.is_alphanumeric())
        .filter(|s| s.chars().count() > 1)
        .map(str::to_lowercase)
        .collect()
}
pub fn retrieve(n: &Notebook, query: &str, selected: &[String], overview: bool) -> Vec<Evidence> {
    let q = tokens(query);
    let sources: Vec<_> = n
        .sources
        .iter()
        .filter(|s| selected.is_empty() || selected.contains(&s.id))
        .collect();
    let mut ranked = Vec::new();
    for s in &sources {
        for (index, chunk) in chunks(&s.content).into_iter().enumerate() {
            let terms = tokens(&chunk);
            let score = q.intersection(&terms).count() as f64 / (terms.len().max(1) as f64).sqrt();
            ranked.push((score, index, s, chunk));
        }
    }
    ranked.sort_by(|a, b| b.0.total_cmp(&a.0).then(a.1.cmp(&b.1)));
    let mut picked = Vec::new();
    let mut seen = HashSet::new();
    // Overview coverage: one excerpt per selected source before relevance fill.
    if overview {
        for s in sources.iter().take(12) {
            if let Some((_, idx, _, chunk)) =
                ranked.iter().find(|(_, _, source, _)| source.id == s.id)
            {
                seen.insert((s.id.clone(), *idx));
                picked.push(Evidence {
                    number: picked.len() + 1,
                    source_id: s.id.clone(),
                    title: s.title.clone(),
                    excerpt: chunk.clone(),
                });
            }
        }
    }
    for (_, idx, s, chunk) in ranked {
        if picked.len() >= 12 {
            break;
        }
        if seen.insert((s.id.clone(), idx)) {
            picked.push(Evidence {
                number: picked.len() + 1,
                source_id: s.id.clone(),
                title: s.title.clone(),
                excerpt: chunk,
            });
        }
    }
    picked
}
async fn complete(
    a: &App,
    n: &Notebook,
    instruction: &str,
    evidence: &[Evidence],
    history: bool,
) -> Result<String> {
    complete_for(
        a,
        n,
        instruction,
        evidence,
        history,
        if history { "chat" } else { "source-guide" },
    )
    .await
}
async fn complete_for(
    a: &App,
    n: &Notebook,
    instruction: &str,
    evidence: &[Evidence],
    history: bool,
    task: &str,
) -> Result<String> {
    let provider = ai::resolve(a, task).await;
    if provider.model.is_empty() {
        return Err(bad("Add an AI provider and choose a default in Settings."));
    }
    let local = provider.kind == "native";
    let _permit = a.ai_slots.try_acquire().map_err(|_| {
        Error(
            StatusCode::TOO_MANY_REQUESTS,
            "Two jobs are already running; try again shortly".into(),
        )
    })?;
    let context = evidence
        .iter()
        .take(if local { 4 } else { 12 })
        .map(|e| {
            format!(
                "[{}] {}\n{}",
                e.number,
                e.title,
                e.excerpt
                    .chars()
                    .take(if local { 700 } else { 1200 })
                    .collect::<String>()
            )
        })
        .collect::<Vec<_>>()
        .join("\n\n");
    let mut messages = vec![json!({"role":"system","content":nie::system(n,&context,local)})];
    if history {
        for m in n
            .messages
            .iter()
            .rev()
            .take(if local { 2 } else { 8 })
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
        {
            messages.push(
                json!({"role":m.role,"content":m.content.chars().take(if local {700} else {8000}).collect::<String>()}),
            );
        }
    }
    messages.push(json!({"role":"user","content":instruction}));
    ai::request(a, &provider, messages).await
}
#[derive(Deserialize)]
struct ChatInput {
    question: String,
    #[serde(default)]
    source_ids: Vec<String>,
}
fn validate_selection(n: &Notebook, ids: &[String]) -> Result<()> {
    if ids.iter().any(|id| !n.sources.iter().any(|s| &s.id == id)) {
        return Err(bad("Selected source does not belong to this notebook"));
    }
    Ok(())
}
async fn chat(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
    Json(p): Json<ChatInput>,
) -> Result<Json<Message>> {
    authorized(&h, &a)?;
    let question = text(&p.question, "Question", 12000)?;
    let n = a.notebook(&nid).await?;
    validate_selection(&n, &p.source_ids)?;
    let evidence = retrieve(&n, &question, &p.source_ids, false);
    if evidence.is_empty() {
        return Err(bad("Add at least one source before asking a question"));
    }
    let answer = complete(&a, &n, &question, &evidence, true).await?;
    let assistant = Message {
        id: id(),
        role: "assistant".into(),
        content: answer,
        evidence,
        created: now(),
    };
    a.mutate(|db| {
        let current = notebook_mut(db, &nid)?;
        if current.messages.len() != n.messages.len()
            || current.messages.last().map(|m| &m.id) != n.messages.last().map(|m| &m.id)
        {
            return Err(Error(
                StatusCode::CONFLICT,
                "Conversation changed during generation; retry".into(),
            ));
        }
        if current
            .sources
            .iter()
            .map(|s| (&s.id, &s.content))
            .collect::<Vec<_>>()
            != n.sources
                .iter()
                .map(|s| (&s.id, &s.content))
                .collect::<Vec<_>>()
        {
            return Err(Error(
                StatusCode::CONFLICT,
                "Sources changed during generation; retry".into(),
            ));
        }
        current.messages.push(Message {
            id: id(),
            role: "user".into(),
            content: question,
            evidence: vec![],
            created: now(),
        });
        current.messages.push(assistant.clone());
        current.updated = now();
        Ok(())
    })
    .await?;
    Ok(Json(assistant))
}
async fn clear_chat(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    a.mutate(|d| {
        let n = notebook_mut(d, &nid)?;
        n.messages.clear();
        n.updated = now();
        Ok(())
    })
    .await?;
    Ok(Json(json!({"deleted":true})))
}
#[derive(Deserialize)]
struct NoteInput {
    title: String,
    content: String,
}
async fn add_note(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
    Json(p): Json<NoteInput>,
) -> Result<Json<Note>> {
    authorized(&h, &a)?;
    let note = Note {
        id: id(),
        title: text(&p.title, "Note title", 300)?,
        content: text(&p.content, "Note", MAX_TEXT)?,
        created: now(),
    };
    Ok(Json(
        a.mutate(|d| {
            let n = notebook_mut(d, &nid)?;
            n.notes.push(note.clone());
            n.updated = now();
            Ok(note)
        })
        .await?,
    ))
}
async fn remove_note(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, item)): Path<(String, String)>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    a.mutate(|d| {
        let n = notebook_mut(d, &nid)?;
        let i = n
            .notes
            .iter()
            .position(|s| s.id == item)
            .ok_or_else(missing)?;
        n.notes.remove(i);
        n.updated = now();
        Ok(())
    })
    .await?;
    Ok(Json(json!({"deleted":true})))
}
pub const KINDS: &[&str] = &[
    "summary",
    "study-guide",
    "faq",
    "briefing",
    "timeline",
    "flashcards",
    "quiz",
    "mind-map",
    "data-table",
    "podcast-script",
    "slide-outline",
    "slides",
    "audio-overview",
    "motion-graphic",
];
#[derive(Deserialize)]
struct GenerateInput {
    kind: String,
    #[serde(default)]
    instructions: String,
    #[serde(default)]
    source_ids: Vec<String>,
}
async fn generate(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
    Json(p): Json<GenerateInput>,
) -> Result<Json<Artifact>> {
    authorized(&h, &a)?;
    if !KINDS.contains(&p.kind.as_str()) {
        return Err(bad("Unsupported generation type"));
    }
    if p.instructions.len() > 4000 {
        return Err(bad("Instructions exceed 4000 bytes"));
    }
    let n = a.notebook(&nid).await?;
    validate_selection(&n, &p.source_ids)?;
    let evidence = retrieve(&n, &p.instructions, &p.source_ids, true);
    if evidence.is_empty() {
        return Err(bad("Add sources before generating"));
    }
    let (content, data) = studio::generate_content(&a, &n, &p, &evidence).await?;
    let mut item = Artifact {
        id: id(),
        kind: p.kind.clone(),
        title: p.kind.replace('-', " "),
        content,
        evidence,
        created: now(),
        data,
        progress: Value::Null,
        media: false,
    };
    if p.kind == "audio-overview" {
        studio::synthesize(&a, &nid, &mut item).await?;
    }
    let media_id = item.id.clone();
    let has_media = item.media;
    let result = a
        .mutate(|d| {
            let current = notebook_mut(d, &nid)?;
            if current
                .sources
                .iter()
                .map(|s| (&s.id, &s.content))
                .collect::<Vec<_>>()
                != n.sources
                    .iter()
                    .map(|s| (&s.id, &s.content))
                    .collect::<Vec<_>>()
            {
                return Err(Error(
                    StatusCode::CONFLICT,
                    "Sources changed during generation; retry".into(),
                ));
            }
            current.artifacts.push(item.clone());
            current.updated = now();
            Ok(item)
        })
        .await;
    if result.is_err() && has_media {
        studio::cleanup_media(&a, &nid, &media_id).await;
    }
    result.map(Json)
}
async fn remove_artifact(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, item)): Path<(String, String)>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    a.mutate(|d| {
        let n = notebook_mut(d, &nid)?;
        let i = n
            .artifacts
            .iter()
            .position(|s| s.id == item)
            .ok_or_else(missing)?;
        n.artifacts.remove(i);
        n.updated = now();
        Ok(())
    })
    .await?;
    studio::cleanup_media(&a, &nid, &item).await;
    Ok(Json(json!({"deleted":true})))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unicode_chunking() {
        let s = "കേരളം🦀".repeat(600);
        let c = chunks(&s);
        assert!(c.len() > 1);
        assert!(c.iter().all(|s| s.chars().count() <= 1200));
        assert!(chunks("").is_empty());
    }
    #[test]
    fn network_boundaries() {
        for s in [
            "127.0.0.1",
            "10.0.0.1",
            "169.254.169.254",
            "100.64.0.1",
            "::1",
            "::ffff:127.0.0.1",
            "fd00::1",
            "224.0.0.1",
        ] {
            assert!(!public_ip(s.parse().unwrap()), "{s}");
        }
        assert!(public_ip("8.8.8.8".parse().unwrap()));
    }
    #[test]
    fn ranking_and_selection() {
        let mut n = Notebook::new("test".into());
        for (title, content) in [
            ("Plants", "Plants use sunlight for photosynthesis"),
            ("Space", "Stars are distant balls of plasma"),
        ] {
            n.sources.push(Source {
                frames: vec![],
                id: id(),
                title: title.into(),
                content: content.into(),
                kind: "text".into(),
                url: None,
                created: 0,
            });
        }
        let e = retrieve(&n, "sunlight photosynthesis", &[], false);
        assert_eq!(e[0].title, "Plants");
        let e = retrieve(&n, "sunlight", &[n.sources[1].id.clone()], false);
        assert_eq!(e.len(), 1);
        assert_eq!(e[0].title, "Space");
    }
}
