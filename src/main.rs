use base64::Engine;
use clap::{Parser, Subcommand};
use serde_json::{json, Value};
use sourcebook::{App, Config};
use std::path::PathBuf;

#[derive(Parser)]
#[command(
    name = "sourcebook",
    version,
    about = "Source-grounded research notebooks. Independent of Google."
)]
struct Cli {
    #[arg(
        long,
        env = "SOURCEBOOK_URL",
        default_value = "http://127.0.0.1:3000",
        global = true
    )]
    url: String,
    #[arg(long, env = "SOURCEBOOK_TOKEN", global = true, hide_env_values = true)]
    token: Option<String>,
    #[command(subcommand)]
    command: Command,
}
#[derive(Subcommand)]
enum Command {
    /// Start the browser UI and HTTP API (single process per data file).
    Serve {
        #[arg(long, default_value = "127.0.0.1:3000")]
        bind: String,
        #[arg(long, env = "SOURCEBOOK_DATA", default_value = "data/notebooks.json")]
        data: PathBuf,
        #[arg(long, env = "AI_BASE_URL", default_value = "https://api.openai.com/v1")]
        base_url: String,
        #[arg(long, env = "AI_MODEL", default_value = "")]
        model: String,
    },
    /// List notebook IDs and metadata.
    List,
    Create {
        title: String,
    },
    Show {
        notebook: String,
    },
    /// Add a UTF-8 text/Markdown or PDF file, or a public URL.
    Source {
        notebook: String,
        #[arg(long)]
        file: Option<PathBuf>,
        #[arg(long)]
        link: Option<String>,
        #[arg(long)]
        title: Option<String>,
    },
    Ask {
        notebook: String,
        question: String,
        #[arg(long)]
        source: Vec<String>,
    },
    Generate {
        notebook: String,
        kind: String,
        #[arg(long, default_value = "")]
        instructions: String,
        #[arg(long)]
        source: Vec<String>,
    },
    Note {
        notebook: String,
        title: String,
        content: String,
    },
    Export {
        notebook: String,
        #[arg(long)]
        output: Option<PathBuf>,
    },
    /// Restore a notebook JSON export with fresh IDs.
    Import {
        file: PathBuf,
    },
    /// Download generated JSON/CSV, or an MP3 with --audio.
    Download {
        notebook: String,
        artifact: String,
        #[arg(long)]
        audio: bool,
        #[arg(long)]
        output: PathBuf,
    },
    /// Generate a summary, topics and suggested questions for one source.
    Guide {
        notebook: String,
        source: String,
    },
    /// Grade a quiz using comma-separated, zero-based answer indexes.
    Review {
        notebook: String,
        artifact: String,
        #[arg(long, value_delimiter = ',')]
        answers: Vec<usize>,
    },
    /// Record a flashcard review.
    Card {
        notebook: String,
        artifact: String,
        index: usize,
        #[arg(long)]
        known: bool,
    },
    /// Enable read-only sharing, or revoke existing links.
    Share {
        notebook: String,
        #[arg(long)]
        revoke: bool,
    },
    Delete {
        notebook: String,
        #[arg(long)]
        yes: bool,
    },
}
#[tokio::main]
async fn main() {
    if let Err(e) = run().await {
        eprintln!("Error: {e}");
        std::process::exit(1);
    }
}
async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    let token = cli.token.ok_or(
        "Set SOURCEBOOK_TOKEN (16+ characters); the same token protects the server and CLI",
    )?;
    if let Command::Serve {
        bind,
        data,
        base_url,
        model,
    } = &cli.command
    {
        let parsed = reqwest::Url::parse(base_url)?;
        if !["http", "https"].contains(&parsed.scheme())
            || !parsed.username().is_empty()
            || parsed.password().is_some()
        {
            return Err("AI_BASE_URL must be an HTTP(S) URL without embedded credentials".into());
        }
        if parsed.scheme() == "http"
            && !matches!(parsed.host_str(), Some("localhost" | "127.0.0.1" | "[::1]"))
        {
            return Err("Non-local AI endpoints require HTTPS".into());
        }
        let app = App::open(Config {
            data: data.clone(),
            token,
            base_url: base_url.clone(),
            model: model.clone(),
            api_key: std::env::var("AI_API_KEY").unwrap_or_default(),
        })
        .await?;
        let listener = tokio::net::TcpListener::bind(bind).await?;
        eprintln!("Sourcebook listening on {bind}. Open the UI and enter SOURCEBOOK_TOKEN. Do not expose publicly without TLS/access controls.");
        axum::serve(listener, sourcebook::router(app))
            .with_graceful_shutdown(async {
                let _ = tokio::signal::ctrl_c().await;
            })
            .await?;
        return Ok(());
    }
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(150))
        .redirect(reqwest::redirect::Policy::none())
        .build()?;
    let base = format!("{}/api/notebooks", cli.url.trim_end_matches('/'));
    if let Command::Download {
        notebook,
        artifact,
        audio,
        output,
    } = &cli.command
    {
        let endpoint = if *audio { "media" } else { "download" };
        let response = client
            .get(format!("{base}/{notebook}/artifacts/{artifact}/{endpoint}"))
            .bearer_auth(&token)
            .send()
            .await?;
        if !response.status().is_success() {
            return Err(format!("Download failed: HTTP {}", response.status()).into());
        }
        tokio::fs::write(output, response.bytes().await?).await?;
        eprintln!("Saved {}", output.display());
        return Ok(());
    }
    let (method, path, payload, output) = match cli.command {
        Command::List => ("GET", base, None, None),
        Command::Create { title } => ("POST", base, Some(json!({"title":title})), None),
        Command::Show { notebook } => ("GET", format!("{base}/{notebook}"), None, None),
        Command::Source {
            notebook,
            file,
            link,
            title,
        } => {
            if file.is_some() == link.is_some() {
                return Err("Specify exactly one of --file or --link".into());
            }
            let payload = if let Some(path) = file {
                if tokio::fs::metadata(&path).await?.len() > 10 * 1024 * 1024 {
                    return Err("File exceeds 10 MB".into());
                }
                let bytes = tokio::fs::read(&path).await?;
                let ext = path
                    .extension()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_lowercase();
                let pdf = bytes.starts_with(b"%PDF-");
                let kind = if pdf {
                    "pdf"
                } else if ext == "docx" {
                    "docx"
                } else if ["mp3", "wav", "m4a", "mp4", "webm", "ogg"].contains(&ext.as_str()) {
                    "audio"
                } else {
                    "text"
                };
                let content = if kind != "text" {
                    base64::engine::general_purpose::STANDARD.encode(&bytes)
                } else {
                    String::from_utf8(bytes)?
                };
                json!({"title":title.unwrap_or_else(||path.file_name().unwrap_or_default().to_string_lossy().into_owned()),"kind":kind,"content":content,"filename":path.file_name().unwrap_or_default().to_string_lossy()})
            } else {
                let url = link.unwrap();
                json!({"title":title.unwrap_or_else(||url.clone()),"kind":"url","url":url})
            };
            (
                "POST",
                format!(
                    "{base}/{notebook}/{}",
                    if payload["kind"] == "audio" {
                        "transcribe"
                    } else {
                        "sources"
                    }
                ),
                Some(payload),
                None,
            )
        }
        Command::Ask {
            notebook,
            question,
            source,
        } => (
            "POST",
            format!("{base}/{notebook}/chat"),
            Some(json!({"question":question,"source_ids":source})),
            None,
        ),
        Command::Generate {
            notebook,
            kind,
            instructions,
            source,
        } => (
            "POST",
            format!("{base}/{notebook}/generate"),
            Some(json!({"kind":kind,"instructions":instructions,"source_ids":source})),
            None,
        ),
        Command::Note {
            notebook,
            title,
            content,
        } => (
            "POST",
            format!("{base}/{notebook}/notes"),
            Some(json!({"title":title,"content":content})),
            None,
        ),
        Command::Export { notebook, output } => {
            ("GET", format!("{base}/{notebook}/export"), None, output)
        }
        Command::Import { file } => {
            if tokio::fs::metadata(&file).await?.len() > 16 * 1024 * 1024 {
                return Err("Export exceeds 16 MB".into());
            }
            let value: Value = serde_json::from_slice(&tokio::fs::read(file).await?)?;
            ("POST", format!("{base}/import"), Some(value), None)
        }
        Command::Guide { notebook, source } => (
            "POST",
            format!("{base}/{notebook}/sources/{source}/guide"),
            Some(json!({})),
            None,
        ),
        Command::Review {
            notebook,
            artifact,
            answers,
        } => (
            "POST",
            format!("{base}/{notebook}/artifacts/{artifact}/review"),
            Some(json!({"answers":answers})),
            None,
        ),
        Command::Card {
            notebook,
            artifact,
            index,
            known,
        } => (
            "POST",
            format!("{base}/{notebook}/artifacts/{artifact}/review"),
            Some(json!({"card":index,"known":known})),
            None,
        ),
        Command::Share { notebook, revoke } => (
            if revoke { "DELETE" } else { "POST" },
            format!("{base}/{notebook}/share"),
            Some(json!({})),
            None,
        ),
        Command::Download { .. } => unreachable!(),
        Command::Delete { notebook, yes } => {
            if !yes {
                return Err("Deleting a notebook is permanent. Pass --yes to confirm.".into());
            }
            ("DELETE", format!("{base}/{notebook}"), None, None)
        }
        Command::Serve { .. } => unreachable!(),
    };
    let mut req = client.request(method.parse()?, path).bearer_auth(token);
    if let Some(payload) = payload {
        req = req.json(&payload);
    }
    let response = req.send().await?;
    let status = response.status();
    let value: Value = response.json().await?;
    if !status.is_success() {
        return Err(format!(
            "HTTP {status}: {}",
            value["error"].as_str().unwrap_or("Request failed")
        )
        .into());
    }
    let rendered = serde_json::to_string_pretty(&value)?;
    if let Some(path) = output {
        tokio::fs::write(path, rendered).await?;
    } else {
        println!("{rendered}");
    }
    Ok(())
}
