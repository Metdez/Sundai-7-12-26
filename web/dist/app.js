// src/app.ts
var $ = (sel) => {
  const el = document.querySelector(sel);
  if (!el)
    throw new Error(`missing element ${sel}`);
  return el;
};
var esc = (value) => String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
async function fetchJson(url, init) {
  const response = await fetch(url, init);
  if (!response.ok)
    throw new Error(`${url}: HTTP ${response.status}`);
  return await response.json();
}
function badge(reason, status) {
  const label = reason ?? status;
  const cls = reason === "success" ? "ok" : status === "running" || status === "queued" ? "busy" : "bad";
  return `<span class="badge ${cls}">${esc(label)}</span>`;
}
function agentLabel(run) {
  if (run.agent_name && run.agent_model)
    return `${run.agent_name} (${run.agent_model})`;
  if (run.agent_name)
    return run.agent_name;
  if (run.agent_model)
    return run.agent_model;
  return run.agent_revision_id;
}
function parseHash() {
  const hash = window.location.hash.replace(/^#\/?/, "");
  const parts = hash.split("/").filter(Boolean);
  if (parts[0] === "run" && parts[1])
    return { view: "run", runId: parts[1] };
  if (parts[0] === "compare" && parts[1] && parts[2])
    return { view: "compare", a: parts[1], b: parts[2] };
  if (parts[0] === "rubric")
    return { view: "rubric" };
  return { view: "home" };
}
var currentRoute = { view: "home" };
async function render() {
  currentRoute = parseHash();
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    const active = tab.dataset.view === "home" && currentRoute.view === "home" || tab.dataset.view === "rubric" && currentRoute.view === "rubric";
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-current", active ? "page" : "false");
  });
  const view = $("#view");
  try {
    if (currentRoute.view === "home")
      await renderHome(view);
    else if (currentRoute.view === "run")
      await renderRunPage(view, currentRoute.runId);
    else if (currentRoute.view === "compare")
      await renderComparePage(view, currentRoute.a, currentRoute.b);
    else
      await renderRubricPage(view);
  } catch (err) {
    view.innerHTML = `<p class="empty">Failed to load: ${esc(String(err))}</p>`;
  }
}
var compareSelection = /* @__PURE__ */ new Set();
function runCard(run) {
  const checked = compareSelection.has(run.run_id) ? "checked" : "";
  return `
    <li class="run-card">
      <label class="compare-pick" title="Select for comparison">
        <input type="checkbox" data-pick="${esc(run.run_id)}" ${checked}
               aria-label="Select ${esc(run.run_id)} for comparison">
      </label>
      <a class="run-link" href="#/run/${esc(run.run_id)}" target="_blank" rel="noopener">
        <span class="run-id">${esc(run.run_id)}</span>
        <span class="run-meta">${esc(run.scenario_id)} \xB7 seed ${run.seed}</span>
        <span class="run-meta">${esc(agentLabel(run))}</span>
        <span class="run-meta">${badge(run.terminal_reason, run.status)}
          ${run.scorecard ? `<strong>${run.scorecard.overall_score}</strong>/100` : ""}</span>
      </a>
    </li>`;
}
async function renderHome(view) {
  const runs = await fetchJson("/api/v1/runs?limit=200");
  if (parseHash().view !== "home")
    return;
  const cards = runs.length ? runs.map(runCard).join("") : "<li class='empty'>No runs yet. Start one with the CLI: <code>agent-debugger run \u2026</code></li>";
  view.innerHTML = `
    <section class="home" aria-label="Runs">
      <div class="home-head">
        <h2>Runs</h2>
        <p class="hint">Click a run to open it in a new tab. Tick two boxes to compare runs side by side.</p>
        <button id="btn-compare" class="compare-btn" disabled>Select 2 runs to compare</button>
      </div>
      <ul class="run-grid">${cards}</ul>
    </section>`;
  wireHomeControls();
}
function wireHomeControls() {
  const button = document.getElementById("btn-compare");
  if (!button)
    return;
  const sync = () => {
    const picked = [...compareSelection];
    button.disabled = picked.length !== 2;
    button.textContent = picked.length === 2 ? `Compare ${picked[0]} vs ${picked[1]}` : `Select 2 runs to compare (${picked.length}/2)`;
  };
  document.querySelectorAll("input[data-pick]").forEach((box) => {
    box.addEventListener("change", () => {
      const id = box.dataset.pick;
      if (box.checked) {
        if (compareSelection.size >= 2) {
          box.checked = false;
          return;
        }
        compareSelection.add(id);
      } else {
        compareSelection.delete(id);
      }
      sync();
    });
  });
  button.addEventListener("click", () => {
    const [a, b] = [...compareSelection];
    if (a && b)
      window.open(`#/compare/${a}/${b}`, "_blank", "noopener");
  });
  sync();
}
function scorecardHtml(scorecard) {
  if (!scorecard)
    return "<p>No scorecard (run not scored \u2014 infrastructure failures are never scored as agent failures).</p>";
  const rows = scorecard.dimensions.map((dim) => {
    if (dim.not_applicable) {
      return `<tr><th scope="row">${esc(dim.dimension)}</th><td>\u2013</td><td>${dim.maximum}</td>
                <td>N/A \u2014 ${esc(dim.na_reason)}</td></tr>`;
    }
    const findings = dim.findings.map(
      (f) => `<div class="finding"><code>${esc(f.code)}</code> ${esc(f.summary)}
             ${f.evidence.map((e) => `<span class="evidence">${esc(e.ref)}</span>`).join(" ")}</div>`
    ).join("");
    return `<tr><th scope="row">${esc(dim.dimension)}</th>
              <td>${dim.score}</td><td>${dim.maximum}</td><td>${findings}</td></tr>`;
  }).join("");
  return `
    <p class="overall">Overall <strong>${scorecard.overall_score}</strong> / ${scorecard.overall_maximum}
       <small>(scorer v${esc(scorecard.scorer_version)})</small>
       <a class="rubric-link" href="#/rubric" target="_blank" rel="noopener">How is this graded?</a></p>
    <table aria-label="Scorecard">
      <thead><tr><th scope="col">Dimension</th><th scope="col">Score</th>
                 <th scope="col">Max</th><th scope="col">Findings & evidence</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}
function eventBody(event) {
  const p = event.payload;
  switch (event.event_type) {
    case "agent.action": {
      const action = p.action ?? {};
      return `<code>${esc(action.action_type)}</code> ${esc(JSON.stringify(action.params ?? {}))}` + (action.thought ? `<div class="thought">\u{1F4AD} ${esc(action.thought)}</div>` : "");
    }
    case "policy.decision":
      return `${esc(p.decision)} \xB7 class=${esc(p.action_class)} \xB7 ${esc(p.reason)}`;
    case "state.transition":
      return `${p.ok ? "ok" : `error: ${esc(p.error?.code)}`} \xB7 hash <code>${esc(String(p.state_hash).slice(0, 12))}\u2026</code>` + (Array.isArray(p.changed_paths) && p.changed_paths.length ? ` \xB7 changed: ${p.changed_paths.map(esc).join(", ")}` : "");
    case "observation.rendered":
      return `<details><summary>${esc(p.status)} \xB7 source=${esc(p.source)}</summary><pre>${esc(p.body)}</pre></details>`;
    case "run.terminal":
      return `<strong>${esc(p.reason)}</strong> \xB7 final hash <code>${esc(String(p.final_state_hash).slice(0, 12))}\u2026</code>`;
    case "score.completed":
      return `overall ${esc(p.overall)}`;
    default:
      return `<details><summary>payload</summary><pre>${esc(JSON.stringify(p, null, 1))}</pre></details>`;
  }
}
var EVENT_FILTERS = [
  "agent.action",
  "policy.decision",
  "state.transition",
  "observation.rendered",
  "renderer.fallback",
  "run.limit",
  "run.error",
  "run.terminal",
  "score.completed"
];
var currentEvents = [];
var activeFilters = new Set(EVENT_FILTERS);
function renderTimeline() {
  const container = document.getElementById("timeline");
  if (!container)
    return;
  const rows = currentEvents.filter((e) => activeFilters.has(e.event_type) || !EVENT_FILTERS.includes(e.event_type)).map((e) => {
    const safety = e.event_type === "policy.decision" && e.payload.decision !== "allow" ? " safety" : "";
    return `<li id="evt-${esc(e.event_id)}" class="evt ${esc(e.event_type.replace(/\./g, "-"))}${safety}">
        <span class="seq">#${e.seq}</span>
        <span class="etype">${esc(e.event_type)}</span>
        <span class="ebody">${eventBody(e)}</span>
      </li>`;
  }).join("");
  container.innerHTML = `<ol class="timeline">${rows}</ol>`;
}
async function renderRunPage(view, runId) {
  const [run, events, report] = await Promise.all([
    fetchJson(`/api/v1/runs/${runId}`),
    fetchJson(`/api/v1/runs/${runId}/events`),
    fetchJson(`/api/v1/runs/${runId}/report`)
  ]);
  const route = parseHash();
  if (route.view !== "run" || route.runId !== runId)
    return;
  currentEvents = events;
  const manifest = run.manifest ?? {};
  const changed = Object.entries(
    report.outcome?.changed_files ?? {}
  );
  view.innerHTML = `
    <section class="run-page" aria-label="Run detail">
      <div id="detail-header">
        <h2>${esc(run.run_id)} ${badge(run.terminal_reason, run.status)}</h2>
        <dl class="manifest">
          <dt>Scenario</dt><dd>${esc(run.scenario_id)} v${esc(manifest.scenario_version)}</dd>
          <dt>Agent</dt><dd>${esc(agentLabel(run))} <code class="agent-rev">${esc(run.agent_revision_id)}</code></dd>
          <dt>Renderer</dt><dd>${esc(manifest.renderer)}</dd>
          <dt>Seed</dt><dd>${run.seed}</dd>
          <dt>Scenario digest</dt><dd><code>${esc(String(manifest.scenario_digest).slice(0, 16))}\u2026</code></dd>
        </dl>
        <div class="actions">
          <button id="btn-replay">Verify replay</button>
          <a href="/api/v1/runs/${esc(runId)}/report.html" target="_blank" rel="noopener">HTML report</a>
          <a href="/api/v1/runs/${esc(runId)}/report.md" target="_blank" rel="noopener">Markdown</a>
        </div>
        <p id="replay-result" role="status"></p>
      </div>
      <h3>Scorecard</h3>
      <div id="scorecard">${scorecardHtml(run.scorecard)}</div>
      <h3>Changed files</h3>
      <div id="patch">${changed.length ? `<ul>${changed.map(([p, k]) => `<li><code>${esc(p)}</code> <em>${esc(k)}</em></li>`).join("")}</ul>` : "<p>No files changed.</p>"}</div>
      <h3>Timeline</h3>
      <fieldset id="filters" class="filters" aria-label="Event type filters"></fieldset>
      <div id="timeline"></div>
    </section>`;
  $("#btn-replay").addEventListener("click", async () => {
    $("#replay-result").textContent = "Replaying\u2026";
    try {
      const result = await fetchJson(`/api/v1/runs/${runId}/replay`, {
        method: "POST"
      });
      $("#replay-result").textContent = result.match ? `\u2714 Replay matches (${result.transitions_replayed} transitions, chain verified)` : `\u2718 Divergence at seq ${result.divergence?.seq}`;
    } catch (err) {
      $("#replay-result").textContent = `Replay failed: ${err}`;
    }
  });
  $("#filters").innerHTML = EVENT_FILTERS.map(
    (f) => `
    <label><input type="checkbox" data-filter="${f}" ${activeFilters.has(f) ? "checked" : ""}> ${f}</label>`
  ).join("");
  document.querySelectorAll("#filters input").forEach((box) => {
    box.addEventListener("change", () => {
      if (box.checked)
        activeFilters.add(box.dataset.filter);
      else
        activeFilters.delete(box.dataset.filter);
      renderTimeline();
    });
  });
  renderTimeline();
}
function metricCell(value) {
  return value === null || value === void 0 ? "\u2013" : esc(value);
}
async function renderComparePage(view, a, b) {
  const [runA, runB] = await Promise.all([
    fetchJson(`/api/v1/runs/${a}`),
    fetchJson(`/api/v1/runs/${b}`)
  ]);
  const route = parseHash();
  if (route.view !== "compare" || route.a !== a || route.b !== b)
    return;
  const dims = /* @__PURE__ */ new Map();
  for (const d of runA.scorecard?.dimensions ?? [])
    dims.set(d.dimension, { a: d });
  for (const d of runB.scorecard?.dimensions ?? []) {
    dims.set(d.dimension, { ...dims.get(d.dimension) ?? {}, b: d });
  }
  const dimRows = [...dims.entries()].map(([name, pair]) => {
    const scoreOf = (d) => d && !d.not_applicable ? d.score : null;
    const sa = scoreOf(pair.a);
    const sb = scoreOf(pair.b);
    let delta = "\u2013";
    let deltaClass = "";
    if (sa !== null && sb !== null) {
      const diff = Math.round((sb - sa) * 100) / 100;
      delta = diff > 0 ? `+${diff}` : `${diff}`;
      deltaClass = diff > 0 ? "delta-up" : diff < 0 ? "delta-down" : "";
    }
    const show = (d) => d ? d.not_applicable ? `N/A` : `${d.score}` : "\u2013";
    return `<tr><th scope="row">${esc(name)}</th>
        <td>${show(pair.a)}</td><td>${show(pair.b)}</td>
        <td class="${deltaClass}">${delta}</td></tr>`;
  }).join("");
  const overall = (run) => run.scorecard ? `<strong>${run.scorecard.overall_score}</strong>/100` : "not scored";
  const metricsRow = (key, label) => `<tr><th scope="row">${esc(label)}</th>
     <td>${metricCell(runA.metrics?.[key])}</td>
     <td>${metricCell(runB.metrics?.[key])}</td><td></td></tr>`;
  const head = (run) => `
    <a href="#/run/${esc(run.run_id)}" target="_blank" rel="noopener"><code>${esc(run.run_id)}</code></a>
    <div>${esc(run.scenario_id)} \xB7 seed ${run.seed}</div>
    <div>${esc(agentLabel(run))}</div>
    <div>${badge(run.terminal_reason, run.status)} ${overall(run)}</div>`;
  view.innerHTML = `
    <section class="compare-page" aria-label="Run comparison">
      <h2>Compare runs <a class="rubric-link" href="#/rubric" target="_blank" rel="noopener">How is this graded?</a></h2>
      <table class="compare-table">
        <thead>
          <tr><th></th><th>${head(runA)}</th><th>${head(runB)}</th><th>\u0394 (B \u2212 A)</th></tr>
        </thead>
        <tbody>
          ${dimRows}
          <tr class="metrics-divider"><th colspan="4">Metrics</th></tr>
          ${metricsRow("actions", "actions taken")}
          ${metricsRow("invalid_actions", "invalid actions")}
          ${metricsRow("tokens_used", "tokens used")}
          ${metricsRow("elapsed_seconds", "elapsed seconds")}
        </tbody>
      </table>
      <p class="hint">Dimension scores are each out of 10 \u2014 see the rubric for the exact rules and weights.</p>
    </section>`;
}
async function renderRubricPage(view) {
  const rubric = await fetchJson("/api/v1/scoring/rubric");
  if (parseHash().view !== "rubric")
    return;
  const weightRows = Object.entries(rubric.weights).map(
    ([dim, w]) => `<tr><th scope="row">${esc(dim)}</th><td>${Math.round(w * 100)}%</td><td>${rubric.max_per_dimension}</td></tr>`
  ).join("");
  const dimSections = rubric.dimensions.map((dim) => {
    const rules = dim.rules.map(
      (r) => `<tr><td><code>${esc(r.code)}</code></td>
            <td class="${r.points < 0 ? "delta-down" : ""}">${r.points > 0 ? "+" : ""}${r.points}</td>
            <td>${esc(r.description)}</td></tr>`
    ).join("");
    const formula = dim.formula ? `<p class="formula"><strong>Formula:</strong> <code>${esc(dim.formula)}</code></p>` + (dim.example ? `<p class="formula">Worked example: ${dim.example.actions} actions vs par ${dim.example.par} \u2192 <code>${esc(dim.example.computation)}</code></p>` : "") + (dim.par_source ? `<p class="hint">par comes from: ${esc(dim.par_source)}</p>` : "") : "";
    return `
        <details class="rubric-dim" open>
          <summary><strong>${esc(dim.name)}</strong> \u2014 weight ${Math.round(dim.weight * 100)}% \xB7 ${esc(dim.kind)}</summary>
          ${formula}
          ${rules ? `<table><thead><tr><th>Rule</th><th>Points</th><th>When it applies</th></tr></thead><tbody>${rules}</tbody></table>` : ""}
          ${dim.notes ? `<p class="hint">${esc(dim.notes)}</p>` : ""}
        </details>`;
  }).join("");
  view.innerHTML = `
    <section class="rubric-page" aria-label="Scoring rubric">
      <h2>How runs are graded <small>(scorer v${esc(rubric.scorer_version)})</small></h2>
      <p>${esc(rubric.overall_formula)}</p>
      <h3>Dimension weights</h3>
      <table class="weights-table">
        <thead><tr><th>Dimension</th><th>Weight</th><th>Max score</th></tr></thead>
        <tbody>${weightRows}</tbody>
      </table>
      <h3>Rules per dimension</h3>
      ${dimSections}
      <p class="provenance">${esc(rubric.provenance)}</p>
    </section>`;
}
window.addEventListener("hashchange", () => {
  void render();
});
setInterval(() => {
  if (currentRoute.view === "home")
    void render();
}, 5e3);
void render();
