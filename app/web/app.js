/* InstantMesh Studio — frontend.
 * Talks only to this app's own /api/* routes. No API tokens ever reach the browser.
 */
const $ = (sel) => document.querySelector(sel);

const state = {
  providers: [],
  activeProvider: null,
  file: null,
  jobId: null,
  pollTimer: null,
  lastJob: null,
};

const HINTS = {
  provider_unavailable:
    "The provider is not configured or the server cannot reach it. Check server egress/credentials, or switch provider.",
  inference_failed:
    "The model ran but failed. Common causes: GPU quota exhausted, an upstream Space change, or an input the pipeline rejects.",
  internal_error: "Unexpected server error — see server logs.",
};

/* ------------------------------------------------------------------ providers */
async function loadProviders() {
  const res = await fetch("/api/providers");
  const data = await res.json();
  state.providers = data.providers;
  state.activeProvider = data.active;

  const select = $("#provider-select");
  select.innerHTML = "";
  for (const p of state.providers) {
    const opt = document.createElement("option");
    opt.value = p.name;
    const flags = [];
    if (!p.configured) flags.push("needs config");
    if (p.reachable === false) flags.push("unreachable");
    if (p.real_inference === false) flags.push("simulation");
    opt.textContent = p.label + (flags.length ? ` — ${flags.join(", ")}` : "");
    if (p.name === data.active) opt.selected = true;
    select.appendChild(opt);
  }

  const tbody = $("#provider-rows");
  tbody.innerHTML = "";
  for (const p of state.providers) {
    const tr = document.createElement("tr");
    const reachable = p.reachable === undefined ? "—" : p.reachable ? "yes" : "no";
    tr.innerHTML = `
      <td><strong>${p.name}</strong>${p.active ? ' <span class="pill pill-warn">active</span>' : ""}</td>
      <td>${p.real_inference ? "real model" : '<span class="pill pill-warn">mock</span>'}</td>
      <td><span class="pill ${p.configured ? "pill-yes" : "pill-no"}">${p.configured ? "yes" : "no"}</span>
          ${p.required_env && p.required_env.length ? `<div class="detail">${p.required_env.join(", ")}</div>` : ""}</td>
      <td><span class="pill ${reachable === "yes" ? "pill-yes" : reachable === "no" ? "pill-no" : ""}">${reachable}</span></td>
      <td class="detail">${(p.probe_detail || p.notes || "")}${p.probe_latency_ms ? ` · ${p.probe_latency_ms}ms` : ""}</td>`;
    tbody.appendChild(tr);
  }

  updateProviderDetail();
  updateBanners();
}

function currentProvider() {
  return state.providers.find((p) => p.name === $("#provider-select").value);
}

function updateProviderDetail() {
  const p = currentProvider();
  if (!p) return;
  const bits = [];
  if (!p.real_inference) bits.push("Placeholder geometry — not AI output.");
  if (p.reachable === false) bits.push("Server cannot reach this host (network egress blocked or service down).");
  if (!p.configured) bits.push(`Missing: ${(p.required_env || []).join(", ")}`);
  if (p.notes) bits.push(p.notes);
  $("#provider-detail").textContent = bits.join(" ");
  $("#provider-chip").textContent = `${p.name} · ${p.real_inference ? "real inference" : "simulation"}`;
  $("#provider-chip").className = "chip " + (p.real_inference ? "chip-ok" : "chip-muted");
}

function updateBanners() {
  const p = currentProvider();
  $("#sim-banner").hidden = !(p && !p.real_inference);

  const blocked = state.providers.filter((x) => x.real_inference && x.reachable === false);
  const banner = $("#net-banner");
  if (blocked.length) {
    banner.hidden = false;
    banner.innerHTML =
      "<strong>Network restriction detected.</strong> The server cannot reach: " +
      blocked.map((b) => `<code>${b.name}</code>`).join(", ") +
      ". Real inference will fail from this host — deploy the server somewhere with open egress, or run the free-GPU notebook.";
  } else {
    banner.hidden = true;
  }
}

/* ------------------------------------------------------------------ upload */
function setFile(file) {
  if (!file) return;
  if (!/^image\/(png|jpeg|webp)$/.test(file.type)) return showFormError("Use a PNG, JPEG or WebP image.");
  if (file.size > 12 * 1024 * 1024) return showFormError("Image is larger than 12 MB.");
  state.file = file;
  const img = $("#preview-img");
  img.src = URL.createObjectURL(file);
  img.hidden = false;
  $("#dropzone-empty").hidden = true;
  $("#generate").disabled = false;
  hideFormError();
}

function showFormError(msg) {
  const el = $("#form-error");
  el.textContent = msg;
  el.hidden = false;
}
function hideFormError() {
  $("#form-error").hidden = true;
}

$("#dropzone").addEventListener("click", () => $("#file-input").click());
$("#dropzone").addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") $("#file-input").click();
});
$("#file-input").addEventListener("change", (e) => setFile(e.target.files[0]));
["dragenter", "dragover"].forEach((ev) =>
  $("#dropzone").addEventListener(ev, (e) => {
    e.preventDefault();
    $("#dropzone").classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  $("#dropzone").addEventListener(ev, (e) => {
    e.preventDefault();
    $("#dropzone").classList.remove("dragover");
  })
);
$("#dropzone").addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));

/* ------------------------------------------------------------------ examples */
const EXAMPLES = ["fox.jpg", "robot.jpg", "bulldog.png", "cake.jpg"];
(async function buildExamples() {
  const wrap = $("#examples");
  for (const name of EXAMPLES) {
    const url = `/static/examples/${name}`;
    const res = await fetch(url, { method: "HEAD" });
    if (!res.ok) continue;
    const img = document.createElement("img");
    img.src = url;
    img.alt = name;
    img.title = name;
    img.addEventListener("click", async () => {
      const blob = await (await fetch(url)).blob();
      setFile(new File([blob], name, { type: blob.type || "image/jpeg" }));
    });
    wrap.appendChild(img);
  }
})();

/* ------------------------------------------------------------------ generate */
$("#steps").addEventListener("input", (e) => ($("#steps-out").textContent = e.target.value));
$("#provider-select").addEventListener("change", () => {
  updateProviderDetail();
  updateBanners();
});

$("#generate").addEventListener("click", async () => {
  if (!state.file) return;
  stopPolling();
  hideFormError();
  $("#generate").disabled = true;
  $("#generate").textContent = "Generating…";
  $("#error-panel").hidden = true;
  resetResult();

  const body = new FormData();
  body.append("image", state.file);
  body.append("provider", $("#provider-select").value);
  body.append("seed", $("#seed").value);
  body.append("steps", $("#steps").value);
  body.append("remove_background", $("#remove-bg").checked);
  body.append("export_texmap", $("#texmap").checked);
  body.append("export_video", $("#video").checked);

  try {
    const res = await fetch("/api/jobs", { method: "POST", body });
    const job = await res.json();
    if (!res.ok) throw new Error(job.detail || `HTTP ${res.status}`);
    state.jobId = job.id;
    $("#job-id").textContent = job.id;
    setStatus(job);
    poll();
  } catch (err) {
    finishRun();
    showError({ error_kind: "internal_error", error: String(err), message: "Request failed" });
  }
});

function poll() {
  state.pollTimer = setInterval(async () => {
    if (!state.jobId) return stopPolling();
    try {
      const res = await fetch(`/api/jobs/${state.jobId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const job = await res.json();
      setStatus(job);
      if (job.status === "succeeded") {
        stopPolling();
        renderResult(job);
        finishRun();
      } else if (job.status === "failed") {
        stopPolling();
        showError(job);
        finishRun();
      }
    } catch (err) {
      stopPolling();
      showError({ error_kind: "internal_error", error: String(err), message: "Lost contact with server" });
      finishRun();
    }
  }, 900);
}

function stopPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = null;
}

function finishRun() {
  $("#generate").disabled = !state.file;
  $("#generate").textContent = "Generate 3D mesh";
}

/* ------------------------------------------------------------------ rendering */
const STAGES = ["preprocess", "multiview", "reconstruct", "export"];

function setStatus(job) {
  state.lastJob = job;
  $("#progress-bar").style.width = `${job.progress || 0}%`;
  $("#progress-msg").textContent = job.message || job.stage;
  $("#progress-pct").textContent = `${job.progress || 0}%`;
  $("#raw-json").textContent = JSON.stringify(job, null, 2);

  const order = { preprocess: 0, connect: 0, load: 0, submit: 0, upload: 0, multiview: 1, waiting: 1, reconstruct: 2, extract: 2, render: 3, download: 3, export: 3, done: 4 };
  const idx = order[job.stage] ?? 0;
  document.querySelectorAll(".step").forEach((el, i) => {
    el.classList.toggle("active", i === idx && job.status === "running");
    el.classList.toggle("done", i < idx || job.status === "succeeded");
  });
}

function resetResult() {
  window.__modelSrc = null;
  ["glb", "obj", "multiview", "video"].forEach((k) => {
    const el = $(`#dl-${k}`);
    el.hidden = true;
    el.removeAttribute("href");
  });
  $("#dl-none").hidden = false;
  $("#pane-multiview").innerHTML = '<div class="viewer-empty">Multi-view grid will appear here.</div>';
  $("#pane-video").innerHTML = '<div class="viewer-empty">Turntable video will appear here.</div>';
  $("#mv").removeAttribute("src");
  $("#meta-grid").innerHTML = "";
}

async function renderResult(job) {
  resetResult();
  const files = job.files || {};
  $("#raw-json").textContent = JSON.stringify(job, null, 2);

  const label = (kind, text) => {
    const el = $(`#dl-${kind}`);
    el.href = files[kind];
    el.textContent = `⤓ ${text}`;
    el.hidden = false;
  };

  if (files.glb) {
    label("glb", job.simulated ? "GLB (simulated)" : "GLB");
    const viewer = $("#mv");
    /* Cache-bust so re-runs of the same job id always reload geometry. */
    viewer.setAttribute("src", `${files.glb}?t=${Date.now()}`);
    viewer.setAttribute("alt", job.simulated ? "Simulated placeholder mesh" : "Generated 3D mesh");
    $("#pane-model").classList.add("active");
    switchTab("model");
  } else if (files.obj) {
    switchTab("model");
    $("#pane-model").innerHTML =
      '<div class="viewer-empty">This provider returned OBJ only (no GLB), so the in-page 3D viewer cannot display it. Download the OBJ below.</div>';
  }
  if (files.obj) label("obj", "OBJ");
  if (files.multiview) {
    label("multiview", "multi-view PNG");
    $("#pane-multiview").innerHTML = `<img src="${files.multiview}" alt="Generated multi-view grid" />`;
  }
  if (files.video) {
    label("video", "MP4");
    $("#pane-video").innerHTML = `<video src="${files.video}" controls autoplay loop muted playsinline></video>`;
  }
  $("#dl-none").hidden = Object.keys(files).length > 0;

  const meta = {
    status: job.status,
    provider: job.provider,
    simulated: job.simulated,
    duration_s: job.duration_s,
    seed: job.options?.seed,
    steps: job.options?.steps,
  };
  Object.entries(job.metadata || {}).forEach(([k, v]) => (meta[k] = v));

  const grid = $("#meta-grid");
  grid.innerHTML = "";
  for (const [k, v] of Object.entries(meta)) {
    if (v === null || v === undefined || v === "") continue;
    const div = document.createElement("div");
    div.className = "meta-item";
    div.innerHTML = `<dt>${k}</dt><dd>${String(v)}</dd>`;
    grid.appendChild(div);
  }
}

function showError(job) {
  const panel = $("#error-panel");
  panel.hidden = false;
  $("#error-title").textContent = job.message || "Generation failed";
  $("#error-body").textContent = job.error || "Unknown error";
  $("#error-hint").textContent = HINTS[job.error_kind] || "";
}

/* ------------------------------------------------------------------ tabs */
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("active", p.id === `pane-${name}`));
}
document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));

/* ------------------------------------------------------------------ boot */
loadProviders().catch((err) => {
  $("#provider-rows").innerHTML = `<tr><td colspan="5" class="detail">Failed to load providers: ${err}</td></tr>`;
});
