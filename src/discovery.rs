//! Explicit discovery is separate from source-only AI. No model invents URLs.
use super::*;
pub(super) async fn recommendations(
    State(a): State<App>,
    h: HeaderMap,
    Path(nid): Path<String>,
) -> Result<Json<Value>> {
    authorized(&h, &a)?;
    if a.offline {
        return Err(bad(
            "Source discovery requires network access. AI answers remain source-only.",
        ));
    }
    let n = a.notebook(&nid).await?;
    let response = a
        .client
        .get("https://en.wikipedia.org/w/api.php")
        .query(&[
            ("action", "query"),
            ("list", "search"),
            ("srsearch", n.title.as_str()),
            ("srlimit", "6"),
            ("format", "json"),
        ])
        .header(
            "User-Agent",
            "Sourcebook/0.6 (user-initiated notebook source discovery)",
        )
        .timeout(Duration::from_secs(20))
        .send()
        .await
        .map_err(|_| {
            bad("Discovery service unavailable. You can still add a source URL manually.")
        })?;
    if !response.status().is_success() {
        return Err(bad(
            "Discovery service could not complete this search. Try again later or import a URL.",
        ));
    }
    let mut response = response;
    let mut bytes = vec![];
    while let Some(c) = response
        .chunk()
        .await
        .map_err(|_| bad("Discovery interrupted"))?
    {
        if bytes.len() + c.len() > 500_000 {
            return Err(bad("Discovery response too large"));
        }
        bytes.extend_from_slice(&c);
    }
    let v: Value = serde_json::from_slice(&bytes).map_err(|_| bad("Invalid discovery response"))?;
    let mut suggestions = vec![];
    for item in v["query"]["search"]
        .as_array()
        .into_iter()
        .flatten()
        .take(6)
    {
        if let Some(title) = item["title"].as_str() {
            let mut url =
                reqwest::Url::parse("https://en.wikipedia.org/wiki/").map_err(internal)?;
            url.path_segments_mut()
                .map_err(|_| bad("Invalid discovery URL"))?
                .pop_if_empty()
                .push(&title.replace(' ', "_"));
            suggestions.push(json!({"title":title,"url":url.to_string(),"reason":"Related title returned by Wikipedia search. Not read, verified or added to notebook yet."}));
        }
    }
    Ok(Json(
        json!({"suggestions":suggestions,"query":n.title,"service":"Wikipedia search","notice":"Discovery results are not notebook evidence. Add a page to import its text. AI answers do not browse."}),
    ))
}
