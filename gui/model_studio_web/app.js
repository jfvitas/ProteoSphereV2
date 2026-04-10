const state = {
  workspace: null,
  currentDraft: null,
  pipelineList: [],
  recentRuns: [],
  currentRun: null,
  runComparison: null,
  selectedRunId: "",
  compareRunIds: [],
  viewMode: "guided",
  actionStatus: {
    level: "idle",
    title: "Workspace ready",
    detail: "Choose a step to begin.",
  },
  tableState: {
    candidate: { query: "", page: 1, pageSize: 25 },
    build: { query: "", page: 1, pageSize: 25 },
  },
  fieldFeedback: {},
  pollHandle: null,
};

function getEl(id) {
  return document.getElementById(id);
}

function setFieldFeedback(controlId, tone, title, detail) {
  if (!controlId) return;
  state.fieldFeedback[controlId] = { tone, title, detail };
}

function clearFieldFeedback(controlId) {
  if (!controlId) return;
  delete state.fieldFeedback[controlId];
}

function syncDraftFromVisibleForm() {
  if (!state.currentDraft) return;
  if (!getEl("study-title-input")) return;
  try {
    state.currentDraft = collectDraftFromForm();
    ensureDraftShape();
  } catch {
    // Keep the current draft when the visible form is mid-render or incomplete.
  }
}

function renderFieldFeedbacks() {
  document.querySelectorAll(".has-field-feedback").forEach((node) => {
    node.classList.remove("has-field-feedback", "warning", "neutral");
  });
  document.querySelectorAll(".field-feedback:not(.persistent-field-feedback)").forEach((node) => node.remove());
  Object.entries(state.fieldFeedback || {}).forEach(([controlId, feedback]) => {
    const control = getEl(controlId);
    if (!control || !feedback) return;
    const host = control.closest("label") || control.parentElement;
    if (!host) return;
    host.classList.add("has-field-feedback", feedback.tone || "neutral");
    const note = document.createElement("div");
    note.className = `field-feedback ${feedback.tone || "neutral"}`;
    note.innerHTML = `
      <strong>${escapeHtml(feedback.title || "Note")}</strong>
      <div>${escapeHtml(feedback.detail || "")}</div>
    `;
    host.append(note);
  });
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const text = await response.text();
  const contentType = response.headers.get("content-type") || "";
  let payload = {};
  if (text) {
    if (contentType.includes("application/json")) {
      payload = JSON.parse(text);
    } else {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = { detail: text };
      }
    }
  }
  if (!response.ok) {
    const detail = payload.detail || payload.error || text || `${response.status}`;
    const summary = payload.error_summary || payload.error || "Request failed";
    throw new Error(`${summary}: ${detail}`);
  }
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function toCsvString(values) {
  return (values || []).join(", ");
}

function safeNumber(value, digits = 3) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "n/a";
}

function optionValue(option) {
  return typeof option === "string" ? option : option?.value;
}

function optionLabel(option) {
  if (typeof option === "string") return option;
  return option?.label || option?.value || "";
}

function optionStatus(option) {
  return typeof option === "string" ? "release" : option?.status || "release";
}

function optionReason(option) {
  return typeof option === "string" ? "" : option?.reason || "";
}

function optionAudience(option) {
  return typeof option === "string" ? "default" : option?.audience_visibility || "default";
}

function optionInactiveReason(option) {
  return typeof option === "string" ? "" : option?.inactive_reason || option?.reason || "";
}

function isActiveStatus(status) {
  return ["release", "beta"].includes(status || "release");
}

function isBetaSoonStatus(status) {
  return (status || "") === "beta_soon";
}

function uiOptionRegistry() {
  return state.workspace?.catalog?.ui_option_registry || {};
}

function capabilityRegistry() {
  return state.workspace?.catalog?.capability_registry || {};
}

function fieldHelpRegistry() {
  return state.workspace?.catalog?.field_help_registry || {};
}

function fromCheckedValues(containerId) {
  return Array.from(
    document.querySelectorAll(`#${containerId} [data-chip-value][aria-pressed="true"]`),
  ).map((node) => node.getAttribute("data-chip-value"));
}

function fromSelectValues(selectId) {
  const select = getEl(selectId);
  if (!select) return [];
  return Array.from(select.selectedOptions || []).map((option) => option.value).filter(Boolean);
}

function setActionStatus(level, title, detail = "") {
  state.actionStatus = { level, title, detail };
  renderStatusRail();
}

function showInactiveExplanation(label, reason) {
  getEl("inactive-explanation").innerHTML = `
    <div class="stack-item">
      <strong>${label}</strong>
      <div class="muted">${reason}</div>
    </div>
  `;
  setActionStatus("warning", `${label} is inactive`, reason);
}

function actionEligibility() {
  const previewRows = state.workspace?.training_set_preview?.candidate_preview?.rows || [];
  const latestBuild = state.workspace?.latest_training_set_build;
  const runStatus = currentRunManifest()?.status || "idle";
  const reportPath = state.currentRun?.artifacts?.["report.md"];
  const compareReady = Boolean((state.compareRunIds || []).filter(Boolean).length >= 2);
  return {
    validate: {
      enabled: true,
      reason: "Validate the current draft and show any blockers before compiling or running.",
    },
    compile: {
      enabled: true,
      reason: "Compile the execution graph for the current draft from the Pipeline Composer pane.",
    },
    preview: {
      enabled: true,
      reason: "Preview candidate dataset rows and diagnostics for the current request.",
    },
    build: {
      enabled: previewRows.length > 0,
      reason: previewRows.length
        ? "Build the study dataset from the previewed candidate rows."
        : "Preview the dataset first so the Studio can show the candidate rows that will be built.",
    },
    launch: {
      enabled: Boolean(latestBuild),
      reason: latestBuild
        ? "Launch a run with the latest built study dataset."
        : "Build and split the study dataset before launching the pipeline run.",
    },
    cancel: {
      enabled: ["running", "queued"].includes(runStatus),
      reason: ["running", "queued"].includes(runStatus)
        ? "Cancel the currently active run at the next stage boundary."
        : "A run must be active before cancellation is available.",
    },
    resume: {
      enabled: false,
      reason:
        "Resume-in-place is not yet enabled in the internal alpha. Relaunch from the saved draft instead.",
    },
    report: {
      enabled: Boolean(reportPath),
      reason: reportPath
        ? "Show the current report artifact path."
        : "Complete a run to generate a report artifact first.",
    },
    compare: {
      enabled: compareReady,
      reason: compareReady
        ? "Refresh the comparison for the two selected completed runs."
        : "Select two completed runs before refreshing the comparison view.",
    },
  };
}

function groupOptions(options) {
  return {
    available: (options || []).filter((option) => isActiveStatus(optionStatus(option))),
    betaSoon: (options || []).filter((option) => isBetaSoonStatus(optionStatus(option))),
    inactive: (options || []).filter((option) => {
      const status = optionStatus(option);
      return !isActiveStatus(status) && !isBetaSoonStatus(status);
    }),
  };
}

function configureActionButton(buttonId, eligibility, activeLabel, inactiveLabelText = null) {
  const button = getEl(buttonId);
  if (!button) return;
  button.classList.toggle("inactive-action", !eligibility.enabled);
  button.setAttribute("aria-disabled", eligibility.enabled ? "false" : "true");
  button.dataset.enabled = eligibility.enabled ? "true" : "false";
  button.dataset.reason = eligibility.reason || "";
  button.title = eligibility.reason;
  if (inactiveLabelText) {
    button.textContent = eligibility.enabled ? activeLabel : inactiveLabelText;
  }
}

function ensureDraftShape() {
  const draft = state.currentDraft;
  draft.data_strategy ??= {};
  draft.feature_recipes ??= [];
  draft.graph_recipes ??= [];
  draft.training_set_request ??= {};
  draft.preprocess_plan ??= {};
  draft.preprocess_plan.options ??= {};
  draft.split_plan ??= {};
  draft.example_materialization ??= {};
  draft.training_plan ??= {};
  draft.evaluation_plan ??= {};

  if (!draft.feature_recipes.length) {
    draft.feature_recipes.push({
      recipe_id: "feature:custom-v1",
      node_feature_policy: "normalized_continuous",
      edge_feature_policy: "normalized_continuous",
      global_feature_sets: ["assay_globals", "structure_quality"],
      distributed_feature_sets: ["residue_contacts", "interface_geometry"],
      notes: [],
    });
  }
  if (!draft.graph_recipes.length) {
    draft.graph_recipes.push({
      recipe_id: "graph:custom-v1",
      graph_kind: "interface_graph",
      region_policy: "interface_only",
      node_granularity: "residue",
      encoding_policy: "normalized_continuous",
      feature_recipe_id: draft.feature_recipes[0].recipe_id,
      partner_awareness: "symmetric",
      include_waters: false,
      include_salt_bridges: false,
      include_contact_shell: false,
      notes: [],
    });
  }

  draft.training_set_request.request_id ??= `training-set-request:${draft.pipeline_id || "custom"}`;
  draft.training_set_request.task_type ??= draft.data_strategy.task_type || "protein-protein";
  draft.training_set_request.label_type ??= draft.data_strategy.label_type || "delta_G";
  draft.training_set_request.structure_source_policy ??=
    draft.data_strategy.structure_source_policy || "experimental_only";
  draft.training_set_request.source_families ??= ["release_frozen"];
  draft.training_set_request.dataset_refs ??= draft.data_strategy.dataset_refs || [
    "release_pp_alpha_benchmark_v1",
  ];
  draft.training_set_request.target_size ??= 144;
  draft.training_set_request.acceptable_fidelity ??= "pilot_ready";
  draft.training_set_request.inclusion_filters ??= { max_resolution: 3.5, min_release_year: 1990 };
  draft.training_set_request.exclusion_filters ??= { exclude_pdb_ids: [] };

  draft.split_plan.plan_id ??= `split:${draft.pipeline_id || "custom"}`;
  draft.split_plan.objective ??= "leakage_aware_component_balanced";
  draft.split_plan.grouping_policy ??= "protein_accession_components";
  draft.split_plan.holdout_policy ??= "explicit_test_holdout";
  draft.split_plan.train_fraction ??= 0.7;
  draft.split_plan.val_fraction ??= 0.1;
  draft.split_plan.test_fraction ??= 0.2;
  draft.split_plan.hard_constraints ??= ["no_direct_accession_overlap", "prefer_label_balance"];

  draft.example_materialization.spec_id ??= `materialization:${draft.pipeline_id || "custom"}`;
  draft.example_materialization.graph_recipe_ids ??= [draft.graph_recipes[0].recipe_id];
  draft.example_materialization.feature_recipe_ids ??= [draft.feature_recipes[0].recipe_id];
  draft.example_materialization.preprocess_modules ??= draft.preprocess_plan.modules || [];
  draft.example_materialization.region_policy ??= draft.graph_recipes[0].region_policy;
  draft.example_materialization.cache_policy ??= "prefer_cached_materializations";
  draft.example_materialization.include_global_features ??= true;
  draft.example_materialization.include_distributed_features ??= true;
  draft.example_materialization.include_graph_payloads ??= true;

  draft.training_plan.plan_id ??= `training:${draft.pipeline_id || "custom"}`;
  draft.training_plan.model_family ??= "multimodal_fusion";
  draft.training_plan.architecture ??= "graph_global_fusion";
  draft.training_plan.optimizer ??= "adamw";
  draft.training_plan.scheduler ??= "cosine_decay";
  draft.training_plan.loss_function ??= "mse";
  draft.training_plan.epoch_budget ??= 60;
  draft.training_plan.batch_policy ??= "dynamic_by_graph_size";
  draft.training_plan.mixed_precision ??= "bf16";
  draft.training_plan.uncertainty_head ??= "heteroscedastic_regression";
  draft.training_plan.ablations ??= ["graph_only", "global_only", "graph_plus_global"];
  draft.trainingPlanPreset ??= "regression_plus_calibration";
  draft.preprocess_plan.options.hardware_runtime_preset ??= "auto_recommend";
}

function inactiveLabel(option) {
  const status = optionStatus(option);
  if (status === "release") return optionLabel(option);
  if (status === "beta") return `${optionLabel(option)} (Beta)`;
  if (status === "beta_soon") return `${optionLabel(option)} (Beta soon)`;
  return `${optionLabel(option)} (Inactive)`;
}

function renderSelect(targetId, options, selected) {
  const target = getEl(targetId);
  if (!target) return;
  const grouped = groupOptions(options);
  const fallback = grouped.available[0] || grouped.betaSoon[0] || grouped.inactive[0] || options[0];
  const safeSelected =
    options.find((option) => optionValue(option) === selected)?.value ||
    optionValue(fallback) ||
    "";
  const optionMarkup = (label, items) =>
    items.length
      ? `<optgroup label="${label}">${items
          .map(
            (option) => `
            <option
              value="${escapeHtml(optionValue(option))}"
              data-status="${escapeHtml(optionStatus(option))}"
              data-reason="${escapeHtml(optionInactiveReason(option) || optionReason(option))}"
              data-label="${escapeHtml(optionLabel(option))}"
              ${optionValue(option) === safeSelected ? "selected" : ""}
            >
              ${escapeHtml(inactiveLabel(option))}
            </option>`,
          )
          .join("")}</optgroup>`
      : "";
  target.innerHTML = [
    optionMarkup("Available now", grouped.available),
    optionMarkup("Beta soon", grouped.betaSoon),
    optionMarkup("Planned / inactive", grouped.inactive),
  ].join("");
}

function renderMultiSelect(targetId, options, selectedValues, size = 5) {
  const target = getEl(targetId);
  if (!target) return;
  target.size = size;
  const selected = new Set(selectedValues || []);
  const grouped = groupOptions(options);
  const optionMarkup = (label, items) =>
    items.length
      ? `<optgroup label="${label}">${items
          .map(
            (option) => `
            <option
              value="${escapeHtml(optionValue(option))}"
              data-status="${escapeHtml(optionStatus(option))}"
              data-reason="${escapeHtml(optionInactiveReason(option) || optionReason(option))}"
              data-label="${escapeHtml(optionLabel(option))}"
              ${selected.has(optionValue(option)) ? "selected" : ""}
            >
              ${escapeHtml(inactiveLabel(option))}
            </option>`,
          )
          .join("")}</optgroup>`
      : "";
  target.innerHTML = [
    optionMarkup("Available now", grouped.available),
    optionMarkup("Beta soon", grouped.betaSoon),
    optionMarkup("Planned / inactive", grouped.inactive),
  ].join("");
}

function renderChipControl(containerId, options, selectedValues) {
  const container = getEl(containerId);
  if (!container) return;
  const selected = new Set(selectedValues || []);
  container.innerHTML = (options || [])
    .map((option) => {
      const value = optionValue(option);
      const active = selected.has(value);
      const activeStatus = isActiveStatus(optionStatus(option));
      return `
        <button
          type="button"
          class="choice-chip ${active ? "active" : ""} ${activeStatus ? "" : "inactive"}"
          data-chip-value="${value}"
          data-chip-label="${optionLabel(option)}"
          data-chip-status="${optionStatus(option)}"
          data-chip-reason="${optionInactiveReason(option) || optionReason(option)}"
          aria-pressed="${active ? "true" : "false"}"
        >
          <span>${inactiveLabel(option)}</span>
        </button>`;
    })
    .join("");
}

function injectHelpButtons() {
  document.querySelectorAll("[data-help-key]").forEach((label) => {
    if (label.querySelector(".info-button")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "info-button";
    button.setAttribute("data-help-trigger", label.getAttribute("data-help-key"));
    button.textContent = "i";
    const title = label.querySelector("span");
    if (title) {
      title.insertAdjacentElement("afterend", button);
    } else {
      label.prepend(button);
    }
  });
}

function openHelpPopover(helpKey, anchor) {
  const help = fieldHelpRegistry()[helpKey];
  const popover = getEl("help-popover");
  if (!help || !anchor || !popover) return;
  popover.innerHTML = `
    <div class="help-card">
      <strong>${help.title}</strong>
      <p>${help.summary}</p>
      <div class="help-line"><span>Includes</span><div>${help.includes}</div></div>
      <div class="help-line"><span>Excludes</span><div>${help.excludes}</div></div>
      <div class="help-line"><span>Artifacts</span><div>${help.artifacts}</div></div>
      <div class="help-line"><span>Assumptions</span><div>${help.assumptions}</div></div>
    </div>
  `;
  const rect = anchor.getBoundingClientRect();
  popover.classList.remove("hidden");
  popover.style.top = `${window.scrollY + rect.bottom + 10}px`;
  popover.style.left = `${Math.max(18, window.scrollX + rect.left - 40)}px`;
}

function closeHelpPopover() {
  getEl("help-popover").classList.add("hidden");
}

function setViewMode(mode) {
  state.viewMode = mode;
  document.body.classList.toggle("advanced-mode", mode === "advanced");
  getEl("guided-view-button").classList.toggle("mode-active", mode === "guided");
  getEl("advanced-view-button").classList.toggle("mode-active", mode === "advanced");
  getEl("stepper").classList.toggle("hidden", mode === "advanced");
}

async function refreshRunComparison() {
  const selectedIds = (state.compareRunIds || []).filter(Boolean);
  if (selectedIds.length < 2) {
    state.runComparison = null;
    return;
  }
  const query = selectedIds.map((runId) => `run_id=${encodeURIComponent(runId)}`).join("&");
  state.runComparison = await fetchJson(`/api/model-studio/compare?${query}`);
}

function currentRunManifest() {
  return state.currentRun?.run_manifest || null;
}

function renderNav() {
  getEl("workspace-nav").innerHTML = (state.workspace.workspace_sections || [])
    .map((name) => `<a href="#workspace-${name.toLowerCase().replaceAll(" ", "-")}">${name}</a>`)
    .join("");
}

function renderHero() {
  const draft = state.currentDraft;
  const quality = state.workspace.quality_gates;
  const hardware = state.workspace.hardware_profile || {};
  getEl("study-title").textContent = draft.study_title;
  getEl("study-summary").textContent =
    "Build a structure-backed training set, split it intelligently, materialize graph and feature bundles, train a released local model, and review results in one guided flow.";
  getEl("hero-badges").innerHTML = [
    draft.data_strategy.task_type,
    draft.training_plan.model_family,
    draft.data_strategy.split_strategy,
    `target:${draft.training_set_request?.target_size || "auto"}`,
    `quality:${quality.status}`,
    `runtime:${hardware.recommended_preset || "auto"}`,
  ]
    .map((item) => `<span class="badge">${item}</span>`)
    .join("");
}

function renderToplineCards() {
  const quality = state.workspace.quality_gates;
  getEl("quality-gate-status").textContent = quality.status;
  getEl("warning-count").textContent = String(quality.warning_count || 0);
  getEl("stage-count").textContent = String(state.workspace.execution_graph.stages.length);
  getEl("queued-task-count").textContent = String(state.workspace.program_status.curated_wave_queue_count || 0);
}

function renderStatusRail() {
  const rail = getEl("action-status-rail");
  const runManifest = currentRunManifest();
  const resolvedBackend =
    state.currentRun?.model_details?.resolved_backend ||
    runManifest?.resolved_backend ||
    state.workspace?.status_rail?.resolved_backend ||
    "n/a";
  const resolvedExecutionDevice =
    state.currentRun?.model_details?.resolved_execution_device ||
    runManifest?.resolved_execution_device ||
    state.workspace?.status_rail?.resolved_execution_device ||
    "n/a";
  const hardwareMode =
    runManifest?.hardware_mode ||
    state.workspace?.status_rail?.hardware_mode ||
    betaCurrentHardwareMode();
  rail.innerHTML = `
    <div class="status-pill ${state.actionStatus.level}">
      <strong>${state.actionStatus.title}</strong>
      <span>${state.actionStatus.detail || "No active warning."}</span>
    </div>
    <div class="status-pill neutral">
      <strong>Current stage</strong>
      <span>${runManifest?.active_stage || "idle"}</span>
    </div>
    <div class="status-pill neutral">
      <strong>Last heartbeat</strong>
      <span>${runManifest?.heartbeat_at || state.workspace?.status_rail?.last_heartbeat || "n/a"}</span>
    </div>
    <div class="status-pill neutral">
      <strong>Run status</strong>
      <span>${runManifest?.status || "idle"}</span>
    </div>
    <div class="status-pill neutral">
      <strong>Resolved backend</strong>
      <span>${resolvedBackend}</span>
    </div>
    <div class="status-pill neutral">
      <strong>Execution placement</strong>
      <span>${resolvedExecutionDevice}</span>
    </div>
    <div class="status-pill neutral">
      <strong>Hardware mode</strong>
      <span>${hardwareMode}</span>
    </div>
  `;
}

function renderActionButtons() {
  const eligibility = actionEligibility();
  configureActionButton("validate-draft-button", eligibility.validate, "Validate");
  configureActionButton("validate-step-button", eligibility.validate, "Validate configuration");
  configureActionButton("compile-step-button", eligibility.compile, "Compile graph");
  configureActionButton("preview-dataset-button", eligibility.preview, "Preview dataset");
  configureActionButton("preview-step-button", eligibility.preview, "Preview candidate dataset");
  configureActionButton("build-dataset-button", eligibility.build, "Build dataset");
  configureActionButton("build-step-button", eligibility.build, "Build study dataset");
  configureActionButton("launch-run-button", eligibility.launch, "Launch run");
  configureActionButton("launch-step-button", eligibility.launch, "Launch run");
  configureActionButton("cancel-run-button", eligibility.cancel, "Cancel run");
  configureActionButton(
    "resume-run-button",
    eligibility.resume,
    "Resume run",
    "Resume run (Inactive)",
  );
  configureActionButton(
    "open-report-button",
    eligibility.report,
    "Show report path",
    "Show report path (Inactive)",
  );
  configureActionButton(
    "compare-step-button",
    eligibility.compare,
    "Refresh comparison",
    "Refresh comparison (Inactive)",
  );
}

function computeStepStatuses() {
  const base = state.workspace?.stepper || [];
  const runManifest = currentRunManifest();
  const runStatus = runManifest?.status || "idle";
  const latestBuild = state.workspace?.latest_training_set_build;
  const previewRows = state.workspace?.training_set_preview?.candidate_preview?.rows || [];
  return base.map((step, index) => {
    let status = step.status || "next";
    if (step.id === "run-monitor") {
      status =
        runStatus === "running"
          ? "current"
          : runStatus === "completed"
            ? "completed"
            : runStatus === "failed" || runStatus === "blocked"
              ? "blocked"
              : latestBuild
                ? "next"
                : "next";
    }
    if (step.id === "analysis-compare") {
      status = runStatus === "completed" ? "current" : latestBuild ? "next" : "next";
    }
    if (step.id === "export-review") {
      status = runStatus === "completed" ? "next" : "inactive";
    }
    if (!latestBuild && step.id === "build-split") status = previewRows.length ? "current" : "next";
    if (!previewRows.length && step.id === "dataset-preview") status = "current";
    if (index === 0 && status === "next") status = "current";
    return { ...step, status };
  });
}

function renderStepper() {
  const steps = computeStepStatuses();
  getEl("stepper").innerHTML = steps
    .map(
      (step) => `
        <article class="step-card ${step.status}">
          <div class="step-header">
            <span class="step-index">${step.label}</span>
            <span class="pill ${step.status === "blocked" ? "blocker" : step.status === "inactive" ? "warning" : "neutral"}">${step.status}</span>
          </div>
          <p>${step.summary}</p>
          <div class="step-produced">
            ${(step.produced || []).map((item) => `<div class="stack-item">${item}</div>`).join("")}
            ${!(step.produced || []).length ? `<div class="stack-item muted">No artifacts yet.</div>` : ""}
          </div>
          <div class="step-next"><strong>Next:</strong> ${step.next_action}</div>
          ${(step.blockers || []).length ? `<div class="step-blockers">${step.blockers.map((item) => `<div class="stack-item">${item}</div>`).join("")}</div>` : ""}
          <div class="step-actions">
            <button type="button" class="secondary" data-scroll-target="${step.workspace}">Go to step</button>
          </div>
        </article>`,
    )
    .join("");
}

function renderProgramPanels() {
  const programStatus = state.workspace.program_status;
  const uiContract = state.workspace.ui_contract || {};
  const preview = programStatus.program_preview || {};
  const orchestrator = programStatus.orchestrator_state || {};
  const summary = preview.summary || {};
  const datasetPools = uiContract.dataset_pools || [];
  const candidatePoolSummary = uiContract.candidate_pool_summary || {};
  const activationLedger = uiContract.activation_ledger || [];
  getEl("program-mini-status").innerHTML = `
    <div class="stack-item"><strong>${summary.status || "unknown"}</strong><div class="muted">release status</div></div>
    <div class="stack-item"><strong>${programStatus.training_set_build_count || 0}</strong><div class="muted">study dataset builds</div></div>
    <div class="stack-item"><strong>${(orchestrator.active_workers || []).length}</strong><div class="muted">active workers</div></div>
  `;
  getEl("pipeline-library").innerHTML = state.pipelineList
    .map(
      (item) => `
        <button class="library-item" data-pipeline-id="${item.pipeline_id}">
          <strong>${item.study_title}</strong>
          <div class="muted">${item.task_type} / ${item.model_family}</div>
        </button>`,
    )
    .join("");
  getEl("program-status-detail").innerHTML = [
    ["Schema", state.workspace.schema_version],
    ["Mode", preview.mode || "release"],
    ["Draft specs", programStatus.draft_count || 0],
    ["Studio runs", programStatus.run_count || 0],
    ["Study builds", programStatus.training_set_build_count || 0],
    ["Review artifacts", programStatus.release_review_artifact_count || 0],
  ]
    .map(([label, value]) => `<div class="kv"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
  getEl("quality-gates").innerHTML = (state.workspace.quality_gates.checks || [])
    .map(
      (check) => `
        <div class="recommendation ${check.status === "blocked" ? "blocker" : check.status === "review_required" ? "warning" : ""}">
          <span class="pill ${check.status === "blocked" ? "blocker" : check.status === "review_required" ? "warning" : "neutral"}">${check.status}</span>
          <strong>${check.gate}</strong>
          <p>${check.detail}</p>
        </div>`,
    )
    .join("");
  getEl("recent-runs").innerHTML = state.recentRuns.length
    ? state.recentRuns
        .slice(0, 6)
        .map(
          (run) => `
            <button class="library-item" data-run-id="${run.run_id}">
              <strong>${run.run_id}</strong>
              <div class="muted">${run.dataset_ref || "n/a"} / ${run.status}</div>
            </button>`,
        )
        .join("")
    : `<div class="muted">No Studio runs yet.</div>`;
  const selectedDataset = state.workspace.selected_dataset;
  const knownDatasets = programStatus.known_datasets || [];
  getEl("known-datasets").innerHTML = `
    <div class="stack-item">
      <strong>${candidatePoolSummary.total_row_count || 0}</strong>
      <div class="muted">rows across promoted beta pools (${(candidatePoolSummary.promoted_pool_ids || []).length || 0} pools)</div>
    </div>
    ${
      selectedDataset
        ? `<div class="stack-item">
            <strong>${escapeHtml(selectedDataset.label)}</strong>
            <div class="muted">${escapeHtml(selectedDataset.dataset_ref)} | ${selectedDataset.row_count} rows</div>
            <div class="muted">split: ${escapeHtml(selectedDataset.split_strategy || "n/a")} | maturity: ${escapeHtml(selectedDataset.maturity || "n/a")}</div>
          </div>`
        : `<div class="stack-item muted">Select a primary dataset to inspect its details here.</div>`
    }
    <div class="stack-item">
      <strong>Promoted pools</strong>
      <div class="muted">${datasetPools
        .filter((item) => isActiveStatus(item.status))
        .slice(0, 4)
        .map((item) => `${escapeHtml(item.label)} (${item.row_count})`)
        .join(" | ") || "none"}</div>
    </div>
    <div class="stack-item">
      <strong>Activation wave</strong>
      <div class="muted">${activationLedger.length} tracked feature gates | ${knownDatasets.length} known runnable dataset manifests</div>
    </div>
  `;
  const steps = computeStepStatuses();
  getEl("completion-summary").innerHTML = steps
    .map((step) => `<div class="stack-item"><strong>${step.label}</strong><div class="muted">${step.status}</div></div>`)
    .join("");
  const current = steps.find((step) => step.status === "current") || steps[0];
  getEl("recommended-next-action").innerHTML = `
    <div class="stack-item">
      <strong>${current?.label || "Next step"}</strong>
      <div class="muted">${current?.next_action || "Continue through the guided flow."}</div>
    </div>
  `;
}

function filteredRows(rows, query) {
  if (!query) return rows;
  const lowered = query.toLowerCase();
  return rows.filter((row) =>
    Object.values(row || {}).some((value) => String(value ?? "").toLowerCase().includes(lowered)),
  );
}

function renderPreviewTable(rows, columns, tableKey) {
  if (!rows.length) return `<div class="muted">No rows to show yet.</div>`;
  const tableState = state.tableState[tableKey] || { query: "", page: 1, pageSize: 25 };
  const filtered = filteredRows(rows, tableState.query);
  const totalPages = Math.max(1, Math.ceil(filtered.length / tableState.pageSize));
  const currentPage = Math.min(tableState.page, totalPages);
  const pageRows = filtered.slice(
    (currentPage - 1) * tableState.pageSize,
    currentPage * tableState.pageSize,
  );
  const labels = {
    pdb_id: "PDB",
    description: "Description",
    label: "Label",
    source_family: "Source",
    structure_status: "Structure",
    split: "Split",
    inclusion_reason: "Inclusion",
  };
  return `
    <div class="table-toolbar">
      <input class="table-filter-input" data-table-filter="${tableKey}" type="search" placeholder="Filter rows" value="${escapeHtml(tableState.query)}" />
      <div class="table-toolbar-summary">Showing ${pageRows.length} of ${filtered.length} matching rows (${rows.length} total)</div>
      <div class="table-toolbar-actions">
        <button type="button" class="secondary compact-button" data-table-page="${tableKey}" data-table-direction="-1">Prev</button>
        <span class="muted">Page ${currentPage} / ${totalPages}</span>
        <button type="button" class="secondary compact-button" data-table-page="${tableKey}" data-table-direction="1">Next</button>
      </div>
    </div>
    <table class="data-table">
      <thead><tr>${columns.map((column) => `<th>${labels[column] || column}</th>`).join("")}</tr></thead>
      <tbody>
        ${pageRows
          .map(
            (row) =>
              `<tr>${columns
                .map((column) => `<td>${escapeHtml(row[column] ?? "n/a")}</td>`)
                .join("")}</tr>`,
          )
          .join("")}
      </tbody>
    </table>`;
}

function architectureOptionsForModel(modelFamily) {
  const all = uiOptionRegistry().architectures || [];
  const preferred = {
    xgboost: "boosted_trees_regression",
    catboost: "bagged_tree_regression",
    mlp: "tabular_mlp",
    multimodal_fusion: "graph_global_fusion",
    graphsage: "graphsage_interface_encoder",
    gin: "gin_encoder",
    gcn: "gcn_encoder",
    gat: "gat_encoder",
    late_fusion_ensemble: "late_fusion_stack",
  }[modelFamily];
  return [...all].sort((a, b) => {
    if (optionValue(a) === preferred) return -1;
    if (optionValue(b) === preferred) return 1;
    return optionLabel(a).localeCompare(optionLabel(b));
  });
}

function renderDataStrategyForm() {
  const capabilities = capabilityRegistry();
  const options = uiOptionRegistry();
  const strategy = state.currentDraft.data_strategy;
  const request = state.currentDraft.training_set_request;
  const knownDatasets = betaDatasetOptions();

  renderSelect("task-type-select", capabilities.task_types || [], strategy.task_type);
  renderSelect("label-type-select", capabilities.label_types || [], strategy.label_type);
  renderSelect("split-strategy-select", capabilities.split_strategies || [], strategy.split_strategy);
  renderSelect("structure-policy-select", capabilities.structure_source_policies || [], strategy.structure_source_policy);
  renderSelect("dataset-primary-select", knownDatasets, (strategy.dataset_refs || [])[0] || "release_pp_alpha_benchmark_v1");
  renderSelect("acceptable-fidelity-select", options.acceptable_fidelity_levels || [], request.acceptable_fidelity);
  renderMultiSelect("source-families-select", options.source_families || [], request.source_families || [], 4);
  renderMultiSelect("dataset-refs-select", knownDatasets, strategy.dataset_refs || [], 5);

  getEl("study-title-input").value = state.currentDraft.study_title || "";
  getEl("target-size-input").value = request.target_size || "";
  getEl("max-resolution-input").value = request.inclusion_filters?.max_resolution ?? "";
  getEl("min-release-year-input").value = request.inclusion_filters?.min_release_year ?? "";
  getEl("exclude-pdb-ids-input").value = toCsvString(request.exclusion_filters?.exclude_pdb_ids);

  const auditOptions = [
    { value: "sequence_leakage", label: "sequence leakage", status: "release", reason: "Required audit." },
    { value: "partner_overlap", label: "partner overlap", status: "release", reason: "Required audit." },
    { value: "state_reuse", label: "state reuse", status: "release", reason: "Required audit." },
    { value: "label_balance", label: "label balance", status: "release", reason: "Recommended audit." },
    { value: "source_maturity", label: "source maturity", status: "release", reason: "Recommended audit." },
  ];
  renderChipControl("audit-requirements", auditOptions, strategy.audit_requirements || []);

  const preview = state.workspace.training_set_preview || {};
  const candidate = preview.candidate_preview || {};
  const diagnostics = preview.diagnostics || {};
  getEl("training-set-preview").innerHTML = [
    `Sources: ${toCsvString(preview.resolved_dataset_refs) || "none"}`,
    `Rows: ${candidate.row_count || 0}`,
    `Structure coverage: ${safeNumber(diagnostics.structure_coverage, 2)}`,
    `Leakage risk: ${diagnostics.leakage_risk || "unknown"}`,
    `Maturity: ${diagnostics.status || "unknown"}`,
    `Label range: ${safeNumber(diagnostics.label_min, 2)} to ${safeNumber(diagnostics.label_max, 2)}`,
  ]
    .map((line) => `<div class="stack-item">${line}</div>`)
    .join("");
  getEl("training-set-table-summary").innerHTML = [
    `Total candidate rows: ${candidate.row_count || 0}`,
    `Dropped rows: ${(candidate.dropped_rows || []).length}`,
    `Source families: ${Object.keys(candidate.source_breakdown || {}).length}`,
  ]
    .map((line) => `<div class="stack-item">${line}</div>`)
    .join("");
  getEl("training-set-table").innerHTML = renderPreviewTable(candidate.rows || [], [
    "pdb_id",
    "description",
    "label",
    "source_family",
    "structure_status",
    "split",
    "inclusion_reason",
  ], "candidate");

  const built = state.workspace.latest_training_set_build;
  getEl("training-set-build-summary").innerHTML = built
    ? [
        `Build id: ${built.build_id}`,
        `Dataset ref: ${built.dataset_ref}`,
        `Rows: ${built.row_count}`,
        `Split: ${built.split_preview?.train_count || 0} / ${built.split_preview?.val_count || 0} / ${built.split_preview?.test_count || 0}`,
      ]
        .map((line) => `<div class="stack-item">${line}</div>`)
        .join("")
    : `<div class="muted">No study dataset has been built yet.</div>`;
  const buildCharts = built?.charts || preview.charts || {};
  getEl("data-diagnostics").innerHTML = [
    `Current split strategy: ${strategy.split_strategy}`,
    `Grouping policy: ${state.currentDraft.split_plan.grouping_policy}`,
    `Holdout policy: ${state.currentDraft.split_plan.holdout_policy}`,
    `Diagnostics blockers: ${(diagnostics.blockers || []).length}`,
    `Label bins: ${(buildCharts.label_distribution || []).length}`,
  ]
    .map((line) => `<div class="stack-item">${line}</div>`)
    .join("");
  getEl("build-split-table-summary").innerHTML = built
    ? [
        `Selected rows: ${(built.selected_rows || []).length}`,
        `Excluded rows: ${(built.excluded_rows || []).length}`,
        `Split counts: ${built.split_preview?.train_count || 0} / ${built.split_preview?.val_count || 0} / ${built.split_preview?.test_count || 0}`,
      ]
        .map((line) => `<div class="stack-item">${line}</div>`)
        .join("")
    : `<div class="muted">Build a study dataset to inspect all selected and excluded rows.</div>`;
  getEl("build-split-table").innerHTML = built
    ? `
      <div class="table-group">
        <h5>Selected rows</h5>
        ${renderPreviewTable(built.selected_rows || built.selected_rows_preview || [], ["pdb_id", "description", "label", "split", "structure_status", "inclusion_reason"], "build")}
      </div>
      <div class="table-group">
        <h5>Excluded rows</h5>
        ${(built.excluded_rows || built.excluded_rows_preview || []).length
          ? `<div class="stack">${(built.excluded_rows || built.excluded_rows_preview).map((item) => `<div class="stack-item mono">${escapeHtml(item)}</div>`).join("")}</div>`
          : `<div class="muted">No excluded rows recorded.</div>`}
      </div>`
    : `<div class="muted">Build a study dataset to inspect selected and excluded rows.</div>`;
}

function renderModelDiagram(modelFamily) {
  const templates = {
    xgboost: ["Tabular features", "Tree ensemble", "Affinity regression head"],
    catboost: ["Tabular features", "Forest adapter", "Affinity regression head"],
    mlp: ["Tabular features", "MLP encoder", "Regression head"],
    multimodal_fusion: ["Graph summary", "Global features", "Fusion MLP", "Regression head"],
    graphsage: ["Graph payload", "GraphSAGE-lite", "Pooling", "Regression head"],
    gin: ["Graph payload", "GIN encoder", "Pooling", "Regression head"],
    gcn: ["Graph payload", "GCN adapter", "Pooling", "Regression head"],
    late_fusion_ensemble: ["XGBoost-like", "CatBoost-like", "MLP stack", "Averaged ensemble"],
  };
  const nodes = templates[modelFamily] || ["Inactive model family", "Not yet enabled"];
  return `<div class="diagram-flow vertical">${nodes
    .map((node) => `<div class="diagram-node">${node}</div>`)
    .join('<div class="diagram-arrow">v</div>')}</div>`;
}

function renderRepresentationForm() {
  ensureDraftShape();
  const capabilities = capabilityRegistry();
  const options = uiOptionRegistry();
  const feature = state.currentDraft.feature_recipes[0];
  const graph = state.currentDraft.graph_recipes[0];
  renderSelect("graph-kind-select", capabilities.graph_kinds || [], graph.graph_kind);
  renderSelect("region-policy-select", capabilities.region_policies || [], graph.region_policy);
  renderSelect("encoding-policy-select", capabilities.node_feature_policies || [], graph.encoding_policy);
  renderSelect("node-feature-policy-select", capabilities.node_feature_policies || [], feature.node_feature_policy);
  renderSelect("edge-feature-policy-select", capabilities.node_feature_policies || [], feature.edge_feature_policy);
  renderSelect(
    "node-granularity-select",
    options.node_granularities || [],
    graph.node_granularity || "residue",
  );
  renderChipControl("global-features-control", options.global_feature_sets || [], feature.global_feature_sets || []);
  renderChipControl("distributed-features-control", options.distributed_feature_sets || [], feature.distributed_feature_sets || []);
  getEl("include-waters-toggle").checked = Boolean(graph.include_waters);
  getEl("include-salt-bridges-toggle").checked = Boolean(graph.include_salt_bridges);
  getEl("include-contact-shell-toggle").checked = Boolean(graph.include_contact_shell);

  getEl("representation-compatibility").innerHTML = [
    `Graph kind: ${graph.graph_kind}`,
    `Region policy: ${graph.region_policy}`,
    `Waters: ${graph.include_waters ? "enabled" : "disabled"}`,
    `Salt bridges: ${graph.include_salt_bridges ? "enabled" : "disabled"}`,
    `Contact shell: ${graph.include_contact_shell ? "enabled" : "disabled"}`,
  ]
    .map((line) => `<div class="stack-item">${line}</div>`)
    .join("");
  getEl("example-bundle-summary").innerHTML = [
    `Global feature bundles: ${toCsvString(feature.global_feature_sets) || "none"}`,
    `Distributed bundles: ${toCsvString(feature.distributed_feature_sets) || "none"}`,
    `Graph payloads: ${state.currentDraft.example_materialization.include_graph_payloads ? "included" : "disabled"}`,
    `Cache policy: ${state.currentDraft.example_materialization.cache_policy}`,
  ]
    .map((line) => `<div class="stack-item">${line}</div>`)
    .join("");
  getEl("pipeline-diagram").innerHTML = `
    <div class="diagram-flow">
      <div class="diagram-node">Dataset</div>
      <div class="diagram-arrow">-&gt;</div>
      <div class="diagram-node">Preprocess<br /><span>${toCsvString(state.currentDraft.preprocess_plan.modules || []) || "none"}</span></div>
      <div class="diagram-arrow">-&gt;</div>
      <div class="diagram-node">Graph<br /><span>${graph.graph_kind}</span></div>
      <div class="diagram-arrow">-&gt;</div>
      <div class="diagram-node">Features<br /><span>${toCsvString(feature.global_feature_sets || []) || "none"}</span></div>
      <div class="diagram-arrow">-&gt;</div>
      <div class="diagram-node">Evaluation</div>
    </div>`;
  getEl("model-structure-diagram").innerHTML = renderModelDiagram(state.currentDraft.training_plan.model_family);
}

function renderPipelineComposer() {
  const capabilities = capabilityRegistry();
  const options = uiOptionRegistry();
  const plan = state.currentDraft.training_plan;
  renderSelect("model-family-select", capabilities.model_families || [], plan.model_family);
  renderSelect("architecture-select", architectureOptionsForModel(plan.model_family), plan.architecture);
  renderSelect("optimizer-select", options.optimizer_policies || [], plan.optimizer);
  renderSelect("scheduler-select", options.scheduler_policies || [], plan.scheduler);
  renderSelect("loss-function-select", options.loss_functions || [], plan.loss_function);
  renderSelect("batch-policy-select", options.batch_policies || [], plan.batch_policy);
  renderSelect("mixed-precision-select", options.mixed_precision_policies || [], plan.mixed_precision);
  renderSelect("uncertainty-head-select", options.uncertainty_heads || [], plan.uncertainty_head || "none");
  renderSelect("evaluation-preset-select", options.evaluation_presets || [], state.currentDraft.trainingPlanPreset || "regression_plus_calibration");
  renderSelect("hardware-runtime-select", options.hardware_runtime_presets || [], state.currentDraft.preprocess_plan.options.hardware_runtime_preset);
  renderChipControl("ablation-options-control", options.ablation_options || [], plan.ablations || []);
  getEl("epoch-budget-input").value = plan.epoch_budget || 1;

  const hardware = state.workspace.hardware_profile || {};
  getEl("hardware-runtime-summary").innerHTML = [
    `CPU cores: ${hardware.cpu_count || "n/a"}`,
    `RAM: ${hardware.total_ram_gb || "n/a"} GB`,
    `CUDA: ${hardware.cuda_available ? "available" : "not detected"}`,
    `GPU: ${hardware.gpu_name || "none"}`,
    `Recommended preset: ${hardware.recommended_preset || "auto_recommend"}`,
    ...(hardware.warnings || []),
  ]
    .map((line) => `<div class="stack-item">${line}</div>`)
    .join("");

  getEl("composer-recommendations").innerHTML = (state.workspace.recommendation_report.items || [])
    .slice(0, 8)
    .map(
      (item) => `
        <div class="recommendation ${item.level}">
          <span class="pill ${item.level === "blocker" ? "blocker" : item.level === "warning" ? "warning" : "neutral"}">${item.level}</span>
          <strong>${item.category}</strong>
          <p>${item.message}</p>
          ${item.action ? `<p class="muted">Suggested action: ${item.action}</p>` : ""}
        </div>`,
    )
    .join("");
  getEl("training-plan-summary").innerHTML = [
    `Architecture: ${plan.architecture || "n/a"}`,
    `Optimizer: ${plan.optimizer || "n/a"}`,
    `Scheduler: ${plan.scheduler || "n/a"}`,
    `Loss: ${plan.loss_function || "n/a"}`,
    `Epoch budget: ${plan.epoch_budget || 1}`,
    `Ablations: ${toCsvString(plan.ablations) || "none"}`,
    `Hardware preset: ${state.currentDraft.preprocess_plan.options.hardware_runtime_preset || "auto_recommend"}`,
  ]
    .map((line) => `<div class="stack-item">${line}</div>`)
    .join("");
}

function renderExecutionConsole() {
  const capabilities = capabilityRegistry();
  renderChipControl("preprocess-modules", capabilities.preprocessing_modules || [], state.currentDraft.preprocess_plan.modules || []);

  const graph = state.workspace.execution_graph;
  const currentRunStages = state.currentRun?.stage_status || {};
  getEl("execution-graph").innerHTML = `
    <div class="timeline">
      ${graph.stages
        .map((stage) => {
          const stageStatus = currentRunStages[stage];
          const stageClass =
            stageStatus?.status === "blocked" || stageStatus?.status === "failed"
              ? "warning"
              : stageStatus?.status === "completed"
                ? "active"
                : stageStatus?.status === "running"
                  ? "running"
                  : "";
          return `
            <div class="timeline-stage ${stageClass}">
              <strong>${stage}</strong>
              <div class="muted">${stageStatus?.detail || "Waiting for execution."}</div>
              <div class="muted">heartbeat: ${stageStatus?.updated_at || "n/a"}</div>
            </div>`;
        })
        .join("")}
    </div>`;

  const runPreview = state.currentRun?.run_manifest || state.workspace.run_preview;
  getEl("run-preview").innerHTML = `
    <div class="kv-list">
      <div class="kv"><span>Run id</span><strong>${runPreview.run_id || "preview"}</strong></div>
      <div class="kv"><span>Status</span><strong>${runPreview.status || "draft"}</strong></div>
      <div class="kv"><span>Active stage</span><strong>${runPreview.active_stage || "n/a"}</strong></div>
      <div class="kv"><span>Dataset</span><strong>${runPreview.dataset_ref || "n/a"}</strong></div>
      <div class="kv"><span>Model</span><strong>${runPreview.model_family || state.currentDraft.training_plan.model_family || "n/a"}</strong></div>
      <div class="kv"><span>Last heartbeat</span><strong>${runPreview.heartbeat_at || "n/a"}</strong></div>
    </div>`;

  getEl("run-stage-cards").innerHTML = (graph.stages || [])
    .map((stage) => {
      const item = currentRunStages[stage] || { status: "pending", detail: "Waiting for execution." };
      return `
        <article class="stage-card ${item.status}">
          <div class="stage-card-head">
            <strong>${stage}</strong>
            <span class="pill ${item.status === "completed" ? "neutral" : item.status === "running" ? "warning" : item.status === "failed" || item.status === "blocked" ? "blocker" : "neutral"}">${item.status}</span>
          </div>
          <p>${item.detail || "Waiting for execution."}</p>
          ${item.blockers?.length ? `<div class="stack">${item.blockers.map((blocker) => `<div class="stack-item">${blocker}</div>`).join("")}</div>` : ""}
          ${item.technical_detail ? `<div class="stack-item mono">${item.technical_detail}</div>` : ""}
          <div class="muted">Updated: ${item.updated_at || "n/a"}</div>
          <div class="muted">Artifacts: ${(item.artifact_refs || []).length}</div>
        </article>`;
    })
    .join("");

  const artifacts = state.currentRun?.artifacts || {};
  getEl("current-run-artifacts").innerHTML = Object.keys(artifacts).length
    ? Object.entries(artifacts)
        .map(([label, value]) => `<div class="stack-item"><strong>${label}</strong><div class="muted">${value}</div></div>`)
        .join("")
    : `<div class="muted">Launch a run to inspect artifacts.</div>`;
  const logs = state.currentRun?.logs?.lines || [];
  getEl("current-run-logs").innerHTML = logs.length
    ? logs.slice(-10).map((line) => `<div class="stack-item mono">${line}</div>`).join("")
    : `<div class="muted">No run logs yet.</div>`;
  getEl("split-packaging-summary").innerHTML =
    state.currentRun?.artifacts?.["packaging_manifest.json"]
      ? [
          "Current run packaged train, val, and test examples.",
          "Example bundles include graph, global, and distributed features when enabled.",
        ]
          .map((line) => `<div class="stack-item">${line}</div>`)
          .join("")
      : `<div class="muted">Launch a run to inspect split packaging and artifact bundles.</div>`;
  const buildDiagnostics = state.workspace.latest_training_set_build?.diagnostics || {};
  getEl("execution-dataset-diagnostics").innerHTML = Object.keys(buildDiagnostics).length
    ? [
        `Status: ${buildDiagnostics.status || "unknown"}`,
        `Structure coverage: ${safeNumber(buildDiagnostics.structure_coverage, 2)}`,
        `Missing structures: ${buildDiagnostics.missing_structure_count || 0}`,
        `Leakage risk: ${buildDiagnostics.leakage_risk || "n/a"}`,
      ]
        .map((line) => `<div class="stack-item">${line}</div>`)
        .join("")
    : `<div class="muted">Build a study dataset to inspect dataset diagnostics here.</div>`;
}

function renderMetricsChart(metrics) {
  const values = [
    ["RMSE", Number(metrics.test_rmse || 0)],
    ["MAE", Number(metrics.test_mae || 0)],
    ["Pearson", Number(metrics.test_pearson || 0)],
    ["R2", Number(metrics.test_r2 || 0)],
  ];
  const maxValue = Math.max(...values.map(([, value]) => Math.abs(value)), 1);
  return values
    .map(
      ([label, value]) => `
        <div class="metric-bar">
          <span>${label}</span>
          <div class="metric-bar-track"><div class="metric-bar-fill" style="width:${(Math.abs(value) / maxValue) * 100}%"></div></div>
          <strong>${safeNumber(value)}</strong>
        </div>`,
    )
    .join("");
}

function renderSplitChart(splitPreview) {
  const total = (splitPreview.train_count || 0) + (splitPreview.val_count || 0) + (splitPreview.test_count || 0) || 1;
  const segments = [
    ["Train", splitPreview.train_count || 0, "#0f6f8a"],
    ["Val", splitPreview.val_count || 0, "#7ab1ff"],
    ["Test", splitPreview.test_count || 0, "#9fe7cf"],
  ];
  return segments
    .map(
      ([label, value, color]) => `
        <div class="split-segment">
          <span>${label}</span>
          <div class="metric-bar-track"><div class="metric-bar-fill" style="width:${(value / total) * 100}%; background:${color}"></div></div>
          <strong>${value}</strong>
        </div>`,
    )
    .join("");
}

function renderRecommendations() {
  const report = state.workspace.recommendation_report;
  getEl("recommendations").innerHTML = (report.items || [])
    .map(
      (item) => `
        <div class="recommendation ${item.level}">
          <span class="pill ${item.level === "blocker" ? "blocker" : item.level === "warning" ? "warning" : "neutral"}">${item.level}</span>
          <strong>${item.category}</strong>
          <p>${item.message}</p>
          ${item.action ? `<p class="muted">Suggested action: ${item.action}</p>` : ""}
        </div>`,
    )
    .join("");
  getEl("review-lanes").innerHTML = (state.workspace.catalog.reviewer_lanes || [])
    .map((lane) => `<div class="stack-item">${lane}</div>`)
    .join("");

  const metrics = state.currentRun?.metrics || {};
  getEl("run-metrics").innerHTML = Object.keys(metrics).length
    ? Object.entries(metrics)
        .map(([label, value]) => `<div class="kv"><span>${label}</span><strong>${typeof value === "number" ? safeNumber(value) : value}</strong></div>`)
        .join("")
    : `<div class="muted">Metrics appear after a run completes.</div>`;
  const outliers = state.currentRun?.outliers?.items || [];
  getEl("run-outliers").innerHTML = outliers.length
    ? outliers
        .slice(0, 8)
        .map((item) => `<div class="stack-item"><strong>${item.pdb_id}</strong><div class="muted">target ${safeNumber(item.target)} / prediction ${safeNumber(item.prediction)} / abs err ${safeNumber(item.absolute_error)}</div></div>`)
        .join("")
    : `<div class="muted">No outliers yet.</div>`;
  getEl("metrics-chart").innerHTML = Object.keys(metrics).length
    ? renderMetricsChart(metrics)
    : `<div class="muted">Run a study to render evaluation charts.</div>`;

  const latestBuild = state.workspace.latest_training_set_build;
  const splitPreview = latestBuild?.split_preview || state.workspace.training_set_preview?.split_preview || {};
  getEl("split-chart").innerHTML = Object.keys(splitPreview).length
    ? renderSplitChart(splitPreview)
    : `<div class="muted">Preview or build a dataset to render split charts.</div>`;
  const compareOptions = state.recentRuns.filter((item) => item.status === "completed").map((item) => ({
    value: item.run_id,
    label: item.run_id,
    status: "release",
    reason: item.status,
  }));
  renderSelect("compare-run-a-select", compareOptions, state.compareRunIds[0] || "");
  renderSelect("compare-run-b-select", compareOptions, state.compareRunIds[1] || "");
  getEl("run-comparison").innerHTML = state.runComparison?.items?.length
    ? state.runComparison.items
        .map((item) => `<div class="stack-item"><strong>${item.run_id}</strong><div class="muted">${item.requested_model_family} | backend ${item.resolved_backend} | RMSE ${safeNumber(item.test_rmse)}</div></div>`)
        .join("")
    : `<div class="muted">Run comparison appears when at least two completed runs are available.</div>`;
  getEl("split-diagnostics").innerHTML = Object.keys(splitPreview).length
    ? [
        `Grouping: ${splitPreview.grouping_policy || "n/a"}`,
        `Objective: ${splitPreview.objective || "n/a"}`,
        `Split counts: ${splitPreview.train_count || 0} / ${splitPreview.val_count || 0} / ${splitPreview.test_count || 0}`,
        `Components: ${splitPreview.component_count || 0}`,
      ]
        .map((line) => `<div class="stack-item">${line}</div>`)
        .join("")
    : `<div class="muted">Split diagnostics appear after previewing or building a study dataset.</div>`;
  getEl("study-summary-card").innerHTML = [
    `Study title: ${state.currentDraft.study_title}`,
    `Dataset build: ${latestBuild?.build_id || "not built yet"}`,
    `Run status: ${currentRunManifest()?.status || "idle"}`,
    `Report: ${state.currentRun?.artifacts?.["report.md"] || "No report yet"}`,
  ]
    .map((line) => `<div class="stack-item">${line}</div>`)
    .join("");
}

function renderAll() {
  ensureDraftShape();
  injectHelpButtons();
  renderNav();
  renderHero();
  renderToplineCards();
  renderStatusRail();
  renderActionButtons();
  renderStepper();
  renderProgramPanels();
  renderDataStrategyForm();
  renderRepresentationForm();
  renderPipelineComposer();
  renderExecutionConsole();
  renderRecommendations();
  bindDynamicButtons();
  renderFieldFeedbacks();
}

function applyEvaluationPreset(preset, draft) {
  const evaluation = draft.evaluation_plan;
  if (preset === "regression_core") {
    evaluation.metric_families = ["regression"];
    evaluation.robustness_slices = ["interface_size_bucket"];
  } else {
    evaluation.metric_families = ["regression", "ranking", "calibration"];
    evaluation.robustness_slices = ["uniref_family_holdout", "interface_size_bucket", "partner_novelty"];
  }
  draft.trainingPlanPreset = preset;
}

function collectDraftFromForm() {
  ensureDraftShape();
  const draft = structuredClone(state.currentDraft);
  const feature = draft.feature_recipes[0];
  const graph = draft.graph_recipes[0];
  draft.study_title = getEl("study-title-input").value.trim();
  draft.data_strategy.task_type = getEl("task-type-select").value;
  draft.data_strategy.label_type = getEl("label-type-select").value;
  draft.data_strategy.split_strategy = getEl("split-strategy-select").value;
  draft.data_strategy.structure_source_policy = getEl("structure-policy-select").value;
  draft.data_strategy.dataset_refs = Array.from(
    new Set([
      getEl("dataset-primary-select").value,
      ...fromSelectValues("dataset-refs-select"),
    ]),
  ).filter(Boolean);
  draft.data_strategy.audit_requirements = fromCheckedValues("audit-requirements");
  draft.training_set_request.task_type = draft.data_strategy.task_type;
  draft.training_set_request.label_type = draft.data_strategy.label_type;
  draft.training_set_request.structure_source_policy = draft.data_strategy.structure_source_policy;
  draft.training_set_request.dataset_refs = draft.data_strategy.dataset_refs;
  draft.training_set_request.source_families = fromSelectValues("source-families-select");
  draft.training_set_request.target_size = Number(getEl("target-size-input").value || "0");
  draft.training_set_request.acceptable_fidelity = getEl("acceptable-fidelity-select").value;
  draft.training_set_request.inclusion_filters = {
    max_resolution: Number(getEl("max-resolution-input").value || "0") || undefined,
    min_release_year: Number(getEl("min-release-year-input").value || "0") || undefined,
  };
  draft.training_set_request.exclusion_filters = {
    exclude_pdb_ids: (getEl("exclude-pdb-ids-input").value || "").split(",").map((item) => item.trim()).filter(Boolean),
  };
  graph.graph_kind = getEl("graph-kind-select").value;
  graph.region_policy = getEl("region-policy-select").value;
  graph.node_granularity = getEl("node-granularity-select").value;
  graph.encoding_policy = getEl("encoding-policy-select").value;
  graph.include_waters = getEl("include-waters-toggle").checked;
  graph.include_salt_bridges = getEl("include-salt-bridges-toggle").checked;
  graph.include_contact_shell = getEl("include-contact-shell-toggle").checked;
  feature.node_feature_policy = getEl("node-feature-policy-select").value;
  feature.edge_feature_policy = getEl("edge-feature-policy-select").value;
  feature.global_feature_sets = fromCheckedValues("global-features-control");
  feature.distributed_feature_sets = fromCheckedValues("distributed-features-control");
  draft.preprocess_plan.modules = fromCheckedValues("preprocess-modules");
  draft.preprocess_plan.cache_policy ??= "prefer_cached_materializations";
  draft.preprocess_plan.source_policy = draft.data_strategy.structure_source_policy;
  draft.preprocess_plan.options.hardware_runtime_preset = getEl("hardware-runtime-select").value;
  draft.example_materialization.graph_recipe_ids = [graph.recipe_id];
  draft.example_materialization.feature_recipe_ids = [feature.recipe_id];
  draft.example_materialization.preprocess_modules = draft.preprocess_plan.modules;
  draft.example_materialization.region_policy = graph.region_policy;
  draft.training_plan.model_family = getEl("model-family-select").value;
  draft.training_plan.architecture = getEl("architecture-select").value;
  draft.training_plan.optimizer = getEl("optimizer-select").value;
  draft.training_plan.scheduler = getEl("scheduler-select").value;
  draft.training_plan.loss_function = getEl("loss-function-select").value;
  draft.training_plan.epoch_budget = Number(getEl("epoch-budget-input").value || "1");
  draft.training_plan.batch_policy = getEl("batch-policy-select").value;
  draft.training_plan.mixed_precision = getEl("mixed-precision-select").value;
  draft.training_plan.uncertainty_head = getEl("uncertainty-head-select").value;
  draft.training_plan.ablations = fromCheckedValues("ablation-options-control");
  applyEvaluationPreset(getEl("evaluation-preset-select").value, draft);
  draft.data_strategy.graph_recipe_ids = [graph.recipe_id];
  draft.data_strategy.feature_recipe_ids = [feature.recipe_id];
  graph.feature_recipe_id = feature.recipe_id;
  return draft;
}

async function runDraftAction(endpoint, title) {
  try {
    setActionStatus("pending", title, "Working...");
    const payload = collectDraftFromForm();
    const result = await fetchJson(endpoint, { method: "POST", body: JSON.stringify(payload) });
    state.currentDraft = structuredClone(payload);
    state.workspace = { ...state.workspace, ...result, pipeline_spec: state.currentDraft };
    setActionStatus("success", title, "Completed successfully.");
    renderAll();
    return { ok: true, result };
  } catch (error) {
    setActionStatus("failed", title, error.message);
    return { ok: false, error };
  }
}

async function previewDataset() {
  try {
    setActionStatus("pending", "Previewing dataset", "Building candidate rows and diagnostics.");
    const payload = collectDraftFromForm();
    const result = await fetchJson("/api/model-studio/training-set-requests/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.currentDraft = structuredClone(payload);
    state.workspace = { ...state.workspace, pipeline_spec: state.currentDraft, training_set_preview: result };
    setActionStatus("success", "Dataset preview ready", `${result.candidate_preview?.row_count || 0} rows available for review.`);
    renderAll();
  } catch (error) {
    setActionStatus("failed", "Dataset preview failed", error.message);
  }
}

async function buildDataset() {
  const eligibility = actionEligibility();
  if (!eligibility.build.enabled) {
    setActionStatus("warning", "Build blocked", eligibility.build.reason);
    return;
  }
  try {
    setActionStatus("pending", "Building dataset", "Creating the study dataset and split artifacts.");
    const payload = collectDraftFromForm();
    const result = await fetchJson("/api/model-studio/training-set-builds/build", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.currentDraft = structuredClone(payload);
    state.workspace = { ...state.workspace, pipeline_spec: state.currentDraft, latest_training_set_build: result.build_manifest };
    setActionStatus("success", "Dataset build completed", result.build_manifest.dataset_ref);
    await loadWorkspace(state.currentDraft.pipeline_id);
  } catch (error) {
    setActionStatus("failed", "Dataset build failed", error.message);
  }
}

async function launchRun() {
  const eligibility = actionEligibility();
  if (!eligibility.launch.enabled) {
    setActionStatus("warning", "Run launch blocked", eligibility.launch.reason);
    return;
  }
  try {
    setActionStatus("pending", "Launching run", "Starting background study execution.");
    const payload = collectDraftFromForm();
    const result = await fetchJson("/api/model-studio/runs/launch", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.currentDraft = structuredClone(payload);
    state.currentRun = result.run;
    state.workspace.latest_training_set_build = result.latest_training_set_build || state.workspace.latest_training_set_build;
    state.recentRuns = result.recent_runs || [];
    state.selectedRunId = result.run?.run_manifest?.run_id || "";
    setActionStatus("success", "Run started", `Monitoring ${state.selectedRunId}.`);
    startRunPolling();
    await refreshRunComparison();
    renderAll();
  } catch (error) {
    setActionStatus("failed", "Run launch failed", error.message);
  }
}

async function openRun(runId, { restartPolling = true } = {}) {
  state.currentRun = await fetchJson(`/api/model-studio/runs/${runId}`);
  state.selectedRunId = runId;
  if (restartPolling) {
    startRunPolling();
  }
  syncDraftFromVisibleForm();
  renderAll();
}

async function refreshHardware() {
  try {
    setActionStatus("pending", "Discovering hardware", "Refreshing local CPU, RAM, and CUDA info.");
    state.workspace.hardware_profile = await fetchJson("/api/model-studio/hardware-profile");
    setActionStatus("success", "Hardware profile updated", state.workspace.hardware_profile.recommended_preset);
    renderAll();
  } catch (error) {
    setActionStatus("failed", "Hardware discovery failed", error.message);
  }
}

async function cancelRun() {
  const eligibility = actionEligibility();
  if (!eligibility.cancel.enabled) {
    setActionStatus("warning", "Cancel unavailable", eligibility.cancel.reason);
    return;
  }
  if (!state.selectedRunId) {
    setActionStatus("warning", "No run selected", "Choose or launch a run before cancelling.");
    return;
  }
  try {
    setActionStatus("pending", "Cancelling run", state.selectedRunId);
    await fetchJson(`/api/model-studio/runs/${state.selectedRunId}/cancel`, { method: "POST", body: "{}" });
    await openRun(state.selectedRunId);
    startRunPolling();
    setActionStatus("success", "Cancellation requested", "The runtime will stop at the next stage boundary.");
  } catch (error) {
    setActionStatus("failed", "Cancel failed", error.message);
  }
}

async function resumeRun() {
  const eligibility = actionEligibility();
  showInactiveExplanation("Resume run", eligibility.resume.reason);
}

function exportSummary() {
  const summary = [
    `Study title: ${state.currentDraft.study_title}`,
    `Run: ${state.selectedRunId || "none"}`,
    `Model family: ${state.currentDraft.training_plan.model_family}`,
    `Dataset build: ${state.workspace.latest_training_set_build?.dataset_ref || "none"}`,
    `Run status: ${currentRunManifest()?.status || "idle"}`,
    `Metrics: ${JSON.stringify(state.currentRun?.metrics || {}, null, 2)}`,
  ].join("\n");
  const blob = new Blob([summary], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "model_studio_summary.txt";
  link.click();
  URL.revokeObjectURL(url);
  getEl("study-export").innerHTML = `<div class="stack-item">Exported a local text summary for the current study.</div>`;
  setActionStatus("success", "Summary exported", "Downloaded model_studio_summary.txt");
}

function openReport() {
  const eligibility = actionEligibility();
  if (!eligibility.report.enabled) {
    setActionStatus("warning", "Report unavailable", eligibility.report.reason);
    return;
  }
  const reportPath = state.currentRun?.artifacts?.["report.md"];
  if (!reportPath) {
    setActionStatus("warning", "Report not available", "Complete a run before opening the report.");
    return;
  }
  getEl("study-export").innerHTML = `<div class="stack-item"><strong>Current report artifact</strong><div class="mono">${reportPath}</div></div>`;
  setActionStatus("success", "Report path ready", reportPath);
}

function bindDynamicButtons() {
  document.querySelectorAll("[data-pipeline-id]").forEach((button) => {
    button.onclick = async () => loadWorkspace(button.getAttribute("data-pipeline-id"));
  });
  document.querySelectorAll("[data-run-id]").forEach((button) => {
    button.onclick = async () => openRun(button.getAttribute("data-run-id"));
  });
  document.querySelectorAll("[data-scroll-target]").forEach((button) => {
    button.onclick = () => getEl(button.getAttribute("data-scroll-target"))?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  document.querySelectorAll("[data-chip-value]").forEach((button) => {
    button.onclick = () => {
      if (!isActiveStatus(button.getAttribute("data-chip-status") || "release")) {
        showInactiveExplanation(button.getAttribute("data-chip-label"), button.getAttribute("data-chip-reason"));
        return;
      }
      const pressed = button.getAttribute("aria-pressed") === "true";
      button.setAttribute("aria-pressed", pressed ? "false" : "true");
      button.classList.toggle("active", !pressed);
      setActionStatus("success", "Selection updated", `${button.getAttribute("data-chip-label")} ${pressed ? "removed" : "selected"}.`);
    };
  });
  document.querySelectorAll("[data-help-trigger]").forEach((button) => {
    button.onclick = (event) => {
      event.stopPropagation();
      openHelpPopover(button.getAttribute("data-help-trigger"), button);
    };
  });
  const draftControlIds = [
    "task-type-select",
    "label-type-select",
    "split-strategy-select",
    "structure-policy-select",
    "dataset-primary-select",
    "acceptable-fidelity-select",
    "graph-kind-select",
    "region-policy-select",
    "partner-awareness-select",
    "encoding-policy-select",
    "node-feature-policy-select",
    "edge-feature-policy-select",
    "model-family-select",
    "architecture-select",
    "optimizer-select",
    "scheduler-select",
    "loss-function-select",
    "batch-policy-select",
    "mixed-precision-select",
    "uncertainty-head-select",
    "evaluation-preset-select",
    "hardware-runtime-select",
    "study-title-input",
    "target-size-input",
    "max-resolution-input",
    "min-release-year-input",
    "exclude-pdb-ids-input",
    "epoch-budget-input",
    "include-waters-toggle",
    "include-salt-bridges-toggle",
    "include-contact-shell-toggle",
  ];
  const liveInputIds = new Set([
    "study-title-input",
    "target-size-input",
    "max-resolution-input",
    "min-release-year-input",
    "exclude-pdb-ids-input",
    "epoch-budget-input",
  ]);
  const handleDraftControlMutation = (id, node) => {
    const inactiveSelections = Array.from(node.selectedOptions || []).filter(
      (option) => !isActiveStatus(option.getAttribute("data-status") || "release"),
    );
    if (inactiveSelections.length) {
      const selectedOption = inactiveSelections[0];
      setFieldFeedback(
        id,
        "warning",
        `${selectedOption.getAttribute("data-label") || selectedOption.value} is not active`,
        selectedOption.getAttribute("data-reason") || "This option is not enabled yet.",
      );
      showInactiveExplanation(
        selectedOption.getAttribute("data-label") || selectedOption.value,
        selectedOption.getAttribute("data-reason") || "This option is not enabled yet.",
      );
      renderAll();
      return;
    }
    clearFieldFeedback(id);
    state.currentDraft = collectDraftFromForm();
    state.workspace = {
      ...state.workspace,
      pipeline_spec: state.currentDraft,
      training_set_preview: null,
      latest_training_set_build: null,
    };
    if (liveInputIds.has(id)) {
      if (typeof refreshInteractiveDraftFeedback === "function") {
        refreshInteractiveDraftFeedback();
      }
      renderActionButtons();
      renderFieldFeedbacks();
      return;
    }
    setActionStatus("idle", "Draft updated", `${id.replaceAll("-", " ")} changed.`);
    renderAll();
  };
  draftControlIds.forEach((id) => {
    const node = getEl(id);
    if (!node) return;
    const handler = () => handleDraftControlMutation(id, node);
    node.onchange = liveInputIds.has(id) ? null : handler;
    node.oninput = liveInputIds.has(id) ? handler : null;
    node.onkeyup = liveInputIds.has(id) ? handler : null;
  });
}

function bindStaticActions() {
  getEl("save-draft-button")?.addEventListener("click", async () => {
    const result = await runDraftAction("/api/model-studio/pipeline-specs/save-draft", "Draft saved");
    if (result.ok) {
      await loadWorkspace(state.currentDraft.pipeline_id);
    }
  });
  getEl("validate-draft-button")?.addEventListener("click", async () => {
    await runDraftAction("/api/model-studio/pipeline-specs/validate", "Draft validated");
  });
  getEl("compile-draft-button")?.addEventListener("click", async () => {
    await runDraftAction("/api/model-studio/pipeline-specs/compile", "Execution graph compiled");
  });
  getEl("preview-dataset-button")?.addEventListener("click", previewDataset);
  getEl("preview-step-button")?.addEventListener("click", previewDataset);
  getEl("build-dataset-button")?.addEventListener("click", buildDataset);
  getEl("build-step-button")?.addEventListener("click", buildDataset);
  getEl("launch-run-button")?.addEventListener("click", launchRun);
  getEl("refresh-runs-button")?.addEventListener("click", async () => {
    await loadWorkspace(state.currentDraft?.pipeline_id || "");
    setActionStatus("success", "Workspace refreshed", "Latest runs, datasets, and hardware have been reloaded.");
  });
  getEl("guided-view-button")?.addEventListener("click", () => setViewMode("guided"));
  getEl("advanced-view-button")?.addEventListener("click", () => setViewMode("advanced"));
  getEl("discover-hardware-button")?.addEventListener("click", refreshHardware);
  getEl("cancel-run-button")?.addEventListener("click", cancelRun);
  getEl("resume-run-button")?.addEventListener("click", resumeRun);
  getEl("compare-run-a-select")?.addEventListener("change", async (event) => {
    state.compareRunIds = [event.target.value, state.compareRunIds[1] || ""];
    await refreshRunComparison();
    renderAll();
  });
  getEl("compare-run-b-select")?.addEventListener("change", async (event) => {
    state.compareRunIds = [state.compareRunIds[0] || "", event.target.value];
    await refreshRunComparison();
    renderAll();
  });
  getEl("export-summary-button")?.addEventListener("click", exportSummary);
  getEl("open-report-button")?.addEventListener("click", openReport);
  document.body.addEventListener("click", (event) => {
    if (!event.target.closest(".info-button") && !event.target.closest("#help-popover")) closeHelpPopover();
  });
}

function startRunPolling() {
  if (state.pollHandle) {
    window.clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
  if (!state.selectedRunId) return;
  if (!["running", "queued"].includes(currentRunManifest()?.status)) return;
  state.pollHandle = window.setInterval(async () => {
    try {
      await openRun(state.selectedRunId, { restartPolling: false });
      if (!["running", "queued"].includes(currentRunManifest()?.status)) {
        window.clearInterval(state.pollHandle);
        state.pollHandle = null;
        await loadWorkspace(state.currentDraft?.pipeline_id || "");
        setActionStatus("success", "Run finished", `${state.selectedRunId} is now ${currentRunManifest()?.status}.`);
      }
    } catch (error) {
      setActionStatus("failed", "Run polling failed", error.message);
      window.clearInterval(state.pollHandle);
      state.pollHandle = null;
    }
  }, 2500);
}

async function loadWorkspace(pipelineId = "") {
  const query = pipelineId ? `?pipeline_id=${encodeURIComponent(pipelineId)}` : "";
  const [workspace, pipelines, runs] = await Promise.all([
    fetchJson(`/api/model-studio/workspace-preview${query}`),
    fetchJson("/api/model-studio/pipeline-specs"),
    fetchJson("/api/model-studio/runs"),
  ]);
  state.workspace = workspace;
  state.currentDraft = structuredClone(workspace.pipeline_spec);
  ensureDraftShape();
  state.pipelineList = pipelines.items || [];
  state.recentRuns = runs.items || [];
  const preferredRun =
    state.recentRuns.find((item) => item.run_id === state.selectedRunId) ||
    state.recentRuns.find((item) => item.status === "running") ||
    state.recentRuns.find((item) => item.status === "completed") ||
    state.recentRuns[0];
  state.currentRun = preferredRun ? await fetchJson(`/api/model-studio/runs/${preferredRun.run_id}`) : null;
  state.selectedRunId = preferredRun?.run_id || "";
  const completedRuns = state.recentRuns.filter((item) => item.status === "completed");
  if (state.compareRunIds.length < 2) {
    state.compareRunIds = completedRuns.slice(0, 2).map((item) => item.run_id);
  }
  await refreshRunComparison();
  renderAll();
  startRunPolling();
}

if (document.body?.dataset?.studioVariant !== "beta") {
  bindStaticActions();
  setViewMode("guided");
  loadWorkspace().catch((error) => {
    getEl("study-title").textContent = "Model Studio failed to load";
    getEl("study-summary").textContent = error.message;
    setActionStatus("failed", "Workspace failed to load", error.message);
  });
}
