//! Typed study materials, restore, media and content editing. Provider calls stay in Rust.
use super::*;
use std::collections::HashMap;
use std::io::Read;

#[derive(Clone, Default)]
pub struct MediaConfig {
    pub tts_model: String,
    pub voice: String,
    pub transcription_model: String,
}
impl MediaConfig {
    pub fn from_env() -> Self {
        Self {
            tts_model: std::env::var("AI_TTS_MODEL").unwrap_or_default(),
            voice: std::env::var("AI_TTS_VOICE").unwrap_or_else(|_| "alloy".into()),
            transcription_model: std::env::var("AI_TRANSCRIPTION_MODEL").unwrap_or_default(),
        }
    }
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Card {
    pub front: String,
    pub back: String,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Question {
    pub question: String,
    pub options: Vec<String>,
    pub answer: usize,
    pub explanation: String,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Branch {
    pub label: String,
    #[serde(default)]
    pub children: Vec<Branch>,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Slide {
    pub title: String,
    pub bullets: Vec<String>,
    #[serde(default)]
    pub notes: String,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum Material {
    Flashcards {
        cards: Vec<Card>,
    },
    Quiz {
        questions: Vec<Question>,
    },
    MindMap {
        root: Branch,
    },
    Slides {
        slides: Vec<Slide>,
    },
    DataTable {
        columns: Vec<String>,
        rows: Vec<Vec<String>>,
    },
}
fn bounded(s: &str) -> bool {
    !s.trim().is_empty() && s.len() <= 12000
}
fn tree_valid(b: &Branch, depth: usize, budget: &mut usize) -> bool {
    if depth > 5 || *budget == 0 || !bounded(&b.label) {
        return false;
    }
    *budget -= 1;
    b.children.iter().all(|c| tree_valid(c, depth + 1, budget))
}
impl Material {
    fn validate(&self) -> bool {
        match self {
            Self::Flashcards { cards } => {
                (1..=50).contains(&cards.len())
                    && cards.iter().all(|c| bounded(&c.front) && bounded(&c.back))
            }
            Self::Quiz { questions } => {
                (1..=30).contains(&questions.len())
                    && questions.iter().all(|q| {
                        bounded(&q.question)
                            && (2..=6).contains(&q.options.len())
                            && q.options.iter().all(|s| bounded(s))
                            && q.answer < q.options.len()
                            && bounded(&q.explanation)
                    })
            }
            Self::MindMap { root } => tree_valid(root, 0, &mut 120),
            Self::Slides { slides } => {
                (1..=30).contains(&slides.len())
                    && slides.iter().all(|s| {
                        bounded(&s.title)
                            && (1..=12).contains(&s.bullets.len())
                            && s.bullets.iter().all(|v| bounded(v))
                            && s.notes.len() <= 12000
                    })
            }
            Self::DataTable { columns, rows } => {
                (1..=15).contains(&columns.len())
                    && (1..=100).contains(&rows.len())
                    && columns.iter().all(|c| bounded(c))
                    && rows
                        .iter()
                        .all(|r| r.len() == columns.len() && r.iter().all(|s| s.len() <= 12000))
            }
        }
    }
    fn kind(&self) -> &'static str {
        match self {
            Self::Flashcards { .. } => "flashcards",
            Self::Quiz { .. } => "quiz",
            Self::MindMap { .. } => "mind-map",
            Self::Slides { .. } => "slides",
            Self::DataTable { .. } => "data-table",
        }
    }
    fn markdown(&self) -> String {
        match self {
            Self::Flashcards { cards } => cards
                .iter()
                .enumerate()
                .map(|(i, c)| {
                    format!(
                        "## Card {}\n\n{}\n\n**Answer:** {}\n",
                        i + 1,
                        c.front,
                        c.back
                    )
                })
                .collect::<Vec<_>>()
                .join("\n"),
            Self::Quiz { questions } => questions
                .iter()
                .enumerate()
                .map(|(i, q)| {
                    format!(
                        "## Question {}\n\n{}\n\n{}\n\n**Answer:** {}\n\n{}\n",
                        i + 1,
                        q.question,
                        q.options
                            .iter()
                            .enumerate()
                            .map(|(j, o)| format!("{}. {}", j + 1, o))
                            .collect::<Vec<_>>()
                            .join("\n"),
                        q.answer + 1,
                        q.explanation
                    )
                })
                .collect::<Vec<_>>()
                .join("\n"),
            Self::MindMap { root } => {
                fn walk(b: &Branch, d: usize, out: &mut String) {
                    out.push_str(&format!("{}- {}\n", "  ".repeat(d), b.label));
                    for c in &b.children {
                        walk(c, d + 1, out);
                    }
                }
                let mut s = String::new();
                walk(root, 0, &mut s);
                s
            }
            Self::Slides { slides } => slides
                .iter()
                .enumerate()
                .map(|(i, s)| {
                    format!(
                        "## Slide {}: {}\n\n{}\n\nSpeaker notes: {}\n",
                        i + 1,
                        s.title,
                        s.bullets
                            .iter()
                            .map(|b| format!("- {b}"))
                            .collect::<Vec<_>>()
                            .join("\n"),
                        s.notes
                    )
                })
                .collect::<Vec<_>>()
                .join("\n"),
            Self::DataTable { columns, rows } => {
                let safe = |r: &[String]| {
                    format!(
                        "| {} |",
                        r.iter()
                            .map(|s| s.replace('|', "\\|").replace('\n', " "))
                            .collect::<Vec<_>>()
                            .join(" | ")
                    )
                };
                format!(
                    "{}\n{}\n{}",
                    safe(columns),
                    safe(&vec!["---".into(); columns.len()]),
                    rows.iter().map(|r| safe(r)).collect::<Vec<_>>().join("\n")
                )
            }
        }
    }
}
pub(super) fn parse_material(raw: &str, kind: &str) -> Result<Material> {
    let raw = raw.trim();
    let raw = raw
        .strip_prefix("```json")
        .or_else(|| raw.strip_prefix("```"))
        .unwrap_or(raw);
    let raw = raw.trim().strip_suffix("```").unwrap_or(raw).trim();
    let m: Material = serde_json::from_str(raw).map_err(|_| {
        Error(
            StatusCode::BAD_GATEWAY,
            "Model returned invalid study JSON. Try a model with reliable structured output."
                .into(),
        )
    })?;
    if m.kind() != kind || !m.validate() {
        return Err(Error(
            StatusCode::BAD_GATEWAY,
            "Generated study material failed schema validation; nothing saved".into(),
        ));
    }
    Ok(m)
}
pub(super) async fn generate_content(
    a: &App,
    n: &Notebook,
    p: &GenerateInput,
    evidence: &[Evidence],
) -> Result<(String, Option<Value>)> {
    let schema = match p.kind.as_str() {
        "flashcards" => {
            Some(r#"{"type":"flashcards","cards":[{"front":"Question [1]","back":"Answer [1]"}]}"#)
        }
        "quiz" => Some(
            r#"{"type":"quiz","questions":[{"question":"Question [1]","options":["A","B","C","D"],"answer":0,"explanation":"Why A is right [1]"}]}"#,
        ),
        "mind-map" => Some(
            r#"{"type":"mind-map","root":{"label":"Topic","children":[{"label":"Subtopic [1]","children":[]}]}}"#,
        ),
        "slides" => Some(
            r#"{"type":"slides","slides":[{"title":"Title","bullets":["Point [1]"],"notes":"Speaker notes"}]}"#,
        ),
        "data-table" => Some(
            r#"{"type":"data-table","columns":["Topic","Evidence"],"rows":[["A","Fact [1]"]]}"#,
        ),
        _ => None,
    };
    let format = if let Some(s) = schema {
        format!("Return ONLY valid JSON in this exact schema (no Markdown fence): {s}. Use 8–12 cards/questions, 6–10 slides when appropriate. Quiz answer is a zero-based integer. Mind map maximum depth 5 and maximum 120 nodes. Table rows must match column count. Use concise text. Include source citation markers inside relevant strings.")
    } else if p.kind == "audio-overview" {
        if a.media.tts_model.is_empty() {
            return Err(bad(
                "Set AI_TTS_MODEL and optionally AI_TTS_VOICE to enable real audio generation",
            ));
        }
        "Write a conversational single-narrator audio overview, maximum 3000 characters. Plain speech without Markdown, stage directions or citation markers. Explain key ideas and mention source titles naturally. Never invent facts. This script will be synthesized into audio.".into()
    } else if p.kind == "podcast-script" {
        "Write a two-host podcast SCRIPT, clearly labeling speakers and source citations. This is a script, not audio.".into()
    } else {
        "Write structured Markdown with headings and citations. For slide-outline create a numbered text outline; do not claim a slide file exists.".into()
    };
    let prompt = format!(
        "Create a {} from the source excerpts. {} Additional preferences: {}",
        p.kind, format, p.instructions
    );
    let content = complete(a, n, &prompt, evidence, false).await?;
    if schema.is_some() {
        let data = parse_material(&content, &p.kind)?;
        Ok((
            data.markdown(),
            Some(serde_json::to_value(data).map_err(internal)?),
        ))
    } else {
        Ok((content, None))
    }
}

pub(super) fn docx(raw: &str) -> Result<String> {
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(raw)
        .map_err(|_| bad("DOCX must be base64"))?;
    if bytes.len() > 10 * 1024 * 1024 {
        return Err(bad("DOCX exceeds 10 MB"));
    }
    let mut zip = zip::ZipArchive::new(std::io::Cursor::new(bytes))
        .map_err(|_| bad("Invalid DOCX ZIP archive"))?;
    let entry = zip
        .by_name("word/document.xml")
        .map_err(|_| bad("DOCX is missing word/document.xml"))?;
    let mut xml = String::new();
    entry
        .take((MAX_TEXT + 1) as u64)
        .read_to_string(&mut xml)
        .map_err(|_| bad("Invalid DOCX XML"))?;
    if xml.len() > MAX_TEXT {
        return Err(bad("DOCX document XML exceeds 2 MB"));
    }
    let mut reader = quick_xml::Reader::from_str(&xml);
    let mut content = String::new();
    let mut in_text = false;
    loop {
        match reader.read_event() {
            Ok(quick_xml::events::Event::Start(e)) => {
                if e.name().as_ref() == b"w:t" {
                    in_text = true;
                }
            }
            Ok(quick_xml::events::Event::Text(e)) if in_text => {
                content.push_str(&e.unescape().map_err(|_| bad("Invalid XML escape"))?);
            }
            Ok(quick_xml::events::Event::End(e)) => {
                if e.name().as_ref() == b"w:t" {
                    in_text = false;
                }
                if e.name().as_ref() == b"w:p" {
                    content.push('\n');
                }
            }
            Ok(quick_xml::events::Event::Eof) => break,
            Err(_) => return Err(bad("Could not parse DOCX")),
            _ => {}
        }
    }
    text(&content, "DOCX text", MAX_TEXT)
}

pub(super) async fn edit_source(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, sid)): Path<(String, String)>,
    Json(p): Json<NoteInput>,
) -> Result<Json<Source>> {
    authorized(&h, &a)?;
    let title = text(&p.title, "Source title", 300)?;
    let content = text(&p.content, "Source text", MAX_TEXT)?;
    Ok(Json(
        a.mutate(|d| {
            let n = notebook_mut(d, &nid)?;
            let s = n
                .sources
                .iter_mut()
                .find(|s| s.id == sid)
                .ok_or_else(missing)?;
            s.title = title;
            s.content = content;
            n.updated = now();
            Ok(s.clone())
        })
        .await?,
    ))
}
pub(super) async fn edit_note(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, item)): Path<(String, String)>,
    Json(p): Json<NoteInput>,
) -> Result<Json<Note>> {
    authorized(&h, &a)?;
    let title = text(&p.title, "Note title", 300)?;
    let content = text(&p.content, "Note text", MAX_TEXT)?;
    Ok(Json(
        a.mutate(|d| {
            let n = notebook_mut(d, &nid)?;
            let note = n
                .notes
                .iter_mut()
                .find(|s| s.id == item)
                .ok_or_else(missing)?;
            note.title = title;
            note.content = content;
            n.updated = now();
            Ok(note.clone())
        })
        .await?,
    ))
}
pub(super) async fn restore(
    State(a): State<App>,
    h: HeaderMap,
    Json(mut n): Json<Notebook>,
) -> Result<Json<Notebook>> {
    authorized(&h, &a)?;
    n.title = text(&n.title, "Notebook title", 200)?;
    if n.sources.len() > 100
        || n.messages.len() > 2000
        || n.artifacts.len() > 500
        || n.notes.len() > 1000
    {
        return Err(bad("Notebook exceeds restore limits"));
    }
    let mut mapping = HashMap::new();
    for s in &mut n.sources {
        s.title = text(&s.title, "Source title", 300)?;
        s.content = text(&s.content, "Source content", MAX_TEXT)?;
        let new = id();
        mapping.insert(s.id.clone(), new.clone());
        s.id = new;
    }
    fn remap(e: &mut [Evidence], map: &HashMap<String, String>) {
        for x in e {
            x.source_id = map.get(&x.source_id).cloned().unwrap_or_default();
        }
    }
    for m in &mut n.messages {
        if !["user", "assistant"].contains(&m.role.as_str()) {
            return Err(bad("Invalid imported message role"));
        }
        m.content = text(&m.content, "Message", MAX_TEXT)?;
        m.id = id();
        remap(&mut m.evidence, &mapping);
    }
    for note in &mut n.notes {
        note.id = id();
        note.title = text(&note.title, "Note title", 300)?;
        note.content = text(&note.content, "Note", MAX_TEXT)?;
    }
    for art in &mut n.artifacts {
        art.id = id();
        art.title = text(&art.title, "Artifact title", 300)?;
        art.content = text(&art.content, "Artifact", MAX_TEXT)?;
        remap(&mut art.evidence, &mapping);
        if let Some(data) = &art.data {
            let parsed: Material = serde_json::from_value(data.clone())
                .map_err(|_| bad("Invalid imported structured artifact"))?;
            if !parsed.validate() {
                return Err(bad("Imported study data failed validation"));
            }
        }
        if art.media {
            art.content.push_str(
                "\n\n[Audio not included in JSON restore; keep the downloaded MP3 separately.]",
            );
        }
        art.media = false;
        art.progress = Value::Null;
    }
    n.id = id();
    n.share_token = None;
    n.updated = now();
    Ok(Json(
        a.mutate(|db| {
            db.notebooks.push(n.clone());
            Ok(n)
        })
        .await?,
    ))
}

#[derive(Deserialize)]
pub(super) struct ReviewInput {
    #[serde(default)]
    answers: Vec<usize>,
    card: Option<usize>,
    known: Option<bool>,
}
pub(super) async fn review(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, aid)): Path<(String, String)>,
    Json(p): Json<ReviewInput>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    Ok(Json(
        a.mutate(|d| {
            let n = notebook_mut(d, &nid)?;
            let art = n
                .artifacts
                .iter_mut()
                .find(|a| a.id == aid)
                .ok_or_else(missing)?;
            let m: Material = serde_json::from_value(
                art.data
                    .clone()
                    .ok_or_else(|| bad("This artifact is not interactive"))?,
            )
            .map_err(internal)?;
            let result = match m {
                Material::Quiz { questions } => {
                    if p.answers.len() != questions.len()
                        || p.answers
                            .iter()
                            .zip(&questions)
                            .any(|(i, q)| *i >= q.options.len())
                    {
                        return Err(bad("Provide one valid answer index per question"));
                    }
                    let marks: Vec<_> = p
                        .answers
                        .iter()
                        .zip(&questions)
                        .map(|(i, q)| *i == q.answer)
                        .collect();
                    let score = marks.iter().filter(|m| **m).count();
                    json!({"score":score,"total":questions.len(),"correct":marks,"reviewed":now()})
                }
                Material::Flashcards { cards } => {
                    let card = p.card.ok_or_else(|| bad("Card index is required"))?;
                    if card >= cards.len() {
                        return Err(bad("Invalid card index"));
                    }
                    let known = p.known.ok_or_else(|| bad("known boolean is required"))?;
                    let mut marks = art
                        .progress
                        .get("known")
                        .and_then(|v| v.as_array())
                        .filter(|v| v.len() == cards.len())
                        .cloned()
                        .unwrap_or_else(|| vec![Value::Bool(false); cards.len()]);
                    marks[card] = Value::Bool(known);
                    json!({"known":marks,"reviewed":now()})
                }
                _ => return Err(bad("Only quizzes and flashcards support review")),
            };
            art.progress = result.clone();
            n.updated = now();
            Ok(result)
        })
        .await?,
    ))
}
pub(super) async fn source_guide(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, sid)): Path<(String, String)>,
) -> Result<Json<Artifact>> {
    authorized(&h, &a)?;
    let n = a.notebook(&nid).await?;
    let s = n.sources.iter().find(|s| s.id == sid).ok_or_else(missing)?;
    let evidence = retrieve(
        &n,
        "key concepts summary themes",
        std::slice::from_ref(&sid),
        true,
    );
    let content=complete(&a,&n,"Create a source guide with a short summary, key topics, and five useful questions to ask. Cite the provided excerpts.",&evidence,false).await?;
    let item = Artifact {
        id: id(),
        kind: "source-guide".into(),
        title: format!("Guide: {}", s.title).chars().take(300).collect(),
        content,
        evidence,
        created: now(),
        data: None,
        progress: Value::Null,
        media: false,
    };
    Ok(Json(
        a.mutate(|d| {
            let current = notebook_mut(d, &nid)?;
            if !current.sources.iter().any(|s| {
                s.id == sid
                    && n.sources
                        .iter()
                        .any(|old| old.id == sid && old.content == s.content)
            }) {
                return Err(Error(StatusCode::CONFLICT, "Source changed; retry".into()));
            }
            current.artifacts.push(item.clone());
            current.updated = now();
            Ok(item)
        })
        .await?,
    ))
}
fn media_path(a: &App, nid: &str, aid: &str) -> Result<PathBuf> {
    if Uuid::parse_str(nid).is_err() || Uuid::parse_str(aid).is_err() {
        return Err(missing());
    }
    Ok(a.config
        .data
        .with_extension("media")
        .join(format!("{nid}-{aid}.mp3")))
}
async fn provider_bytes(mut r: reqwest::Response, max: usize) -> Result<Vec<u8>> {
    if !r.status().is_success() {
        return Err(Error(
            StatusCode::BAD_GATEWAY,
            format!(
                "Media provider returned HTTP {}. Check model support and credentials.",
                r.status()
            ),
        ));
    }
    let mut bytes = Vec::new();
    while let Some(c) = r
        .chunk()
        .await
        .map_err(|_| bad("Media response interrupted"))?
    {
        if bytes.len() + c.len() > max {
            return Err(bad("Media provider response exceeds limit"));
        }
        bytes.extend_from_slice(&c);
    }
    Ok(bytes)
}
pub(super) async fn synthesize(a: &App, nid: &str, item: &mut Artifact) -> Result<()> {
    if a.media.tts_model.is_empty() {
        return Err(bad("AI_TTS_MODEL is required"));
    }
    if item.content.chars().count() > 4000 {
        return Err(bad(
            "Generated audio script exceeds 4000 characters; request a shorter overview",
        ));
    }
    let _permit = a
        .ai_slots
        .try_acquire()
        .map_err(|_| Error(StatusCode::TOO_MANY_REQUESTS, "Server busy".into()))?;
    let mut req=a.client.post(format!("{}/audio/speech",a.config.base_url.trim_end_matches('/'))).json(&json!({"model":a.media.tts_model,"voice":a.media.voice,"input":item.content,"response_format":"mp3"}));
    if !a.config.api_key.is_empty() {
        req = req.bearer_auth(&a.config.api_key);
    }
    let response = req.send().await.map_err(|_| {
        Error(
            StatusCode::BAD_GATEWAY,
            "Could not connect to speech provider".into(),
        )
    })?;
    let bytes = provider_bytes(response, 20 * 1024 * 1024).await?;
    if bytes.len() < 4
        || !(bytes.starts_with(b"ID3") || (bytes[0] == 0xff && bytes[1] & 0xe0 == 0xe0))
    {
        return Err(Error(
            StatusCode::BAD_GATEWAY,
            "Speech provider did not return MP3 bytes".into(),
        ));
    }
    let path = media_path(a, nid, &item.id)?;
    let parent = path
        .parent()
        .ok_or_else(|| bad("Invalid media directory"))?;
    tokio::fs::create_dir_all(parent).await.map_err(internal)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        tokio::fs::set_permissions(parent, std::fs::Permissions::from_mode(0o700))
            .await
            .map_err(internal)?;
    }
    tokio::fs::write(path, &bytes).await.map_err(internal)?;
    item.media = true;
    Ok(())
}
pub(super) async fn media_file(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, aid)): Path<(String, String)>,
) -> Result<Response> {
    authorized(&h, &a)?;
    let n = a.notebook(&nid).await?;
    if !n.artifacts.iter().any(|i| i.id == aid && i.media) {
        return Err(missing());
    }
    let bytes = tokio::fs::read(media_path(&a, &nid, &aid)?)
        .await
        .map_err(|_| missing())?;
    Ok((
        [
            ("content-type", "audio/mpeg"),
            ("cache-control", "no-store"),
        ],
        bytes,
    )
        .into_response())
}
#[derive(Deserialize)]
pub(super) struct AudioInput {
    title: String,
    filename: String,
    content: String,
}
pub(super) async fn transcribe(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
    Json(p): Json<AudioInput>,
) -> Result<Json<Source>> {
    authorized(&h, &a)?;
    a.notebook(&nid).await?;
    if a.media.transcription_model.is_empty() {
        return Err(bad(
            "Set AI_TRANSCRIPTION_MODEL to enable audio/video transcription",
        ));
    }
    let title = text(&p.title, "Source title", 300)?;
    let ext = p.filename.rsplit('.').next().unwrap_or("").to_lowercase();
    let mime = match ext.as_str() {
        "mp3" => "audio/mpeg",
        "wav" => "audio/wav",
        "m4a" | "mp4" => "audio/mp4",
        "webm" => "audio/webm",
        "ogg" => "audio/ogg",
        _ => {
            return Err(bad(
                "Supported transcription formats: mp3, wav, m4a, mp4, webm, ogg",
            ))
        }
    };
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(&p.content)
        .map_err(|_| bad("Audio must be base64"))?;
    if bytes.is_empty() || bytes.len() > 10 * 1024 * 1024 {
        return Err(bad("Audio must contain 1 byte to 10 MB"));
    }
    let _permit = a
        .ai_slots
        .try_acquire()
        .map_err(|_| Error(StatusCode::TOO_MANY_REQUESTS, "Server busy".into()))?;
    let part = reqwest::multipart::Part::bytes(bytes)
        .file_name(format!("upload.{ext}"))
        .mime_str(mime)
        .map_err(internal)?;
    let form = reqwest::multipart::Form::new()
        .text("model", a.media.transcription_model.clone())
        .text("response_format", "json")
        .part("file", part);
    let mut req = a
        .client
        .post(format!(
            "{}/audio/transcriptions",
            a.config.base_url.trim_end_matches('/')
        ))
        .multipart(form);
    if !a.config.api_key.is_empty() {
        req = req.bearer_auth(&a.config.api_key);
    }
    let response = req.send().await.map_err(|_| {
        Error(
            StatusCode::BAD_GATEWAY,
            "Transcription connection failed".into(),
        )
    })?;
    let bytes = provider_bytes(response, MAX_TEXT).await?;
    let data: Value = serde_json::from_slice(&bytes)
        .map_err(|_| bad("Transcription provider returned invalid JSON"))?;
    let content = text(data["text"].as_str().unwrap_or(""), "Transcript", MAX_TEXT)?;
    let source = Source {
        id: id(),
        title,
        content,
        kind: "transcript".into(),
        url: None,
        created: now(),
    };
    Ok(Json(
        a.mutate(|d| {
            let n = notebook_mut(d, &nid)?;
            if n.sources.len() >= 100 {
                return Err(bad("Limit: 100 sources"));
            }
            n.sources.push(source.clone());
            n.updated = now();
            Ok(source)
        })
        .await?,
    ))
}
fn csv_cell(s: &str) -> String {
    let s = if s.trim_start().starts_with(['=', '+', '-', '@']) || s.starts_with(['\t', '\r']) {
        format!("'{s}")
    } else {
        s.into()
    };
    format!("\"{}\"", s.replace('"', "\"\""))
}
pub(super) async fn download(
    State(a): State<App>,
    h: HeaderMap,
    Path((nid, aid)): Path<(String, String)>,
) -> Result<Response> {
    authorized(&h, &a)?;
    let n = a.notebook(&nid).await?;
    let item = n
        .artifacts
        .iter()
        .find(|i| i.id == aid)
        .ok_or_else(missing)?;
    let (mime, filename, content) = if let Some(data) = &item.data {
        let m: Material = serde_json::from_value(data.clone()).map_err(internal)?;
        match m {
            Material::DataTable { columns, rows } => {
                let mut rows = rows;
                rows.insert(0, columns);
                (
                    "text/csv; charset=utf-8",
                    "table.csv",
                    rows.iter()
                        .map(|r| r.iter().map(|s| csv_cell(s)).collect::<Vec<_>>().join(","))
                        .collect::<Vec<_>>()
                        .join("\r\n"),
                )
            }
            _ => (
                "application/json",
                "study-material.json",
                serde_json::to_string_pretty(data).map_err(internal)?,
            ),
        }
    } else {
        (
            "text/markdown; charset=utf-8",
            "artifact.md",
            item.content.clone(),
        )
    };
    let disposition = format!("attachment; filename={filename}");
    Ok((
        [
            ("content-type", mime),
            ("content-disposition", disposition.as_str()),
            ("cache-control", "no-store"),
        ],
        content,
    )
        .into_response())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn structured_validation() {
        assert!(parse_material(r#"{"type":"quiz","questions":[{"question":"Q","options":["a","b"],"answer":4,"explanation":"E"}]}"#,"quiz").is_err());
        assert!(parse_material(
            r#"{"type":"flashcards","cards":[{"front":"Q","back":"A"}]}"#,
            "flashcards"
        )
        .is_ok());
        assert!(parse_material(
            r#"{"type":"data-table","columns":["a"],"rows":[["a","b"]]}"#,
            "data-table"
        )
        .is_err());
    }
    #[test]
    fn safe_csv() {
        assert_eq!(csv_cell("=cmd()"), "\"'=cmd()\"");
        assert_eq!(csv_cell("a\"b"), "\"a\"\"b\"");
    }
}

pub(super) async fn enable_share(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    let share = a
        .mutate(|d| {
            let n = notebook_mut(d, &nid)?;
            let token = n.share_token.get_or_insert_with(id).clone();
            Ok(token)
        })
        .await?;
    Ok(Json(
        json!({"path":format!("/?share={share}"),"token":share}),
    ))
}
pub(super) async fn disable_share(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    a.mutate(|d| {
        notebook_mut(d, &nid)?.share_token = None;
        Ok(())
    })
    .await?;
    Ok(Json(json!({"disabled":true})))
}
pub(super) async fn shared(State(a): State<App>, Path(token): Path<String>) -> Result<Response> {
    if Uuid::parse_str(&token).is_err() {
        return Err(missing());
    }
    let db = a.db.read().await;
    let mut n = db
        .notebooks
        .iter()
        .find(|n| n.share_token.as_ref() == Some(&token))
        .cloned()
        .ok_or_else(missing)?;
    n.share_token = None;
    Ok((
        [
            ("cache-control", "no-store"),
            ("referrer-policy", "no-referrer"),
        ],
        Json(n),
    )
        .into_response())
}
pub(super) async fn shared_media(
    State(a): State<App>,
    Path((token, aid)): Path<(String, String)>,
) -> Result<Response> {
    if Uuid::parse_str(&token).is_err() {
        return Err(missing());
    }
    let n =
        a.db.read()
            .await
            .notebooks
            .iter()
            .find(|n| n.share_token.as_ref() == Some(&token))
            .cloned()
            .ok_or_else(missing)?;
    if !n.artifacts.iter().any(|i| i.id == aid && i.media) {
        return Err(missing());
    }
    let bytes = tokio::fs::read(media_path(&a, &n.id, &aid)?)
        .await
        .map_err(|_| missing())?;
    Ok((
        [
            ("content-type", "audio/mpeg"),
            ("cache-control", "no-store"),
        ],
        bytes,
    )
        .into_response())
}
pub(super) async fn cleanup_media(a: &App, nid: &str, aid: &str) {
    if let Ok(path) = media_path(a, nid, aid) {
        let _ = tokio::fs::remove_file(path).await;
    }
}
