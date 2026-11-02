/* Loom UI — S0–S2 (stdlib backend, hand-off LLM steps) */

const qs = new URLSearchParams(location.search);
const token = qs.get("t") || "";

const headers = () => {
  const h = { Accept: "application/json" };
  if (token) h["X-Loom-Token"] = token;
  return h;
};

const jsonHeaders = () => ({ ...headers(), "Content-Type": "application/json" });

async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { ...(opts.method === "POST" ? jsonHeaders() : headers()), ...opts.headers } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || body.ok === false) {
    const msg = body.error?.message || res.statusText;
    throw new Error(msg);
  }
  showWarnings(body.warnings || []);
  return body;
}

function showWarnings(list) {
  const el = document.getElementById("warnings");
  if (!list.length) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.innerHTML = "<strong>Warnings</strong><ul>" + list.map((w) => `<li>${escapeHtml(w)}</li>`).join("") + "</ul>";
}

function logActivity(line) {
  const sec = document.getElementById("activity");
  const pre = document.getElementById("activity-log");
  sec.hidden = false;
  pre.textContent += line + "\n";
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

let state = { slug: localStorage.getItem("loom_slug") || "", engagements: [] };
let viewGen = 0;

function bumpView() {
  viewGen += 1;
  return viewGen;
}

function staleView(gen) {
  return gen !== viewGen;
}

function setSlug(slug) {
  state.slug = slug;
  localStorage.setItem("loom_slug", slug);
}

function nav(screen) {
  bumpView();
  document.querySelectorAll(".nav button[data-screen]").forEach((b) => {
    b.setAttribute("aria-current", b.dataset.screen === screen ? "true" : "false");
  });
  const screens = { overview: renderOverview, create: renderCreate, keystore: renderKeystore, evidence: renderEvidence };
  screens[screen]?.();
}

async function loadMeta() {
  const { data } = await api("/api/meta");
  document.getElementById("approver").textContent = data.approver;
}

async function renderOverview() {
  const gen = viewGen;
  const main = document.getElementById("main");
  main.innerHTML = "<p class='beat'>Loading…</p>";
  const engResp = await api("/api/engagements");
  if (staleView(gen)) return;
  state.engagements = engResp.data || [];
  const hy = await api("/api/hygiene");
  if (staleView(gen)) return;
  const ok = (hy.data?.ok || []).join("; ");
  const findings = (hy.data?.findings || []).join("; ");
  let nextHtml = "";
  if (state.slug) {
    let d = null;
    try {
      const n = await api(`/api/e/${encodeURIComponent(state.slug)}/next?fs=1`);
      d = n.state || n.data;
    } catch {
      setSlug("");
    }
    if (!d) {
      /* stale picker — engagement removed from root */
    } else {
    const stale = (d.blockers || []).some((b) => b.includes("stale"));
    nextHtml = `
      <article class="frame">
        <p class="eyebrow">Overview · ${escapeHtml(d.slug)}</p>
        <h2>${escapeHtml(d.company || d.slug)}</h2>
        ${stale ? `<p class="callout" role="alert"><strong>Re-run required</strong> — inputs or artifacts changed.</p>` : ""}
        <p><strong>Phase:</strong> ${escapeHtml(d.phase)}</p>
        <p><strong>Next:</strong> ${escapeHtml(d.next_action)}</p>
        ${d.command ? `<p class="meta">$ ${escapeHtml(d.command)}</p>` : ""}
        <p class="meta">Qualification: ${escapeHtml(d.qualification)} · Vision: ${escapeHtml(d.vision)} · Keystore: ${escapeHtml(d.keystore)}</p>
        ${listBlock("Blockers", d.blockers)}
        ${listBlock("Notes", d.notes)}
      </article>`;
    }
  }
  if (staleView(gen)) return;
  main.innerHTML = `
    <article class="frame">
      <h2>Engagements</h2>
      <label class="field">Active engagement
        <select id="eng-picker" aria-label="Engagement picker">
          <option value="">— select —</option>
          ${state.engagements.map((e) => `<option value="${escapeHtml(e.slug)}" ${e.slug === state.slug ? "selected" : ""}>${escapeHtml(e.display_name || e.slug)}</option>`).join("")}
        </select>
      </label>
      <p class="meta">Hygiene: ${escapeHtml(ok)}${findings ? " · " + escapeHtml(findings) : ""}</p>
    </article>
    ${nextHtml}`;
  document.getElementById("eng-picker")?.addEventListener("change", (ev) => {
    setSlug(ev.target.value);
    renderOverview();
  });
}

function listBlock(title, items) {
  if (!items?.length) return "";
  return `<p><strong>${escapeHtml(title)}</strong></p><ul class="list">${items.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`;
}

async function renderCreate() {
  const gen = viewGen;
  const main = document.getElementById("main");
  main.innerHTML = `
    <article class="frame">
      <p class="eyebrow">SB-01</p>
      <h2>Create engagement</h2>
      <form id="create-form">
        <div class="field"><label for="company">Company (private)</label><input id="company" name="company" required class="fake-input" autocomplete="organization"></div>
        <div class="field"><label for="opportunity">Opportunity (private)</label><input id="opportunity" name="opportunity" required class="fake-input"></div>
        <div class="field"><label for="display">Public display name</label><input id="display" name="display" required class="fake-input"></div>
        <div class="field"><label for="slug">Public slug</label><input id="slug" name="slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" class="fake-input"></div>
        <div class="field"><label for="solution">Solution area</label>
          <select id="solution" name="solution" class="fake-input">
            <option value="unknown">Unknown</option><option value="security">Security</option><option value="observability">Observability</option><option value="search">Search</option><option value="cross_solution">Cross-solution</option>
          </select>
        </div>
        <div class="field"><label for="notes-files">Discovery docs (files → inputs/)</label>
          <input id="notes-files" type="file" class="file-input" multiple
            accept=".md,.txt,.markdown,.csv,.json,.yml,.yaml,.log,.html,.htm,.pdf,.zip,text/*,application/pdf,application/zip">
        </div>
        <div class="field"><label for="notes">Or paste notes</label><textarea id="notes" class="fake-area" rows="6"></textarea></div>
        <p id="create-errors" class="callout" role="alert" hidden></p>
        <div class="actions"><button type="submit" class="btn primary">Create</button></div>
      </form>
    </article>`;
  const form = document.getElementById("create-form");
  const errEl = document.getElementById("create-errors");
  async function validateLive() {
    const body = {
      company: form.company.value,
      opportunity: form.opportunity.value,
      slug: form.slug.value,
      display: form.display.value,
    };
    try {
      const r = await api("/api/validate-public", { method: "POST", body: JSON.stringify(body) });
      const errors = r.data.errors || {};
      if (Object.keys(errors).length) {
        errEl.hidden = false;
        errEl.textContent = Object.entries(errors).map(([k, v]) => `${k}: private identity leak (${v.join(", ")})`).join("; ");
      } else errEl.hidden = true;
    } catch {
      errEl.hidden = true;
    }
  }
  ["company", "opportunity", "slug", "display"].forEach((id) => document.getElementById(id).addEventListener("input", validateLive));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    errEl.hidden = true;
    let uploads = [];
    try {
      uploads = await filesFromInput(document.getElementById("notes-files"));
    } catch (e) {
      errEl.hidden = false;
      errEl.textContent = e.message;
      return;
    }
    const paste = form.notes.value.trim();
    if (!uploads.length && !paste) {
      errEl.hidden = false;
      errEl.textContent = "Add discovery docs via the file picker or paste notes.";
      return;
    }
    const first = uploads[0];
    const rest = uploads.slice(1);
    const body = {
      company: form.company.value,
      opportunity: form.opportunity.value,
      display: form.display.value,
      slug: form.slug.value,
      entry_mode: "notes",
      solution: form.solution.value,
      note_filename: first ? first.filename : "call-notes.md",
      note_text: first && first.content != null ? first.content : paste || "(see uploaded discovery docs)",
    };
    // Binary first file: create with placeholder paste, then upload all files into inputs/
    const deferAllUploads = Boolean(first && first.content_base64 != null);
    if (deferAllUploads) {
      body.note_filename = "call-notes.md";
      body.note_text = paste || `Discovery docs attached: ${uploads.map((u) => u.filename).join(", ")}`;
    }
    try {
      const r = await api("/api/engagements", { method: "POST", body: JSON.stringify(body) });
      setSlug(r.data.slug);
      if (deferAllUploads) await postUploads(r.data.slug, uploads);
      else if (rest.length) await postUploads(r.data.slug, rest);
      logActivity(`create ${r.data.slug} · ${uploads.length || 1} input(s) · warp-listen hand-off next`);
      await renderOverview();
    } catch (e) {
      errEl.hidden = false;
      errEl.textContent = e.message;
    }
  });
}

async function renderKeystore() {
  const gen = viewGen;
  const main = document.getElementById("main");
  if (!state.slug) {
    main.innerHTML = "<p class='beat'>Select an engagement on Overview first.</p>";
    return;
  }
  main.innerHTML = "<p class='beat'>Loading keystore…</p>";
  const ksResp = await api(`/api/e/${encodeURIComponent(state.slug)}/keys`);
  const ks = ksResp.data;
  const ksol = ks.kibana_solution || {};
  const sibs = await api(`/api/keys/siblings?slug=${encodeURIComponent(state.slug)}`);
  main.innerHTML = `
    <article class="frame">
      <p class="eyebrow">SB-02</p>
      <h2>Input settings · ${escapeHtml(state.slug)}</h2>
      <p>Keystore: <span class="chip">${escapeHtml(ks.status || "unknown")}</span>${ks.deferred ? " (deferred)" : ""}</p>
      ${ks.missing?.length ? `<p>Missing: ${escapeHtml(ks.missing.join(", "))}</p>` : ""}
      <section aria-labelledby="ksol-head">
        <h3 id="ksol-head">Kibana space solution</h3>
        <p>${escapeHtml(ksol.value || "—")} · ${ksol.confirmed ? "confirmed by you" : "suggested"}</p>
        ${ksol.reason ? `<p class="meta">${escapeHtml(ksol.reason)}</p>` : ""}
        <div class="row" role="group" aria-label="Override KIBANA_SOLUTION">
          ${(ksol.options || ["classic", "es", "oblt", "security"]).map((o) =>
            `<button type="button" class="btn ksol-opt" data-val="${escapeHtml(o)}">${escapeHtml(o)}</button>`).join("")}
        </div>
      </section>
      <section>
        <h3>Set values (not shown after save)</h3>
        <form id="key-form" class="add-row">
          <div class="field"><label for="es-url">ELASTICSEARCH_URL</label><input id="es-url" type="password" autocomplete="off" class="fake-input"></div>
          <div class="field"><label for="es-key">ES_API_KEY</label><input id="es-key" type="password" autocomplete="off" class="fake-input"></div>
          <button type="submit" class="btn">Save keys</button>
        </form>
      </section>
      <section>
        <h3>Clone from sibling</h3>
        <select id="clone-from" class="fake-input" aria-label="Clone from sibling">
          <option value="">—</option>
          ${(sibs.data || []).filter((s) => s.has_env).map((s) => `<option value="${escapeHtml(s.slug)}">${escapeHtml(s.slug)} — ${escapeHtml(s.summary || "")}</option>`).join("")}
        </select>
        <button type="button" id="clone-btn" class="btn">Clone</button>
      </section>
      <div class="actions">
        <button type="button" id="defer-btn" class="btn">Set up later</button>
        <button type="button" id="validate-btn" class="btn">Validate (local)</button>
      </div>
      <p id="ks-msg" class="meta" role="status"></p>
    </article>`;
  document.querySelectorAll(".ksol-opt").forEach((btn) => btn.addEventListener("click", async () => {
    await api(`/api/e/${encodeURIComponent(state.slug)}/keys/set`, {
      method: "POST",
      body: JSON.stringify({ key: "KIBANA_SOLUTION", value: btn.dataset.val }),
    });
    logActivity(`keys set KIBANA_SOLUTION=${btn.dataset.val}`);
    renderKeystore();
  }));
  document.getElementById("defer-btn").addEventListener("click", async () => {
    await api(`/api/e/${encodeURIComponent(state.slug)}/keys/defer`, { method: "POST", body: "{}" });
    renderKeystore();
  });
  document.getElementById("validate-btn").addEventListener("click", async () => {
    await api(`/api/e/${encodeURIComponent(state.slug)}/keys/validate`, { method: "POST", body: "{}" });
    renderKeystore();
  });
  document.getElementById("clone-btn").addEventListener("click", async () => {
    const source = document.getElementById("clone-from").value;
    if (!source) return;
    await api(`/api/e/${encodeURIComponent(state.slug)}/keys/clone`, { method: "POST", body: JSON.stringify({ source, no_secrets: true }) });
    renderKeystore();
  });
  document.getElementById("key-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const pairs = [];
    if (document.getElementById("es-url").value) pairs.push(`ELASTICSEARCH_URL=${document.getElementById("es-url").value}`);
    if (document.getElementById("es-key").value) pairs.push(`ES_API_KEY=${document.getElementById("es-key").value}`);
    await api(`/api/e/${encodeURIComponent(state.slug)}/keys/set`, { method: "POST", body: JSON.stringify({ pairs }) });
    document.getElementById("ks-msg").textContent = "Saved (values not shown).";
    document.getElementById("key-form").reset();
  });
}

function buildAgentPrompt(plan) {
  return [
    "Run warp-listen for this engagement using the plan below.",
    `Slug (verbatim): ${plan.slug}`,
    "Inputs:",
    ...(plan.inputs || []).map((i) => `  - ${i.file} (${i.sha256?.slice(0, 12)}…)`),
    "Write outputs:",
    ...(plan.outputs || []).map((o) => `  - ${o}`),
    "Contract:",
    ...(plan.contract || []).map((c) => `  - ${c}`),
    `Then run: loom_state listen record ${plan.slug}`,
  ].join("\n");
}

const TEXT_UPLOAD_RE = /\.(md|txt|markdown|csv|json|yml|yaml|log|html?)$/i;
const MAX_UI_UPLOAD = 20 * 1024 * 1024;

function basenameOnly(path) {
  return String(path || "").split(/[/\\]/).pop() || "upload.bin";
}

function arrayBufferToBase64(buf) {
  const bytes = new Uint8Array(buf);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

async function fileToUpload(file) {
  if (file.size > MAX_UI_UPLOAD) {
    throw new Error(`${file.name} exceeds 20 MiB UI limit — use loom_state inputs add`);
  }
  const filename = basenameOnly(file.name);
  if (TEXT_UPLOAD_RE.test(filename) || (file.type && file.type.startsWith("text/"))) {
    const content = await file.text();
    return { filename, content };
  }
  const buf = await file.arrayBuffer();
  return { filename, content_base64: arrayBufferToBase64(buf) };
}

async function filesFromInput(input) {
  const list = Array.from(input?.files || []);
  const uploads = [];
  for (const f of list) uploads.push(await fileToUpload(f));
  return uploads;
}

async function postUploads(slug, uploads) {
  if (!uploads.length) return;
  await api(`/api/e/${encodeURIComponent(slug)}/inputs`, {
    method: "POST",
    body: JSON.stringify({ uploads }),
  });
}

async function renderEvidence() {
  const gen = viewGen;
  const main = document.getElementById("main");
  if (!state.slug) {
    main.innerHTML = "<p class='beat'>Select an engagement on Overview first.</p>";
    return;
  }
  main.innerHTML = "<p class='beat'>Loading evidence…</p>";
  let plan;
  try {
    const p = await api(`/api/e/${encodeURIComponent(state.slug)}/listen/plan`);
    if (staleView(gen)) return;
    plan = p.data;
  } catch (e) {
    if (staleView(gen)) return;
    main.innerHTML = `<p class="callout" role="alert">${escapeHtml(e.message)}</p>`;
    return;
  }
  const gapsR = await api(`/api/e/${encodeURIComponent(state.slug)}/gaps`);
  if (staleView(gen)) return;
  const gaps = gapsR.data?.gaps || [];
  const claims = gapsR.data?.claims || [];
  const staleBlockers = (gapsR.state?.blockers || []).filter((b) => /stale/i.test(b));
  main.innerHTML = `
    <article class="frame">
      <p class="eyebrow">SB-03</p>
      <h2>Evidence · ${escapeHtml(state.slug)}</h2>
      ${staleBlockers.length ? `<p class="callout" role="alert"><strong>Inputs changed</strong> — ${escapeHtml(staleBlockers.join("; "))}. Re-run warp-listen in Cursor, then Check outputs.</p>` : ""}
      <h3>Inputs</h3>
      <p class="beat">Files land in <code>inputs/</code> under this engagement (source of truth for listen).</p>
      <ul class="list">${(plan.inputs || []).map((i) => `<li><span aria-hidden="true">📄</span><span>${escapeHtml(i.file)}<br><span class="meta">${escapeHtml(i.sha256 || "")}</span></span></li>`).join("") || "<li>No inputs yet</li>"}</ul>
      <form id="add-files" class="add-row">
        <div class="field"><label for="add-file">Add discovery docs</label>
          <input id="add-file" type="file" class="file-input" multiple
            accept=".md,.txt,.markdown,.csv,.json,.yml,.yaml,.log,.html,.htm,.pdf,.zip,text/*,application/pdf,application/zip">
        </div>
        <button type="submit" class="btn primary">Upload to inputs/</button>
        <p id="upload-msg" class="meta" role="status"></p>
      </form>
      <form id="add-input" class="add-row">
        <div class="field"><label for="add-text">Or paste a follow-up note</label><textarea id="add-text" class="fake-area" rows="4"></textarea></div>
        <button type="submit" class="btn">Add note file</button>
      </form>
      <h3>Agent hand-off</h3>
      <p class="beat">Run <code>warp-listen</code> in Cursor, then check outputs here.</p>
      <textarea id="agent-prompt" class="fake-area" rows="10" readonly aria-label="Copy agent prompt">${escapeHtml(buildAgentPrompt(plan))}</textarea>
      <div class="actions">
        <button type="button" id="copy-prompt" class="btn">Copy agent prompt</button>
        <button type="button" id="check-outputs" class="btn primary">Check outputs</button>
      </div>
      <p id="record-msg" class="meta" role="status"></p>
      <h3>Claims</h3>
      <ul class="list">${claims.map((c) => `<li><span></span><span>${escapeHtml(c.text || "")}<br><span class="meta">${escapeHtml(c.source_ref?.excerpt || "")}</span></span></li>`).join("") || "<li>No claims yet — run listen record after warp-listen.</li>"}</ul>
      <h3>Gaps inbox</h3>
      <ul class="list">${gaps.map((g) => `<li><span class="dot ${g.blocking ? "warn" : "ok"}"></span><span>${escapeHtml(g.gap_id)} — ${escapeHtml(g.question || "")}<br><span class="meta">Update in Inputs: ${escapeHtml(g.update_in || "")}</span></span>
        <button type="button" class="btn gap-respond" data-id="${escapeHtml(g.gap_id)}">Mark answered</button></li>`).join("") || "<li>No open gaps</li>"}</ul>
    </article>`;
  document.getElementById("copy-prompt").addEventListener("click", () => {
    navigator.clipboard.writeText(document.getElementById("agent-prompt").value);
  });
  document.getElementById("check-outputs").addEventListener("click", async () => {
    try {
      const r = await api(`/api/e/${encodeURIComponent(state.slug)}/listen/record`, { method: "POST", body: "{}" });
      const d = r.data;
      document.getElementById("record-msg").textContent =
        `Claims: ${d.claims} · Gaps: ${d.gaps}` + (d.closed_by_reinference?.length ? ` · Closed: ${d.closed_by_reinference.join(", ")}` : "");
      logActivity(`listen record · ${state.slug}`);
      renderEvidence();
    } catch (e) {
      document.getElementById("record-msg").textContent = e.message;
    }
  });
  document.getElementById("add-files").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const msg = document.getElementById("upload-msg");
    msg.textContent = "";
    try {
      const uploads = await filesFromInput(document.getElementById("add-file"));
      if (!uploads.length) {
        msg.textContent = "Choose one or more files first.";
        return;
      }
      await postUploads(state.slug, uploads);
      logActivity(`inputs add · ${uploads.map((u) => u.filename).join(", ")}`);
      renderEvidence();
    } catch (e) {
      msg.textContent = e.message;
    }
  });
  document.getElementById("add-input").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const content = document.getElementById("add-text").value;
    if (!content.trim()) return;
    const name = `follow-up-${Date.now()}.md`;
    await api(`/api/e/${encodeURIComponent(state.slug)}/inputs`, {
      method: "POST",
      body: JSON.stringify({ filename: name, content }),
    });
    logActivity(`inputs add · ${name}`);
    renderEvidence();
  });
  document.querySelectorAll(".gap-respond").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await api(`/api/e/${encodeURIComponent(state.slug)}/gaps/respond`, {
        method: "POST",
        body: JSON.stringify({ gap_id: btn.dataset.id, status: "answered", response: "Updated via UI" }),
      });
      renderEvidence();
    })
  );
}

document.querySelectorAll(".nav button[data-screen]").forEach((b) =>
  b.addEventListener("click", () => {
    bumpView();
    document.querySelectorAll(".nav button[data-screen]").forEach((x) => {
      x.setAttribute("aria-current", x.dataset.screen === b.dataset.screen ? "true" : "false");
    });
    ({ overview: renderOverview, create: renderCreate, keystore: renderKeystore, evidence: renderEvidence })[b.dataset.screen]?.();
  })
);

loadMeta()
  .then(() => {
    bumpView();
    document.querySelector('[data-screen="overview"]')?.setAttribute("aria-current", "true");
    return renderOverview();
  })
  .catch((e) => {
    document.getElementById("main").innerHTML = `<p class="callout">${escapeHtml(e.message)}</p>`;
  });
