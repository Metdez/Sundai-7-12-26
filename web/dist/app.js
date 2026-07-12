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
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [pathPart, queryPart] = raw.split("?");
  const parts = pathPart.split("/").filter(Boolean);
  const query = new URLSearchParams(queryPart ?? "");
  if (parts[0] === "run" && parts[1])
    return { view: "run", runId: parts[1] };
  if (parts[0] === "compare" && parts[1] && parts[2])
    return { view: "compare", a: parts[1], b: parts[2] };
  if (parts[0] === "rubric")
    return { view: "rubric" };
  if (parts[0] === "scenarios")
    return { view: "scenarios" };
  if (parts[0] === "scenario" && parts[1])
    return { view: "scenario", scenarioId: decodeURIComponent(parts[1]) };
  if (parts[0] === "runs")
    return {
      view: "runs",
      filters: {
        scenario: query.get("scenario") ?? "",
        model: query.get("model") ?? "",
        outcome: query.get("outcome") ?? ""
      }
    };
  return { view: "overview" };
}
var TAB_FOR_VIEW = {
  overview: "overview",
  scenarios: "scenarios",
  scenario: "scenarios",
  runs: "runs",
  run: "runs",
  compare: "runs",
  rubric: "rubric"
};
var currentRoute = { view: "overview" };
async function render() {
  currentRoute = parseHash();
  const activeTab = TAB_FOR_VIEW[currentRoute.view];
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    const active = tab.dataset.view === activeTab;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-current", active ? "page" : "false");
  });
  const view = $("#view");
  try {
    if (currentRoute.view === "overview")
      await renderOverview(view);
    else if (currentRoute.view === "scenarios")
      await renderScenarios(view);
    else if (currentRoute.view === "scenario")
      await renderScenarioDetail(view, currentRoute.scenarioId);
    else if (currentRoute.view === "runs")
      await renderRuns(view);
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
function aggregateAgents(runs) {
  const byKey = /* @__PURE__ */ new Map();
  for (const run of runs) {
    const key = agentLabel(run);
    const list = byKey.get(key);
    if (list)
      list.push(run);
    else
      byKey.set(key, [run]);
  }
  const aggs = [];
  for (const [key, list] of byKey) {
    const scored = list.filter((r) => r.scorecard !== null);
    const withActions = list.filter((r) => r.metrics && r.metrics.actions !== void 0);
    const attempted = new Set(list.map((r) => r.scenario_id));
    const solved = new Set(
      list.filter((r) => r.terminal_reason === "success").map((r) => r.scenario_id)
    );
    aggs.push({
      key,
      runCount: list.length,
      scoredCount: scored.length,
      avgScore: scored.length ? Math.round(
        scored.reduce((sum, r) => sum + r.scorecard.overall_score, 0) / scored.length * 100
      ) / 100 : null,
      solvedScenarios: solved.size,
      attemptedScenarios: attempted.size,
      avgActions: withActions.length ? Math.round(
        withActions.reduce((sum, r) => sum + (r.metrics.actions ?? 0), 0) / withActions.length * 10
      ) / 10 : null
    });
  }
  aggs.sort((x, y) => {
    if (x.avgScore === null && y.avgScore === null)
      return x.key.localeCompare(y.key);
    if (x.avgScore === null)
      return 1;
    if (y.avgScore === null)
      return -1;
    return y.avgScore - x.avgScore || x.key.localeCompare(y.key);
  });
  return aggs;
}
var cellKey = (scenarioId, agent) => `${scenarioId}\0${agent}`;
function buildMatrix(runs, scenarios) {
  const cols = [...new Set(runs.map(agentLabel))].sort();
  const rowTitles = /* @__PURE__ */ new Map();
  for (const s of scenarios)
    rowTitles.set(s.scenario_id, s.title);
  for (const r of runs)
    if (!rowTitles.has(r.scenario_id))
      rowTitles.set(r.scenario_id, r.scenario_id);
  const rows = [...rowTitles.entries()].map(([id, title]) => ({ id, title })).sort((a, b) => a.id.localeCompare(b.id));
  const cells = /* @__PURE__ */ new Map();
  for (const r of runs) {
    const key = cellKey(r.scenario_id, agentLabel(r));
    const list = cells.get(key);
    if (list)
      list.push(r);
    else
      cells.set(key, [r]);
  }
  for (const list of cells.values())
    list.sort((a, b) => b.created_at.localeCompare(a.created_at));
  return { rows, cols, cells };
}
function matrixCellHtml(cellRuns, scenarioId) {
  if (!cellRuns || !cellRuns.length)
    return `<td class="cell-none">\u2013</td>`;
  const latest = cellRuns[0];
  const cls = latest.terminal_reason === "success" ? "cell-ok" : latest.status === "running" || latest.status === "queued" ? "cell-busy" : "cell-bad";
  const label = latest.scorecard !== null ? String(latest.scorecard.overall_score) : latest.terminal_reason ?? latest.status;
  const more = cellRuns.length > 1 ? ` <a class="cell-more" href="#/scenario/${encodeURIComponent(scenarioId)}"
             title="${cellRuns.length} runs total on this scenario">+${cellRuns.length - 1}</a>` : "";
  return `<td class="${cls}">
    <a href="#/run/${esc(latest.run_id)}" target="_blank" rel="noopener"
       title="${esc(latest.run_id)} \xB7 seed ${latest.seed}">${esc(label)}</a>${more}</td>`;
}
async function renderOverview(view) {
  const [runs, scenarios] = await Promise.all([
    fetchJson("/api/v1/runs?limit=200"),
    fetchJson("/api/v1/scenarios")
  ]);
  if (parseHash().view !== "overview")
    return;
  const aggs = aggregateAgents(runs);
  const matrix = buildMatrix(runs, scenarios);
  const leaderboardRows = aggs.map(
    (agg, i) => `<tr>
        <td class="rank">${i + 1}</td>
        <th scope="row">${esc(agg.key)}</th>
        <td>${agg.avgScore === null ? "\u2013" : `<strong>${agg.avgScore}</strong>`}</td>
        <td>${agg.solvedScenarios}/${agg.attemptedScenarios}</td>
        <td>${agg.avgActions ?? "\u2013"}</td>
        <td>${agg.runCount}</td>
      </tr>`
  ).join("");
  const matrixHead = matrix.cols.map((c) => `<th scope="col">${esc(c)}</th>`).join("");
  const matrixRows = matrix.rows.map(
    (row) => `<tr>
        <th scope="row"><a href="#/scenario/${encodeURIComponent(row.id)}">${esc(row.title)}</a></th>
        ${matrix.cols.map((col) => matrixCellHtml(matrix.cells.get(cellKey(row.id, col)), row.id)).join("")}
      </tr>`
  ).join("");
  view.innerHTML = `
    <section class="overview" aria-label="Overview">
      <h2>Leaderboard</h2>
      ${aggs.length ? `<table class="leaderboard" aria-label="Model leaderboard">
              <thead><tr><th></th><th scope="col">Agent</th><th scope="col">Avg score</th>
                <th scope="col">Scenarios solved</th><th scope="col">Avg actions</th>
                <th scope="col">Runs</th></tr></thead>
              <tbody>${leaderboardRows}</tbody></table>
            <p class="hint">Average score is over scored runs only. Solved counts distinct scenarios with at least one successful run.</p>` : "<p class='empty'>No runs yet. Start one with the CLI: <code>agent-debugger run \u2026</code></p>"}
      <h2>Results by scenario</h2>
      ${matrix.rows.length ? `<table class="matrix" aria-label="Scenario \xD7 agent results">
              <thead><tr><th scope="col">Scenario</th>${matrixHead}</tr></thead>
              <tbody>${matrixRows}</tbody></table>
            <p class="hint">Each cell shows the most recent run's score \u2014 click it to open the full run in a new tab. Scenario names link to what each test measures.</p>` : "<p class='empty'>No scenarios registered. Add one with <code>agent-debugger scenario add \u2026</code></p>"}
    </section>`;
}
var CHIP = (label) => `<span class="chip">${esc(label)}</span>`;
function truncate(text, max) {
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}\u2026` : text;
}
function scenarioChips(s) {
  const chips = [CHIP(s.difficulty)];
  if (s.failure_type)
    chips.push(CHIP(s.failure_type));
  if (s.par_actions)
    chips.push(CHIP(`par ${s.par_actions} actions`));
  return chips.join("");
}
async function renderScenarios(view) {
  const scenarios = await fetchJson("/api/v1/scenarios");
  if (parseHash().view !== "scenarios")
    return;
  const cards = scenarios.map(
    (s) => `<li class="scenario-card">
        <a href="#/scenario/${encodeURIComponent(s.scenario_id)}">
          <h3>${esc(s.title)}</h3>
          <p class="scenario-chips">${scenarioChips(s)}</p>
          <p class="scenario-task">${esc(truncate(s.task ?? "", 170))}</p>
          <p class="run-meta"><code>${esc(s.scenario_id)}</code> v${esc(s.version)}</p>
        </a>
      </li>`
  ).join("");
  view.innerHTML = `
    <section class="scenarios" aria-label="Scenarios">
      <h2>Test scenarios</h2>
      <p class="hint">Each scenario is a fictional repository with one planted bug. Click a card to see what the test actually measures, the trap (if any), and every run against it.</p>
      ${scenarios.length ? `<ul class="scenario-grid">${cards}</ul>` : "<p class='empty'>No scenarios registered. Add one with <code>agent-debugger scenario add \u2026</code></p>"}
    </section>`;
}
var bullets = (items) => items && items.length ? `<ul>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "";
var numbered = (items) => items && items.length ? `<ol>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ol>` : "";
function predicateText(detail) {
  const lines = [];
  for (const p of detail.success_predicates ?? []) {
    if (p.test_suite)
      lines.push(`Test suite ${p.test_suite} must pass (verified by re-running it).`);
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
function perturbationText(detail) {
  const items = (detail.perturbations ?? []).map(
    (p) => `${p.action_types.join(", ")} fails ${Math.round(p.probability * 100)}% of the time (\u201C${p.message}\u201D) \u2014 agents must tolerate transient tool failures.`
  );
  return items.length ? `<h3>Perturbations</h3>${bullets(items)}` : "";
}
async function renderScenarioDetail(view, scenarioId) {
  const [detail, runs] = await Promise.all([
    fetchJson(`/api/v1/scenarios/${encodeURIComponent(scenarioId)}`).catch(
      () => null
    ),
    fetchJson(`/api/v1/runs?scenario_id=${encodeURIComponent(scenarioId)}&limit=200`)
  ]);
  const route = parseHash();
  if (route.view !== "scenario" || route.scenarioId !== scenarioId)
    return;
  if (!detail) {
    view.innerHTML = `<section><p class="empty">Scenario <code>${esc(scenarioId)}</code> is not registered in this workspace.</p></section>`;
    return;
  }
  const guide = detail.guide;
  const hidden = detail.hidden_facts ?? {};
  const plantedBug = guide?.planted_bug ?? hidden["root_cause"];
  const trap = guide?.the_trap ?? hidden["misleading_path"];
  const criteria = guide?.success_criteria?.length ? guide.success_criteria : predicateText(detail);
  const whatItTests = guide?.what_it_tests?.length ? guide.what_it_tests : detail.failure_type ? [`A ${detail.failure_type} bug in a ${detail.language ?? ""} ${detail.framework ?? ""} project.`] : [];
  const digestWarning = detail.digest_ok === false ? `<p class="digest-warning">\u26A0 Package files changed since registration \u2014 existing runs were scored against the registered version. Re-register the scenario before starting new runs.</p>` : "";
  const degraded = !detail.package_available ? `<p class="digest-warning">\u26A0 Scenario package files are unavailable on disk; showing registered metadata only.</p>` : "";
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

      ${plantedBug || trap || guide?.ideal_path?.length ? `<details class="spoiler">
              <summary>Reveal the planted bug, the trap, and the ideal path (spoiler)</summary>
              ${plantedBug ? `<h3>The planted bug</h3><p>${esc(plantedBug)}</p>` : ""}
              ${trap ? `<h3>The trap</h3><p>${esc(trap)}</p>` : ""}
              ${guide?.ideal_path?.length ? `<h3>Ideal path (par ${detail.par_actions ?? "?"} actions)</h3>${numbered(guide.ideal_path)}` : ""}
            </details>` : ""}

      ${criteria.length ? `<h3>Success criteria</h3>${bullets(criteria)}` : ""}
      ${perturbationText(detail)}
      ${guide?.scoring_notes?.length ? `<h3>Scoring notes</h3>${bullets(guide.scoring_notes)} <p class="hint"><a href="#/rubric">Full scoring rubric \u2192</a></p>` : ""}
      ${guide?.common_failure_modes?.length ? `<h3>Common failure modes</h3>${bullets(guide.common_failure_modes)}` : ""}

      <div class="home-head">
        <h3>Runs on this scenario <small>${runs.length}</small></h3>
        <button id="btn-compare" class="compare-btn" disabled>Select 2 runs to compare</button>
      </div>
      ${runsTableHtml(runs, { showScenario: false })}
    </section>`;
  wireCompareControls();
}
var compareSelection = /* @__PURE__ */ new Set();
function runsTableHtml(runs, opts) {
  if (!runs.length)
    return "<p class='empty'>No runs yet. Start one with the CLI: <code>agent-debugger run \u2026</code></p>";
  const rows = runs.map((run) => {
    const checked = compareSelection.has(run.run_id) ? "checked" : "";
    return `<tr>
        <td class="compare-pick"><input type="checkbox" data-pick="${esc(run.run_id)}" ${checked}
             aria-label="Select ${esc(run.run_id)} for comparison"></td>
        <td><a class="run-id" href="#/run/${esc(run.run_id)}" target="_blank" rel="noopener">${esc(run.run_id)}</a></td>
        ${opts.showScenario ? `<td>${esc(run.scenario_id)}</td>` : ""}
        <td>${esc(agentLabel(run))}</td>
        <td>${run.seed}</td>
        <td>${badge(run.terminal_reason, run.status)}</td>
        <td>${run.scorecard ? `<strong>${run.scorecard.overall_score}</strong>` : "\u2013"}</td>
        <td class="run-meta">${esc(run.created_at.slice(0, 19).replace("T", " "))}</td>
      </tr>`;
  }).join("");
  return `<table class="runs-table" aria-label="Runs">
    <thead><tr><th></th><th scope="col">Run</th>
      ${opts.showScenario ? "<th scope='col'>Scenario</th>" : ""}
      <th scope="col">Agent</th><th scope="col">Seed</th><th scope="col">Outcome</th>
      <th scope="col">Score</th><th scope="col">Created</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}
function wireCompareControls() {
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
async function renderRuns(view) {
  const runs = await fetchJson("/api/v1/runs?limit=200");
  const route = parseHash();
  if (route.view !== "runs")
    return;
  const filters = route.filters;
  const scenarios = [...new Set(runs.map((r) => r.scenario_id))].sort();
  const agents = [...new Set(runs.map(agentLabel))].sort();
  const outcomeMatch = (run) => {
    switch (filters.outcome) {
      case "solved":
        return run.terminal_reason === "success";
      case "unsolved":
        return run.status !== "running" && run.status !== "queued" && run.terminal_reason !== "success";
      case "running":
        return run.status === "running" || run.status === "queued";
      default:
        return true;
    }
  };
  const filtered = runs.filter(
    (r) => (!filters.scenario || r.scenario_id === filters.scenario) && (!filters.model || agentLabel(r) === filters.model) && outcomeMatch(r)
  );
  const selectHtml = (id, label, options, current) => `
    <label class="filter"><span>${esc(label)}</span>
      <select id="${id}">
        <option value="">All</option>
        ${options.map(
    ([value, text]) => `<option value="${esc(value)}" ${value === current ? "selected" : ""}>${esc(text)}</option>`
  ).join("")}
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
      ["running", "In progress"]
    ],
    filters.outcome
  )}
      </div>
      ${runs.length && !filtered.length ? `<p class="empty">No runs match the filters \u2014 <a href="#/runs">clear filters</a>.</p>` : runsTableHtml(filtered, { showScenario: true })}
    </section>`;
  const applyFilters = () => {
    const params = new URLSearchParams();
    const value = (id) => document.getElementById(id).value;
    if (value("f-scenario"))
      params.set("scenario", value("f-scenario"));
    if (value("f-model"))
      params.set("model", value("f-model"));
    if (value("f-outcome"))
      params.set("outcome", value("f-outcome"));
    const qs = params.toString();
    history.replaceState(null, "", qs ? `#/runs?${qs}` : "#/runs");
    void render();
  };
  ["f-scenario", "f-model", "f-outcome"].forEach(
    (id) => document.getElementById(id)?.addEventListener("change", applyFilters)
  );
  wireCompareControls();
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
          <dt>Scenario</dt><dd><a href="#/scenario/${encodeURIComponent(run.scenario_id)}">${esc(run.scenario_id)}</a> v${esc(manifest.scenario_version)}</dd>
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
  if (currentRoute.view !== "overview" && currentRoute.view !== "runs")
    return;
  const active = document.activeElement;
  if (active && (active.tagName === "SELECT" || active.tagName === "INPUT"))
    return;
  void render();
}, 5e3);
void render();
