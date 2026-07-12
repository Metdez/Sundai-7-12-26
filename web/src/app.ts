/**
 * Agent Debugger — web review client (PRD §10.3, FR-025, FR-026).
 * Read-heavy: browse runs, inspect timeline/scorecard/patch, trigger replay.
 * All scoring happens server-side; this client only renders API contracts.
 */

interface RunRow {
  run_id: string;
  scenario_id: string;
  agent_revision_id: string;
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

const $ = (sel: string): HTMLElement => {
  const el = document.querySelector(sel);
  if (!el) throw new Error(`missing element ${sel}`);
  return el as HTMLElement;
};

const esc = (value: unknown): string =>
  String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

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

// ---------------------------------------------------------------- run list
let selectedRun: string | null = null;

async function loadRuns(): Promise<void> {
  const runs = await fetchJson<RunRow[]>("/api/v1/runs?limit=200");
  const list = $("#run-list");
  list.innerHTML = runs.length
    ? runs
        .map(
          (run) => `
      <li>
        <button class="run-item ${run.run_id === selectedRun ? "selected" : ""}"
                data-run="${esc(run.run_id)}" aria-pressed="${run.run_id === selectedRun}">
          <span class="run-id">${esc(run.run_id)}</span>
          <span class="run-meta">${esc(run.scenario_id)} · seed ${run.seed}</span>
          <span class="run-meta">${badge(run.terminal_reason, run.status)}
            ${run.scorecard ? `<strong>${run.scorecard.overall_score}</strong>/100` : ""}</span>
        </button>
      </li>`
        )
        .join("")
    : "<li class='empty'>No runs yet. Start one with the CLI: <code>agent-debugger run …</code></li>";
  list.querySelectorAll<HTMLButtonElement>(".run-item").forEach((btn) => {
    btn.addEventListener("click", () => selectRun(btn.dataset.run!));
  });
}

// ---------------------------------------------------------------- run detail
function scorecardHtml(scorecard: Scorecard | null): string {
  if (!scorecard) return "<p>No scorecard (run not scored — infrastructure failures are never scored as agent failures).</p>";
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
             ${f.evidence.map((e) => `<a href="#evt-${esc(e.ref)}" class="evidence">${esc(e.ref)}</a>`).join(" ")}</div>`
        )
        .join("");
      return `<tr><th scope="row">${esc(dim.dimension)}</th>
              <td>${dim.score}</td><td>${dim.maximum}</td><td>${findings}</td></tr>`;
    })
    .join("");
  return `
    <p class="overall">Overall <strong>${scorecard.overall_score}</strong> / ${scorecard.overall_maximum}
       <small>(scorer v${esc(scorecard.scorer_version)})</small></p>
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
let activeFilters = new Set<string>(EVENT_FILTERS);

function renderTimeline(): void {
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
  $("#timeline").innerHTML = `<ol class="timeline">${rows}</ol>`;
}

async function selectRun(runId: string): Promise<void> {
  selectedRun = runId;
  const [run, events, report] = await Promise.all([
    fetchJson<RunRow>(`/api/v1/runs/${runId}`),
    fetchJson<RunEvent[]>(`/api/v1/runs/${runId}/events`),
    fetchJson<Record<string, any>>(`/api/v1/runs/${runId}/report`),
  ]);
  currentEvents = events;

  const manifest = (run as any).manifest ?? {};
  $("#detail-header").innerHTML = `
    <h2>${esc(run.run_id)} ${badge(run.terminal_reason, run.status)}</h2>
    <dl class="manifest">
      <dt>Scenario</dt><dd>${esc(run.scenario_id)} v${esc(manifest.scenario_version)}</dd>
      <dt>Agent</dt><dd><code>${esc(run.agent_revision_id)}</code></dd>
      <dt>Renderer</dt><dd>${esc(manifest.renderer)}</dd>
      <dt>Seed</dt><dd>${run.seed}</dd>
      <dt>Scenario digest</dt><dd><code>${esc(String(manifest.scenario_digest).slice(0, 16))}…</code></dd>
    </dl>
    <div class="actions">
      <button id="btn-replay">Verify replay</button>
      <a href="/api/v1/runs/${esc(runId)}/report.html" target="_blank" rel="noopener">HTML report</a>
      <a href="/api/v1/runs/${esc(runId)}/report.md" target="_blank" rel="noopener">Markdown</a>
    </div>
    <p id="replay-result" role="status"></p>`;
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

  $("#scorecard").innerHTML = scorecardHtml(run.scorecard);

  const patch = report.timeline
    ? await fetch(`/api/v1/runs/${runId}/report`).then(() => report.outcome?.changed_files ?? {})
    : {};
  const changed = Object.entries(patch as Record<string, string>);
  $("#patch").innerHTML = changed.length
    ? `<ul>${changed.map(([p, k]) => `<li><code>${esc(p)}</code> <em>${esc(k)}</em></li>`).join("")}</ul>`
    : "<p>No files changed.</p>";

  renderTimeline();
  await loadRuns();
}

// ---------------------------------------------------------------- filters + boot
function buildFilters(): void {
  $("#filters").innerHTML = EVENT_FILTERS.map(
    (f) => `
    <label><input type="checkbox" data-filter="${f}" checked> ${f}</label>`
  ).join("");
  document.querySelectorAll<HTMLInputElement>("#filters input").forEach((box) => {
    box.addEventListener("change", () => {
      if (box.checked) activeFilters.add(box.dataset.filter!);
      else activeFilters.delete(box.dataset.filter!);
      renderTimeline();
    });
  });
}

async function boot(): Promise<void> {
  buildFilters();
  await loadRuns();
  setInterval(loadRuns, 5000);
}

boot().catch((err) => {
  $("#run-list").innerHTML = `<li class="empty">Failed to reach API: ${esc(String(err))}</li>`;
});
