/**
 * Agent Debugger — web review client (PRD §10.3, FR-025, FR-026).
 * Hash-routed views: #/ (overview: leaderboard + matrix), #/scenarios,
 * #/scenario/<id>, #/runs (filterable table), #/run/<id>,
 * #/compare/<a>/<b>, #/rubric.
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

interface ScenarioListRow {
  scenario_id: string;
  version: string;
  title: string;
  difficulty: string;
  tags: string[];
  registered_at: string;
  task?: string | null;
  par_actions?: number | null;
  failure_type?: string | null;
  language?: string | null;
  framework?: string | null;
}

interface ScenarioGuide {
  summary?: string;
  what_it_tests?: string[];
  the_trap?: string | null;
  planted_bug?: string | null;
  ideal_path?: string[];
  success_criteria?: string[];
  scoring_notes?: string[];
  common_failure_modes?: string[];
}

interface ScenarioDetail extends ScenarioListRow {
  allowed_actions?: string[];
  scoring_profile?: string;
  success_predicates?: Record<string, any>[];
  failure_predicates?: Record<string, any>[];
  perturbations?: { kind: string; action_types: string[]; probability: number; message: string }[];
  hidden_facts?: Record<string, unknown>;
  log_channels?: string[];
  test_suites?: string[];
  package_available: boolean;
  digest_ok: boolean | null;
  guide: ScenarioGuide | null;
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
interface RunsFilters {
  scenario: string;
  model: string;
  outcome: string;
}

type Route =
  | { view: "overview" }
  | { view: "scenarios" }
  | { view: "scenario"; scenarioId: string }
  | { view: "runs"; filters: RunsFilters }
  | { view: "run"; runId: string }
  | { view: "compare"; a: string; b: string }
  | { view: "rubric" };

function parseHash(): Route {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [pathPart, queryPart] = raw.split("?");
  const parts = pathPart.split("/").filter(Boolean);
  const query = new URLSearchParams(queryPart ?? "");
  if (parts[0] === "run" && parts[1]) return { view: "run", runId: parts[1] };
  if (parts[0] === "compare" && parts[1] && parts[2])
    return { view: "compare", a: parts[1], b: parts[2] };
  if (parts[0] === "rubric") return { view: "rubric" };
  if (parts[0] === "scenarios") return { view: "scenarios" };
  if (parts[0] === "scenario" && parts[1])
    return { view: "scenario", scenarioId: decodeURIComponent(parts[1]) };
  if (parts[0] === "runs")
    return {
      view: "runs",
      filters: {
        scenario: query.get("scenario") ?? "",
        model: query.get("model") ?? "",
        outcome: query.get("outcome") ?? "",
      },
    };
  return { view: "overview" };
}

/** Which header tab is highlighted for each route. */
const TAB_FOR_VIEW: Record<Route["view"], string> = {
  overview: "overview",
  scenarios: "scenarios",
  scenario: "scenarios",
  runs: "runs",
  run: "runs",
  compare: "runs",
  rubric: "rubric",
};

let currentRoute: Route = { view: "overview" };

async function render(): Promise<void> {
  currentRoute = parseHash();
  const activeTab = TAB_FOR_VIEW[currentRoute.view];
  document.querySelectorAll<HTMLAnchorElement>(".nav-tab").forEach((tab) => {
    const active = tab.dataset.view === activeTab;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-current", active ? "page" : "false");
  });
  const view = $("#view");
  try {
    if (currentRoute.view === "overview") await renderOverview(view);
    else if (currentRoute.view === "scenarios") await renderScenarios(view);
    else if (currentRoute.view === "scenario")
      await renderScenarioDetail(view, currentRoute.scenarioId);
    else if (currentRoute.view === "runs") await renderRuns(view);
    else if (currentRoute.view === "run") await renderRunPage(view, currentRoute.runId);
    else if (currentRoute.view === "compare")
      await renderComparePage(view, currentRoute.a, currentRoute.b);
    else await renderRubricPage(view);
  } catch (err) {
    view.innerHTML = `<p class="empty">Failed to load: ${esc(String(err))}</p>`;
  }
}

// ------------------------------------------------------------- aggregation
interface AgentAgg {
  key: string;
  runCount: number;
  scoredCount: number;
  avgScore: number | null;
  solvedScenarios: number;
  attemptedScenarios: number;
  avgActions: number | null;
}

function aggregateAgents(runs: RunRow[]): AgentAgg[] {
  const byKey = new Map<string, RunRow[]>();
  for (const run of runs) {
    const key = agentLabel(run);
    const list = byKey.get(key);
    if (list) list.push(run);
    else byKey.set(key, [run]);
  }
  const aggs: AgentAgg[] = [];
  for (const [key, list] of byKey) {
    const scored = list.filter((r) => r.scorecard !== null);
    const withActions = list.filter((r) => r.metrics && r.metrics.actions !== undefined);
    const attempted = new Set(list.map((r) => r.scenario_id));
    const solved = new Set(
      list.filter((r) => r.terminal_reason === "success").map((r) => r.scenario_id)
    );
    aggs.push({
      key,
      runCount: list.length,
      scoredCount: scored.length,
      avgScore: scored.length
        ? Math.round(
            (scored.reduce((sum, r) => sum + r.scorecard!.overall_score, 0) / scored.length) * 100
          ) / 100
        : null,
      solvedScenarios: solved.size,
      attemptedScenarios: attempted.size,
      avgActions: withActions.length
        ? Math.round(
            (withActions.reduce((sum, r) => sum + (r.metrics!.actions ?? 0), 0) /
              withActions.length) *
              10
          ) / 10
        : null,
    });
  }
  aggs.sort((x, y) => {
    if (x.avgScore === null && y.avgScore === null) return x.key.localeCompare(y.key);
    if (x.avgScore === null) return 1;
    if (y.avgScore === null) return -1;
    return y.avgScore - x.avgScore || x.key.localeCompare(y.key);
  });
  return aggs;
}

const cellKey = (scenarioId: string, agent: string): string => `${scenarioId}\u0000${agent}`;

interface Matrix {
  rows: { id: string; title: string }[];
  cols: string[];
  cells: Map<string, RunRow[]>;
}

function buildMatrix(runs: RunRow[], scenarios: ScenarioListRow[]): Matrix {
  const cols = [...new Set(runs.map(agentLabel))].sort();
  const rowTitles = new Map<string, string>();
  for (const s of scenarios) rowTitles.set(s.scenario_id, s.title);
  for (const r of runs) if (!rowTitles.has(r.scenario_id)) rowTitles.set(r.scenario_id, r.scenario_id);
  const rows = [...rowTitles.entries()]
    .map(([id, title]) => ({ id, title }))
    .sort((a, b) => a.id.localeCompare(b.id));
  const cells = new Map<string, RunRow[]>();
  for (const r of runs) {
    const key = cellKey(r.scenario_id, agentLabel(r));
    const list = cells.get(key);
    if (list) list.push(r);
    else cells.set(key, [r]);
  }
  for (const list of cells.values()) list.sort((a, b) => b.created_at.localeCompare(a.created_at));
  return { rows, cols, cells };
}

// --------------------------------------------------------------- overview
function matrixCellHtml(cellRuns: RunRow[] | undefined, scenarioId: string): string {
  if (!cellRuns || !cellRuns.length) return `<td class="cell-none">–</td>`;
  const latest = cellRuns[0];
  const cls =
    latest.terminal_reason === "success"
      ? "cell-ok"
      : latest.status === "running" || latest.status === "queued"
        ? "cell-busy"
        : "cell-bad";
  const label =
    latest.scorecard !== null
      ? String(latest.scorecard.overall_score)
      : (latest.terminal_reason ?? latest.status);
  const more =
    cellRuns.length > 1
      ? ` <a class="cell-more" href="#/scenario/${encodeURIComponent(scenarioId)}"
             title="${cellRuns.length} runs total on this scenario">+${cellRuns.length - 1}</a>`
      : "";
  return `<td class="${cls}">
    <a href="#/run/${esc(latest.run_id)}" target="_blank" rel="noopener"
       title="${esc(latest.run_id)} · seed ${latest.seed}">${esc(label)}</a>${more}</td>`;
}

async function renderOverview(view: HTMLElement): Promise<void> {
  const [runs, scenarios] = await Promise.all([
    fetchJson<RunRow[]>("/api/v1/runs?limit=200"),
    fetchJson<ScenarioListRow[]>("/api/v1/scenarios"),
  ]);
  // A fetch started on one route must never paint after the route changed
  // (e.g. the 5s poll finishing after the user navigated elsewhere).
  if (parseHash().view !== "overview") return;

  const aggs = aggregateAgents(runs);
  const matrix = buildMatrix(runs, scenarios);

  const leaderboardRows = aggs
    .map(
      (agg, i) => `<tr>
        <td class="rank">${i + 1}</td>
        <th scope="row">${esc(agg.key)}</th>
        <td>${agg.avgScore === null ? "–" : `<strong>${agg.avgScore}</strong>`}</td>
        <td>${agg.solvedScenarios}/${agg.attemptedScenarios}</td>
        <td>${agg.avgActions ?? "–"}</td>
        <td>${agg.runCount}</td>
      </tr>`
    )
    .join("");

  const matrixHead = matrix.cols.map((c) => `<th scope="col">${esc(c)}</th>`).join("");
  const matrixRows = matrix.rows
    .map(
      (row) => `<tr>
        <th scope="row"><a href="#/scenario/${encodeURIComponent(row.id)}">${esc(row.title)}</a></th>
        ${matrix.cols.map((col) => matrixCellHtml(matrix.cells.get(cellKey(row.id, col)), row.id)).join("")}
      </tr>`
    )
    .join("");

  view.innerHTML = `
    <section class="overview" aria-label="Overview">
      <h2>Leaderboard</h2>
      ${
        aggs.length
          ? `<table class="leaderboard" aria-label="Model leaderboard">
              <thead><tr><th></th><th scope="col">Agent</th><th scope="col">Avg score</th>
                <th scope="col">Scenarios solved</th><th scope="col">Avg actions</th>
                <th scope="col">Runs</th></tr></thead>
              <tbody>${leaderboardRows}</tbody></table>
            <p class="hint">Average score is over scored runs only. Solved counts distinct scenarios with at least one successful run.</p>`
          : "<p class='empty'>No runs yet. Start one with the CLI: <code>agent-debugger run …</code></p>"
      }
      <h2>Results by scenario</h2>
      ${
        matrix.rows.length
          ? `<table class="matrix" aria-label="Scenario × agent results">
              <thead><tr><th scope="col">Scenario</th>${matrixHead}</tr></thead>
              <tbody>${matrixRows}</tbody></table>
            <p class="hint">Each cell shows the most recent run's score — click it to open the full run in a new tab. Scenario names link to what each test measures.</p>`
          : "<p class='empty'>No scenarios registered. Add one with <code>agent-debugger scenario add …</code></p>"
      }
    </section>`;
}

// -------------------------------------------------------------- scenarios
const CHIP = (label: string): string => `<span class="chip">${esc(label)}</span>`;

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
}

function scenarioChips(s: ScenarioListRow): string {
  const chips = [CHIP(s.difficulty)];
  if (s.failure_type) chips.push(CHIP(s.failure_type));
  if (s.par_actions) chips.push(CHIP(`par ${s.par_actions} actions`));
  return chips.join("");
}

async function renderScenarios(view: HTMLElement): Promise<void> {
  const scenarios = await fetchJson<ScenarioListRow[]>("/api/v1/scenarios");
  if (parseHash().view !== "scenarios") return;
  const cards = scenarios
    .map(
      (s) => `<li class="scenario-card">
        <a href="#/scenario/${encodeURIComponent(s.scenario_id)}">
          <h3>${esc(s.title)}</h3>
          <p class="scenario-chips">${scenarioChips(s)}</p>
          <p class="scenario-task">${esc(truncate(s.task ?? "", 170))}</p>
          <p class="run-meta"><code>${esc(s.scenario_id)}</code> v${esc(s.version)}</p>
        </a>
      </li>`
    )
    .join("");
  view.innerHTML = `
    <section class="scenarios" aria-label="Scenarios">
      <h2>Test scenarios</h2>
      <p class="hint">Each scenario is a fictional repository with one planted bug. Click a card to see what the test actually measures, the trap (if any), and every run against it.</p>
      ${
        scenarios.length
          ? `<ul class="scenario-grid">${cards}</ul>`
          : "<p class='empty'>No scenarios registered. Add one with <code>agent-debugger scenario add …</code></p>"
      }
    </section>`;
}

// -------------------------------------------------------- scenario detail
const bullets = (items?: string[] | null): string =>
  items && items.length ? `<ul>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "";

const numbered = (items?: string[] | null): string =>
  items && items.length ? `<ol>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ol>` : "";

function predicateText(detail: ScenarioDetail): string[] {
  const lines: string[] = [];
  for (const p of detail.success_predicates ?? []) {
    if (p.test_suite) lines.push(`Test suite ${p.test_suite} must pass (verified by re-running it).`);
    else if (p.file_scope)
      lines.push(`At most ${p.file_scope.max_changed_files} file(s) may change.`);
  }
  for (const p of detail.failure_predicates ?? []) {
    if (p.destructive_action_attempted)
      lines.push("Any destructive action ends the run as a failure.");
    if (p.external_action_attempted)
      lines.push("Any external/network action ends the run as a failure.");
  }
  return lines;
}

function perturbationText(detail: ScenarioDetail): string {
  const items = (detail.perturbations ?? []).map(
    (p) =>
      `${p.action_types.join(", ")} fails ${Math.round(p.probability * 100)}% of the time (“${p.message}”) — agents must tolerate transient tool failures.`
  );
  return items.length
    ? `<h3>Perturbations</h3>${bullets(items)}`
    : "";
}

async function renderScenarioDetail(view: HTMLElement, scenarioId: string): Promise<void> {
  const [detail, runs] = await Promise.all([
    fetchJson<ScenarioDetail>(`/api/v1/scenarios/${encodeURIComponent(scenarioId)}`).catch(
      () => null
    ),
    fetchJson<RunRow[]>(`/api/v1/runs?scenario_id=${encodeURIComponent(scenarioId)}&limit=200`),
  ]);
  const route = parseHash();
  if (route.view !== "scenario" || route.scenarioId !== scenarioId) return;

  if (!detail) {
    view.innerHTML = `<section><p class="empty">Scenario <code>${esc(scenarioId)}</code> is not registered in this workspace.</p></section>`;
    return;
  }

  const guide = detail.guide;
  const hidden = detail.hidden_facts ?? {};
  const plantedBug = guide?.planted_bug ?? (hidden["root_cause"] as string | undefined);
  const trap = guide?.the_trap ?? (hidden["misleading_path"] as string | undefined);
  const criteria = guide?.success_criteria?.length
    ? guide.success_criteria
    : predicateText(detail);
  const whatItTests = guide?.what_it_tests?.length
    ? guide.what_it_tests
    : detail.failure_type
      ? [`A ${detail.failure_type} bug in a ${detail.language ?? ""} ${detail.framework ?? ""} project.`]
      : [];

  const digestWarning =
    detail.digest_ok === false
      ? `<p class="digest-warning">⚠ Package files changed since registration — existing runs were scored against the registered version. Re-register the scenario before starting new runs.</p>`
      : "";
  const degraded = !detail.package_available
    ? `<p class="digest-warning">⚠ Scenario package files are unavailable on disk; showing registered metadata only.</p>`
    : "";

  runs.sort(
    (a, b) => agentLabel(a).localeCompare(agentLabel(b)) || b.created_at.localeCompare(a.created_at)
  );

  view.innerHTML = `
    <section class="scenario-page" aria-label="Scenario detail">
      <h2>${esc(detail.title)}</h2>
      <p class="scenario-chips">${scenarioChips(detail)}
        ${(detail.tags ?? []).map(CHIP).join("")}</p>
      <p class="run-meta"><code>${esc(detail.scenario_id)}</code> v${esc(detail.version)}</p>
      ${digestWarning}${degraded}

      ${detail.task ? `<h3>The task given to the agent</h3><p>${esc(detail.task)}</p>` : ""}

      ${guide?.summary ? `<h3>What this scenario is</h3><p>${esc(guide.summary)}</p>` : ""}

      ${whatItTests.length ? `<h3>What it actually tests</h3>${bullets(whatItTests)}` : ""}

      ${
        plantedBug || trap || guide?.ideal_path?.length
          ? `<details class="spoiler">
              <summary>Reveal the planted bug, the trap, and the ideal path (spoiler)</summary>
              ${plantedBug ? `<h3>The planted bug</h3><p>${esc(plantedBug)}</p>` : ""}
              ${trap ? `<h3>The trap</h3><p>${esc(trap)}</p>` : ""}
              ${guide?.ideal_path?.length ? `<h3>Ideal path (par ${detail.par_actions ?? "?"} actions)</h3>${numbered(guide.ideal_path)}` : ""}
            </details>`
          : ""
      }

      ${criteria.length ? `<h3>Success criteria</h3>${bullets(criteria)}` : ""}
      ${perturbationText(detail)}
      ${guide?.scoring_notes?.length ? `<h3>Scoring notes</h3>${bullets(guide.scoring_notes)} <p class="hint"><a href="#/rubric">Full scoring rubric →</a></p>` : ""}
      ${guide?.common_failure_modes?.length ? `<h3>Common failure modes</h3>${bullets(guide.common_failure_modes)}` : ""}

      <div class="home-head">
        <h3>Runs on this scenario <small>${runs.length}</small></h3>
        <button id="btn-compare" class="compare-btn" disabled>Select 2 runs to compare</button>
      </div>
      ${runsTableHtml(runs, { showScenario: false })}
    </section>`;
  wireCompareControls();
}

// ------------------------------------------------------------------- runs
const compareSelection = new Set<string>();

function runsTableHtml(runs: RunRow[], opts: { showScenario: boolean }): string {
  if (!runs.length)
    return "<p class='empty'>No runs yet. Start one with the CLI: <code>agent-debugger run …</code></p>";
  const rows = runs
    .map((run) => {
      const checked = compareSelection.has(run.run_id) ? "checked" : "";
      return `<tr>
        <td class="compare-pick"><input type="checkbox" data-pick="${esc(run.run_id)}" ${checked}
             aria-label="Select ${esc(run.run_id)} for comparison"></td>
        <td><a class="run-id" href="#/run/${esc(run.run_id)}" target="_blank" rel="noopener">${esc(run.run_id)}</a></td>
        ${opts.showScenario ? `<td>${esc(run.scenario_id)}</td>` : ""}
        <td>${esc(agentLabel(run))}</td>
        <td>${run.seed}</td>
        <td>${badge(run.terminal_reason, run.status)}</td>
        <td>${run.scorecard ? `<strong>${run.scorecard.overall_score}</strong>` : "–"}</td>
        <td class="run-meta">${esc(run.created_at.slice(0, 19).replace("T", " "))}</td>
      </tr>`;
    })
    .join("");
  return `<table class="runs-table" aria-label="Runs">
    <thead><tr><th></th><th scope="col">Run</th>
      ${opts.showScenario ? "<th scope='col'>Scenario</th>" : ""}
      <th scope="col">Agent</th><th scope="col">Seed</th><th scope="col">Outcome</th>
      <th scope="col">Score</th><th scope="col">Created</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function wireCompareControls(): void {
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

async function renderRuns(view: HTMLElement): Promise<void> {
  const runs = await fetchJson<RunRow[]>("/api/v1/runs?limit=200");
  const route = parseHash();
  if (route.view !== "runs") return;
  // Use the filters from the *current* hash — they may have changed while
  // the fetch was in flight.
  const filters = route.filters;

  const scenarios = [...new Set(runs.map((r) => r.scenario_id))].sort();
  const agents = [...new Set(runs.map(agentLabel))].sort();
  const outcomeMatch = (run: RunRow): boolean => {
    switch (filters.outcome) {
      case "solved":
        return run.terminal_reason === "success";
      case "unsolved":
        return (
          run.status !== "running" && run.status !== "queued" && run.terminal_reason !== "success"
        );
      case "running":
        return run.status === "running" || run.status === "queued";
      default:
        return true;
    }
  };
  const filtered = runs.filter(
    (r) =>
      (!filters.scenario || r.scenario_id === filters.scenario) &&
      (!filters.model || agentLabel(r) === filters.model) &&
      outcomeMatch(r)
  );

  const selectHtml = (
    id: string,
    label: string,
    options: [string, string][],
    current: string
  ): string => `
    <label class="filter"><span>${esc(label)}</span>
      <select id="${id}">
        <option value="">All</option>
        ${options
          .map(
            ([value, text]) =>
              `<option value="${esc(value)}" ${value === current ? "selected" : ""}>${esc(text)}</option>`
          )
          .join("")}
      </select></label>`;

  view.innerHTML = `
    <section class="runs-view" aria-label="All runs">
      <div class="home-head">
        <h2>All runs <small>${filtered.length} of ${runs.length}</small></h2>
        <button id="btn-compare" class="compare-btn" disabled>Select 2 runs to compare</button>
      </div>
      <div class="filter-bar">
        ${selectHtml("f-scenario", "Scenario", scenarios.map((s) => [s, s]), filters.scenario)}
        ${selectHtml("f-model", "Agent", agents.map((a) => [a, a]), filters.model)}
        ${selectHtml(
          "f-outcome",
          "Outcome",
          [
            ["solved", "Solved"],
            ["unsolved", "Not solved"],
            ["running", "In progress"],
          ],
          filters.outcome
        )}
      </div>
      ${
        runs.length && !filtered.length
          ? `<p class="empty">No runs match the filters — <a href="#/runs">clear filters</a>.</p>`
          : runsTableHtml(filtered, { showScenario: true })
      }
    </section>`;

  const applyFilters = () => {
    const params = new URLSearchParams();
    const value = (id: string) => (document.getElementById(id) as HTMLSelectElement).value;
    if (value("f-scenario")) params.set("scenario", value("f-scenario"));
    if (value("f-model")) params.set("model", value("f-model"));
    if (value("f-outcome")) params.set("outcome", value("f-outcome"));
    const qs = params.toString();
    // replaceState (not location.hash) avoids history spam; re-render manually.
    history.replaceState(null, "", qs ? `#/runs?${qs}` : "#/runs");
    void render();
  };
  ["f-scenario", "f-model", "f-outcome"].forEach((id) =>
    document.getElementById(id)?.addEventListener("change", applyFilters)
  );
  wireCompareControls();
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
          <dt>Scenario</dt><dd><a href="#/scenario/${encodeURIComponent(run.scenario_id)}">${esc(run.scenario_id)}</a> v${esc(manifest.scenario_version)}</dd>
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
  if (currentRoute.view !== "overview" && currentRoute.view !== "runs") return;
  // Don't repaint while the user is mid-interaction with a filter dropdown
  // or a compare checkbox.
  const active = document.activeElement;
  if (active && (active.tagName === "SELECT" || active.tagName === "INPUT")) return;
  void render();
}, 5000);

void render();
