/**
 * Agent Debugger — web review client (PRD §10.3, FR-025, FR-026).
 * Hash-routed views: #/ (runs), #/run/<id>, #/compare/<a>/<b>, #/rubric.
 * All scoring happens server-side; this client only renders API contracts.
 */

interface RunRow {
  run_id: string;
  scenario_id: string;
  agent_revision_id: string;
  agent_name: string | null;
  agent_model: string | null;
  status: string;
  terminal_reason: string | null;
  seed: number;
  suite_id: string | null;
  created_at: string;
  scorecard: Scorecard | null;
  metrics: Record<string, number> | null;
}

interface Finding {
  code: string;
  summary: string;
  delta: number;
  evidence: { kind: string; ref: string }[];
}

interface Dimension {
  dimension: string;
  score: number;
  maximum: number;
  not_applicable?: boolean;
  na_reason?: string | null;
  findings: Finding[];
}

interface Scorecard {
  overall_score: number;
  overall_maximum: number;
  scorer_version: string;
  dimensions: Dimension[];
}

interface RunEvent {
  seq: number;
  event_id: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

interface RubricRule {
  code: string;
  points: number;
  description: string;
}

interface RubricDimension {
  name: string;
  weight: number;
  kind: string;
  rules: RubricRule[];
  notes?: string;
  formula?: string;
  par_source?: string;
  example?: { actions: number; par: number; computation: string };
}

interface Rubric {
  scorer_version: string;
  max_per_dimension: number;
  overall_formula: string;
  weights: Record<string, number>;
  dimensions: RubricDimension[];
  provenance: string;
}

const $ = (sel: string): HTMLElement => {
  const el = document.querySelector(sel);
  if (!el) throw new Error(`missing element ${sel}`);
  return el as HTMLElement;
};

const esc = (value: unknown): string =>
  String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return (await response.json()) as T;
}

function badge(reason: string | null, status: string): string {
  const label = reason ?? status;
  const cls =
    reason === "success" ? "ok" : status === "running" || status === "queued" ? "busy" : "bad";
  return `<span class="badge ${cls}">${esc(label)}</span>`;
}

function agentLabel(run: RunRow): string {
  if (run.agent_name && run.agent_model) return `${run.agent_name} (${run.agent_model})`;
  if (run.agent_name) return run.agent_name;
  if (run.agent_model) return run.agent_model;
  return run.agent_revision_id;
}

// ------------------------------------------------------------------ router
type Route =
  | { view: "home" }
  | { view: "run"; runId: string }
  | { view: "compare"; a: string; b: string }
  | { view: "rubric" };

function parseHash(): Route {
  const hash = window.location.hash.replace(/^#\/?/, "");
  const parts = hash.split("/").filter(Boolean);
  if (parts[0] === "run" && parts[1]) return { view: "run", runId: parts[1] };
  if (parts[0] === "compare" && parts[1] && parts[2])
    return { view: "compare", a: parts[1], b: parts[2] };
  if (parts[0] === "rubric") return { view: "rubric" };
  return { view: "home" };
}

let currentRoute: Route = { view: "home" };

async function render(): Promise<void> {
  currentRoute = parseHash();
  document.querySelectorAll<HTMLAnchorElement>(".nav-tab").forEach((tab) => {
    const active =
      (tab.dataset.view === "home" && currentRoute.view === "home") ||
      (tab.dataset.view === "rubric" && currentRoute.view === "rubric");
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-current", active ? "page" : "false");
  });
  const view = $("#view");
  try {
    if (currentRoute.view === "home") await renderHome(view);
    else if (currentRoute.view === "run") await renderRunPage(view, currentRoute.runId);
    else if (currentRoute.view === "compare")
      await renderComparePage(view, currentRoute.a, currentRoute.b);
    else await renderRubricPage(view);
  } catch (err) {
    view.innerHTML = `<p class="empty">Failed to load: ${esc(String(err))}</p>`;
  }
}

// ------------------------------------------------------------------- home
const compareSelection = new Set<string>();

function runCard(run: RunRow): string {
  const checked = compareSelection.has(run.run_id) ? "checked" : "";
  return `
    <li class="run-card">
      <label class="compare-pick" title="Select for comparison">
        <input type="checkbox" data-pick="${esc(run.run_id)}" ${checked}
               aria-label="Select ${esc(run.run_id)} for comparison">
      </label>
      <a class="run-link" href="#/run/${esc(run.run_id)}" target="_blank" rel="noopener">
        <span class="run-id">${esc(run.run_id)}</span>
        <span class="run-meta">${esc(run.scenario_id)} · seed ${run.seed}</span>
        <span class="run-meta">${esc(agentLabel(run))}</span>
        <span class="run-meta">${badge(run.terminal_reason, run.status)}
          ${run.scorecard ? `<strong>${run.scorecard.overall_score}</strong>/100` : ""}</span>
      </a>
    </li>`;
}

async function renderHome(view: HTMLElement): Promise<void> {
  const runs = await fetchJson<RunRow[]>("/api/v1/runs?limit=200");
  // A fetch started on one route must never paint after the route changed
  // (e.g. the 5s home poll finishing after the user navigated to a run page).
  if (parseHash().view !== "home") return;
  const cards = runs.length
    ? runs.map(runCard).join("")
    : "<li class='empty'>No runs yet. Start one with the CLI: <code>agent-debugger run …</code></li>";
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

function wireHomeControls(): void {
  const button = document.getElementById("btn-compare") as HTMLButtonElement | null;
  if (!button) return;

  const sync = () => {
    const picked = [...compareSelection];
    button.disabled = picked.length !== 2;
    button.textContent =
      picked.length === 2
        ? `Compare ${picked[0]} vs ${picked[1]}`
        : `Select 2 runs to compare (${picked.length}/2)`;
  };
  document.querySelectorAll<HTMLInputElement>("input[data-pick]").forEach((box) => {
    box.addEventListener("change", () => {
      const id = box.dataset.pick!;
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
    if (a && b) window.open(`#/compare/${a}/${b}`, "_blank", "noopener");
  });
  sync();
}

// --------------------------------------------------------------- run page
function scorecardHtml(scorecard: Scorecard | null): string {
  if (!scorecard)
    return "<p>No scorecard (run not scored — infrastructure failures are never scored as agent failures).</p>";
  const rows = scorecard.dimensions
    .map((dim) => {
      if (dim.not_applicable) {
        return `<tr><th scope="row">${esc(dim.dimension)}</th><td>–</td><td>${dim.maximum}</td>
                <td>N/A — ${esc(dim.na_reason)}</td></tr>`;
      }
      const findings = dim.findings
        .map(
          (f) =>
            `<div class="finding"><code>${esc(f.code)}</code> ${esc(f.summary)}
             ${f.evidence.map((e) => `<span class="evidence">${esc(e.ref)}</span>`).join(" ")}</div>`
        )
        .join("");
      return `<tr><th scope="row">${esc(dim.dimension)}</th>
              <td>${dim.score}</td><td>${dim.maximum}</td><td>${findings}</td></tr>`;
    })
    .join("");
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

function eventBody(event: RunEvent): string {
  const p = event.payload as Record<string, any>;
  switch (event.event_type) {
    case "agent.action": {
      const action = p.action ?? {};
      return `<code>${esc(action.action_type)}</code> ${esc(JSON.stringify(action.params ?? {}))}` +
        (action.thought ? `<div class="thought">💭 ${esc(action.thought)}</div>` : "");
    }
    case "policy.decision":
      return `${esc(p.decision)} · class=${esc(p.action_class)} · ${esc(p.reason)}`;
    case "state.transition":
      return `${p.ok ? "ok" : `error: ${esc(p.error?.code)}`} · hash <code>${esc(String(p.state_hash).slice(0, 12))}…</code>` +
        (Array.isArray(p.changed_paths) && p.changed_paths.length
          ? ` · changed: ${p.changed_paths.map(esc).join(", ")}`
          : "");
    case "observation.rendered":
      return `<details><summary>${esc(p.status)} · source=${esc(p.source)}</summary><pre>${esc(p.body)}</pre></details>`;
    case "run.terminal":
      return `<strong>${esc(p.reason)}</strong> · final hash <code>${esc(String(p.final_state_hash).slice(0, 12))}…</code>`;
    case "score.completed":
      return `overall ${esc(p.overall)}`;
    default:
      return `<details><summary>payload</summary><pre>${esc(JSON.stringify(p, null, 1))}</pre></details>`;
  }
}

const EVENT_FILTERS = [
  "agent.action",
  "policy.decision",
  "state.transition",
  "observation.rendered",
  "renderer.fallback",
  "run.limit",
  "run.error",
  "run.terminal",
  "score.completed",
];

let currentEvents: RunEvent[] = [];
const activeFilters = new Set<string>(EVENT_FILTERS);

function renderTimeline(): void {
  const container = document.getElementById("timeline");
  if (!container) return;
  const rows = currentEvents
    .filter((e) => activeFilters.has(e.event_type) || !EVENT_FILTERS.includes(e.event_type))
    .map((e) => {
      const safety =
        e.event_type === "policy.decision" && (e.payload as any).decision !== "allow"
          ? " safety"
          : "";
      return `<li id="evt-${esc(e.event_id)}" class="evt ${esc(e.event_type.replace(/\./g, "-"))}${safety}">
        <span class="seq">#${e.seq}</span>
        <span class="etype">${esc(e.event_type)}</span>
        <span class="ebody">${eventBody(e)}</span>
      </li>`;
    })
    .join("");
  container.innerHTML = `<ol class="timeline">${rows}</ol>`;
}

async function renderRunPage(view: HTMLElement, runId: string): Promise<void> {
  const [run, events, report] = await Promise.all([
    fetchJson<RunRow>(`/api/v1/runs/${runId}`),
    fetchJson<RunEvent[]>(`/api/v1/runs/${runId}/events`),
    fetchJson<Record<string, any>>(`/api/v1/runs/${runId}/report`),
  ]);
  const route = parseHash();
  if (route.view !== "run" || route.runId !== runId) return;
  currentEvents = events;

  const manifest = (run as any).manifest ?? {};
  const changed = Object.entries(
    (report.outcome?.changed_files ?? {}) as Record<string, string>
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
          <dt>Scenario digest</dt><dd><code>${esc(String(manifest.scenario_digest).slice(0, 16))}…</code></dd>
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
      <div id="patch">${
        changed.length
          ? `<ul>${changed.map(([p, k]) => `<li><code>${esc(p)}</code> <em>${esc(k)}</em></li>`).join("")}</ul>`
          : "<p>No files changed.</p>"
      }</div>
      <h3>Timeline</h3>
      <fieldset id="filters" class="filters" aria-label="Event type filters"></fieldset>
      <div id="timeline"></div>
    </section>`;

  $("#btn-replay").addEventListener("click", async () => {
    $("#replay-result").textContent = "Replaying…";
    try {
      const result = await fetchJson<Record<string, any>>(`/api/v1/runs/${runId}/replay`, {
        method: "POST",
      });
      $("#replay-result").textContent = result.match
        ? `✔ Replay matches (${result.transitions_replayed} transitions, chain verified)`
        : `✘ Divergence at seq ${result.divergence?.seq}`;
    } catch (err) {
      $("#replay-result").textContent = `Replay failed: ${err}`;
    }
  });

  $("#filters").innerHTML = EVENT_FILTERS.map(
    (f) => `
    <label><input type="checkbox" data-filter="${f}" ${activeFilters.has(f) ? "checked" : ""}> ${f}</label>`
  ).join("");
  document.querySelectorAll<HTMLInputElement>("#filters input").forEach((box) => {
    box.addEventListener("change", () => {
      if (box.checked) activeFilters.add(box.dataset.filter!);
      else activeFilters.delete(box.dataset.filter!);
      renderTimeline();
    });
  });
  renderTimeline();
}

// ------------------------------------------------------------ compare page
function metricCell(value: unknown): string {
  return value === null || value === undefined ? "–" : esc(value);
}

async function renderComparePage(view: HTMLElement, a: string, b: string): Promise<void> {
  const [runA, runB] = await Promise.all([
    fetchJson<RunRow>(`/api/v1/runs/${a}`),
    fetchJson<RunRow>(`/api/v1/runs/${b}`),
  ]);
  const route = parseHash();
  if (route.view !== "compare" || route.a !== a || route.b !== b) return;

  const dims = new Map<string, { a?: Dimension; b?: Dimension }>();
  for (const d of runA.scorecard?.dimensions ?? []) dims.set(d.dimension, { a: d });
  for (const d of runB.scorecard?.dimensions ?? []) {
    dims.set(d.dimension, { ...(dims.get(d.dimension) ?? {}), b: d });
  }

  const dimRows = [...dims.entries()]
    .map(([name, pair]) => {
      const scoreOf = (d?: Dimension) => (d && !d.not_applicable ? d.score : null);
      const sa = scoreOf(pair.a);
      const sb = scoreOf(pair.b);
      let delta = "–";
      let deltaClass = "";
      if (sa !== null && sb !== null) {
        const diff = Math.round((sb - sa) * 100) / 100;
        delta = diff > 0 ? `+${diff}` : `${diff}`;
        deltaClass = diff > 0 ? "delta-up" : diff < 0 ? "delta-down" : "";
      }
      const show = (d?: Dimension) =>
        d ? (d.not_applicable ? `N/A` : `${d.score}`) : "–";
      return `<tr><th scope="row">${esc(name)}</th>
        <td>${show(pair.a)}</td><td>${show(pair.b)}</td>
        <td class="${deltaClass}">${delta}</td></tr>`;
    })
    .join("");

  const overall = (run: RunRow) =>
    run.scorecard ? `<strong>${run.scorecard.overall_score}</strong>/100` : "not scored";
  const metricsRow = (key: string, label: string) =>
    `<tr><th scope="row">${esc(label)}</th>
     <td>${metricCell(runA.metrics?.[key])}</td>
     <td>${metricCell(runB.metrics?.[key])}</td><td></td></tr>`;

  const head = (run: RunRow) => `
    <a href="#/run/${esc(run.run_id)}" target="_blank" rel="noopener"><code>${esc(run.run_id)}</code></a>
    <div>${esc(run.scenario_id)} · seed ${run.seed}</div>
    <div>${esc(agentLabel(run))}</div>
    <div>${badge(run.terminal_reason, run.status)} ${overall(run)}</div>`;

  view.innerHTML = `
    <section class="compare-page" aria-label="Run comparison">
      <h2>Compare runs <a class="rubric-link" href="#/rubric" target="_blank" rel="noopener">How is this graded?</a></h2>
      <table class="compare-table">
        <thead>
          <tr><th></th><th>${head(runA)}</th><th>${head(runB)}</th><th>Δ (B − A)</th></tr>
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
      <p class="hint">Dimension scores are each out of 10 — see the rubric for the exact rules and weights.</p>
    </section>`;
}

// ------------------------------------------------------------- rubric page
async function renderRubricPage(view: HTMLElement): Promise<void> {
  const rubric = await fetchJson<Rubric>("/api/v1/scoring/rubric");
  if (parseHash().view !== "rubric") return;

  const weightRows = Object.entries(rubric.weights)
    .map(
      ([dim, w]) =>
        `<tr><th scope="row">${esc(dim)}</th><td>${Math.round(w * 100)}%</td><td>${rubric.max_per_dimension}</td></tr>`
    )
    .join("");

  const dimSections = rubric.dimensions
    .map((dim) => {
      const rules = dim.rules
        .map(
          (r) => `<tr><td><code>${esc(r.code)}</code></td>
            <td class="${r.points < 0 ? "delta-down" : ""}">${r.points > 0 ? "+" : ""}${r.points}</td>
            <td>${esc(r.description)}</td></tr>`
        )
        .join("");
      const formula = dim.formula
        ? `<p class="formula"><strong>Formula:</strong> <code>${esc(dim.formula)}</code></p>` +
          (dim.example
            ? `<p class="formula">Worked example: ${dim.example.actions} actions vs par ${dim.example.par} → <code>${esc(dim.example.computation)}</code></p>`
            : "") +
          (dim.par_source ? `<p class="hint">par comes from: ${esc(dim.par_source)}</p>` : "")
        : "";
      return `
        <details class="rubric-dim" open>
          <summary><strong>${esc(dim.name)}</strong> — weight ${Math.round(dim.weight * 100)}% · ${esc(dim.kind)}</summary>
          ${formula}
          ${rules ? `<table><thead><tr><th>Rule</th><th>Points</th><th>When it applies</th></tr></thead><tbody>${rules}</tbody></table>` : ""}
          ${dim.notes ? `<p class="hint">${esc(dim.notes)}</p>` : ""}
        </details>`;
    })
    .join("");

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

// ------------------------------------------------------------------- boot
window.addEventListener("hashchange", () => {
  void render();
});

setInterval(() => {
  if (currentRoute.view === "home") void render();
}, 5000);

void render();
