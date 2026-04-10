function betaTitleCase(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function betaFormatTimestamp(value) {
  if (!value) return "n/a";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

function betaStageTone(status) {
  if (status === "completed") return "completed";
  if (status === "running" || status === "queued" || status === "current") return "running";
  if (status === "blocked" || status === "failed" || status === "cancelled") return "failed";
  return "neutral";
}

function betaStepStatePill(status) {
  if (status === "completed") return "neutral";
  if (status === "current") return "info";
  if (status === "next") return "warning";
  if (status === "blocked") return "blocker";
  if (status === "inactive") return "warning";
  return "neutral";
}

function betaCurrentHardwareMode() {
  return (
    state.currentDraft?.preprocess_plan?.options?.hardware_runtime_preset ||
    state.workspace?.ui_contract?.current_status_rail?.hardware_mode ||
    state.workspace?.status_rail?.hardware_mode ||
    state.workspace?.hardware_profile?.recommended_preset ||
    "auto_recommend"
  );
}

function betaUiContract() {
  return state.workspace?.ui_contract || {};
}

function betaSessionId() {
  if (!state.betaSessionId) {
    state.betaSessionId = `beta-session-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  }
  return state.betaSessionId;
}

async function betaRecordSessionEvent(eventType, detail, context = {}) {
  try {
    await fetchJson("/api/model-studio/session-events", {
      method: "POST",
      body: JSON.stringify({
        session_id: betaSessionId(),
        event_type: eventType,
        detail,
        step_id: context.step_id || null,
        pipeline_id: state.currentDraft?.pipeline_id || null,
        run_id: state.selectedRunId || null,
        context,
      }),
    });
  } catch {
    // Intentionally do not interrupt the beta flow for telemetry failures.
  }
}

function betaDatasetOptions() {
  const registry = uiOptionRegistry().dataset_refs || [];
  const known = new Map(
    (state.workspace?.program_status?.known_datasets || []).map((item) => [item.dataset_ref, item]),
  );
  const poolByRef = new Map();
  (betaUiContract().dataset_pool_views || []).forEach((pool) => {
    (pool.dataset_refs || []).forEach((ref) => {
      if (!poolByRef.has(ref)) {
        poolByRef.set(ref, pool);
      }
    });
  });
  return registry.map((option) => {
    const ref = optionValue(option);
    const knownItem = known.get(ref);
    const poolItem = poolByRef.get(ref);
    return {
      ...option,
      label:
        optionLabel(option) +
        (poolItem?.row_count || knownItem?.row_count
          ? ` (${poolItem?.row_count || knownItem?.row_count} rows)`
          : ""),
      reason:
        optionReason(option) ||
        poolItem?.use_now_summary ||
        poolItem?.maturity ||
        knownItem?.maturity ||
        "Known dataset option.",
      inactive_reason:
        optionInactiveReason(option) ||
        poolItem?.launchability_reason ||
        optionReason(option) ||
        poolItem?.notes?.join(" | ") ||
        poolItem?.maturity ||
        knownItem?.maturity ||
        "",
    };
  });
}

function betaOptionsByValue(category) {
  return new Map((uiOptionRegistry()[category] || []).map((option) => [optionValue(option), option]));
}

function betaSelectedOptionLabel(category, value) {
  return optionLabel(betaOptionsByValue(category).get(value) || value);
}

function betaRenderProgressBar(stageStatus) {
  const current = Number(stageStatus?.progress_current || 0);
  const total = Number(stageStatus?.progress_total || 0);
  const explicit = Number(stageStatus?.progress_percent || 0);
  const percent = total > 0 ? Math.max(0, Math.min(100, Math.round((current / total) * 100))) : explicit;
  if (!percent && !current && !total) {
    return `<div class="muted">Progress details are not available yet for this stage.</div>`;
  }
  return `
    <div class="progress-block">
      <div class="progress-meta">
        <span>${current || 0}${total ? ` / ${total}` : ""}</span>
        <strong>${percent}%</strong>
      </div>
      <div class="progress-track"><div class="progress-fill" style="width:${percent}%"></div></div>
    </div>
  `;
}

function betaRenderKeyValueList(items) {
  return items
    .filter((item) => item[1] !== undefined && item[1] !== null && item[1] !== "")
    .map(
      ([label, value]) => `
        <div class="kv">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>`,
    )
    .join("");
}

function betaRenderEmpty(message) {
  return `<div class="stack-item muted">${escapeHtml(message)}</div>`;
}

function betaReadableState(value) {
  const text = String(value || "").trim();
  if (!text) return "n/a";
  return betaTitleCase(text);
}

function betaSourceFamilyImpactSummary(sourceFamilies, poolViews) {
  const selected = new Set(sourceFamilies || []);
  const launchable = [];
  const reviewOnly = [];
  const addPools = (predicate) => {
    poolViews.filter(predicate).forEach((pool) => {
      if (pool.is_launchable) {
        launchable.push(pool.pool_id);
      } else {
        reviewOnly.push(pool.pool_id);
      }
    });
  };
  if (selected.has("balanced_ppi_beta_pool")) {
    addPools(() => true);
  }
  if (selected.has("approved_local_ppi")) {
    addPools((pool) => !String(pool.pool_id || "").includes("expanded_pp_benchmark_v1"));
  }
  if (selected.has("release_frozen")) {
    addPools((pool) => String(pool.pool_id || "").includes("release_pp_alpha_benchmark_v1"));
  }
  if (selected.has("robust_structure_backed")) {
    addPools((pool) => String(pool.pool_id || "").includes("robust_pp_benchmark_v1"));
  }
  if (selected.has("expanded_ppi_procurement")) {
    addPools((pool) => String(pool.pool_id || "").includes("expanded_ppi_procurement_bridge"));
  }
  return {
    launchableCount: new Set(launchable).size,
    reviewOnlyCount: new Set(reviewOnly).size,
  };
}

function betaRenderDiagramNodes(nodes) {
  return nodes
    .map(
      (node, index) => `
        <div class="diagram-node ${node.tone || ""}">
          <strong>${escapeHtml(node.title)}</strong>
          ${node.detail ? `<span>${escapeHtml(node.detail)}</span>` : ""}
        </div>
        ${index < nodes.length - 1 ? `<div class="diagram-arrow">-&gt;</div>` : ""}`,
    )
    .join("");
}

function betaRenderPipelineFlowchart() {
  const draft = state.currentDraft;
  const graph = draft.graph_recipes[0];
  const feature = draft.feature_recipes[0];
  const plan = draft.training_plan;
  const preprocess = draft.preprocess_plan.modules || [];
  const warnings = [];
  if (plan.model_family === "graphsage" && !graph.graph_kind) {
    warnings.push("GraphSAGE requires a graph recipe.");
  }
  if (
    !isActiveStatus(
      optionStatus(betaOptionsByValue("node_granularities").get(graph.node_granularity)),
    )
  ) {
    warnings.push(`${betaSelectedOptionLabel("node_granularities", graph.node_granularity)} is currently inactive.`);
  }
  if (preprocess.some((item) => ["PyRosetta", "Free-state comparison"].includes(item))) {
    warnings.push("Selected preprocessing includes inactive structural physics stages.");
  }
  const pipelineNodes = [
    { title: "Training set request", detail: betaSelectedOptionLabel("task_types", draft.data_strategy.task_type), tone: "strong" },
    { title: "Dataset build & split", detail: betaSelectedOptionLabel("split_strategies", draft.data_strategy.split_strategy) },
    {
      title: "Preprocess",
      detail: preprocess.slice(0, 2).join(" + ") || "Core structural summaries",
    },
    {
      title: "Representation",
      detail: `${betaSelectedOptionLabel("graph_kinds", graph.graph_kind)} / ${betaSelectedOptionLabel("node_granularities", graph.node_granularity)} / ${betaSelectedOptionLabel("partner_awareness_modes", graph.partner_awareness || "symmetric")}`,
    },
    {
      title: "Feature bundle",
      detail: `${(feature.global_feature_sets || []).length} global + ${(feature.distributed_feature_sets || []).length} distributed`,
    },
    {
      title: "Model",
      detail: betaSelectedOptionLabel("model_families", plan.model_family),
      tone: isActiveStatus(
        optionStatus(
          betaOptionsByValue("model_families").get(plan.model_family) || plan.model_family,
        ),
      )
        ? "strong"
        : "",
    },
    {
      title: "Evaluation",
      detail: betaSelectedOptionLabel("evaluation_presets", draft.trainingPlanPreset || "regression_plus_calibration"),
    },
    { title: "Report", detail: "Metrics + charts + export pack" },
  ];
  return `
    <div class="diagram-flow-wrap">
      <div class="diagram-flow">${betaRenderDiagramNodes(pipelineNodes)}</div>
      ${
        warnings.length
          ? `<div class="diagram-warning-list">${warnings
              .map((warning) => `<div class="stack-item warning">${escapeHtml(warning)}</div>`)
              .join("")}</div>`
          : `<div class="diagram-footnote">The flow updates from the selected dataset, representation, preprocessing, and model settings.</div>`
      }
    </div>
  `;
}

renderHero = function renderHero() {
  const draft = state.currentDraft;
  const quality = state.workspace.quality_gates;
  const hardware = state.workspace.hardware_profile || {};
  const latestBuild = state.workspace.latest_training_set_build;
  getEl("study-title").textContent = draft.study_title;
  getEl("study-summary").textContent =
    "Define a study dataset, inspect the full candidate/build tables, configure the launchable or review-pending PPI lane, run the selected beta path with explicit backend disclosure, and review the resulting metrics and charts.";
  getEl("hero-badges").innerHTML = [
    betaSelectedOptionLabel("task_types", draft.data_strategy.task_type),
    betaSelectedOptionLabel("model_families", draft.training_plan.model_family),
    betaSelectedOptionLabel("split_strategies", draft.data_strategy.split_strategy),
    `rows:${latestBuild?.row_count || draft.training_set_request?.target_size || "auto"}`,
    `quality:${quality.status}`,
    `runtime:${hardware.recommended_preset || "auto"}`,
  ]
    .map((item) => `<span class="badge">${escapeHtml(item)}</span>`)
    .join("");
};

renderModelDiagram = function renderModelDiagram(modelFamily) {
  const templates = {
    xgboost: [
      [{ title: "Global features", detail: "Engineered assay + structure inputs", tone: "strong" }],
      [{ title: "HistGradientBoosting adapter", detail: "Release backend for xgboost-like flow" }],
      [{ title: "Regression output", detail: "delta_G prediction" }],
    ],
    catboost: [
      [{ title: "Global features", detail: "Engineered assay + structure inputs", tone: "strong" }],
      [{ title: "RandomForest adapter", detail: "Release backend for catboost-like flow" }],
      [{ title: "Regression output", detail: "delta_G prediction" }],
    ],
    mlp: [
      [{ title: "Global features", detail: "Normalized tabular inputs", tone: "strong" }],
      [
        { title: "Dense layer 1", detail: "Embedding / projection" },
        { title: "Dense layer 2", detail: "Hidden representation" },
        { title: "Regression head", detail: "Affinity estimate" },
      ],
    ],
    multimodal_fusion: [
      [
        { title: "Graph branch", detail: "Graph summary / pooled structural context", tone: "strong" },
        { title: "Global branch", detail: "Engineered study-level features", tone: "strong" },
        { title: "Distributed branch", detail: "Packed tensor summaries", tone: "strong" },
      ],
      [
        { title: "Fusion block", detail: "Concatenate + align modalities" },
        { title: "MLP trunk", detail: "Joint latent representation" },
        { title: "Regression head", detail: "delta_G prediction" },
      ],
    ],
    graphsage: [
      [{ title: "Graph payload", detail: "Residue/interface graph", tone: "strong" }],
      [
        { title: "GraphSAGE-lite", detail: "Neighborhood aggregation" },
        { title: "Global pooling", detail: "Graph-level summary" },
        { title: "Regression head", detail: "Affinity estimate" },
      ],
    ],
    gin: [
      [{ title: "Graph payload", detail: "Residue/interface graph", tone: "strong" }],
      [
        { title: "Graph adapter family", detail: "GIN-labeled request resolved through the shared lightweight graph backend" },
        { title: "Global pooling", detail: "Graph-level summary" },
        { title: "Regression head", detail: "Affinity estimate" },
      ],
    ],
    gcn: [
      [{ title: "Graph payload", detail: "Residue/interface graph", tone: "strong" }],
      [
        { title: "Graph adapter family", detail: "GCN-labeled request resolved through the shared lightweight graph backend" },
        { title: "Global pooling", detail: "Graph-level summary" },
        { title: "Regression head", detail: "Affinity estimate" },
      ],
    ],
    gat: [
      [{ title: "Graph payload", detail: "Residue/interface graph", tone: "strong" }],
      [
        { title: "Graph adapter family", detail: "GAT-labeled request resolved through the shared lightweight graph backend with explicit adapter disclosure" },
        { title: "Global pooling", detail: "Graph-level summary" },
        { title: "Regression head", detail: "Affinity estimate" },
      ],
    ],
    late_fusion_ensemble: [
      [
        { title: "XGBoost-like branch", detail: "Tree-based tabular prediction", tone: "strong" },
        { title: "CatBoost-like branch", detail: "Forest adapter tabular prediction", tone: "strong" },
        { title: "MLP branch", detail: "Dense nonlinear tabular prediction", tone: "strong" },
      ],
      [
        { title: "Late fusion ensemble", detail: "Averages the branch predictions" },
        { title: "Regression head", detail: "delta_G estimate" },
      ],
    ],
  };
  const rows = templates[modelFamily] || [
    [{ title: "Planned model family", detail: "Visible in catalog, inactive in current beta lane." }],
  ];
  return `
    <div class="diagram-model">
      ${rows
        .map(
          (row) => `
            <div class="diagram-row">
              ${betaRenderDiagramNodes(row)}
            </div>`,
        )
        .join("")}
    </div>
  `;
};

showInactiveExplanation = function showInactiveExplanation(label, reason) {
  const inactiveCatalog = betaUiContract().inactive_explanations || [];
  const featureGateViews = betaUiContract().feature_gate_views || [];
  const matching = inactiveCatalog.find((item) => item.label === label || item.value === label);
  const matchingGate = featureGateViews.find(
    (item) => item.feature_id === label || item.feature_id.endsWith(`:${label}`),
  );
  const summary = matching?.help_summary || reason || "This option is visible for planning but not enabled in the current beta lane.";
  const audienceLabel =
    matchingGate?.audience_state === "launchable_now"
      ? "Launchable now"
      : matchingGate?.audience_state === "review_pending"
      ? "Review pending"
      : matching?.status
      ? betaReadableState(matching.status)
      : "Inactive";
  const explanationHeading = audienceLabel === "Review pending" ? "Why review is pending" : "Why inactive";
  getEl("inactive-explanation").innerHTML = `
    <div class="stack-item">
      <strong>${escapeHtml(matching?.label || label)}</strong>
      <div class="muted">${escapeHtml(summary)}</div>
    </div>
    ${
      matching?.inactive_reason
        ? `<div class="stack-item"><strong>${escapeHtml(explanationHeading)}</strong><div class="muted">${escapeHtml(matching.inactive_reason)}</div></div>`
        : ""
    }
    ${
      audienceLabel
        ? `<div class="stack-item"><strong>Status</strong><div class="muted">${escapeHtml(audienceLabel)}</div></div>`
        : ""
    }
    ${
      matchingGate?.prototype_artifact
        ? `<div class="stack-item"><strong>Prototype artifact</strong><div class="muted">${escapeHtml(matchingGate.prototype_artifact)}</div></div>`
        : ""
    }
    ${
      matchingGate?.required_reviewers?.length
        ? `<div class="stack-item"><strong>Required reviewers</strong><div class="muted">${escapeHtml(matchingGate.required_reviewers.join(", "))}</div></div>`
        : ""
    }
    ${
      matchingGate?.required_matrix_tests?.length
        ? `<div class="stack-item"><strong>Required evidence</strong><div class="muted">${escapeHtml(matchingGate.required_matrix_tests.join(", "))}</div></div>`
        : ""
    }
  `;
  setActionStatus(
    "warning",
    `${matching?.label || label} is ${audienceLabel.toLowerCase()}`,
    matching?.inactive_reason || matchingGate?.launchability_reason || summary,
  );
  betaRecordSessionEvent("inactive_explanation_opened", matching?.label || label, {
    step_id: "inactive-explanation",
    status: matching?.status || "planned_inactive",
  });
};

computeStepStatuses = function computeStepStatuses() {
  return (state.workspace?.stepper || []).map((step, index, all) => {
    if (step.status) return step;
    return {
      ...step,
      status: index === 0 ? "current" : index === 1 ? "next" : "inactive",
      next_action: step.next_action || (all[index + 1] ? `Continue to ${all[index + 1].label}.` : "Review outputs."),
      produced: step.produced || [],
      blockers: step.blockers || [],
    };
  });
};

renderStatusRail = function renderStatusRail() {
  const rail = getEl("action-status-rail");
  const runManifest = currentRunManifest();
  const workspaceRail = betaUiContract().current_status_rail || state.workspace?.status_rail || {};
  const currentStageStatus =
    (runManifest?.active_stage && state.currentRun?.stage_status?.[runManifest.active_stage]) || null;
  const cards = [
    {
      label: "Latest action",
      value: state.actionStatus.title,
      detail: state.actionStatus.detail || "No active warning.",
      tone: state.actionStatus.level || "neutral",
    },
    {
      label: "Current step",
      value: workspaceRail.current_step || "Training Set Request",
      detail: workspaceRail.current_study || state.currentDraft?.study_title || "Current study",
      tone: "neutral",
    },
    {
      label: "Current stage",
      value: betaTitleCase(runManifest?.active_stage || workspaceRail.current_run_status || "idle"),
      detail: currentStageStatus?.substage || currentStageStatus?.detail || "No stage is currently active.",
      tone: betaStageTone(runManifest?.status || "idle"),
    },
    {
      label: "Last heartbeat",
      value: betaFormatTimestamp(runManifest?.heartbeat_at || workspaceRail.last_heartbeat),
      detail: runManifest?.status === "running" ? "Heartbeat updates while work is active." : "No active heartbeat yet.",
      tone: "neutral",
    },
    {
      label: "Requested hardware",
      value: betaSelectedOptionLabel("hardware_runtime_presets", betaCurrentHardwareMode()),
      detail: state.workspace?.hardware_profile?.gpu_name
        ? `${state.workspace.hardware_profile.gpu_name} / ${safeNumber(state.workspace.hardware_profile.gpu_memory_gb, 1)} GB VRAM detected locally`
        : "CPU-focused execution requested or inferred",
      tone: "requested",
    },
    {
      label: "Execution placement",
      value:
        state.currentRun?.model_details?.resolved_execution_device ||
        runManifest?.resolved_execution_device ||
        workspaceRail.resolved_execution_device ||
        "n/a",
      detail:
        state.currentRun?.model_details?.resolved_hardware_preset ||
        workspaceRail.resolved_hardware_mode ||
        "Resolved separately from the requested hardware strategy.",
      tone: "resolved",
    },
    {
      label: "Resolved backend",
      value:
        state.currentRun?.model_details?.resolved_backend ||
        runManifest?.resolved_backend ||
        workspaceRail.resolved_backend ||
        "n/a",
      detail: "Shows the truthful backend or adapter actually used for the selected model family.",
      tone: "resolved",
    },
    {
      label: "Latest artifact",
      value: workspaceRail.latest_artifact ? workspaceRail.latest_artifact.split(/[\\/]/).slice(-1)[0] : "none",
      detail: workspaceRail.latest_error || workspaceRail.latest_warning || "No active warning from the current workspace snapshot.",
      tone: workspaceRail.latest_error ? "failed" : workspaceRail.latest_warning ? "warning" : "neutral",
    },
  ];
  rail.innerHTML = cards
    .map(
      (card) => `
        <article class="status-card ${card.tone}">
          <span class="label">${escapeHtml(card.label)}</span>
          <strong>${escapeHtml(card.value || "n/a")}</strong>
          <div class="muted status-detail">${escapeHtml(card.detail || "")}</div>
        </article>`,
    )
    .join("");
};

function betaTrainingSetSizingSummary() {
  const previewCandidate = state.workspace?.training_set_preview?.candidate_preview || {};
  const buildManifest = state.workspace?.latest_training_set_build || {};
  const liveTargetValue = Number(getEl("target-size-input")?.value || "0") || null;
  const summary = {
    total_candidate_count: previewCandidate.total_candidate_count ?? buildManifest.total_candidate_count ?? 0,
    filtered_candidate_count: previewCandidate.filtered_candidate_count ?? buildManifest.filtered_candidate_count ?? 0,
    eligible_quality_ceiling: previewCandidate.eligible_quality_ceiling ?? buildManifest.eligible_quality_ceiling ?? 0,
    requested_target_size: liveTargetValue
      || state.currentDraft?.training_set_request?.target_size
      || previewCandidate.requested_target_size
      || buildManifest.requested_target_size
      || null,
    resolved_target_cap: previewCandidate.resolved_target_cap ?? buildManifest.resolved_target_cap ?? 0,
    final_selected_count: previewCandidate.final_selected_count ?? buildManifest.final_selected_count ?? 0,
    target_size_warning: previewCandidate.target_size_warning || buildManifest.target_size_warning || "",
  };
  return summary;
}

function betaRenderTrainingSetSizing(summary) {
  const lines = [
    ["Total candidate universe", summary.total_candidate_count || 0],
    ["Filtered candidates", summary.filtered_candidate_count || 0],
    ["Eligible quality ceiling", summary.eligible_quality_ceiling || 0],
    ["Requested target", summary.requested_target_size || "Auto ceiling"],
    ["Resolved target cap", summary.resolved_target_cap || 0],
    ["Final selected count", summary.final_selected_count || 0],
  ];
  return lines
    .map(
      ([label, value]) => `
        <div class="stack-item">
          <strong>${escapeHtml(String(label))}</strong>
          <div class="muted">${escapeHtml(String(value))}</div>
        </div>`,
    )
    .join("");
}

function refreshInteractiveDraftFeedback() {
  const sizing = betaTrainingSetSizingSummary();
  const targetGuidance = getEl("target-size-guidance");
  if (targetGuidance) {
    targetGuidance.className = `field-feedback inline-guidance persistent-field-feedback ${sizing.target_size_warning ? "warning" : "neutral"}`;
    targetGuidance.innerHTML = betaRenderTrainingSetSizing(sizing);
    if (sizing.target_size_warning) {
      targetGuidance.innerHTML += `
        <div class="stack-item warning">
          <strong>Target cap warning</strong>
          <div>${escapeHtml(sizing.target_size_warning)}</div>
        </div>`;
    }
  }
  const enteredTargetSize = Number(getEl("target-size-input")?.value || "0") || null;
  if (enteredTargetSize && sizing.eligible_quality_ceiling && enteredTargetSize > sizing.eligible_quality_ceiling) {
    setFieldFeedback(
      "target-size-input",
      "warning",
      "Requested target exceeds the eligible ceiling",
      `This draft requests ${enteredTargetSize} rows, but the current quality-controlled ceiling is ${sizing.eligible_quality_ceiling}. Build will cap at ${Math.min(enteredTargetSize, sizing.eligible_quality_ceiling)}.`,
    );
  } else {
    clearFieldFeedback("target-size-input");
  }
}

function renderOnboardingPanel() {
  const onboarding = betaUiContract().onboarding || {};
  const betaSupport = betaUiContract().beta_support || {};
  const betaDocs = betaSupport.beta_docs || [];
  getEl("onboarding-summary").innerHTML = `
    <div class="stack-item">
      <strong>${escapeHtml(onboarding.title || "How this guided study works")}</strong>
      <div class="muted">${escapeHtml(onboarding.summary || "Use the guided stepper to define a study, build the dataset, run the model, and review the outputs.")}</div>
    </div>
    ${
      betaSupport.how_this_beta_works
        ? `<div class="stack-item"><strong>How this beta works</strong><div class="muted">${escapeHtml(betaSupport.how_this_beta_works)}</div></div>`
        : ""
    }
  `;
  getEl("onboarding-steps").innerHTML = (onboarding.steps || [])
    .map((item, index) => `<div class="stack-item"><strong>Step ${index + 1}</strong><div class="muted">${escapeHtml(item)}</div></div>`)
    .join("");
  getEl("beta-safe-now").innerHTML = `
    <div class="stack-item">
      <strong>What is safe to use now</strong>
      <div class="muted">${escapeHtml((betaSupport.safe_to_use_now || []).join(" ")) || "The launchable beta lane is shown directly in the guided controls."}</div>
    </div>
  `;
  getEl("beta-review-pending").innerHTML = `
    <div class="stack-item">
      <strong>What is review-pending</strong>
      <div class="muted">${escapeHtml((betaSupport.review_pending || []).join(" ")) || "Review-pending items stay visible for planning, but they are not safe for routine study launches yet."}</div>
    </div>
  `;
  getEl("beta-reporting-help").innerHTML = `
    <div class="stack-item">
      <strong>How to report an issue</strong>
      <div class="muted">${escapeHtml(betaSupport.how_to_report || "Use Need help / report issue whenever a field, blocker, chart, or result feels unclear.")}</div>
    </div>
  `;
  if (getEl("beta-known-limitations")) {
    getEl("beta-known-limitations").innerHTML = `
      <div class="stack-item">
        <strong>Known limitations</strong>
        <div class="muted">${escapeHtml((betaSupport.known_limitations || []).join(" ")) || "Current beta limitations are not available yet."}</div>
      </div>
    `;
  }
  if (getEl("beta-support-expectation")) {
    getEl("beta-support-expectation").innerHTML = `
      <div class="stack-item">
        <strong>Support response expectation</strong>
        <div class="muted">${escapeHtml(betaSupport.support_response_expectation || "Support response expectations are not available yet.")}</div>
      </div>
    `;
  }
  if (getEl("beta-escalation-path")) {
    getEl("beta-escalation-path").innerHTML = (betaSupport.escalation_path || []).length
      ? (betaSupport.escalation_path || [])
          .map((item) => `<div class="stack-item muted">${escapeHtml(item)}</div>`)
          .join("")
      : betaRenderEmpty("No escalation path is recorded yet.");
  }
  if (getEl("beta-doc-pack")) {
    getEl("beta-doc-pack").innerHTML = betaDocs.length
      ? betaDocs
          .map(
            (doc) => `
              <div class="stack-item">
                <strong>${escapeHtml(doc.title || doc.doc_id)}</strong>
                <div class="muted">${escapeHtml(doc.summary || "No summary recorded.")}</div>
                <div class="muted">${escapeHtml(betaReadableState(doc.category || "general"))} | ${escapeHtml(betaReadableState(doc.audience || "internal"))}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No beta documentation pack is registered yet.");
  }
}

renderStepper = function renderStepper() {
  const steps = computeStepStatuses();
  getEl("stepper").innerHTML = steps
    .map(
      (step, index) => `
        <article class="step-card ${step.status}">
          <div class="step-header">
            <div class="step-title-block">
              <span class="step-index">Step ${index + 1}</span>
              <strong>${escapeHtml(step.label)}</strong>
            </div>
            <span class="pill ${betaStepStatePill(step.status)}">${escapeHtml(step.status)}</span>
          </div>
          <p>${escapeHtml(step.summary || "")}</p>
          <div class="step-produced">
            ${(step.produced || [])
              .map((item) => `<div class="stack-item">${escapeHtml(item)}</div>`)
              .join("") || `<div class="stack-item muted">No artifacts yet.</div>`}
          </div>
          <div class="step-next"><strong>Next:</strong> ${escapeHtml(step.next_action || "Continue through the guided flow.")}</div>
          ${
            (step.blockers || []).length
              ? `<div class="step-blockers">${step.blockers
                  .map((item) => `<div class="stack-item">${escapeHtml(item)}</div>`)
                  .join("")}</div>`
              : ""
          }
          <div class="step-actions">
            <button type="button" class="secondary compact-button" data-scroll-target="${escapeHtml(step.workspace)}">Open step</button>
          </div>
        </article>`,
    )
    .join("");
};

renderProgramPanels = function renderProgramPanels() {
  const programStatus = state.workspace.program_status;
  const uiContract = betaUiContract();
  const preview = programStatus.program_preview || {};
  const orchestrator = programStatus.orchestrator_state || {};
  const summary = preview.summary || {};
  const knownDatasets = programStatus.known_datasets || [];
  const canonicalKnownDatasets = knownDatasets.filter(
    (item) => !String(item.dataset_ref || "").startsWith("study_build:"),
  );
  const selectedDataset = state.workspace.selected_dataset;
  const datasetPools = uiContract.dataset_pools || [];
  const candidatePoolSummary = uiContract.candidate_pool_summary || {};
  const candidateDatabaseSummary =
    uiContract.candidate_database_summary_canonical || uiContract.candidate_database_summary_v3 || uiContract.candidate_database_summary || {};
  const candidateDatabaseSummaryV2 = uiContract.candidate_database_summary_v2 || {};
  const candidateDatabaseSummaryV3 = uiContract.candidate_database_summary_v3 || {};
  const governedBridgeManifests = uiContract.governed_bridge_manifests || [];
  const governedSubsetManifests = uiContract.governed_subset_manifests_v2 || uiContract.governed_subset_manifests || [];
  const activationLedger = uiContract.activation_ledger || [];
  const promotionReports = uiContract.pool_promotion_reports || [];
  const promotionQueue = uiContract.promotion_queue_canonical || uiContract.promotion_queue_v2 || uiContract.promotion_queue || [];
  const stage2ScientificTracks = uiContract.stage2_scientific_tracks || [];
  const featureGateViews = uiContract.feature_gate_views || [];
  const modelActivationMatrix = uiContract.model_activation_matrix || { entries: [] };
  const betaSupport = uiContract.beta_support || {};
  const betaReadiness = uiContract.beta_readiness_dashboard || programStatus.beta_readiness_dashboard || {};
  const betaTestAgents = uiContract.beta_test_agents || programStatus.beta_test_agents || [];
  const betaTestAgentStatus = uiContract.beta_test_agent_status || programStatus.beta_test_agent_status || {};
  const betaTestAgentMatrix = uiContract.beta_test_agent_matrix || programStatus.beta_test_agent_matrix || { coverage: [] };
  const betaTestAgentFindings = uiContract.beta_test_agent_findings || programStatus.beta_test_agent_findings || { open_findings: [] };
  const referenceLibraryStatus = uiContract.reference_library_status || programStatus.reference_library_status || {};
  const referenceLibraryInstall = uiContract.reference_library_install_status || programStatus.reference_library_install_status || {};
  const referenceLibraryChunkCatalog = uiContract.reference_library_chunk_catalog || programStatus.reference_library_chunk_catalog || [];
  const referenceLibraryGaps = uiContract.reference_library_gaps || programStatus.reference_library_gaps || {};
  getEl("program-mini-status").innerHTML = `
    <div class="stack-item"><strong>${escapeHtml(summary.status || "unknown")}</strong><div class="muted">beta lane status</div></div>
    <div class="stack-item"><strong>${programStatus.training_set_build_count || 0}</strong><div class="muted">study dataset builds</div></div>
    <div class="stack-item"><strong>${(orchestrator.active_workers || []).length}</strong><div class="muted">active workers</div></div>
  `;
  getEl("pipeline-library").innerHTML = state.pipelineList
    .map(
      (item) => `
        <button class="library-item" data-pipeline-id="${item.pipeline_id}">
          <strong>${escapeHtml(item.study_title)}</strong>
          <div class="muted">${escapeHtml(item.task_type)} / ${escapeHtml(item.model_family)}</div>
        </button>`,
    )
    .join("");
  getEl("program-status-detail").innerHTML = betaRenderKeyValueList([
    ["Schema", state.workspace.schema_version],
    ["Mode", preview.mode || "release"],
    ["Draft specs", programStatus.draft_count || 0],
    ["Studio runs", programStatus.run_count || 0],
    ["Study builds", programStatus.training_set_build_count || 0],
    ["Review artifacts", programStatus.release_review_artifact_count || 0],
  ]);
  getEl("quality-gates").innerHTML = (state.workspace.quality_gates.checks || [])
    .map(
      (check) => `
        <div class="recommendation ${check.status === "blocked" ? "blocker" : check.status === "review_required" ? "warning" : ""}">
          <span class="pill ${check.status === "blocked" ? "blocker" : check.status === "review_required" ? "warning" : "neutral"}">${escapeHtml(check.status)}</span>
          <strong>${escapeHtml(check.gate)}</strong>
          <p>${escapeHtml(check.detail)}</p>
        </div>`,
    )
    .join("");
  getEl("recent-runs").innerHTML = state.recentRuns.length
    ? state.recentRuns
        .slice(0, 8)
        .map(
          (run) => `
            <button class="library-item" data-run-id="${run.run_id}">
              <strong>${escapeHtml(run.run_id)}</strong>
              <div class="muted">${escapeHtml(run.dataset_ref || "n/a")} / ${escapeHtml(run.status)}</div>
            </button>`,
        )
        .join("")
    : betaRenderEmpty("No Studio runs yet.");
  getEl("known-datasets").innerHTML = `
    <div class="stack-item">
      <strong>${candidatePoolSummary.total_row_count || 0}</strong>
      <div class="muted">rows across promoted pools in the current beta lane</div>
    </div>
    ${
      selectedDataset
        ? `<div class="stack-item">
            <strong>${escapeHtml(selectedDataset.label)}</strong>
            <div class="muted">${escapeHtml(selectedDataset.dataset_ref)} | ${selectedDataset.row_count} rows</div>
            <div class="muted">split: ${escapeHtml(selectedDataset.split_strategy || "n/a")} | maturity: ${escapeHtml(selectedDataset.maturity || "n/a")}</div>
          </div>`
        : `<div class="stack-item muted">Choose a primary dataset to inspect its build details here.</div>`
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
      <div class="muted">${activationLedger.length} tracked feature gates | ${canonicalKnownDatasets.length} canonical runnable dataset manifests | ${stage2ScientificTracks.length} Stage 2 prototype tracks</div>
    </div>
  `;
  if (getEl("capability-matrix-summary")) {
    getEl("capability-matrix-summary").innerHTML = `
      <div class="stack-item"><strong>${activationLedger.length}</strong><div class="muted">feature gates tracked in the current activation ledger</div></div>
      <div class="stack-item"><strong>${(modelActivationMatrix.entries || []).length}</strong><div class="muted">model x graph x feature x split combinations in the activation matrix</div></div>
      <div class="stack-item"><strong>${activationLedger.filter((item) => isActiveStatus(item.current_state)).length}</strong><div class="muted">features already promoted into the broadened beta lane</div></div>
    `;
  }
  if (getEl("pool-promotion-summary")) {
    getEl("pool-promotion-summary").innerHTML = promotionReports.length
      ? promotionReports
          .slice(0, 6)
          .map(
            (report) => `
              <div class="stack-item">
                <strong>${escapeHtml(report.pool_id)}</strong>
                <div class="muted">${escapeHtml(betaReadableState(report.status))} | ${escapeHtml(betaReadableState(report.promotion_readiness || "hold"))}</div>
                <div class="muted">${escapeHtml(report.launchability_reason || report.blockers?.[0] || "No launchability note recorded.")}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No pool promotion reports are available yet.");
  }
  if (getEl("candidate-database-summary")) {
    const queuedGovernedSubsetCount = governedSubsetManifests.filter((item) => item.status !== "launchable_now").length;
    getEl("candidate-database-summary").innerHTML = `
      <div class="stack-item"><strong>${candidateDatabaseSummary.total_governed_rows || 0}</strong><div class="muted">staged database rows compiled into the governed source graph for future promotion review</div></div>
      <div class="stack-item"><strong>${candidateDatabaseSummary.governing_ready_rows || 0}</strong><div class="muted">rows that are already marked governing-ready, rather than candidate-only or support-only</div></div>
      <div class="stack-item"><strong>${Object.keys(candidateDatabaseSummary.source_family_mix || {}).length}</strong><div class="muted">staged source families currently represented in the expanded candidate database</div></div>
      <div class="stack-item"><strong>${queuedGovernedSubsetCount}</strong><div class="muted">governed subsets currently sitting in the formal promotion queue under review</div></div>
      <div class="stack-item"><strong>${candidateDatabaseSummaryV3.promoted_subset_count || 0}</strong><div class="muted">governed subsets currently promoted into the launchable PPI beta lane</div></div>
      <div class="stack-item"><strong>${candidateDatabaseSummaryV3.promotion_backlog_count || promotionQueue.length || 0}</strong><div class="muted">items still waiting in the canonical promotion backlog before broader beta exposure</div></div>
      ${
        ((candidateDatabaseSummaryV3.bias_hotspots || []).length || (candidateDatabaseSummaryV2.bias_diagnostics || []).length || (candidateDatabaseSummary.bias_diagnostics || []).length)
          ? `<div class="stack-item warning">${escapeHtml((candidateDatabaseSummaryV3.bias_hotspots || [])[0] || (candidateDatabaseSummaryV2.bias_diagnostics || [])[0] || (candidateDatabaseSummary.bias_diagnostics || [])[0])}</div>`
          : ""
      }
    `;
  }
  if (getEl("beta-launch-readiness-summary")) {
    const gates = betaReadiness.gates || [];
    getEl("beta-launch-readiness-summary").innerHTML = `
      <div class="stack-item"><strong>${escapeHtml(summary.status || "unknown")}</strong><div class="muted">current controlled external beta program state</div></div>
      <div class="stack-item"><strong>${escapeHtml(String(betaReadiness.completion_percent ?? "0"))}%</strong><div class="muted">machine-scored readiness progress across the current beta gates</div></div>
      <div class="stack-item"><strong>${escapeHtml(betaReadableState(betaReadiness.current_focus || "unknown"))}</strong><div class="muted">current focus for the continuous wave train</div></div>
      <div class="stack-item"><strong>${(uiContract.launchable_dataset_pools || []).length}</strong><div class="muted">dataset pools currently marked Launchable now by the backend</div></div>
      <div class="stack-item"><strong>${(betaSupport.known_limitations || []).length}</strong><div class="muted">known limitations currently called out to invited beta users</div></div>
      <div class="stack-item"><strong>${(betaSupport.blocked_prototype_lanes || []).length}</strong><div class="muted">blocked prototype scientific lanes still visible for review only</div></div>
      ${
        gates.length
          ? `<div class="stack-item ${gates.some((item) => item.status !== "ready") ? "warning" : ""}">${escapeHtml(
              gates.find((item) => item.status !== "ready")?.detail || "All readiness gates are currently green.",
            )}</div>`
          : ""
      }
    `;
  }
  if (getEl("beta-doc-ops-summary")) {
    getEl("beta-doc-ops-summary").innerHTML = `
      <div class="stack-item"><strong>${(betaSupport.beta_docs || []).length}</strong><div class="muted">repo-tracked beta program docs and runbooks currently registered in the support pack</div></div>
      <div class="stack-item"><strong>${escapeHtml((betaSupport.issue_intake_categories || []).join(", ") || "n/a")}</strong><div class="muted">issue intake taxonomy for support and review routing</div></div>
      <div class="stack-item"><strong>${escapeHtml(betaSupport.support_response_expectation || "n/a")}</strong></div>
    `;
  }
  if (getEl("beta-program-lanes-summary")) {
    getEl("beta-program-lanes-summary").innerHTML = (betaReadiness.program_lanes || []).length
      ? (betaReadiness.program_lanes || [])
          .map(
            (lane) => `
              <div class="stack-item">
                <strong>${escapeHtml(lane.label || lane.lane_id)}</strong>
                <div class="muted">${escapeHtml(betaReadableState(lane.state || "unknown"))}</div>
                <div class="muted">${escapeHtml(lane.summary || "No lane summary recorded.")}</div>
                ${
                  (lane.launchable_pool_ids || []).length
                    ? `<div class="muted">launchable pools: ${escapeHtml(lane.launchable_pool_ids.join(", "))}</div>`
                    : ""
                }
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No beta program lane status is available yet.");
  }
  if (getEl("beta-evidence-summary")) {
    getEl("beta-evidence-summary").innerHTML = (betaReadiness.evidence_checklist || []).length
      ? (betaReadiness.evidence_checklist || [])
          .map(
            (artifact) => `
              <div class="stack-item ${artifact.status !== "ready" ? "warning" : ""}">
                <strong>${escapeHtml(artifact.label || artifact.artifact_id)}</strong>
                <div class="muted">${escapeHtml(betaReadableState(artifact.status || "unknown"))}</div>
                <div class="muted">${escapeHtml(artifact.detail || "No evidence note recorded.")}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No beta evidence checklist is available yet.");
  }
  if (getEl("beta-agent-status-summary")) {
    getEl("beta-agent-status-summary").innerHTML = `
      <div class="stack-item ${betaTestAgentStatus.status !== "ready" ? "warning" : ""}">
        <strong>${escapeHtml(betaReadableState(betaTestAgentStatus.status || "unknown"))}</strong>
      <div class="muted">required viewport ${escapeHtml(`${betaTestAgentStatus.required_viewport?.width || 1920}x${betaTestAgentStatus.required_viewport?.height || 1080}`)}</div>
      </div>
      <div class="stack-item">
        <strong>${betaTestAgentStatus.current_sweep_complete ? "Complete" : "Needs follow-up"}</strong>
        <div class="muted">${escapeHtml((betaTestAgentStatus.missing_flows || []).join(", ") || "all required flows covered")}</div>
      </div>
      <div class="stack-item">
        <strong>${escapeHtml(betaTestAgentStatus.runner_environment?.live_capture_ready ? "live browser ready" : "live browser setup incomplete")}</strong>
        <div class="muted">${escapeHtml(betaTestAgentStatus.runner_environment?.install_note || "No browser-agent runtime note recorded.")}</div>
      </div>
      <div class="stack-item">
        <strong>${escapeHtml(String(betaTestAgentStatus.open_p1_findings || 0))}</strong>
        <div class="muted">open P1 findings</div>
      </div>
    `;
  }
  if (getEl("beta-agent-definitions")) {
    getEl("beta-agent-definitions").innerHTML = betaTestAgents.length
      ? betaTestAgents
          .map(
            (agent) => `
              <div class="stack-item">
                <strong>${escapeHtml(agent.title || agent.agent_id)}</strong>
                <div class="muted">${escapeHtml(agent.goal || "No goal recorded.")}</div>
                <div class="muted">routing: ${escapeHtml((agent.issue_routing || []).join(", ") || "n/a")}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No beta-agent definitions are available yet.");
  }
  if (getEl("beta-agent-matrix-summary")) {
    getEl("beta-agent-matrix-summary").innerHTML = (betaTestAgentMatrix.coverage || []).length
      ? (betaTestAgentMatrix.coverage || [])
          .map(
            (flow) => `
              <div class="stack-item ${flow.status !== "ready" ? "warning" : ""}">
                <strong>${escapeHtml(flow.label || flow.flow_id)}</strong>
                <div class="muted">${escapeHtml(betaReadableState(flow.status || "unknown"))}</div>
                <div class="muted">${escapeHtml(flow.coverage_note || "No coverage note recorded.")}</div>
                <div class="muted">agents: ${escapeHtml((flow.agent_results || []).map((item) => `${item.agent_id}:${item.status}`).join(", ") || "none")}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No beta-agent coverage matrix is available yet.");
  }
  if (getEl("beta-agent-findings-summary")) {
    getEl("beta-agent-findings-summary").innerHTML = (betaTestAgentFindings.open_findings || []).length
      ? (betaTestAgentFindings.open_findings || [])
          .map(
            (finding) => `
              <div class="stack-item ${finding.severity === "P1" ? "blocker" : finding.severity === "P2" ? "warning" : ""}">
                <strong>${escapeHtml(`${finding.severity} - ${finding.agent_id}`)}</strong>
                <div class="muted">${escapeHtml(finding.flow_id || "unknown flow")}</div>
                <div>${escapeHtml(finding.summary || "No finding summary recorded.")}</div>
                <div class="muted">owner: ${escapeHtml(finding.owner_lane || "n/a")}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No beta-agent findings are open.");
  }
  if (getEl("reference-library-status")) {
    getEl("reference-library-status").innerHTML = `
      <div class="stack-item">
        <strong>${escapeHtml(referenceLibraryStatus.build_state || "unknown")}</strong>
        <div class="muted">${escapeHtml(referenceLibraryStatus.bundle_kind || "bundle kind unavailable")}</div>
      </div>
      <div class="stack-item">
        <strong>${escapeHtml(String(referenceLibraryStatus.bundle_size_bytes || 0))}</strong>
        <div class="muted">bundle size bytes</div>
      </div>
      ${(referenceLibraryStatus.source_coverage_summary || [])
        .map((item) => `<div class="stack-item"><div class="muted">${escapeHtml(item)}</div></div>`)
        .join("")}
    `;
  }
  if (getEl("reference-library-install-status")) {
    getEl("reference-library-install-status").innerHTML = `
      <div class="stack-item">
        <strong>${referenceLibraryInstall.core_bundle_local ? "core bundle local" : "core bundle missing"}</strong>
        <div class="muted">${escapeHtml(referenceLibraryInstall.core_bundle_filename || "n/a")}</div>
      </div>
      <div class="stack-item">
        <strong>${escapeHtml(String(referenceLibraryInstall.chunk_count || 0))}</strong>
        <div class="muted">logical chunk count</div>
      </div>
      <div class="stack-item">
        <strong>${escapeHtml(referenceLibraryInstall.suite_decoder_ready ? "suite decoder ready" : "suite decoder missing")}</strong>
        <div class="muted">${escapeHtml(referenceLibraryInstall.hydration_note || "No hydration note recorded.")}</div>
      </div>
    `;
  }
  if (getEl("reference-library-chunks")) {
    getEl("reference-library-chunks").innerHTML = referenceLibraryChunkCatalog.length
      ? referenceLibraryChunkCatalog
          .map(
            (chunk) => `
              <div class="stack-item">
                <strong>${escapeHtml(chunk.label || chunk.chunk_id)}</strong>
                <div class="muted">${escapeHtml(chunk.storage_kind || "unknown storage")}</div>
                <div class="muted">families: ${escapeHtml((chunk.families || []).join(", ") || "none")}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No reference-library chunk catalog is available yet.");
  }
  if (getEl("reference-library-gaps")) {
    getEl("reference-library-gaps").innerHTML = `
      <div class="stack-item">
        <strong>Missing families</strong>
        <div class="muted">${escapeHtml((referenceLibraryGaps.missing_families || []).join(", ") || "none")}</div>
      </div>
      <div class="stack-item">
        <strong>Conditional families</strong>
        <div class="muted">${escapeHtml((referenceLibraryGaps.conditional_families || []).join(", ") || "none")}</div>
      </div>
      <div class="stack-item">
        <strong>Large external dependencies</strong>
        <div class="muted">${escapeHtml((referenceLibraryGaps.known_large_external_dependencies_not_yet_compacted || []).join(", ") || "none")}</div>
      </div>
    `;
  }
  if (getEl("governed-bridge-summary")) {
    getEl("governed-bridge-summary").innerHTML = governedBridgeManifests.length
        ? governedBridgeManifests
          .map(
            (manifest) => `
              <div class="stack-item">
                <strong>${escapeHtml(manifest.bridge_id)}</strong>
                <div class="muted">${manifest.row_count || 0} staged rows | ${escapeHtml(betaReadableState(manifest.promotion_readiness || "hold"))}</div>
                <div class="muted">${escapeHtml(manifest.launchability_reason || "No launchability note recorded.")}</div>
                <div class="muted">${escapeHtml(
                  (manifest.governing_ready_count || 0) > 0
                    ? "Review pending; not launchable now until promotion review closes."
                    : "Inactive; not launchable now until governing-ready coverage exists."
                )}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No governed bridge manifests are available yet.");
  }
  if (getEl("governed-subset-summary")) {
    getEl("governed-subset-summary").innerHTML = governedSubsetManifests.length
      ? governedSubsetManifests
          .map(
            (subset) => `
              <div class="stack-item">
                <strong>${escapeHtml(subset.label || subset.subset_id)}</strong>
                <div class="muted">${subset.row_count || 0} rows | ${escapeHtml(betaReadableState(subset.status || subset.promotion_readiness || "hold"))} | review: ${escapeHtml(betaReadableState(subset.review_signoff_state || "pending"))}</div>
                <div class="muted">${escapeHtml(subset.launchability_reason || "No launchability note recorded.")}</div>
              </div>`,
          )
          .join("")
      : betaRenderEmpty("No governed subsets are in the promotion program yet.");
  }
  if (getEl("promotion-queue-summary")) {
    getEl("promotion-queue-summary").innerHTML = promotionQueue.length
      ? promotionQueue
          .slice(0, 6)
          .map(
            (item) => `
              <div class="stack-item">
                <strong>${escapeHtml(item.label || item.queue_id)}</strong>
                <div class="muted">${escapeHtml(betaReadableState(item.kind || "queue"))} | ${escapeHtml(betaReadableState(item.promotion_readiness || "hold"))} | review: ${escapeHtml(betaReadableState(item.review_signoff_state || "pending"))}</div>
                <div class="muted">${escapeHtml(item.launchability_reason || item.blockers?.[0] || "No launchability note recorded.")}</div>
                ${
                  (item.required_reviewers || []).length
                    ? `<div class="muted">reviewers: ${escapeHtml(item.required_reviewers.join(", "))}</div>`
                    : ""
                }
              </div>`,
          )
          .join("")
      : betaRenderEmpty("The promotion queue is empty.");
  }
  if (getEl("activation-matrix-detail")) {
    const entries = modelActivationMatrix.entries || [];
    const currentDraft = state.currentDraft || {};
    const currentGraph = currentDraft.graph_recipes?.[0]?.graph_kind || "unknown";
    const currentModel = currentDraft.training_plan?.model_family || "unknown";
    const currentSplit = currentDraft.data_strategy?.split_strategy || "unknown";
    getEl("activation-matrix-detail").innerHTML = entries.length
      ? [
          `<div class="stack-item"><strong>Current study fit</strong><div class="muted">${escapeHtml(betaReadableState(currentModel))} with ${escapeHtml(betaReadableState(currentGraph))} on ${escapeHtml(betaReadableState(currentSplit))}</div></div>`,
          ...entries
          .slice(0, 8)
          .map(
            (entry) => `
              <div class="stack-item">
                <strong>${escapeHtml(entry.model_family)}</strong>
                <div class="muted">${escapeHtml(betaReadableState(entry.graph_kind))} | ${escapeHtml(betaReadableState(entry.feature_bundle))} | ${escapeHtml(betaReadableState(entry.status))}</div>
                <div class="muted">splits: ${escapeHtml((entry.supported_splits || []).join(", ") || "n/a")} | hardware: ${escapeHtml((entry.supported_hardware || []).join(", ") || "n/a")}</div>
                <div class="muted">resolved backend family: ${escapeHtml(entry.resolved_backend_family || "n/a")}</div>
                ${
                  (entry.dataset_scope_constraints?.governed_ppi_blended_subset_v2 || entry.dataset_scope_constraints?.governed_ppi_blended_subset_v1)
                    ? `<div class="muted">governed subset scope: ${escapeHtml(
                        (
                          entry.dataset_scope_constraints.governed_ppi_blended_subset_v2 ||
                          entry.dataset_scope_constraints.governed_ppi_blended_subset_v1
                        ).reason ||
                          "No governed-subset scope note recorded.",
                      )}</div>`
                    : ""
                }
                ${
                  entry.graph_kind === "atom_graph"
                    ? `<div class="muted">Atom-native beta: native atom parsing is active, but keep current limits visible in analysis and compare views.</div>`
                    : ""
                }
              </div>`,
          )
          ,
          ...stage2ScientificTracks.slice(0, 2).map(
            (track) => `
              <div class="stack-item">
                <strong>${escapeHtml(track.track_label || track.track_id)}</strong>
                <div class="muted">${escapeHtml(betaReadableState(track.status || "review_pending"))} | artifact: ${escapeHtml(track.artifact_path || "n/a")}</div>
                <div class="muted">${escapeHtml((track.blockers || [])[0] || "Prototype track is still review-pending.")}</div>
              </div>`,
          )
        ].join("")
      : betaRenderEmpty("No activation-matrix rows are available yet.");
  }
  if (getEl("inactive-explanation") && featureGateViews.length) {
    const highlightedGate =
      featureGateViews.find((item) => item.status === "beta_soon" || item.status === "inactive" || item.status === "planned_inactive") ||
      featureGateViews[0];
    if (highlightedGate && !getEl("inactive-explanation").innerHTML.trim()) {
      getEl("inactive-explanation").innerHTML = `
        <div class="stack-item">
          <strong>${escapeHtml(highlightedGate.feature_id)}</strong>
          <div class="muted">${escapeHtml(highlightedGate.launchability_reason || "Blocked until additional implementation and review evidence land.")}</div>
          ${
            highlightedGate.prototype_artifact
              ? `<div class="muted">prototype artifact: ${escapeHtml(highlightedGate.prototype_artifact)}</div>`
              : ""
          }
        </div>
      `;
    }
  }
  const steps = computeStepStatuses();
  getEl("completion-summary").innerHTML = steps
    .map(
      (step, index) => `
        <div class="stack-item">
          <strong>Step ${index + 1}: ${escapeHtml(step.label)}</strong>
          <div class="muted">${escapeHtml(step.status)}</div>
        </div>`,
    )
    .join("");
  const current = steps.find((step) => step.status === "current" || step.status === "next" || step.status === "blocked") || steps[0];
  getEl("recommended-next-action").innerHTML = `
    <div class="stack-item">
      <strong>${escapeHtml(current?.label || "Next step")}</strong>
      <div class="muted">${escapeHtml(current?.next_action || "Continue through the guided flow.")}</div>
    </div>
  `;
};

renderPreviewTable = function renderPreviewTable(rows, columns, tableKey) {
  if (!rows.length) return `<div class="muted">No rows to show yet.</div>`;
  const currentState = state.tableState[tableKey] || { query: "", page: 1, pageSize: 25 };
  const filtered = filteredRows(rows, currentState.query);
  const pageSize = currentState.pageSize === -1 ? filtered.length || rows.length : currentState.pageSize;
  const totalPages = Math.max(1, Math.ceil(filtered.length / Math.max(1, pageSize)));
  const currentPage = Math.min(currentState.page, totalPages);
  const pageRows =
    currentState.pageSize === -1
      ? filtered
      : filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);
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
      <input class="table-filter-input" data-table-filter="${tableKey}" type="search" placeholder="Filter rows" value="${escapeHtml(currentState.query)}" />
      <div class="table-toolbar-summary">Showing ${pageRows.length} of ${filtered.length} matching rows (${rows.length} total)</div>
      <div class="table-toolbar-actions">
        <label class="table-page-size-label">
          <span>Rows</span>
          <select data-table-page-size="${tableKey}">
            ${[
              [25, "25"],
              [50, "50"],
              [100, "100"],
              [-1, "All"],
            ]
              .map(
                ([value, label]) =>
                  `<option value="${value}" ${Number(currentState.pageSize) === Number(value) ? "selected" : ""}>${label}</option>`,
              )
              .join("")}
          </select>
        </label>
        <button type="button" class="secondary compact-button" data-table-page="${tableKey}" data-table-direction="-1">Prev</button>
        <span class="muted">Page ${currentPage} / ${totalPages}</span>
        <button type="button" class="secondary compact-button" data-table-page="${tableKey}" data-table-direction="1">Next</button>
      </div>
    </div>
    <table class="data-table">
      <thead><tr>${columns.map((column) => `<th>${labels[column] || betaTitleCase(column)}</th>`).join("")}</tr></thead>
      <tbody>
        ${pageRows
          .map(
            (row) => `
              <tr>
                ${columns
                  .map((column) => `<td>${escapeHtml(row[column] ?? "")}</td>`)
                  .join("")}
              </tr>`,
          )
          .join("")}
      </tbody>
    </table>
  `;
};

renderDataStrategyForm = function renderDataStrategyForm() {
  const capabilities = capabilityRegistry();
  const options = uiOptionRegistry();
  const strategy = state.currentDraft.data_strategy;
  const request = state.currentDraft.training_set_request;
  const datasetOptions = betaDatasetOptions();
  renderSelect("task-type-select", capabilities.task_types || [], strategy.task_type);
  renderSelect("label-type-select", capabilities.label_types || [], strategy.label_type);
  renderSelect("split-strategy-select", capabilities.split_strategies || [], strategy.split_strategy);
  renderSelect("structure-policy-select", capabilities.structure_source_policies || [], strategy.structure_source_policy);
  renderSelect("dataset-primary-select", datasetOptions, (strategy.dataset_refs || [])[0] || optionValue(datasetOptions[0] || ""));
  renderSelect("acceptable-fidelity-select", options.acceptable_fidelity_levels || [], request.acceptable_fidelity);
  renderMultiSelect("source-families-select", options.source_families || [], request.source_families || [], 6);
  renderMultiSelect("dataset-refs-select", datasetOptions, strategy.dataset_refs || [], 6);

  getEl("study-title-input").value = state.currentDraft.study_title || "";
  getEl("target-size-input").value = request.target_size || "";
  getEl("max-resolution-input").value = request.inclusion_filters?.max_resolution ?? "";
  getEl("min-release-year-input").value = request.inclusion_filters?.min_release_year ?? "";
  getEl("exclude-pdb-ids-input").value = toCsvString(request.exclusion_filters?.exclude_pdb_ids);

  const auditOptions = [
    { value: "sequence_leakage", label: "Sequence leakage", status: "release", reason: "Required audit." },
    { value: "partner_overlap", label: "Partner overlap", status: "release", reason: "Required audit." },
    { value: "state_reuse", label: "State reuse", status: "release", reason: "Required audit." },
    { value: "free_state_drift", label: "Free-state drift", status: "lab", reason: "Visible for planning, but not active in beta." },
  ];
  renderChipControl("audit-requirements", auditOptions, strategy.audit_requirements || []);

  const preview = state.workspace.training_set_preview || {};
  const build = state.workspace.latest_training_set_build || null;
  const sizing = betaTrainingSetSizingSummary();
  const diagnostics = preview.diagnostics || {};
  const buildDiagnostics = build?.diagnostics || {};
  const poolSummary = betaUiContract().candidate_pool_summary || {};
  const candidateDatabaseSummary =
    betaUiContract().candidate_database_summary_canonical ||
    betaUiContract().candidate_database_summary_v3 ||
    betaUiContract().candidate_database_summary ||
    {};
  const candidateDatabaseSummaryV2 = betaUiContract().candidate_database_summary_v2 || {};
  const candidateDatabaseSummaryV3 = betaUiContract().candidate_database_summary_v3 || {};
  const governedBridgeManifests = betaUiContract().governed_bridge_manifests || [];
  const governedSubsetManifests = betaUiContract().governed_subset_manifests_v2 || betaUiContract().governed_subset_manifests || [];
  const poolReports = betaUiContract().pool_promotion_reports || [];
  const promotionQueue =
    betaUiContract().promotion_queue_canonical ||
    betaUiContract().promotion_queue_v2 ||
    betaUiContract().promotion_queue ||
    [];
  const poolViews = betaUiContract().dataset_pool_views || [];
  const promotedPools = (betaUiContract().pool_promotion_reports || [])
    .filter((item) => ["release", "beta"].includes(item.status))
    .map((item) => item.pool_id.replace("pool:", ""));
  const primaryDatasetRef = (strategy.dataset_refs || [])[0] || optionValue(datasetOptions[0] || "");
  const selectedPrimaryPool = poolViews.find((pool) =>
    (pool.dataset_refs || []).includes(primaryDatasetRef),
  );
  const selectedPrimaryReport = poolReports.find(
    (item) => item.pool_id === selectedPrimaryPool?.pool_id,
  );
  if (state.fieldFeedback["dataset-primary-select"]?.tone !== "warning") {
    if (selectedPrimaryReport?.status === "beta") {
      setFieldFeedback(
        "dataset-primary-select",
        "neutral",
        `${primaryDatasetRef} is a beta study source`,
        (
          selectedPrimaryReport.blockers?.[0] ||
          `Promotion bar: ${selectedPrimaryReport.promotion_bar || "beta_matrix_plus_review"}`
        ),
      );
      if (selectedPrimaryPool?.truth_boundary?.whole_complex_only_for_staged_rows) {
        setFieldFeedback(
          "dataset-primary-select",
          "warning",
          `${primaryDatasetRef} is under promotion review with graph-scope limits`,
          "Staged rows in this governed subset are currently whole-complex only. Keep graph kind on whole_complex_graph and partner awareness on symmetric until native partner-role resolution lands.",
        );
      }
    } else if (selectedPrimaryReport?.status === "beta_soon") {
      setFieldFeedback(
        "dataset-primary-select",
        "warning",
        `${primaryDatasetRef} is review pending`,
        selectedPrimaryReport.launchability_reason ||
          selectedPrimaryReport.blockers?.[0] ||
          "This dataset remains visible for audit and promotion review, but it is not launchable now.",
      );
    } else {
      clearFieldFeedback("dataset-primary-select");
    }
  }
  if ((request.source_families || []).length) {
    const sourceFamilyImpact = betaSourceFamilyImpactSummary(request.source_families || [], poolViews);
    setFieldFeedback(
      "source-families-select",
      "neutral",
      "Source families broaden the candidate universe",
      sourceFamilyImpact.launchableCount || sourceFamilyImpact.reviewOnlyCount
        ? `${sourceFamilyImpact.launchableCount} launchable pool(s) and ${sourceFamilyImpact.reviewOnlyCount} review-only pool(s) match the current family mix.`
        : "Use this control to widen the staged candidate pool; the selected families affect balance, overlap, and which staged sources are considered before the primary dataset is built.",
    );
  } else {
    clearFieldFeedback("source-families-select");
  }
  if ((strategy.dataset_refs || []).length > 1) {
    const secondaryPoolStates = (strategy.dataset_refs || [])
      .slice(1)
      .map((ref) => betaUiContract().dataset_pool_views?.find((pool) => (pool.dataset_refs || []).includes(ref)))
      .filter(Boolean);
    setFieldFeedback(
      "dataset-refs-select",
      "neutral",
      "Multiple dataset refs are active in this request",
      secondaryPoolStates.length
        ? `Additional refs currently add ${secondaryPoolStates.filter((pool) => pool.is_launchable).length} launchable source(s) and ${secondaryPoolStates.filter((pool) => !pool.is_launchable).length} review-only source(s).`
        : "Additional dataset refs expand the candidate universe beyond the primary runnable benchmark. Keep an eye on the selected-pool diagnostics and the promoted-pool summary when mixing sources.",
    );
  } else {
    clearFieldFeedback("dataset-refs-select");
  }
  const selectedBridgeManifest = governedBridgeManifests.find((item) =>
    (selectedPrimaryPool?.pool_id || "").endsWith(item.bridge_id.replace("bridge:", "")),
  );
  const selectedSubsetManifest = governedSubsetManifests.find(
    (item) => item.promoted_dataset_ref === primaryDatasetRef,
  );
  const selectedPoolUseNow =
    selectedPrimaryReport?.status === "release" ||
    (selectedPrimaryReport?.status === "beta" && !(selectedPrimaryReport?.blockers || []).length);
  refreshInteractiveDraftFeedback();
  getEl("training-set-preview").innerHTML = betaRenderKeyValueList([
    ["Total candidates", sizing.total_candidate_count || 0],
    ["Filtered candidates", sizing.filtered_candidate_count || 0],
    ["Eligible ceiling", sizing.eligible_quality_ceiling || 0],
    ["Requested target", sizing.requested_target_size || "Auto ceiling"],
    ["Resolved cap", sizing.resolved_target_cap || 0],
    ["Final selected count", sizing.final_selected_count || 0],
    ["Leakage risk", diagnostics.leakage_risk || "n/a"],
    ["Structure coverage", diagnostics.structure_coverage != null ? `${safeNumber(diagnostics.structure_coverage * 100, 1)}%` : "n/a"],
    ["Maturity", diagnostics.maturity || preview.candidate_preview?.maturity || "preview"],
    ["Missing structures", diagnostics.missing_structure_count ?? 0],
    ["Promoted pools", promotedPools.join(", ") || "n/a"],
    ["Promoted row universe", poolSummary.total_row_count || 0],
    ["Governed staged rows", candidateDatabaseSummary.total_governed_rows || 0],
  ]);
  getEl("selected-pool-diagnostics").innerHTML = selectedPrimaryPool
    ? `
      <div class="stack-item">
        <strong>${escapeHtml(selectedPrimaryPool.label)}</strong>
        <div class="muted">${escapeHtml(selectedPrimaryPool.pool_id || "dataset pool")} | ${escapeHtml(selectedPrimaryPool.audience_label || betaReadableState(selectedPrimaryPool.audience_state || selectedPrimaryReport?.status || selectedPrimaryPool.status || "unknown"))}</div>
      </div>
      <div class="stack-item">
        <strong>Launchability</strong>
        <div class="muted">${escapeHtml(selectedPrimaryPool.launchability_reason || selectedPrimaryReport?.launchability_reason || "No launchability note recorded.")}</div>
      </div>
      <div class="stack-item">
        <strong>Use now?</strong>
        <div class="muted">${escapeHtml(
          selectedPoolUseNow
            ? "Yes. This pool is in the current launchable beta lane."
            : "Not yet. This pool is still informative or under promotion review rather than launchable."
        )}</div>
      </div>
      <div class="stack-item">
        <strong>Promotion readiness</strong>
        <div class="muted">${escapeHtml(betaReadableState(selectedPrimaryReport?.promotion_readiness || selectedSubsetManifest?.promotion_readiness || selectedBridgeManifest?.promotion_readiness || "hold"))}</div>
      </div>
      ${
        selectedPrimaryPool.required_reviewers?.length
          ? `<div class="stack-item">
              <strong>Required reviewers</strong>
              <div class="muted">${escapeHtml(selectedPrimaryPool.required_reviewers.join(", "))}</div>
            </div>`
          : ""
      }
      ${
        selectedPrimaryPool.required_matrix_tests?.length
          ? `<div class="stack-item">
              <strong>Required matrix tests</strong>
              <div class="muted">${escapeHtml(selectedPrimaryPool.required_matrix_tests.join(", "))}</div>
            </div>`
          : ""
      }
      <div class="stack-item">
        <strong>Balance notes</strong>
        <div class="muted">${escapeHtml((selectedSubsetManifest?.notes || [])[0] || (poolSummary.bias_hotspots || [])[0] || (candidateDatabaseSummaryV3.bias_hotspots || [])[0] || candidateDatabaseSummaryV2.bias_diagnostics?.[0] || candidateDatabaseSummary.bias_diagnostics?.[0] || "No dominant balance hotspot is currently recorded.")}</div>
      </div>
      <div class="stack-item">
        <strong>Overlap / admissibility</strong>
        <div class="muted">${escapeHtml(
          selectedSubsetManifest
            ? `review=${betaReadableState(selectedSubsetManifest.review_signoff_state || "pending")}; source mix=${Object.entries(selectedSubsetManifest.source_family_mix || {})
                .map(([key, value]) => `${key}=${value}`)
                .join(", ")}; assay mix=${Object.entries(selectedSubsetManifest.assay_family_mix || {})
                .map(([key, value]) => `${key}=${value}`)
                .join(", ")}`
            : selectedBridgeManifest
            ? `governing-ready rows=${selectedBridgeManifest.governing_ready_count || 0}; staged row states=${Object.entries(selectedBridgeManifest.readiness_counts || {})
                .map(([key, value]) => `${key}=${value}`)
                .join(", ")}`
            : (selectedPrimaryPool.truth_boundary?.governed_bridge_promotion_readiness
                ? `governed bridge readiness=${betaReadableState(selectedPrimaryPool.truth_boundary.governed_bridge_promotion_readiness)}`
                : "Pool is benchmark-backed rather than bridge-backed.")
        )}</div>
      </div>
      <div class="stack-item">
        <strong>Graph scope</strong>
        <div class="muted">${escapeHtml(
          selectedPrimaryPool?.truth_boundary?.whole_complex_only_for_staged_rows
            ? "Whole-complex only for staged rows until native partner-role resolution lands."
            : "No staged-row graph-scope override is currently recorded for this pool."
        )}</div>
      </div>
      ${
        selectedSubsetManifest?.caps_met
          ? `<div class="stack-item">
              <strong>Balance caps</strong>
              <div class="muted">${escapeHtml(
                Object.entries(selectedSubsetManifest.caps_met)
                  .map(([key, value]) => `${key}=${value ? "met" : "not met"}`)
                  .join(", "),
              )}</div>
            </div>`
          : ""
      }
      ${
        promotionQueue.length
          ? `<div class="stack-item">
              <strong>Promotion queue</strong>
              <div class="muted">${escapeHtml(
                (promotionQueue.find((item) => item.promoted_dataset_ref === primaryDatasetRef) || {}).review_signoff_state ||
                  "Not currently queued."
              )}</div>
            </div>`
          : ""
      }
    `
    : betaRenderEmpty("Choose a primary dataset to inspect its promotion, balance, and admissibility diagnostics.");
  getEl("training-set-table-summary").innerHTML = `
    <div class="stack-item"><strong>${sizing.total_candidate_count || 0} total candidates</strong><div class="muted">The source universe before filter and quality gates.</div></div>
    <div class="stack-item"><strong>${sizing.filtered_candidate_count || 0} filtered candidates</strong><div class="muted">Rows remaining after your current request filters.</div></div>
    <div class="stack-item"><strong>${sizing.eligible_quality_ceiling || 0} eligible quality-controlled rows</strong><div class="muted">The highest study size currently available after balance, redundancy, admissibility, and structure rules.</div></div>
    <div class="stack-item"><strong>${sizing.resolved_target_cap || 0} resolved target cap</strong><div class="muted">The build uses min(requested target, eligible quality ceiling).</div></div>
    <div class="stack-item"><strong>${preview.candidate_preview?.rows?.length || 0} previewed rows</strong><div class="muted">Use search, page size, and paging controls to inspect the full candidate preview.</div></div>
    ${
      (preview.candidate_preview?.dropped_rows || []).length
        ? `<div class="stack-item"><strong>${preview.candidate_preview.dropped_rows.length} dropped rows</strong><div class="muted">Dropped rows are available in the preview payload and build manifest.</div></div>`
        : ""
    }
  `;
  getEl("training-set-table").innerHTML = renderPreviewTable(
    preview.candidate_preview?.rows || [],
    ["pdb_id", "description", "label", "source_family", "structure_status", "inclusion_reason"],
    "candidate",
  );

  getEl("training-set-build-summary").innerHTML = build
    ? betaRenderKeyValueList([
        ["Dataset ref", build.dataset_ref],
        ["Total candidates", build.total_candidate_count || 0],
        ["Filtered candidates", build.filtered_candidate_count || 0],
        ["Eligible ceiling", build.eligible_quality_ceiling || 0],
        ["Requested target", build.requested_target_size || "Auto ceiling"],
        ["Resolved cap", build.resolved_target_cap || 0],
        ["Rows built", build.row_count],
        ["Maturity", build.maturity],
        ["Train / val / test", `${build.split_preview?.train_count || 0} / ${build.split_preview?.val_count || 0} / ${build.split_preview?.test_count || 0}`],
      ])
    : betaRenderEmpty("Build the study dataset to lock train / validation / test membership.");

  getEl("data-diagnostics").innerHTML = build
    ? betaRenderKeyValueList([
        ["Grouping policy", build.split_preview?.grouping_policy || "n/a"],
        ["Leakage risk", buildDiagnostics.leakage_risk || "n/a"],
        ["Structure coverage", buildDiagnostics.structure_coverage != null ? `${safeNumber(buildDiagnostics.structure_coverage * 100, 1)}%` : "n/a"],
        ["Label range", buildDiagnostics.label_min != null ? `${safeNumber(buildDiagnostics.label_min)} to ${safeNumber(buildDiagnostics.label_max)}` : "n/a"],
        ["Split source mix", Object.entries(build.split_preview?.source_mix_by_split?.train || {}).map(([key, value]) => `${key}=${value}`).join(", ") || "n/a"],
      ])
    : betaRenderEmpty("Split and build diagnostics will appear after a successful dataset build.");

  getEl("build-split-table-summary").innerHTML = build
    ? `
      <div class="stack-item"><strong>${build.final_selected_count || (build.selected_rows || []).length} selected rows</strong><div class="muted">Train, validation, and test membership is visible in the full table below.</div></div>
      <div class="stack-item"><strong>${build.resolved_target_cap || 0} resolved target cap</strong><div class="muted">${escapeHtml(build.target_size_warning || "The final selection count follows the current eligible ceiling and requested cap.")}</div></div>
      <div class="stack-item"><strong>${(build.excluded_rows || []).length} excluded rows</strong><div class="muted">Excluded rows include explicit reasons when available.</div></div>
    `
    : betaRenderEmpty("No built dataset rows yet.");
  getEl("build-split-table").innerHTML = build
    ? `
      <div class="table-group">
        <h5>Selected rows</h5>
        ${renderPreviewTable(
          build.selected_rows || [],
          [
            "pdb_id",
            "description",
            "split",
            "label",
            "source_family",
            "structure_status",
            "inclusion_reason",
          ],
          "build",
        )}
      </div>
      <div class="table-group">
        <h5>Excluded rows</h5>
        ${(build.excluded_rows || []).length
          ? `<div class="stack">${build.excluded_rows
              .map((item) => `<div class="stack-item mono">${escapeHtml(item)}</div>`)
              .join("")}</div>`
          : betaRenderEmpty("No excluded rows were recorded for this build.")}
      </div>
    `
    : betaRenderEmpty("Build a dataset to inspect selected and excluded rows.");
};

renderRepresentationForm = function renderRepresentationForm() {
  ensureDraftShape();
  const capabilities = capabilityRegistry();
  const options = uiOptionRegistry();
  const feature = state.currentDraft.feature_recipes[0];
  const graph = state.currentDraft.graph_recipes[0];
  renderSelect("graph-kind-select", capabilities.graph_kinds || [], graph.graph_kind);
  renderSelect("region-policy-select", capabilities.region_policies || [], graph.region_policy);
  renderSelect("node-granularity-select", options.node_granularities || [], graph.node_granularity || "residue");
  renderSelect("partner-awareness-select", options.partner_awareness_modes || [], graph.partner_awareness || "symmetric");
  renderSelect("encoding-policy-select", options.encoding_policies || [], graph.encoding_policy || "normalized_continuous");
  renderSelect("node-feature-policy-select", capabilities.node_feature_policies || [], feature.node_feature_policy);
  renderSelect("edge-feature-policy-select", capabilities.node_feature_policies || [], feature.edge_feature_policy);
  renderChipControl("global-features-control", options.global_feature_sets || [], feature.global_feature_sets || []);
  renderChipControl("distributed-features-control", options.distributed_feature_sets || [], feature.distributed_feature_sets || []);
  getEl("include-waters-toggle").checked = Boolean(graph.include_waters);
  getEl("include-salt-bridges-toggle").checked = Boolean(graph.include_salt_bridges);
  getEl("include-contact-shell-toggle").checked = Boolean(graph.include_contact_shell);

  const compatibility = [
    `Graph kind: ${betaSelectedOptionLabel("graph_kinds", graph.graph_kind)}`,
    `Region policy: ${betaSelectedOptionLabel("region_policies", graph.region_policy)}`,
    `Node granularity: ${betaSelectedOptionLabel("node_granularities", graph.node_granularity || "residue")}`,
    `Partner awareness: ${betaSelectedOptionLabel("partner_awareness_modes", graph.partner_awareness || "symmetric")}`,
    `Encoding policy: ${betaSelectedOptionLabel("encoding_policies", graph.encoding_policy || "normalized_continuous")}`,
    `Node feature policy currently mirrors the encoding choice: ${betaSelectedOptionLabel("node_feature_policies", feature.node_feature_policy)}`,
    `Edge feature policy is descriptive metadata in the current beta lane: ${betaSelectedOptionLabel("node_feature_policies", feature.edge_feature_policy)}`,
    graph.include_waters ? "Waters are included in the current structural summary lane." : "Waters are excluded from the current lane.",
    graph.include_contact_shell ? "Contact shell summaries are requested." : "Contact shell summaries are disabled.",
    graph.include_salt_bridges ? "Salt-bridge context is enabled." : "Salt-bridge context is disabled.",
  ];
  if (graph.partner_awareness === "role_conditioned") {
    setFieldFeedback(
      "partner-awareness-select",
      "warning",
      "Role-conditioned partner awareness is still a beta scientific lane",
      "This mode changes packaging and disclosure, but it remains under broadened beta review rather than a frozen release semantic.",
    );
    compatibility.push(
      "Role-conditioned partner awareness is a beta bound-state feature mode and changes the graph node-feature shape exposed to downstream models.",
    );
  } else {
    clearFieldFeedback("partner-awareness-select");
  }
  if (graph.graph_kind === "atom_graph" || graph.node_granularity === "atom") {
    setFieldFeedback(
      "node-granularity-select",
      "warning",
      "Atom-native beta is active",
      "This lane now uses native atom parsing and atom graph payloads, but it remains beta-scoped and should be interpreted with the resolved backend and analysis caveats in view.",
    );
    compatibility.push(
      "Atom-native beta is active: graph payloads now carry atom records, atom-level feature vectors, and denser short-range connectivity than residue graphs.",
    );
  } else if (state.fieldFeedback["node-granularity-select"]?.summary?.includes("Atom-native beta")) {
    clearFieldFeedback("node-granularity-select");
  }
  const selectedDatasetRef = (state.currentDraft.data_strategy?.dataset_refs || [])[0];
  const selectedPoolView = (betaUiContract().dataset_pool_views || []).find((pool) =>
    (pool.dataset_refs || []).includes(selectedDatasetRef),
  );
  if (selectedPoolView?.truth_boundary?.whole_complex_only_for_staged_rows) {
    const representationBlocked =
      graph.graph_kind !== "whole_complex_graph" ||
      graph.region_policy !== "whole_molecule" ||
      graph.partner_awareness !== "symmetric";
    setFieldFeedback(
      "graph-kind-select",
      representationBlocked ? "warning" : "neutral",
      representationBlocked
        ? "Selected dataset needs whole-complex graph scope"
        : "Selected dataset is in its supported graph scope",
      representationBlocked
        ? "This governed subset includes staged rows without native partner-role resolution. Use whole_complex_graph, whole_molecule, and symmetric partner awareness."
        : "The current whole-complex, symmetric configuration is compatible with staged rows in this governed subset.",
    );
  } else if (state.fieldFeedback["graph-kind-select"]?.summary?.includes("whole-complex graph scope")) {
    clearFieldFeedback("graph-kind-select");
  }
  getEl("representation-compatibility").innerHTML = compatibility.map((item) => `<div class="stack-item">${escapeHtml(item)}</div>`).join("");
  getEl("example-bundle-summary").innerHTML = [
    `Graph payload: ${betaSelectedOptionLabel("graph_kinds", graph.graph_kind)}`,
    `Partner-awareness mode: ${betaSelectedOptionLabel("partner_awareness_modes", graph.partner_awareness || "symmetric")}`,
    `Global features: ${(feature.global_feature_sets || []).join(", ") || "none"}`,
    `Distributed features: ${(feature.distributed_feature_sets || []).join(", ") || "none"}`,
    `Selected preprocess modules: ${(state.currentDraft.preprocess_plan.modules || []).slice(0, 4).join(", ") || "core structural summaries"}`,
  ]
    .map((item) => `<div class="stack-item">${escapeHtml(item)}</div>`)
    .join("");
  getEl("pipeline-diagram").innerHTML = betaRenderPipelineFlowchart();
  getEl("model-structure-diagram").innerHTML = renderModelDiagram(state.currentDraft.training_plan.model_family);
};

renderPipelineComposer = function renderPipelineComposer() {
  const capabilities = capabilityRegistry();
  const options = uiOptionRegistry();
  const plan = state.currentDraft.training_plan;
  const hardware = state.workspace.hardware_profile || {};
  renderSelect("model-family-select", capabilities.model_families || [], plan.model_family);
  renderSelect("architecture-select", architectureOptionsForModel(plan.model_family), plan.architecture);
  renderSelect("optimizer-select", options.optimizer_policies || [], plan.optimizer);
  renderSelect("scheduler-select", options.scheduler_policies || [], plan.scheduler);
  renderSelect("loss-function-select", options.loss_functions || [], plan.loss_function);
  renderSelect("batch-policy-select", options.batch_policies || [], plan.batch_policy);
  renderSelect("mixed-precision-select", options.mixed_precision_policies || [], plan.mixed_precision);
  renderSelect("uncertainty-head-select", options.uncertainty_heads || [], plan.uncertainty_head || "none");
  renderSelect("evaluation-preset-select", options.evaluation_presets || [], state.currentDraft.trainingPlanPreset || "regression_plus_calibration");
  renderSelect("hardware-runtime-select", options.hardware_runtime_presets || [], betaCurrentHardwareMode());
  renderChipControl("ablation-options-control", options.ablation_options || [], plan.ablations || []);
  getEl("epoch-budget-input").value = plan.epoch_budget || 1;
  const selectedModelOption = (capabilities.model_families || []).find(
    (item) => optionValue(item) === plan.model_family,
  );
  if (state.fieldFeedback["model-family-select"]?.tone !== "warning") {
    if (optionStatus(selectedModelOption) === "beta") {
      setFieldFeedback(
        "model-family-select",
        "neutral",
        `${optionLabel(selectedModelOption)} is a beta model family`,
        "The selected family is runnable, but it remains adapter-backed or under broadened-beta review. Keep the resolved backend card in view while interpreting results.",
      );
    } else {
      clearFieldFeedback("model-family-select");
    }
  }

  const gpuSummary = hardware.cuda_available
    ? `${hardware.gpu_name || "CUDA GPU"} / ${safeNumber(hardware.gpu_memory_gb, 1)} GB VRAM`
    : "No CUDA GPU detected";
  getEl("hardware-runtime-summary").innerHTML = `
    <div class="stack-item"><strong>${escapeHtml(hardware.cpu_model || "unknown CPU")}</strong><div class="muted">${hardware.cpu_count || "n/a"} logical cores</div></div>
    <div class="stack-item"><strong>${safeNumber(hardware.total_ram_gb, 1)} GB RAM</strong><div class="muted">${escapeHtml(gpuSummary)}</div></div>
    <div class="stack-item"><strong>${escapeHtml(betaSelectedOptionLabel("hardware_runtime_presets", hardware.recommended_preset || "auto_recommend"))}</strong><div class="muted">recommended runtime preset</div></div>
  `;
  const detectedGpuMarkup = (hardware.detected_gpus || [])
    .map(
      (gpu) => `
        <div class="stack-item">
          <strong>${escapeHtml(gpu.name || "Unknown GPU")}</strong>
          <div class="muted">${gpu.memory_gb ? `${gpu.memory_gb} GB adapter memory reported by Windows` : "Adapter memory unavailable"}</div>
        </div>`,
    )
    .join("");
  getEl("hardware-runtime-diagnostics").innerHTML = [
    detectedGpuMarkup || `<div class="stack-item muted">No additional GPU adapters were reported by the host diagnostics.</div>`,
    ...(hardware.warnings || []).map((warning) => `<div class="stack-item warning">${escapeHtml(warning)}</div>`),
  ].join("");

  const recommendationItems = [
    ...(state.workspace.recommendation_report?.items || []),
    ...(hardware.warnings || []).map((warning) => ({
      level: "warning",
      category: "hardware",
      message: warning,
    })),
  ];
  if (plan.model_family === "gat") {
    recommendationItems.unshift({
      level: "warning",
      category: "resolved_backend",
      message:
        "GAT is currently delivered as an adapter-backed beta model family over the lightweight graph backend; compare results with the disclosed resolved backend in the run monitor and analysis views.",
    });
  }
  getEl("composer-recommendations").innerHTML = recommendationItems.length
    ? recommendationItems
        .slice(0, 8)
        .map(
          (item) => `
            <div class="recommendation ${item.level}">
              <span class="pill ${item.level === "blocker" ? "blocker" : item.level === "warning" ? "warning" : "neutral"}">${escapeHtml(item.level)}</span>
              <strong>${escapeHtml(item.category || "note")}</strong>
              <p>${escapeHtml(item.message || "")}</p>
            </div>`,
        )
        .join("")
    : betaRenderEmpty("No warnings or blockers are currently attached to this configuration.");
  getEl("training-plan-summary").innerHTML = betaRenderKeyValueList([
    ["Model family", betaSelectedOptionLabel("model_families", plan.model_family)],
    ["Architecture", betaSelectedOptionLabel("architectures", plan.architecture)],
    ["Loss", betaSelectedOptionLabel("loss_functions", plan.loss_function)],
    ["Optimizer", betaSelectedOptionLabel("optimizer_policies", plan.optimizer)],
    ["Scheduler", betaSelectedOptionLabel("scheduler_policies", plan.scheduler)],
    ["Epoch budget", plan.epoch_budget || 1],
    ["Batch policy", betaSelectedOptionLabel("batch_policies", plan.batch_policy)],
    ["Mixed precision", betaSelectedOptionLabel("mixed_precision_policies", plan.mixed_precision)],
    ["Evaluation preset", betaSelectedOptionLabel("evaluation_presets", state.currentDraft.trainingPlanPreset || "regression_plus_calibration")],
    ["Hardware mode", betaSelectedOptionLabel("hardware_runtime_presets", betaCurrentHardwareMode())],
  ]);
};

renderExecutionConsole = function renderExecutionConsole() {
  const capabilities = capabilityRegistry();
  renderChipControl("preprocess-modules", capabilities.preprocessing_modules || [], state.currentDraft.preprocess_plan.modules || []);

  const graph = state.workspace.execution_graph || { stages: [] };
  const currentRunStages = state.currentRun?.stage_status || {};
  const currentRun = currentRunManifest();
  getEl("execution-graph").innerHTML = `
    <div class="timeline">
      ${graph.stages
        .map((stage) => {
          const stageStatus = currentRunStages[stage] || {};
          return `
            <div class="timeline-stage ${betaStageTone(stageStatus.status || (currentRun?.active_stage === stage ? "running" : ""))}">
              <strong>${escapeHtml(betaTitleCase(stage))}</strong>
              <div class="muted">${escapeHtml(stageStatus.detail || "Not started yet.")}</div>
              ${stageStatus.substage ? `<div class="muted">Substage: ${escapeHtml(stageStatus.substage)}</div>` : ""}
            </div>`;
        })
        .join("")}
    </div>
  `;
  getEl("run-preview").innerHTML = currentRun
    ? betaRenderKeyValueList([
        ["Run id", currentRun.run_id],
        ["Status", currentRun.status],
        ["Active stage", currentRun.active_stage || "none"],
        ["Heartbeat", betaFormatTimestamp(currentRun.heartbeat_at)],
        ["Hardware mode", betaSelectedOptionLabel("hardware_runtime_presets", currentRun.hardware_mode || betaCurrentHardwareMode())],
      ])
    : betaRenderEmpty("Launch a run to populate the live monitor.");
  getEl("run-stage-cards").innerHTML = graph.stages
    .map((stage) => {
      const stageStatus = currentRunStages[stage] || {
        status: currentRun?.active_stage === stage ? "running" : "idle",
        detail: "Waiting for this stage to start.",
        artifact_refs: [],
        blockers: [],
      };
      return `
        <article class="stage-card ${betaStageTone(stageStatus.status)}">
          <div class="stage-card-head">
            <div>
              <strong>${escapeHtml(betaTitleCase(stage))}</strong>
              <div class="muted">${escapeHtml(stageStatus.detail || "No detail available yet.")}</div>
            </div>
            <span class="pill ${betaStageTone(stageStatus.status) === "running" ? "warning" : betaStageTone(stageStatus.status) === "completed" ? "neutral" : betaStageTone(stageStatus.status) === "failed" ? "blocker" : "neutral"}">${escapeHtml(stageStatus.status || "idle")}</span>
          </div>
          ${stageStatus.substage ? `<div class="muted">Substage: ${escapeHtml(stageStatus.substage)}</div>` : ""}
          ${betaRenderProgressBar(stageStatus)}
          ${
            stageStatus.latest_artifact
              ? `<div class="stack-item"><strong>Latest artifact</strong><div class="mono">${escapeHtml(stageStatus.latest_artifact)}</div></div>`
              : ""
          }
          ${
            (stageStatus.blockers || []).length
              ? `<div class="stack-item"><strong>Blockers</strong><div class="muted">${stageStatus.blockers.map(escapeHtml).join(" | ")}</div></div>`
              : ""
          }
          ${
            stageStatus.technical_detail
              ? `<div class="stack-item"><strong>Technical detail</strong><div class="mono">${escapeHtml(stageStatus.technical_detail)}</div></div>`
              : ""
          }
          <div class="muted">Updated: ${escapeHtml(betaFormatTimestamp(stageStatus.updated_at))}</div>
        </article>`;
    })
    .join("");
  getEl("current-run-artifacts").innerHTML = state.currentRun?.artifacts
    ? Object.entries(state.currentRun.artifacts)
        .map(
          ([name, path]) => `
            <div class="stack-item">
              <strong>${escapeHtml(name)}</strong>
              <div class="mono">${escapeHtml(path)}</div>
            </div>`,
        )
        .join("")
    : betaRenderEmpty("Artifacts will appear here after a run emits them.");
  getEl("current-run-logs").innerHTML = (state.currentRun?.logs?.lines || []).length
    ? state.currentRun.logs.lines
        .slice(-12)
        .map((line) => `<div class="stack-item mono">${escapeHtml(line)}</div>`)
        .join("")
    : betaRenderEmpty("No run logs yet.");
  const latestBuild = state.workspace.latest_training_set_build;
  getEl("split-packaging-summary").innerHTML = latestBuild
    ? betaRenderKeyValueList([
        ["Dataset ref", latestBuild.dataset_ref],
        ["Train / val / test", `${latestBuild.split_preview?.train_count || 0} / ${latestBuild.split_preview?.val_count || 0} / ${latestBuild.split_preview?.test_count || 0}`],
        ["Grouping policy", latestBuild.split_preview?.grouping_policy || "n/a"],
      ])
    : betaRenderEmpty("Build a dataset first to inspect packaging details.");
  getEl("execution-dataset-diagnostics").innerHTML = latestBuild
    ? betaRenderKeyValueList([
        ["Leakage risk", latestBuild.diagnostics?.leakage_risk || "n/a"],
        ["Structure coverage", latestBuild.diagnostics?.structure_coverage != null ? `${safeNumber(latestBuild.diagnostics.structure_coverage * 100, 1)}%` : "n/a"],
        ["Label mean", latestBuild.diagnostics?.label_mean != null ? safeNumber(latestBuild.diagnostics.label_mean) : "n/a"],
        ["Missing structures", latestBuild.diagnostics?.missing_structure_count ?? 0],
      ])
    : betaRenderEmpty("Build diagnostics appear after a successful study dataset build.");
};

function betaSvgFrame(inner, width = 520, height = 240) {
  return `<svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img">${inner}</svg>`;
}

function betaScale(value, min, max, low, high) {
  if (max <= min) return (low + high) / 2;
  return low + ((value - min) / (max - min)) * (high - low);
}

function betaRenderScatterChart(points, { xKey, yKey, xLabel, yLabel, diagonal = false } = {}) {
  if (!(points || []).length) {
    return `<div class="diagram-empty">No point data available yet.</div>`;
  }
  const width = 520;
  const height = 240;
  const padLeft = 56;
  const padBottom = 34;
  const padTop = 18;
  const padRight = 18;
  const xs = points.map((point) => Number(point[xKey] || 0));
  const ys = points.map((point) => Number(point[yKey] || 0));
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys);
  const dots = points
    .map((point) => {
      const x = betaScale(Number(point[xKey] || 0), xMin, xMax, padLeft, width - padRight);
      const y = betaScale(Number(point[yKey] || 0), yMin, yMax, height - padBottom, padTop);
      return `<circle class="chart-dot" cx="${x}" cy="${y}" r="4"><title>${escapeHtml(point.pdb_id || point.example_id || "")}: ${xLabel} ${safeNumber(Number(point[xKey] || 0))}, ${yLabel} ${safeNumber(Number(point[yKey] || 0))}</title></circle>`;
    })
    .join("");
  const diagonalMarkup = diagonal
    ? `<line class="chart-guide" x1="${padLeft}" y1="${height - padBottom}" x2="${width - padRight}" y2="${padTop}" />`
    : "";
  return `
    ${betaSvgFrame(`
      <line class="chart-axis" x1="${padLeft}" y1="${height - padBottom}" x2="${width - padRight}" y2="${height - padBottom}" />
      <line class="chart-axis" x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${height - padBottom}" />
      ${diagonalMarkup}
      ${dots}
    `, width, height)}
    <div class="chart-caption">${escapeHtml(xLabel)} vs ${escapeHtml(yLabel)}</div>
  `;
}

function betaRenderBarChart(items, { labelKey, valueKey, caption } = {}) {
  if (!(items || []).length) {
    return `<div class="diagram-empty">No bar-chart data available yet.</div>`;
  }
  const width = 520;
  const height = 240;
  const padLeft = 42;
  const padBottom = 56;
  const padTop = 18;
  const barWidth = Math.max(28, Math.floor((width - padLeft - 20) / items.length) - 12);
  const maxValue = Math.max(...items.map((item) => Number(item[valueKey] || 0)), 1);
  const bars = items
    .map((item, index) => {
      const value = Number(item[valueKey] || 0);
      const x = padLeft + index * (barWidth + 12);
      const chartHeight = betaScale(value, 0, maxValue, 0, height - padBottom - padTop);
      const y = height - padBottom - chartHeight;
      const label = String(item[labelKey] ?? "");
      return `
        <rect class="chart-bar" x="${x}" y="${y}" width="${barWidth}" height="${chartHeight}"></rect>
        <text class="chart-text" x="${x + barWidth / 2}" y="${height - padBottom + 16}" text-anchor="middle">${escapeHtml(label.slice(0, 12))}</text>
        <text class="chart-text value" x="${x + barWidth / 2}" y="${Math.max(padTop + 12, y - 6)}" text-anchor="middle">${value}</text>
      `;
    })
    .join("");
  return `
    ${betaSvgFrame(`
      <line class="chart-axis" x1="${padLeft}" y1="${height - padBottom}" x2="${width - 10}" y2="${height - padBottom}" />
      ${bars}
    `, width, height)}
    <div class="chart-caption">${escapeHtml(caption || "Distribution")}</div>
  `;
}

function betaRenderLineChart(values, { caption } = {}) {
  if (!(values || []).length) {
    return `<div class="diagram-empty">No line-chart data available yet.</div>`;
  }
  const width = 520;
  const height = 240;
  const padLeft = 42;
  const padBottom = 36;
  const padTop = 18;
  const maxValue = Math.max(...values, 1);
  const minValue = Math.min(...values, 0);
  const coordinates = values.map((value, index) => {
    const x = betaScale(index, 0, Math.max(values.length - 1, 1), padLeft, width - 12);
    const y = betaScale(value, minValue, maxValue, height - padBottom, padTop);
    return `${x},${y}`;
  });
  return `
    ${betaSvgFrame(`
      <polyline class="chart-line" points="${coordinates.join(" ")}" />
      ${values
        .map((value, index) => {
          const [x, y] = coordinates[index].split(",");
          return `<circle class="chart-dot" cx="${x}" cy="${y}" r="3"><title>epoch ${index + 1}: ${safeNumber(value)}</title></circle>`;
        })
        .join("")}
      <line class="chart-axis" x1="${padLeft}" y1="${height - padBottom}" x2="${width - 10}" y2="${height - padBottom}" />
    `, width, height)}
    <div class="chart-caption">${escapeHtml(caption || "Trend")}</div>
  `;
}

function betaRenderComparisonPanel() {
  const runOptions = state.recentRuns.filter((item) => item.status === "completed");
  const optionMarkup = runOptions
    .map((run) => `<option value="${escapeHtml(run.run_id)}">${escapeHtml(run.run_id)} | ${escapeHtml(run.model_family || "model")} | ${escapeHtml(run.status)}</option>`)
    .join("");
  getEl("compare-run-a-select").innerHTML = `<option value="">Select run A</option>${optionMarkup}`;
  getEl("compare-run-b-select").innerHTML = `<option value="">Select run B</option>${optionMarkup}`;
  if (state.compareRunIds[0]) getEl("compare-run-a-select").value = state.compareRunIds[0];
  if (state.compareRunIds[1]) getEl("compare-run-b-select").value = state.compareRunIds[1];
  const comparison = state.runComparison;
  getEl("run-comparison").innerHTML = comparison?.items?.length
    ? comparison.items
        .map(
          (item) => `
            <div class="stack-item">
              <strong>${escapeHtml(item.run_id)}</strong>
              <div class="muted">${escapeHtml(item.requested_model_family || "model")} via ${escapeHtml(item.resolved_backend || "backend")}</div>
              <div class="muted">RMSE ${safeNumber(item.test_rmse)} | MAE ${safeNumber(item.test_mae)} | R^2 ${safeNumber(item.test_r2)}</div>
              <div class="muted">Dataset ${escapeHtml(item.dataset_ref || "n/a")} | outliers ${item.outlier_count || 0}</div>
            </div>`,
        )
        .join("")
    : betaRenderEmpty("Choose two completed runs to compare metrics and dataset lineage.");
}

renderRecommendations = function renderRecommendations() {
  const workspaceReport = state.workspace.recommendation_report || { items: [] };
  const runRecommendations = state.currentRun?.recommendations?.items || [];
  const combined = [...workspaceReport.items, ...runRecommendations];
  getEl("recommendations").innerHTML = combined.length
    ? combined
        .map(
          (item) => `
            <div class="recommendation ${item.level}">
              <span class="pill ${item.level === "blocker" ? "blocker" : item.level === "warning" ? "warning" : "neutral"}">${escapeHtml(item.level)}</span>
              <strong>${escapeHtml(item.category)}</strong>
              <p>${escapeHtml(item.message)}</p>
              ${item.action ? `<p class="muted">Suggested action: ${escapeHtml(item.action)}</p>` : ""}
            </div>`,
        )
        .join("")
    : betaRenderEmpty("No current recommendations or blockers.");
  getEl("review-lanes").innerHTML = (state.workspace.catalog.reviewer_lanes || [])
    .map((lane) => `<div class="stack-item">${escapeHtml(lane)}</div>`)
    .join("");

  const metrics = state.currentRun?.metrics || {};
  getEl("run-metrics").innerHTML = Object.keys(metrics).length
    ? betaRenderKeyValueList(Object.entries(metrics))
    : betaRenderEmpty("Run metrics appear here after evaluation completes.");
  getEl("run-outliers").innerHTML = (state.currentRun?.outliers?.items || []).length
    ? state.currentRun.outliers.items
        .slice(0, 10)
        .map(
          (item) => `
            <div class="stack-item">
              <strong>${escapeHtml(item.pdb_id || item.example_id || "example")}</strong>
              <div class="muted">actual ${safeNumber(item.actual)} | predicted ${safeNumber(item.predicted)} | residual ${safeNumber(item.residual)}</div>
            </div>`,
        )
        .join("")
    : betaRenderEmpty("Outliers appear after a completed run.");

  const analysis = state.currentRun?.analysis || {};
  const datasetCharts = state.workspace.latest_training_set_build?.charts || state.workspace.training_set_preview?.charts || {};
  getEl("prediction-chart").innerHTML = betaRenderScatterChart(analysis.prediction_vs_actual || [], {
    xKey: "actual",
    yKey: "predicted",
    xLabel: "Actual",
    yLabel: "Predicted",
    diagonal: true,
  });
  getEl("residual-chart").innerHTML = (analysis.residuals || []).length
    ? betaRenderScatterChart(analysis.residuals || [], {
        xKey: "predicted",
        yKey: "residual",
        xLabel: "Predicted",
        yLabel: "Residual",
      })
    : betaRenderBarChart(analysis.residual_histogram || [], {
        labelKey: "label",
        valueKey: "count",
        caption: "Residual histogram",
      });
  getEl("label-distribution-chart").innerHTML = betaRenderBarChart(
    datasetCharts.label_distribution || analysis.label_distribution_by_split?.test || [],
    { labelKey: "label", valueKey: "count", caption: "Label distribution" },
  );
  getEl("split-chart").innerHTML = betaRenderBarChart(datasetCharts.split_distribution || [], {
    labelKey: "split",
    valueKey: "count",
    caption: "Split composition",
  });
  const runtimeLearningCurve = state.currentRun?.model_details?.training_curve || [];
  getEl("learning-curve-chart").innerHTML = runtimeLearningCurve.length
    ? betaRenderLineChart(runtimeLearningCurve, { caption: "Training curve" })
    : betaRenderEmpty("Learning curves are available for iterative neural models.");
  getEl("classification-chart").innerHTML = analysis.roc_curve
    ? betaRenderLineChart(analysis.roc_curve.map((point) => point.tpr || 0), { caption: "ROC curve" })
    : `<div class="diagram-empty">${escapeHtml(analysis.roc_unavailable_reason || "Classification-only charts are unavailable for this run.")}</div>`;

  const latestBuild = state.workspace.latest_training_set_build;
  getEl("split-diagnostics").innerHTML = latestBuild
    ? betaRenderKeyValueList([
        ["Grouping policy", latestBuild.split_preview?.grouping_policy || "n/a"],
        ["Objective", latestBuild.split_preview?.objective || "n/a"],
        ["Components", latestBuild.split_preview?.component_count || 0],
        ["Leakage risk", latestBuild.diagnostics?.leakage_risk || "n/a"],
      ])
    : betaRenderEmpty("Split diagnostics appear after the dataset build step.");
  getEl("study-summary-card").innerHTML = `
    <div class="stack-item"><strong>${escapeHtml(state.currentDraft.study_title)}</strong><div class="muted">${escapeHtml(state.currentDraft.data_strategy.task_type)} / ${escapeHtml(state.currentDraft.data_strategy.label_type)}</div></div>
    <div class="stack-item"><strong>Dataset</strong><div class="muted">${escapeHtml(state.workspace.latest_training_set_build?.dataset_ref || state.workspace.selected_dataset?.dataset_ref || "not built yet")}</div></div>
    <div class="stack-item"><strong>Model</strong><div class="muted">${escapeHtml(betaSelectedOptionLabel("model_families", state.currentDraft.training_plan.model_family))}</div></div>
    <div class="stack-item"><strong>Run status</strong><div class="muted">${escapeHtml(currentRunManifest()?.status || "idle")}</div></div>
  `;
  betaRenderComparisonPanel();
};

function betaSelectedInactiveOptions(select) {
  return Array.from(select.selectedOptions || []).filter(
    (option) => !isActiveStatus(option.getAttribute("data-status") || "release"),
  );
}

function betaSelectLabel(select) {
  const label = document.querySelector(`label[for="${select.id}"]`) || select.closest("label");
  return label?.querySelector("span")?.textContent?.trim() || select.id;
}

function betaHandleSelectMutation(select) {
  const inactive = betaSelectedInactiveOptions(select);
  if (inactive.length) {
    const status = inactive[0].getAttribute("data-status") || "planned_inactive";
    const stateLabel =
      status === "beta_soon"
        ? "Review pending"
        : status === "planned_inactive" || status === "blocked"
        ? "Inactive"
        : betaReadableState(status);
    setFieldFeedback(
      select.id,
      "warning",
      `${inactive[0].getAttribute("data-label") || betaSelectLabel(select)} is ${stateLabel.toLowerCase()}`,
      inactive[0].getAttribute("data-reason") || "This option is visible for planning but not enabled in the current beta lane.",
    );
    showInactiveExplanation(
      inactive[0].getAttribute("data-label") || betaSelectLabel(select),
      inactive[0].getAttribute("data-reason") || "This option is visible for planning but not enabled in the current beta lane.",
    );
    renderAll();
    return;
  }
  clearFieldFeedback(select.id);
  state.currentDraft = collectDraftFromForm();
  setActionStatus("success", "Draft updated", `${betaSelectLabel(select)} changed.`);
  renderAll();
}

collectDraftFromForm = function collectDraftFromForm() {
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
    new Set([getEl("dataset-primary-select").value, ...fromSelectValues("dataset-refs-select")]),
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
    exclude_pdb_ids: getEl("exclude-pdb-ids-input")
      .value.split(",")
      .map((item) => item.trim().toUpperCase())
      .filter(Boolean),
  };
  draft.training_set_request.acceptable_fidelity = getEl("acceptable-fidelity-select").value;
  draft.split_plan.objective = draft.data_strategy.split_strategy;
  draft.split_plan.grouping_policy = draft.data_strategy.split_strategy;
  graph.graph_kind = getEl("graph-kind-select").value;
  graph.region_policy = getEl("region-policy-select").value;
  graph.node_granularity = getEl("node-granularity-select").value;
  graph.partner_awareness = getEl("partner-awareness-select").value;
  graph.encoding_policy = getEl("encoding-policy-select").value;
  graph.include_waters = getEl("include-waters-toggle").checked;
  graph.include_salt_bridges = getEl("include-salt-bridges-toggle").checked;
  graph.include_contact_shell = getEl("include-contact-shell-toggle").checked;
  feature.node_feature_policy = getEl("node-feature-policy-select").value;
  feature.edge_feature_policy = getEl("edge-feature-policy-select").value;
  feature.global_feature_sets = fromCheckedValues("global-features-control");
  feature.distributed_feature_sets = fromCheckedValues("distributed-features-control");
  draft.preprocess_plan.modules = fromCheckedValues("preprocess-modules");
  draft.preprocess_plan.options.hardware_runtime_preset = getEl("hardware-runtime-select").value;
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
  return draft;
};

bindDynamicButtons = function bindDynamicButtons() {
  document.querySelectorAll("[data-pipeline-id]").forEach((button) => {
    button.onclick = async () => loadWorkspace(button.getAttribute("data-pipeline-id"));
  });
  document.querySelectorAll("[data-run-id]").forEach((button) => {
    button.onclick = async () => openRun(button.getAttribute("data-run-id"));
  });
  document.querySelectorAll("[data-scroll-target]").forEach((button) => {
    button.onclick = () => {
      const targetId = button.getAttribute("data-scroll-target");
      getEl(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
      betaRecordSessionEvent("step_navigated", `Open ${targetId}`, {
        step_id: targetId,
      });
    };
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
      state.currentDraft = collectDraftFromForm();
      setActionStatus("success", "Selection updated", `${button.getAttribute("data-chip-label")} ${pressed ? "removed" : "selected"}.`);
      renderAll();
    };
  });
  document.querySelectorAll("[data-help-trigger]").forEach((button) => {
    const key = button.getAttribute("data-help-trigger");
    button.onclick = (event) => {
      event.stopPropagation();
      openHelpPopover(key, button);
    };
    button.onmouseenter = () => openHelpPopover(key, button);
    button.onfocus = () => openHelpPopover(key, button);
  });
  document.querySelectorAll("select").forEach((node) => {
    if (node.hasAttribute("data-table-page-size")) return;
    if (node.id === "compare-run-a-select" || node.id === "compare-run-b-select") return;
    node.onchange = () => betaHandleSelectMutation(node);
  });
  [
    "study-title-input",
    "target-size-input",
    "max-resolution-input",
    "min-release-year-input",
    "exclude-pdb-ids-input",
    "epoch-budget-input",
    "include-waters-toggle",
    "include-salt-bridges-toggle",
    "include-contact-shell-toggle",
  ].forEach((id) => {
    const node = getEl(id);
    if (!node) return;
    node.onchange = () => {
      state.currentDraft = collectDraftFromForm();
      setActionStatus("success", "Draft updated", `${id.replaceAll("-", " ")} changed.`);
      renderAll();
    };
  });
  document.querySelectorAll("[data-table-filter]").forEach((input) => {
    input.oninput = () => {
      const key = input.getAttribute("data-table-filter");
      state.tableState[key] = { ...(state.tableState[key] || {}), query: input.value, page: 1 };
      renderAll();
    };
  });
  document.querySelectorAll("[data-table-page]").forEach((button) => {
    button.onclick = () => {
      const key = button.getAttribute("data-table-page");
      const direction = Number(button.getAttribute("data-table-direction") || "0");
      const current = state.tableState[key] || { query: "", page: 1, pageSize: 25 };
      state.tableState[key] = { ...current, page: Math.max(1, current.page + direction) };
      renderAll();
    };
  });
  document.querySelectorAll("[data-table-page-size]").forEach((select) => {
    select.onchange = () => {
      const key = select.getAttribute("data-table-page-size");
      const current = state.tableState[key] || { query: "", page: 1, pageSize: 25 };
      state.tableState[key] = { ...current, pageSize: Number(select.value || "25"), page: 1 };
      renderAll();
    };
  });
};

function betaBindStaticActions() {
  getEl("save-draft-button").onclick = async () => {
    const result = await runDraftAction("/api/model-studio/pipeline-specs/save-draft", "Draft saved");
    if (result.ok) {
      await loadWorkspace(state.currentDraft?.pipeline_id || "");
    }
  };
  getEl("validate-draft-button").onclick = async () => {
    await runDraftAction("/api/model-studio/pipeline-specs/validate", "Draft validated");
  };
  getEl("validate-step-button").onclick = async () => {
    await runDraftAction("/api/model-studio/pipeline-specs/validate", "Pipeline configuration validated");
  };
  getEl("compile-step-button").onclick = async () => {
    await runDraftAction("/api/model-studio/pipeline-specs/compile", "Execution graph compiled");
  };
  getEl("preview-dataset-button").onclick = previewDataset;
  getEl("preview-step-button").onclick = previewDataset;
  getEl("build-dataset-button").onclick = buildDataset;
  getEl("build-step-button").onclick = buildDataset;
  getEl("launch-run-button").onclick = launchRun;
  getEl("launch-step-button").onclick = launchRun;
  getEl("discover-hardware-button").onclick = refreshHardware;
  getEl("cancel-run-button").onclick = cancelRun;
  getEl("resume-run-button").onclick = resumeRun;
  getEl("compare-step-button").onclick = async () => {
    const eligibility = actionEligibility();
    if (!eligibility.compare.enabled) {
      setActionStatus("warning", "Comparison blocked", eligibility.compare.reason);
      return;
    }
    await refreshRunComparison();
    renderAll();
    setActionStatus("success", "Comparison refreshed", "Run comparison results have been updated.");
  };
  getEl("export-summary-button").onclick = exportSummary;
  getEl("open-report-button").onclick = openReport;
  getEl("submit-feedback-button").onclick = submitFeedback;
  getEl("need-help-button").onclick = () => {
    getEl("workspace-analysis-review")?.scrollIntoView({ behavior: "smooth", block: "start" });
    setActionStatus("info", "Feedback panel opened", "Describe what felt confusing, broken, or missing.");
    betaRecordSessionEvent("feedback_panel_opened", "Need help / report issue", {
      step_id: "export-review",
    });
  };
  getEl("refresh-runs-button").onclick = async () => {
    await loadWorkspace(state.currentDraft?.pipeline_id || "");
    setActionStatus("success", "Workspace refreshed", "Latest runs, datasets, and hardware have been reloaded.");
  };
}

openHelpPopover = function openHelpPopover(helpKey, anchor) {
  const help = fieldHelpRegistry()[helpKey];
  const popover = getEl("help-popover");
  if (!help || !anchor || !popover) return;
  popover.innerHTML = `
    <div class="help-card">
      <div class="help-card-head">
        <strong>${escapeHtml(help.title)}</strong>
        <span class="pill neutral">Field guide</span>
      </div>
      <p>${escapeHtml(help.summary)}</p>
      ${help.help_detail ? `<div class="help-line"><span>Details</span><div>${escapeHtml(help.help_detail)}</div></div>` : ""}
      <div class="help-line"><span>Includes</span><div>${escapeHtml(help.includes)}</div></div>
      <div class="help-line"><span>Excludes</span><div>${escapeHtml(help.excludes)}</div></div>
      <div class="help-line"><span>Artifacts</span><div>${escapeHtml(help.artifacts)}</div></div>
      <div class="help-line"><span>Assumptions</span><div>${escapeHtml(help.assumptions)}</div></div>
    </div>
  `;
  const rect = anchor.getBoundingClientRect();
  popover.classList.remove("hidden");
  popover.style.top = `${window.scrollY + rect.bottom + 10}px`;
  popover.style.left = `${Math.min(window.scrollX + rect.left, window.scrollX + window.innerWidth - 420)}px`;
  betaRecordSessionEvent("help_opened", helpKey, {
    step_id: anchor.closest(".panel, .subpanel")?.id || null,
  });
};

previewDataset = async function previewDataset() {
  try {
    setActionStatus("pending", "Previewing dataset", "Building candidate rows and diagnostics.");
    betaRecordSessionEvent("preview_requested", "Preview dataset", { step_id: "dataset-preview" });
    const payload = collectDraftFromForm();
    const result = await fetchJson("/api/model-studio/training-set-requests/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.currentDraft = structuredClone(payload);
    state.workspace = { ...state.workspace, pipeline_spec: state.currentDraft, training_set_preview: result };
    if (result.status === "blocked") {
      const blockerMessage =
        result.blockers?.[0]?.message ||
        result.recommendation_report?.items?.find((item) => item.level === "blocker")?.message ||
        "Dataset preview is blocked until the current configuration issues are resolved.";
      setActionStatus("blocked", "Dataset preview blocked", blockerMessage);
      renderAll();
      return;
    }
    setActionStatus(
      "success",
      "Dataset preview ready",
      result.candidate_preview?.target_size_warning ||
        `${result.candidate_preview?.final_selected_count || result.candidate_preview?.row_count || 0} rows are available for review under the current eligible cap.`,
    );
    renderAll();
  } catch (error) {
    setActionStatus("failed", "Dataset preview failed", error.message);
  }
};

buildDataset = async function buildDataset() {
  const eligibility = actionEligibility();
  if (!eligibility.build.enabled) {
    setActionStatus("warning", "Build blocked", eligibility.build.reason);
    return;
  }
  try {
    setActionStatus("pending", "Building dataset", "Creating the study dataset and split artifacts.");
    betaRecordSessionEvent("build_requested", "Build dataset", { step_id: "build-split" });
    const payload = collectDraftFromForm();
    const result = await fetchJson("/api/model-studio/training-set-builds/build", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.currentDraft = structuredClone(payload);
    state.workspace = { ...state.workspace, pipeline_spec: state.currentDraft, latest_training_set_build: result.build_manifest };
    if (result.status === "blocked" || result.build_manifest?.status === "blocked") {
      const blockerMessage =
        result.blockers?.[0]?.message ||
        result.build_manifest?.blockers?.[0]?.message ||
        result.recommendation_report?.items?.find((item) => item.level === "blocker")?.message ||
        "Dataset build is blocked until the current configuration issues are resolved.";
      setActionStatus("blocked", "Dataset build blocked", blockerMessage);
      renderAll();
      return;
    }
    setActionStatus(
      "success",
      "Dataset build completed",
      result.build_manifest.target_size_warning ||
        `${result.build_manifest.final_selected_count || result.build_manifest.row_count || 0} rows were built into ${result.build_manifest.dataset_ref}.`,
    );
    await loadWorkspace(state.currentDraft.pipeline_id);
  } catch (error) {
    setActionStatus("failed", "Dataset build failed", error.message);
  }
};

launchRun = async function launchRun() {
  const eligibility = actionEligibility();
  if (!eligibility.launch.enabled) {
    setActionStatus("warning", "Run launch blocked", eligibility.launch.reason);
    return;
  }
  try {
    setActionStatus("pending", "Launching run", "Starting background study execution.");
    betaRecordSessionEvent("run_launch_requested", "Launch run", { step_id: "run-monitor" });
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
};

refreshHardware = async function refreshHardware() {
  try {
    setActionStatus("pending", "Discovering hardware", "Refreshing local CPU, RAM, and CUDA info.");
    betaRecordSessionEvent("hardware_refresh_requested", "Refresh hardware profile", { step_id: "pipeline-design" });
    state.workspace.hardware_profile = await fetchJson("/api/model-studio/hardware-profile");
    state.workspace.ui_contract = {
      ...(state.workspace.ui_contract || {}),
      hardware_profile: state.workspace.hardware_profile,
    };
    setActionStatus("success", "Hardware profile updated", state.workspace.hardware_profile.recommended_preset);
    renderAll();
  } catch (error) {
    setActionStatus("failed", "Hardware discovery failed", error.message);
  }
};

exportSummary = function exportSummary() {
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
  betaRecordSessionEvent("summary_exported", "Export summary", { step_id: "export-review" });
};

openReport = function openReport() {
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
  betaRecordSessionEvent("report_path_opened", "Show report path", { step_id: "export-review" });
};

async function submitFeedback() {
  const message = getEl("feedback-message-input")?.value?.trim() || "";
  if (!message) {
    setActionStatus("warning", "Feedback blocked", "Describe the issue before sending feedback.");
    getEl("feedback-status").innerHTML = `<div class="stack-item warning">Describe the issue before sending feedback.</div>`;
    return;
  }
  try {
    setActionStatus("pending", "Sending feedback", "Saving your beta-session note.");
    const response = await fetchJson("/api/model-studio/feedback", {
      method: "POST",
      body: JSON.stringify({
        study_title: state.currentDraft?.study_title || "",
        pipeline_id: state.currentDraft?.pipeline_id || "",
        run_id: state.selectedRunId || "",
        step_id: (computeStepStatuses().find((step) => step.status === "current") || {}).id || "guided-stepper",
        category: getEl("feedback-category-select")?.value || "general",
        severity: getEl("feedback-severity-select")?.value || "normal",
        message,
        context: {
          model_family: state.currentDraft?.training_plan?.model_family || "",
          dataset_ref: state.workspace?.latest_training_set_build?.dataset_ref || state.workspace?.selected_dataset?.dataset_ref || "",
          current_stage: currentRunManifest()?.active_stage || "",
        },
      }),
    });
    getEl("feedback-status").innerHTML = `<div class="stack-item"><strong>Feedback saved</strong><div class="muted">${escapeHtml(response.path || response.feedback_id || "saved")}</div></div>`;
    getEl("feedback-message-input").value = "";
    setActionStatus("success", "Feedback saved", response.feedback_id || "Saved");
    betaRecordSessionEvent("feedback_submitted", "Feedback submitted", {
      step_id: "export-review",
      feedback_id: response.feedback_id || "",
    });
  } catch (error) {
    setActionStatus("failed", "Feedback failed", error.message);
    getEl("feedback-status").innerHTML = `<div class="stack-item warning">${escapeHtml(error.message)}</div>`;
  }
}

renderAll = function renderAll() {
  ensureDraftShape();
  injectHelpButtons();
  renderNav();
  renderHero();
  renderToplineCards();
  renderStatusRail();
  renderOnboardingPanel();
  renderActionButtons();
  renderStepper();
  renderProgramPanels();
  renderDataStrategyForm();
  renderRepresentationForm();
  renderPipelineComposer();
  renderExecutionConsole();
  renderRecommendations();
  betaBindStaticActions();
  bindDynamicButtons();
  renderFieldFeedbacks();
};

loadWorkspace = async function loadWorkspace(pipelineId = "") {
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
  betaRecordSessionEvent("workspace_loaded", "Workspace loaded", {
    step_id: (state.workspace?.stepper || []).find((step) => step.status === "current")?.id || "training-request",
  });
};

if (state.workspace) {
  renderAll();
}

if (document.body?.dataset?.studioVariant === "beta") {
  setViewMode("guided");
  loadWorkspace().catch((error) => {
    getEl("study-title").textContent = "Model Studio failed to load";
    getEl("study-summary").textContent = error.message;
    setActionStatus("failed", "Workspace failed to load", error.message);
  });
}
