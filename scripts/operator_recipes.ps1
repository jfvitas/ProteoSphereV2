param(
    [ValidateSet("acceptance-review", "packet-triage", "benchmark-review", "soak-readiness", "onboarding", "training-set-builder", "release-grade-review", "external-dataset-assessment", "overnight-run-readiness", "list")]
    [string]$Recipe = "list",
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ReportsDir = Join-Path $RepoRoot "docs\reports"
$ResultsDir = Join-Path $RepoRoot "runs\real_data_benchmark\full_results"
$OperatorScriptPath = Join-Path $PSScriptRoot "powershell_interface.ps1"

function Read-JsonPayload {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            exists = $false
            path = $Path
            data = $null
            error = "missing input: $Path"
        }
    }

    try {
        return [pscustomobject]@{
            exists = $true
            path = $Path
            data = (Get-Content -Path $Path -Raw | ConvertFrom-Json)
            error = $null
        }
    }
    catch {
        return [pscustomobject]@{
            exists = $true
            path = $Path
            data = $null
            error = $_.Exception.Message
        }
    }
}

function Read-TextPayload {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            exists = $false
            path = $Path
            data = $null
            error = "missing input: $Path"
        }
    }

    try {
        return [pscustomobject]@{
            exists = $true
            path = $Path
            data = Get-Content -Path $Path -Raw
            error = $null
        }
    }
    catch {
        return [pscustomobject]@{
            exists = $true
            path = $Path
            data = $null
            error = $_.Exception.Message
        }
    }
}

function Get-OperatorSnapshot {
    if (-not (Test-Path $OperatorScriptPath)) {
        return $null
    }

    try {
        $raw = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $OperatorScriptPath -Mode state -AsJson
        if (-not $raw) {
            return $null
        }
        return ($raw | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

function New-RecipeResult {
    param(
        [string]$RecipeId,
        [string]$Title,
        [string]$Status,
        [string]$Summary,
        [object[]]$Artifacts,
        [string[]]$Diagnostics,
        [string[]]$TruthBoundary,
        [string[]]$NextSteps
    )

    return [pscustomobject]@{
        recipe_id = $RecipeId
        title = $Title
        status = $Status
        summary = $Summary
        artifacts = @($Artifacts)
        diagnostics = @($Diagnostics)
        truth_boundary = @($TruthBoundary)
        next_steps = @($NextSteps)
    }
}

function Invoke-AcceptanceReview {
    $matrix = Read-TextPayload -Path (Join-Path $ReportsDir "p20_acceptance_matrix.md")
    $regression = Read-JsonPayload -Path (Join-Path $ResultsDir "user_sim_regression.json")
    $operator = Get-OperatorSnapshot

    $artifacts = @($matrix.path, $regression.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "prototype-bound review surface only",
        "weeklong soak remains unproven"
    )
    $nextSteps = @(
        "use the acceptance matrix as the front-door signoff surface",
        "keep blocked soak and release-grade claims out of pass decisions"
    )

    if (-not $matrix.exists -or -not $regression.exists -or $null -eq $regression.data) {
        if (-not $matrix.exists) { $diagnostics.Add($matrix.error) | Out-Null }
        if (-not $regression.exists) { $diagnostics.Add($regression.error) | Out-Null }
        return New-RecipeResult `
            -RecipeId "acceptance-review" `
            -Title "Acceptance Review" `
            -Status "blocked" `
            -Summary "Acceptance review is blocked because the matrix or regression artifact is missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    $traceStates = $regression.data.summary.trace_states
    $passCount = [int]$traceStates.pass
    $weakCount = [int]$traceStates.weak
    $blockedCount = [int]$traceStates.blocked
    $diagnostics.Add("supported workflows=$passCount") | Out-Null
    $diagnostics.Add("weak workflows=$weakCount") | Out-Null
    $diagnostics.Add("blocked workflows=$blockedCount") | Out-Null
    if ($null -ne $operator) {
        $diagnostics.Add("queue done count=$($operator.queue.status_counts.done)") | Out-Null
        $diagnostics.Add("runtime active workers=$($operator.runtime.active_worker_count)") | Out-Null
    }

    $status = if ($passCount -gt 0) { "supported" } else { "weak" }
    $summary = "Acceptance review is ready as a signoff surface with $passCount supported, $weakCount weak, and $blockedCount blocked workflows."
    return New-RecipeResult `
        -RecipeId "acceptance-review" `
        -Title "Acceptance Review" `
        -Status $status `
        -Summary $summary `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Invoke-PacketTriage {
    $auditMd = Read-TextPayload -Path (Join-Path $ReportsDir "training_packet_audit.md")
    $auditJson = Read-JsonPayload -Path (Join-Path $ResultsDir "training_packet_audit.json")

    $artifacts = @($auditMd.path, $auditJson.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "partial packets remain partial",
        "packet usefulness is not release readiness"
    )
    $nextSteps = @(
        "prioritize richer packets before widening the cohort",
        "keep thin and mixed packets explicit in operator output"
    )

    if (-not $auditMd.exists -or -not $auditJson.exists -or $null -eq $auditJson.data) {
        if (-not $auditMd.exists) { $diagnostics.Add($auditMd.error) | Out-Null }
        if (-not $auditJson.exists) { $diagnostics.Add($auditJson.error) | Out-Null }
        return New-RecipeResult `
            -RecipeId "packet-triage" `
            -Title "Packet Triage" `
            -Status "blocked" `
            -Summary "Packet triage is blocked because the packet audit artifacts are missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    $summary = $auditJson.data.summary
    $packetCount = [int]$summary.packet_count
    $usefulCount = [int]$summary.judgment_counts.useful
    $weakCount = [int]$summary.judgment_counts.weak
    $partialCount = [int]$summary.completeness_counts.partial
    $diagnostics.Add("packet count=$packetCount") | Out-Null
    $diagnostics.Add("useful packets=$usefulCount") | Out-Null
    $diagnostics.Add("weak packets=$weakCount") | Out-Null
    $diagnostics.Add("partial packets=$partialCount") | Out-Null

    $status = if ($usefulCount -eq $packetCount) { "supported" } else { "weak" }
    $summaryText = "Packet triage remains $status because $usefulCount of $packetCount packets are currently useful and $partialCount remain partial."
    return New-RecipeResult `
        -RecipeId "packet-triage" `
        -Title "Packet Triage" `
        -Status $status `
        -Summary $summaryText `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Invoke-BenchmarkReview {
    $runSummary = Read-JsonPayload -Path (Join-Path $ResultsDir "run_summary.json")
    $portfolio = Read-JsonPayload -Path (Join-Path $ResultsDir "model_portfolio_benchmark.json")
    $envelopes = Read-TextPayload -Path (Join-Path $ReportsDir "p19_training_envelopes.md")

    $artifacts = @($runSummary.path, $portfolio.path, $envelopes.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "prototype runtime only",
        "portfolio ranking is not a release-grade family sweep"
    )
    $nextSteps = @(
        "inspect thin and blocked rows before widening benchmark conclusions",
        "use acceptance review for signoff-facing summaries"
    )

    if (-not $runSummary.exists -or -not $portfolio.exists -or -not $envelopes.exists) {
        foreach ($payload in @($runSummary, $portfolio, $envelopes)) {
            if (-not $payload.exists) { $diagnostics.Add($payload.error) | Out-Null }
        }
        return New-RecipeResult `
            -RecipeId "benchmark-review" `
            -Title "Benchmark Review" `
            -Status "blocked" `
            -Summary "Benchmark review is blocked because one or more benchmark artifacts are missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    $diagnostics.Add("selected accessions=$($runSummary.data.selected_accession_count)") | Out-Null
    $diagnostics.Add("runtime surface=$($runSummary.data.runtime_surface)") | Out-Null
    $diagnostics.Add("top portfolio candidate=$($portfolio.data.candidate_families[0].name)") | Out-Null

    return New-RecipeResult `
        -RecipeId "benchmark-review" `
        -Title "Benchmark Review" `
        -Status "supported" `
        -Summary "Benchmark review is supported as a prototype-bound workflow over the frozen cohort artifacts." `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Invoke-SoakReadiness {
    $soak = Read-TextPayload -Path (Join-Path $ReportsDir "p22_weeklong_soak.md")
    $artifacts = @($soak.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "weeklong soak remains unproven",
        "readiness note is not completion evidence"
    )
    $nextSteps = @(
        "run a real long-duration soak before upgrading the claim",
        "keep blocked operational claims visible in operator output"
    )

    if (-not $soak.exists) {
        $diagnostics.Add($soak.error) | Out-Null
        return New-RecipeResult `
            -RecipeId "soak-readiness" `
            -Title "Soak Readiness" `
            -Status "blocked" `
            -Summary "Soak readiness is blocked because the soak note is missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    $text = [string]$soak.data
    if (
        $text -match "not a claim" -or
        $text -match "not yet" -or
        $text -match "readiness assessment" -or
        $text -match "weeklong_claim_allowed\s*=\s*false" -or
        $text -match "boundary remains closed" -or
        $text -match "truth boundary is still intentionally closed" -or
        $text -match "release boundary remains closed"
    ) {
        $diagnostics.Add("soak evidence is still readiness-only") | Out-Null
        return New-RecipeResult `
            -RecipeId "soak-readiness" `
            -Title "Soak Readiness" `
            -Status "blocked" `
            -Summary "Soak readiness remains blocked because the repository still has readiness evidence, not completed weeklong-soak proof." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    return New-RecipeResult `
        -RecipeId "soak-readiness" `
        -Title "Soak Readiness" `
        -Status "supported" `
        -Summary "Soak review is supported." `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Invoke-Onboarding {
    $onboarding = Read-TextPayload -Path (Join-Path $ReportsDir "p21_onboarding_friction.md")
    $acceptance = Read-TextPayload -Path (Join-Path $ReportsDir "p20_acceptance_matrix.md")
    $artifacts = @($onboarding.path, $acceptance.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "PowerShell-first operator path remains the active surface",
        "operator front door should guide, not upgrade evidence"
    )
    $nextSteps = @(
        "surface the acceptance matrix as the front-door review artifact",
        "add a quickstart path for queue, packet, benchmark, and user-sim questions"
    )

    if (-not $onboarding.exists -or -not $acceptance.exists) {
        foreach ($payload in @($onboarding, $acceptance)) {
            if (-not $payload.exists) { $diagnostics.Add($payload.error) | Out-Null }
        }
        return New-RecipeResult `
            -RecipeId "onboarding" `
            -Title "Onboarding Review" `
            -Status "blocked" `
            -Summary "Onboarding review is blocked because the friction analysis or acceptance matrix is missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    $diagnostics.Add("front-door acceptance surface available") | Out-Null
    $diagnostics.Add("onboarding friction report available") | Out-Null
    return New-RecipeResult `
        -RecipeId "onboarding" `
        -Title "Onboarding Review" `
        -Status "supported" `
        -Summary "Onboarding review is supported and can guide operators from acceptance, packet, and benchmark surfaces without widening the truth boundary." `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Invoke-TrainingSetBuilder {
    $procurementSourceCompletion = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_source_completion_preview.json")
    $readiness = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_readiness_preview.json")
    $compiler = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\cohort_compiler_preview.json")
    $rationale = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\cohort_inclusion_rationale_preview.json")
    $gateLadder = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_gate_ladder_preview.json")
    $unlockRoute = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_unlock_route_preview.json")
    $transitionContract = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_transition_contract_preview.json")
    $sourceFixBatch = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_source_fix_batch_preview.json")
    $packageTransitionBatch = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_package_transition_batch_preview.json")
    $packageExecution = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_package_execution_preview.json")
    $previewHoldRegister = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_preview_hold_register_preview.json")
    $previewHoldExitCriteria = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_preview_hold_exit_criteria_preview.json")
    $previewHoldClearanceBatch = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_preview_hold_clearance_batch_preview.json")
    $gatingEvidence = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_gating_evidence_preview.json")
    $actionQueue = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_action_queue_preview.json")
    $blockerBurndown = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_blocker_burndown_preview.json")
    $modalityGap = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_modality_gap_register_preview.json")
    $packageBlockerMatrix = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_package_blocker_matrix_preview.json")
    $packetCompleteness = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_packet_completeness_matrix_preview.json")
    $splitAlignmentRecheck = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_split_alignment_recheck_preview.json")
    $packetMaterializationQueue = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_packet_materialization_queue_preview.json")
    $structuredCorpus = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\seed_plus_neighbors_structured_corpus_preview.json")
    $baselineSidecar = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_baseline_sidecar_preview.json")
    $multimodalSidecar = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_multimodal_sidecar_preview.json")
    $packetSummary = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_packet_summary_preview.json")
    $remediation = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_remediation_plan_preview.json")
    $unblockPlan = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_unblock_plan_preview.json")
    $scrapeBacklog = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\scrape_backlog_remaining_preview.json")
    $package = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\package_readiness_preview.json")
    $session = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_builder_session_preview.json")
    $runbook = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\training_set_builder_runbook_preview.json")

    $artifacts = @($procurementSourceCompletion.path, $readiness.path, $compiler.path, $rationale.path, $gateLadder.path, $unlockRoute.path, $transitionContract.path, $sourceFixBatch.path, $packageTransitionBatch.path, $packageExecution.path, $previewHoldRegister.path, $previewHoldExitCriteria.path, $previewHoldClearanceBatch.path, $gatingEvidence.path, $actionQueue.path, $blockerBurndown.path, $modalityGap.path, $packageBlockerMatrix.path, $packetCompleteness.path, $splitAlignmentRecheck.path, $packetMaterializationQueue.path, $structuredCorpus.path, $baselineSidecar.path, $multimodalSidecar.path, $packetSummary.path, $remediation.path, $unblockPlan.path, $scrapeBacklog.path, $package.path, $session.path, $runbook.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "report-only cohort/build session",
        "package materialization remains locked"
    )
    $nextSteps = @(
        "use training_set_builder_cli.py for refresh-procurement-truth, execute-scrape-wave, materialize-string-interaction, build-canonical-structured-corpus, build-baseline-sidecar, build-multimodal-sidecar, and run-post-tail-unlock-dry-run",
        "use training_set_builder_cli.py for compile-cohort, assess-readiness, plan-package, packet-completeness, packet-summary, and packet-materialization-queue",
        "keep split/package promotion blocked until the current preview gates explicitly unlock"
    )

    foreach ($payload in @($procurementSourceCompletion, $readiness, $compiler, $rationale, $gateLadder, $unlockRoute, $transitionContract, $sourceFixBatch, $packageTransitionBatch, $packageExecution, $previewHoldRegister, $previewHoldExitCriteria, $previewHoldClearanceBatch, $gatingEvidence, $actionQueue, $blockerBurndown, $modalityGap, $packageBlockerMatrix, $packetCompleteness, $splitAlignmentRecheck, $packetMaterializationQueue, $structuredCorpus, $baselineSidecar, $multimodalSidecar, $packetSummary, $remediation, $unblockPlan, $scrapeBacklog, $package, $session, $runbook)) {
        if (-not $payload.exists -or $null -eq $payload.data) {
            if (-not $payload.exists) { $diagnostics.Add($payload.error) | Out-Null }
            elseif ($payload.error) { $diagnostics.Add($payload.error) | Out-Null }
        }
    }
    if ($diagnostics.Count -gt 0) {
        return New-RecipeResult `
            -RecipeId "training-set-builder" `
            -Title "Training Set Builder" `
            -Status "blocked" `
            -Summary "Training-set builder visibility is blocked because one or more report-only builder surfaces are missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    $diagnostics.Add("selected accessions=$($compiler.data.summary.selected_count)") | Out-Null
    $diagnostics.Add("assignment ready=$($readiness.data.summary.assignment_ready)") | Out-Null
    $diagnostics.Add("rationale rows=$(@($rationale.data.rows).Count)") | Out-Null
    $diagnostics.Add("gated rationale rows=$($rationale.data.summary.gated_count)") | Out-Null
    $diagnostics.Add("gate ladder next step=$($gateLadder.data.summary.top_next_steps[0].next_step)") | Out-Null
    $diagnostics.Add("gate ladder alerts=$($gateLadder.data.summary.consistency_alerts.Count)") | Out-Null
    $diagnostics.Add("unlock route next transition=$($unlockRoute.data.summary.next_unlock_stage)") | Out-Null
    $diagnostics.Add("unlock route blocked routes=$($unlockRoute.data.summary.blocking_gate_count)") | Out-Null
    $diagnostics.Add("transition contract next step=$($transitionContract.data.summary.next_transition_contract)") | Out-Null
    $diagnostics.Add("transition contract source-fix pending=$($transitionContract.data.summary.source_fix_transition_pending_count)") | Out-Null
    $diagnostics.Add("source-fix batch rows=$($sourceFixBatch.data.summary.source_fix_batch_row_count)") | Out-Null
    $diagnostics.Add("source-fix batch next ref=$($sourceFixBatch.data.summary.next_source_fix_batch)") | Out-Null
    $diagnostics.Add("package transition batch rows=$($packageTransitionBatch.data.summary.package_transition_batch_row_count)") | Out-Null
    $diagnostics.Add("package transition next batch=$($packageTransitionBatch.data.summary.next_package_batch)") | Out-Null
    $diagnostics.Add("package execution rows=$($packageExecution.data.summary.package_execution_row_count)") | Out-Null
    $diagnostics.Add("package execution lane=$($packageExecution.data.summary.next_execution_lane)") | Out-Null
    $diagnostics.Add("preview hold rows=$($previewHoldRegister.data.summary.preview_hold_row_count)") | Out-Null
    $diagnostics.Add("preview hold lane=$($previewHoldRegister.data.summary.next_hold_lane)") | Out-Null
    $diagnostics.Add("preview hold exit rows=$($previewHoldExitCriteria.data.summary.exit_criteria_row_count)") | Out-Null
    $diagnostics.Add("preview hold exit state=$($previewHoldExitCriteria.data.summary.current_exit_state)") | Out-Null
    $diagnostics.Add("preview hold clearance rows=$($previewHoldClearanceBatch.data.summary.clearance_batch_row_count)") | Out-Null
    $diagnostics.Add("preview hold clearance batch=$($previewHoldClearanceBatch.data.summary.current_batch_state)") | Out-Null
    $diagnostics.Add("gating evidence rows=$(@($gatingEvidence.data.rows).Count)") | Out-Null
    $diagnostics.Add("gating preview-only rows=$($gatingEvidence.data.summary.preview_only_count)") | Out-Null
    $diagnostics.Add("action queue rows=$($actionQueue.data.summary.queue_length)") | Out-Null
    $diagnostics.Add("action queue impacted accessions=$($actionQueue.data.summary.impacted_accession_count)") | Out-Null
    $diagnostics.Add("blocker burndown blocked accessions=$($blockerBurndown.data.summary.blocked_accession_count)") | Out-Null
    $diagnostics.Add("blocker burndown critical actions=$($blockerBurndown.data.summary.critical_action_count)") | Out-Null
    $diagnostics.Add("modality gap blocked modalities=$($modalityGap.data.summary.blocked_modality_count)") | Out-Null
    $diagnostics.Add("top modality gap=$($modalityGap.data.summary.top_gap_modalities[0].modality)") | Out-Null
    $diagnostics.Add("packet summary count=$($packetSummary.data.summary.packet_count)") | Out-Null
    $diagnostics.Add("package blocker rows=$($packageBlockerMatrix.data.summary.selected_accession_count)") | Out-Null
    $diagnostics.Add("package blocker fold export blocked=$($packageBlockerMatrix.data.summary.fold_export_blocked_count)") | Out-Null
    $diagnostics.Add("packet completeness selected=$($packetCompleteness.data.summary.selected_accession_count)") | Out-Null
    $diagnostics.Add("packet completeness governing-ready=$($packetCompleteness.data.summary.packet_lane_counts.governing_ready_but_package_blocked)") | Out-Null
    $diagnostics.Add("split alignment mismatches=$($splitAlignmentRecheck.data.summary.mismatch_count)") | Out-Null
    $diagnostics.Add("split alignment expected 8/2/2=$($splitAlignmentRecheck.data.summary.expected_8_2_2_layout)") | Out-Null
    $diagnostics.Add("packet queue rows=$($packetMaterializationQueue.data.summary.selected_accession_count)") | Out-Null
    $diagnostics.Add("packet queue stub root=$($packetMaterializationQueue.data.summary.stub_root)") | Out-Null
    $diagnostics.Add("source completion string gate=$($procurementSourceCompletion.data.string_completion_status)") | Out-Null
    $diagnostics.Add("source completion uniref gate=$($procurementSourceCompletion.data.uniprot_completion_status)") | Out-Null
    $diagnostics.Add("structured corpus rows=$($structuredCorpus.data.summary.row_count)") | Out-Null
    $diagnostics.Add("structured corpus governing-ready=$($structuredCorpus.data.summary.governing_status_counts.governing_ready)") | Out-Null
    $diagnostics.Add("baseline sidecar examples=$($baselineSidecar.data.summary.example_count)") | Out-Null
    $diagnostics.Add("baseline sidecar governing-ready=$($baselineSidecar.data.summary.governing_ready_example_count)") | Out-Null
    $diagnostics.Add("multimodal sidecar examples=$($multimodalSidecar.data.summary.example_count)") | Out-Null
    $diagnostics.Add("multimodal sidecar issues=$($multimodalSidecar.data.summary.issue_count)") | Out-Null
    $diagnostics.Add("remediation rows=$($remediation.data.summary.selected_count)") | Out-Null
    $diagnostics.Add("unblock impacted accessions=$($unblockPlan.data.summary.impacted_accession_count)") | Out-Null
    $diagnostics.Add("scrape backlog next jobs=$($scrapeBacklog.data.summary.next_priority_job_count)") | Out-Null
    $diagnostics.Add("scrape backlog missing lanes=$($scrapeBacklog.data.summary.still_missing_count)") | Out-Null
    $diagnostics.Add("package blockers=$($unblockPlan.data.summary.blocked_reason_count)") | Out-Null
    $topIssueBucket = $null
    if ($remediation.data.summary.issue_bucket_counts) {
        $topIssueBucket = (
            $remediation.data.summary.issue_bucket_counts.PSObject.Properties |
                Sort-Object -Property Value -Descending |
                Select-Object -First 1
        ).Name
    }
    $diagnostics.Add("top remediation issue=$topIssueBucket") | Out-Null
    $diagnostics.Add("package ready=$($package.data.summary.ready_for_package)") | Out-Null
    $diagnostics.Add("runbook steps=$($runbook.data.summary.command_count)") | Out-Null

    return New-RecipeResult `
        -RecipeId "training-set-builder" `
        -Title "Training Set Builder" `
        -Status "supported" `
        -Summary "Training-set builder surfaces are available for operator review, but remain report-only and fail-closed on packaging." `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Invoke-ReleaseGradeReview {
    $readiness = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_grade_readiness_preview.json")
    $closureQueue = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_grade_closure_queue_preview.json")
    $runtimeMaturity = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_runtime_maturity_preview.json")
    $sourceCoverageDepth = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_source_coverage_depth_preview.json")
    $provenanceDepth = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_provenance_depth_preview.json")
    $runbook = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_grade_runbook_preview.json")
    $accessionClosure = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_accession_closure_matrix_preview.json")
    $accessionActionQueue = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_accession_action_queue_preview.json")
    $promotionGate = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_promotion_gate_preview.json")
    $sourceFixFollowupBatch = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_source_fix_followup_batch_preview.json")
    $candidatePromotion = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\release_candidate_promotion_preview.json")
    $finalBundle = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\final_structured_dataset_bundle_preview.json")
    $summary = Read-JsonPayload -Path (Join-Path $ResultsDir "summary.json")
    $releaseLedger = Read-JsonPayload -Path (Join-Path $ResultsDir "release_corpus_evidence_ledger.json")
    $releaseCards = Read-JsonPayload -Path (Join-Path $ResultsDir "release_cards_manifest.json")

    $artifacts = @($readiness.path, $closureQueue.path, $runtimeMaturity.path, $sourceCoverageDepth.path, $provenanceDepth.path, $runbook.path, $accessionClosure.path, $accessionActionQueue.path, $promotionGate.path, $sourceFixFollowupBatch.path, $candidatePromotion.path, $finalBundle.path, $summary.path, $releaseLedger.path, $releaseCards.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "release-grade review remains report-only",
        "final dataset bundle presence does not authorize a release claim"
    )
    $nextSteps = @(
        "use training_set_builder_cli.py release-grade-readiness, release-grade-closure-queue, and release-accession-action-queue to refresh ranked release work",
        "treat runtime maturity, source coverage depth, and provenance/reporting depth as the remaining real blockers",
        "keep the expansion procurement backlog deferred until the new storage drive is available"
    )

    foreach ($payload in @($readiness, $closureQueue, $runtimeMaturity, $sourceCoverageDepth, $provenanceDepth, $runbook, $accessionClosure, $accessionActionQueue, $promotionGate, $sourceFixFollowupBatch, $candidatePromotion, $finalBundle, $summary, $releaseLedger, $releaseCards)) {
        if (-not $payload.exists -or $null -eq $payload.data) {
            if (-not $payload.exists) { $diagnostics.Add($payload.error) | Out-Null }
            elseif ($payload.error) { $diagnostics.Add($payload.error) | Out-Null }
        }
    }
    if ($diagnostics.Count -gt 0) {
        return New-RecipeResult `
            -RecipeId "release-grade-review" `
            -Title "Release Grade Review" `
            -Status "blocked" `
            -Summary "Release-grade review is blocked because one or more release evidence surfaces are missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    $diagnostics.Add("release-grade status=$($readiness.data.summary.release_grade_status)") | Out-Null
    $diagnostics.Add("release blocker count=$($readiness.data.summary.blocker_count)") | Out-Null
    $diagnostics.Add("closure queue length=$($closureQueue.data.summary.queue_length)") | Out-Null
    $diagnostics.Add("final dataset bundle present=$($finalBundle.data.status)") | Out-Null
    $diagnostics.Add("bundle corpus rows=$($finalBundle.data.summary.corpus_row_count)") | Out-Null
    $diagnostics.Add("strict governing rows=$($finalBundle.data.summary.strict_governing_training_view_count)") | Out-Null
    $diagnostics.Add("release ledger blocked count=$($readiness.data.summary.release_ledger_blocked_count)") | Out-Null
    $diagnostics.Add("release cards published=$($readiness.data.summary.release_card_count)") | Out-Null
    $diagnostics.Add("summary status=$($summary.data.status)") | Out-Null
    $diagnostics.Add("runtime maturity state=$($runtimeMaturity.data.summary.runtime_maturity_state)") | Out-Null
    $diagnostics.Add("thin coverage count=$($sourceCoverageDepth.data.summary.thin_coverage_count)") | Out-Null
    $diagnostics.Add("provenance depth state=$($provenanceDepth.data.summary.provenance_depth_state)") | Out-Null
    $diagnostics.Add("release runbook steps=$($runbook.data.summary.command_count)") | Out-Null
    $diagnostics.Add("closest to release count=$($accessionClosure.data.summary.closest_to_release_count)") | Out-Null
    $diagnostics.Add("promotion review count=$($accessionActionQueue.data.summary.promotion_review_count)") | Out-Null
    $diagnostics.Add("source-fix follow-up count=$($accessionActionQueue.data.summary.source_fix_followup_count)") | Out-Null
    $diagnostics.Add("promotion gate state=$($promotionGate.data.summary.promotion_gate_state)") | Out-Null
    $diagnostics.Add("promotion ready now=$($promotionGate.data.summary.promotion_ready_now)") | Out-Null
    $diagnostics.Add("source-fix batch rows=$($sourceFixFollowupBatch.data.summary.batch_row_count)") | Out-Null
    $diagnostics.Add("release candidate count=$($candidatePromotion.data.summary.candidate_count)") | Out-Null
    if ($closureQueue.data.queue_rows.Count -gt 0) {
        $diagnostics.Add("top closure action=$($closureQueue.data.queue_rows[0].next_action)") | Out-Null
    }

    return New-RecipeResult `
        -RecipeId "release-grade-review" `
        -Title "Release Grade Review" `
        -Status "blocked" `
        -Summary "Release-grade review is actionable and fully instrumented, but remains honestly blocked on the ranked runtime, source-coverage, and provenance evidence bars." `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Invoke-ExternalDatasetAssessment {
    $intake = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_intake_contract_preview.json")
      $assessment = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_assessment_preview.json")
      $manifestLint = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_manifest_lint_preview.json")
      $flawTaxonomy = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_flaw_taxonomy_preview.json")
      $riskRegister = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_risk_register_preview.json")
      $conflictRegister = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_conflict_register_preview.json")
      $acceptanceGate = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_acceptance_gate_preview.json")
      $admissionDecision = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_admission_decision_preview.json")
      $clearanceDelta = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_clearance_delta_preview.json")
      $resolution = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_resolution_preview.json")
      $resolutionDiff = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_resolution_diff_preview.json")
      $acceptancePath = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_acceptance_path_preview.json")
      $remediationTemplate = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_remediation_template_preview.json")
      $fixtureCatalog = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_fixture_catalog_preview.json")
      $remediationReadiness = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_remediation_readiness_preview.json")
      $caveatExecution = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_caveat_execution_preview.json")
      $blockedAcquisitionBatch = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_blocked_acquisition_batch_preview.json")
      $acquisitionUnblock = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_acquisition_unblock_preview.json")
      $advisoryFollowupRegister = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_advisory_followup_register_preview.json")
      $caveatExitCriteria = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_caveat_exit_criteria_preview.json")
      $caveatReviewBatch = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_caveat_review_batch_preview.json")
      $remediationQueue = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_remediation_queue_preview.json")
      $issueMatrix = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\external_dataset_issue_matrix_preview.json")
      $sampleBundle = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\sample_external_dataset_assessment_bundle_preview.json")

      $artifacts = @($intake.path, $assessment.path, $manifestLint.path, $flawTaxonomy.path, $riskRegister.path, $conflictRegister.path, $acceptanceGate.path, $admissionDecision.path, $clearanceDelta.path, $resolution.path, $resolutionDiff.path, $acceptancePath.path, $remediationTemplate.path, $fixtureCatalog.path, $remediationReadiness.path, $caveatExecution.path, $blockedAcquisitionBatch.path, $acquisitionUnblock.path, $advisoryFollowupRegister.path, $caveatExitCriteria.path, $caveatReviewBatch.path, $remediationQueue.path, $issueMatrix.path, $sampleBundle.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "non-mutating external assessment only",
        "verdicts are advisory and fail-closed"
    )
    $nextSteps = @(
        "use external_dataset_assessment_cli.py intake-contract, assess, remediation-template, resolution-diff, and fixture-catalog to inspect outside datasets",
        "treat blocked_pending_mapping and blocked_pending_cleanup as hard remediation gates"
    )

      foreach ($payload in @($intake, $assessment, $manifestLint, $flawTaxonomy, $riskRegister, $conflictRegister, $acceptanceGate, $admissionDecision, $clearanceDelta, $resolution, $resolutionDiff, $acceptancePath, $remediationTemplate, $fixtureCatalog, $remediationReadiness, $caveatExecution, $blockedAcquisitionBatch, $acquisitionUnblock, $advisoryFollowupRegister, $caveatExitCriteria, $caveatReviewBatch, $remediationQueue, $issueMatrix, $sampleBundle)) {
        if (-not $payload.exists -or $null -eq $payload.data) {
            if (-not $payload.exists) { $diagnostics.Add($payload.error) | Out-Null }
            elseif ($payload.error) { $diagnostics.Add($payload.error) | Out-Null }
        }
    }
    if ($diagnostics.Count -gt 0) {
        return New-RecipeResult `
            -RecipeId "external-dataset-assessment" `
            -Title "External Dataset Assessment" `
            -Status "blocked" `
            -Summary "External dataset assessment is blocked because the intake contract or assessment surface is missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

      $diagnostics.Add("accepted shapes=$($intake.data.accepted_shapes.Count)") | Out-Null
        $diagnostics.Add("overall verdict=$($assessment.data.summary.overall_verdict)") | Out-Null
        $diagnostics.Add("dataset accession count=$($assessment.data.summary.dataset_accession_count)") | Out-Null
        $diagnostics.Add("manifest lint verdict=$($manifestLint.data.summary.overall_verdict)") | Out-Null
        $diagnostics.Add("manifest linted shapes=$($manifestLint.data.summary.linted_shape_count)") | Out-Null
        $diagnostics.Add("flaw taxonomy verdict=$($flawTaxonomy.data.summary.overall_verdict)") | Out-Null
        $diagnostics.Add("flaw taxonomy blocking categories=$($flawTaxonomy.data.summary.top_blocking_categories.Count)") | Out-Null
        $diagnostics.Add("risk register verdict=$($riskRegister.data.summary.overall_verdict)") | Out-Null
        $diagnostics.Add("risk register top rows=$($riskRegister.data.summary.top_risk_row_count)") | Out-Null
        $diagnostics.Add("conflict register verdict=$($conflictRegister.data.summary.overall_verdict)") | Out-Null
        $diagnostics.Add("conflict register top rows=$($conflictRegister.data.summary.top_conflict_row_count)") | Out-Null
        $diagnostics.Add("acceptance gate overall verdict=$($acceptanceGate.data.summary.overall_verdict)") | Out-Null
        $diagnostics.Add("blocked gate count=$($acceptanceGate.data.summary.blocked_gate_count)") | Out-Null
        $diagnostics.Add("admission decision=$($admissionDecision.data.summary.overall_decision)") | Out-Null
        $diagnostics.Add("admission blocking gate count=$($admissionDecision.data.summary.blocking_gate_count)") | Out-Null
      $diagnostics.Add("clearance delta state=$($clearanceDelta.data.summary.current_clearance_state)") | Out-Null
      $diagnostics.Add("clearance delta required changes=$($clearanceDelta.data.summary.required_change_count)") | Out-Null
      $diagnostics.Add("resolution overall verdict=$($resolution.data.summary.overall_resolution_verdict)") | Out-Null
      $diagnostics.Add("resolution blocked accessions=$($resolution.data.summary.blocked_accession_count)") | Out-Null
      $diagnostics.Add("resolution diff unresolved=$($resolutionDiff.data.summary.unresolved_or_blocked_count)") | Out-Null
      $diagnostics.Add("resolution diff conflicted=$($resolutionDiff.data.summary.conflicted_accession_count)") | Out-Null
      $diagnostics.Add("acceptance path next transition=$($acceptancePath.data.summary.next_acceptance_stage)") | Out-Null
      $diagnostics.Add("acceptance path blocked transitions=$($acceptancePath.data.summary.blocking_gate_count)") | Out-Null
      $diagnostics.Add("remediation template rows=$($remediationTemplate.data.summary.template_row_count)") | Out-Null
      $diagnostics.Add("fixture catalog count=$($fixtureCatalog.data.summary.fixture_count)") | Out-Null
      $diagnostics.Add("remediation readiness next batch=$($remediationReadiness.data.summary.next_ready_batch)") | Out-Null
      $diagnostics.Add("remediation readiness blocked acquisitions=$($remediationReadiness.data.summary.blocked_pending_acquisition_count)") | Out-Null
      $diagnostics.Add("caveat execution rows=$($caveatExecution.data.summary.caveat_execution_row_count)") | Out-Null
      $diagnostics.Add("caveat execution next batch=$($caveatExecution.data.summary.next_execution_batch)") | Out-Null
      $diagnostics.Add("blocked acquisition batch rows=$($blockedAcquisitionBatch.data.summary.blocked_acquisition_row_count)") | Out-Null
      $diagnostics.Add("blocked acquisition next gate=$($blockedAcquisitionBatch.data.summary.next_blocked_batch)") | Out-Null
      $diagnostics.Add("acquisition unblock rows=$($acquisitionUnblock.data.summary.acquisition_unblock_row_count)") | Out-Null
      $diagnostics.Add("acquisition unblock lane=$($acquisitionUnblock.data.summary.next_unblock_batch)") | Out-Null
      $diagnostics.Add("advisory follow-up rows=$($advisoryFollowupRegister.data.summary.advisory_followup_row_count)") | Out-Null
      $diagnostics.Add("advisory follow-up lane=$($advisoryFollowupRegister.data.summary.next_followup_lane)") | Out-Null
      $diagnostics.Add("caveat exit rows=$($caveatExitCriteria.data.summary.caveat_exit_row_count)") | Out-Null
      $diagnostics.Add("caveat exit state=$($caveatExitCriteria.data.summary.current_exit_state)") | Out-Null
      $diagnostics.Add("caveat review rows=$($caveatReviewBatch.data.summary.review_batch_row_count)") | Out-Null
      $diagnostics.Add("caveat review batch=$($caveatReviewBatch.data.summary.current_batch_state)") | Out-Null
      $diagnostics.Add("remediation queue rows=$($remediationQueue.data.summary.remediation_queue_row_count)") | Out-Null
        $diagnostics.Add("remediation queue blocked accessions=$($remediationQueue.data.summary.blocked_accession_count)") | Out-Null
        $diagnostics.Add("issue rows=$($issueMatrix.data.summary.issue_row_count)") | Out-Null
      $topIssueCategory = $null
      if ($issueMatrix.data.summary.issue_category_counts) {
          $topIssueCategory = (
              $issueMatrix.data.summary.issue_category_counts.PSObject.Properties |
                  Sort-Object -Property Value -Descending |
                  Select-Object -First 1
          ).Name
      }
      $diagnostics.Add("top issue category=$topIssueCategory") | Out-Null
    $diagnostics.Add("sample manifest count=$($sampleBundle.data.summary.sample_manifest_count)") | Out-Null
    $diagnostics.Add("sample bundle verdict=$($sampleBundle.data.summary.assessment_overall_verdict)") | Out-Null

    return New-RecipeResult `
        -RecipeId "external-dataset-assessment" `
        -Title "External Dataset Assessment" `
        -Status "supported" `
        -Summary "The external dataset assessment lane is available and remains advisory, row-aware, and fail-closed." `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Invoke-OvernightRunReadiness {
    $scrapeGap = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\scrape_gap_matrix_preview.json")
    $scrapeBacklog = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\scrape_backlog_remaining_preview.json")
    $queueBacklog = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\overnight_queue_backlog_preview.json")
    $executionContract = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\overnight_execution_contract_preview.json")
    $scrapeWave = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\scrape_execution_wave_preview.json")
    $idleStatus = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\overnight_idle_status_preview.json")
    $pendingReconciliation = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\overnight_pending_reconciliation_preview.json")
    $workerLaunchGap = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\overnight_worker_launch_gap_preview.json")
    $procurementFreshness = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_supervisor_freshness_preview.json")
    $downloadLocationAudit = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\download_location_audit_preview.json")
    $stalePartAudit = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_stale_part_audit_preview.json")
    $postTailUnlock = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\post_tail_unlock_dry_run_preview.json")
    $procurementTailReconciliation = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_tail_signal_reconciliation_preview.json")
    $procurementTailGrowth = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_tail_growth_preview.json")
    $procurementHeadroom = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_headroom_guard_preview.json")
    $procurementTailSpaceDrift = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_tail_space_drift_preview.json")
    $procurementTailSourcePressure = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_tail_source_pressure_preview.json")
    $procurementTailLogProgressRegistry = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_tail_log_progress_registry_preview.json")
    $procurementTailCompletionMargin = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_tail_completion_margin_preview.json")
    $procurementSpaceRecoveryTarget = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_space_recovery_target_preview.json")
    $procurementSpaceRecoveryCandidates = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_space_recovery_candidates_preview.json")
    $procurementSpaceRecoveryExecutionBatch = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_space_recovery_execution_batch_preview.json")
    $procurementSpaceRecoverySafetyRegister = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_space_recovery_safety_register_preview.json")
    $procurementTailFillRisk = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_tail_fill_risk_preview.json")
    $procurementSpaceRecoveryTrigger = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_space_recovery_trigger_preview.json")
    $procurementSpaceRecoveryGapDrift = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_space_recovery_gap_drift_preview.json")
    $procurementSpaceRecoveryCoverage = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_space_recovery_coverage_preview.json")
    $procurementRecoveryInterventionPriority = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_recovery_intervention_priority_preview.json")
    $procurementRecoveryEscalationLane = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_recovery_escalation_lane_preview.json")
    $procurementSpaceRecoveryConcentration = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_space_recovery_concentration_preview.json")
    $procurementRecoveryShortfallBridge = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_recovery_shortfall_bridge_preview.json")
    $procurementRecoveryLaneFragility = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_recovery_lane_fragility_preview.json")
    $procurementBroaderSearchTrigger = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\procurement_broader_search_trigger_preview.json")
    $waveAdvance = Read-JsonPayload -Path (Join-Path $RepoRoot "artifacts\status\overnight_wave_advance_preview.json")

    $artifacts = @($scrapeGap.path, $scrapeBacklog.path, $queueBacklog.path, $executionContract.path, $scrapeWave.path, $idleStatus.path, $pendingReconciliation.path, $workerLaunchGap.path, $procurementFreshness.path, $downloadLocationAudit.path, $stalePartAudit.path, $postTailUnlock.path, $procurementTailReconciliation.path, $procurementTailGrowth.path, $procurementHeadroom.path, $procurementTailSpaceDrift.path, $procurementTailSourcePressure.path, $procurementTailLogProgressRegistry.path, $procurementTailCompletionMargin.path, $procurementSpaceRecoveryTarget.path, $procurementSpaceRecoveryCandidates.path, $procurementSpaceRecoveryExecutionBatch.path, $procurementSpaceRecoverySafetyRegister.path, $procurementTailFillRisk.path, $procurementSpaceRecoveryTrigger.path, $procurementSpaceRecoveryGapDrift.path, $procurementSpaceRecoveryCoverage.path, $procurementRecoveryInterventionPriority.path, $procurementRecoveryEscalationLane.path, $procurementSpaceRecoveryConcentration.path, $procurementRecoveryShortfallBridge.path, $procurementRecoveryLaneFragility.path, $procurementBroaderSearchTrigger.path, $waveAdvance.path)
    $diagnostics = New-Object 'System.Collections.Generic.List[string]'
    $boundary = @(
        "queue-driven overnight execution only",
        "does not itself start the supervisor",
        "idle state remains report-only and procurement-tail aware"
    )
    $nextSteps = @(
        "review the top overnight backlog slice before starting the supervisor",
        "use advance_overnight_wave.py to replenish and dispatch sequentially when the queue is drained",
        "keep procurement supervision and monitor/reviewer health lanes always on",
        "use run_post_tail_unlock.py as the zero-decision dry run for the post-tail handoff"
    )

    foreach ($payload in @($scrapeGap, $scrapeBacklog, $queueBacklog, $executionContract, $scrapeWave, $idleStatus, $pendingReconciliation, $workerLaunchGap, $procurementFreshness, $downloadLocationAudit, $stalePartAudit, $postTailUnlock, $procurementTailReconciliation, $procurementTailGrowth, $procurementHeadroom, $procurementTailSpaceDrift, $procurementTailSourcePressure, $procurementTailLogProgressRegistry, $procurementTailCompletionMargin, $procurementSpaceRecoveryTarget, $procurementSpaceRecoveryCandidates, $procurementSpaceRecoveryExecutionBatch, $procurementSpaceRecoverySafetyRegister, $procurementTailFillRisk, $procurementSpaceRecoveryTrigger, $procurementSpaceRecoveryGapDrift, $procurementSpaceRecoveryCoverage, $procurementRecoveryInterventionPriority, $procurementRecoveryEscalationLane, $procurementSpaceRecoveryConcentration, $procurementRecoveryShortfallBridge, $procurementRecoveryLaneFragility, $procurementBroaderSearchTrigger, $waveAdvance)) {
        if (-not $payload.exists -or $null -eq $payload.data) {
            if (-not $payload.exists) { $diagnostics.Add($payload.error) | Out-Null }
            elseif ($payload.error) { $diagnostics.Add($payload.error) | Out-Null }
        }
    }
    if ($diagnostics.Count -gt 0) {
        return New-RecipeResult `
            -RecipeId "overnight-run-readiness" `
            -Title "Overnight Run Readiness" `
            -Status "blocked" `
            -Summary "Overnight run readiness is blocked because the backlog or execution-contract previews are missing." `
            -Artifacts $artifacts `
            -Diagnostics $diagnostics.ToArray() `
            -TruthBoundary $boundary `
            -NextSteps $nextSteps
    }

    $diagnostics.Add("scrape gap rows=$($scrapeGap.data.row_count)") | Out-Null
    $diagnostics.Add("scrape backlog rows=$($scrapeBacklog.data.summary.implemented_and_harvestable_now_count)") | Out-Null
    $diagnostics.Add("still missing lanes=$($scrapeBacklog.data.summary.still_missing_count)") | Out-Null
    $diagnostics.Add("selected overnight tasks=$($queueBacklog.data.summary.selected_top_count)") | Out-Null
    $diagnostics.Add("estimated cycles=$($executionContract.data.summary.estimated_cycles)") | Out-Null
    $diagnostics.Add("structured scrape jobs=$($scrapeWave.data.summary.structured_job_count)") | Out-Null
    $diagnostics.Add("page scrape jobs=$($scrapeWave.data.summary.page_job_count)") | Out-Null
    $diagnostics.Add("idle state=$($idleStatus.data.idle_state)") | Out-Null
    $diagnostics.Add("idle next action=$($idleStatus.data.next_suggested_action)") | Out-Null
    $diagnostics.Add("pending reconciliation state=$($pendingReconciliation.data.summary.reconciliation_state)") | Out-Null
    $diagnostics.Add("pending reconciliation stale preview=$($pendingReconciliation.data.summary.stale_preview_detected)") | Out-Null
    $diagnostics.Add("worker launch gap state=$($workerLaunchGap.data.summary.launch_gap_state)") | Out-Null
    $diagnostics.Add("worker launch gap detected=$($workerLaunchGap.data.summary.launch_gap_detected)") | Out-Null
    $diagnostics.Add("procurement freshness state=$($procurementFreshness.data.summary.freshness_state)") | Out-Null
    $diagnostics.Add("procurement stale state superseded=$($procurementFreshness.data.summary.stale_state_superseded_by_board)") | Out-Null
    $diagnostics.Add("download audit accounted=$($downloadLocationAudit.data.summary.all_wanted_files_accounted_for)") | Out-Null
    $diagnostics.Add("download audit in process=$($downloadLocationAudit.data.summary.in_process_count)") | Out-Null
    $diagnostics.Add("stale part live transfers=$($stalePartAudit.data.summary.live_transfer_count)") | Out-Null
    $diagnostics.Add("stale part residue count=$($stalePartAudit.data.summary.stale_residue_count)") | Out-Null
    $diagnostics.Add("post-tail unlock ready steps=$($postTailUnlock.data.summary.ready_step_count)") | Out-Null
    $diagnostics.Add("post-tail unlock blocked steps=$($postTailUnlock.data.summary.blocked_step_count)") | Out-Null
    $diagnostics.Add("tail reconciliation state=$($procurementTailReconciliation.data.summary.reconciliation_state)") | Out-Null
    $diagnostics.Add("tail raw process count=$($procurementTailReconciliation.data.summary.raw_process_table_active_count)") | Out-Null
    $diagnostics.Add("tail growth state=$($procurementTailGrowth.data.summary.growth_state)") | Out-Null
    $diagnostics.Add("tail growth bytes/sec=$($procurementTailGrowth.data.summary.aggregate_bytes_per_second)") | Out-Null
    $diagnostics.Add("headroom guard state=$($procurementHeadroom.data.summary.guard_state)") | Out-Null
    $diagnostics.Add("headroom free GiB=$($procurementHeadroom.data.summary.free_gib)") | Out-Null
    $diagnostics.Add("tail space drift state=$($procurementTailSpaceDrift.data.summary.drift_state)") | Out-Null
    $diagnostics.Add("tail source pressure state=$($procurementTailSourcePressure.data.summary.pressure_state)") | Out-Null
    $diagnostics.Add("tail log registry state=$($procurementTailLogProgressRegistry.data.summary.registry_state)") | Out-Null
    $diagnostics.Add("tail completion margin state=$($procurementTailCompletionMargin.data.summary.completion_state)") | Out-Null
    $diagnostics.Add("space recovery target state=$($procurementSpaceRecoveryTarget.data.summary.target_state)") | Out-Null
    $diagnostics.Add("space recovery ranked GiB=$($procurementSpaceRecoveryCandidates.data.summary.total_ranked_reclaim_gib)") | Out-Null
    $diagnostics.Add("space recovery execution state=$($procurementSpaceRecoveryExecutionBatch.data.summary.execution_state)") | Out-Null
    $diagnostics.Add("space recovery safety state=$($procurementSpaceRecoverySafetyRegister.data.summary.safety_state)") | Out-Null
    $diagnostics.Add("tail fill risk state=$($procurementTailFillRisk.data.summary.risk_state)") | Out-Null
    $diagnostics.Add("space recovery trigger state=$($procurementSpaceRecoveryTrigger.data.summary.trigger_state)") | Out-Null
    $diagnostics.Add("space recovery gap drift state=$($procurementSpaceRecoveryGapDrift.data.summary.drift_state)") | Out-Null
    $diagnostics.Add("space recovery coverage state=$($procurementSpaceRecoveryCoverage.data.summary.coverage_state)") | Out-Null
    $diagnostics.Add("space recovery zero-gap coverage=$($procurementSpaceRecoveryCoverage.data.summary.zero_gap_coverage_fraction)") | Out-Null
    $diagnostics.Add("recovery intervention priority state=$($procurementRecoveryInterventionPriority.data.summary.priority_state)") | Out-Null
    $diagnostics.Add("recovery escalation lane state=$($procurementRecoveryEscalationLane.data.summary.escalation_state)") | Out-Null
    $diagnostics.Add("recovery escalation additional ranked GiB=$($procurementRecoveryEscalationLane.data.summary.additional_ranked_reclaim_gib)") | Out-Null
    $diagnostics.Add("recovery concentration state=$($procurementSpaceRecoveryConcentration.data.summary.concentration_state)") | Out-Null
    $diagnostics.Add("recovery concentration top1 fraction=$($procurementSpaceRecoveryConcentration.data.summary.top1_reclaim_fraction)") | Out-Null
    $diagnostics.Add("recovery shortfall bridge state=$($procurementRecoveryShortfallBridge.data.summary.bridge_state)") | Out-Null
    $diagnostics.Add("recovery shortfall bridge review-required count=$($procurementRecoveryShortfallBridge.data.summary.review_required_category_count)") | Out-Null
    $diagnostics.Add("recovery lane fragility state=$($procurementRecoveryLaneFragility.data.summary.fragility_state)") | Out-Null
    $diagnostics.Add("recovery lane fragility lead candidate=$($procurementRecoveryLaneFragility.data.summary.lead_candidate_filename)") | Out-Null
    $diagnostics.Add("broader search trigger state=$($procurementBroaderSearchTrigger.data.summary.trigger_state)") | Out-Null
    $diagnostics.Add("broader search bridge state=$($procurementBroaderSearchTrigger.data.summary.bridge_state)") | Out-Null
    $diagnostics.Add("wave added tasks=$($waveAdvance.data.added_task_count)") | Out-Null
    $diagnostics.Add("wave dispatched count=$($waveAdvance.data.dispatched_count)") | Out-Null
    $diagnostics.Add("wave catalog exhausted=$($waveAdvance.data.catalog_exhausted)") | Out-Null

    return New-RecipeResult `
        -RecipeId "overnight-run-readiness" `
        -Title "Overnight Run Readiness" `
        -Status "supported" `
        -Summary "The overnight execution lane has a queue slice, scrape-gap classification, idle/drained visibility, and a safe sequential wave-advance path ready for operator review." `
        -Artifacts $artifacts `
        -Diagnostics $diagnostics.ToArray() `
        -TruthBoundary $boundary `
        -NextSteps $nextSteps
}

function Get-AvailableRecipes {
    return @(
        [pscustomobject]@{ recipe_id = "acceptance-review"; status = "supported"; title = "Acceptance Review" },
        [pscustomobject]@{ recipe_id = "packet-triage"; status = "weak"; title = "Packet Triage" },
        [pscustomobject]@{ recipe_id = "benchmark-review"; status = "supported"; title = "Benchmark Review" },
        [pscustomobject]@{ recipe_id = "soak-readiness"; status = "blocked"; title = "Soak Readiness" },
        [pscustomobject]@{ recipe_id = "onboarding"; status = "supported"; title = "Onboarding Review" },
        [pscustomobject]@{ recipe_id = "training-set-builder"; status = "supported"; title = "Training Set Builder" },
        [pscustomobject]@{ recipe_id = "release-grade-review"; status = "blocked"; title = "Release Grade Review" },
        [pscustomobject]@{ recipe_id = "external-dataset-assessment"; status = "supported"; title = "External Dataset Assessment" },
        [pscustomobject]@{ recipe_id = "overnight-run-readiness"; status = "supported"; title = "Overnight Run Readiness" }
    )
}

function Render-RecipeText {
    param([object]$Result)

    $lines = @(
        "Recipe: $($Result.recipe_id)",
        "Title: $($Result.title)",
        "Status: $($Result.status)",
        "Summary: $($Result.summary)",
        "Artifacts:"
    )
    foreach ($artifact in @($Result.artifacts)) {
        $lines += "  - $artifact"
    }
    $lines += "Diagnostics:"
    foreach ($diagnostic in @($Result.diagnostics)) {
        $lines += "  - $diagnostic"
    }
    $lines += "Truth boundary:"
    foreach ($item in @($Result.truth_boundary)) {
        $lines += "  - $item"
    }
    $lines += "Next steps:"
    foreach ($step in @($Result.next_steps)) {
        $lines += "  - $step"
    }
    return ($lines -join [Environment]::NewLine)
}

$result =
    switch ($Recipe) {
        "acceptance-review" { Invoke-AcceptanceReview }
        "packet-triage" { Invoke-PacketTriage }
        "benchmark-review" { Invoke-BenchmarkReview }
        "soak-readiness" { Invoke-SoakReadiness }
        "onboarding" { Invoke-Onboarding }
        "training-set-builder" { Invoke-TrainingSetBuilder }
        "release-grade-review" { Invoke-ReleaseGradeReview }
        "external-dataset-assessment" { Invoke-ExternalDatasetAssessment }
        "overnight-run-readiness" { Invoke-OvernightRunReadiness }
        "list" {
            [pscustomobject]@{
                recipes = Get-AvailableRecipes
            }
        }
    }

if ($AsJson) {
    $result | ConvertTo-Json -Depth 8
}
elseif ($Recipe -eq "list") {
    foreach ($recipeRow in $result.recipes) {
        Write-Output ("{0} [{1}] - {2}" -f $recipeRow.recipe_id, $recipeRow.status, $recipeRow.title)
    }
}
else {
    Write-Output (Render-RecipeText -Result $result)
}
