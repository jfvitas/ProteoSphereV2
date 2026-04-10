param(
    [ValidateSet("start", "stop", "status", "run-once", "loop", "queue", "library", "runtime", "state")]
    [string]$Mode = "status",
    [int]$PollSeconds = 60,
    [int]$FullSweepEvery = 10,
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeDir = Join-Path $RepoRoot "artifacts\runtime"
$LogPath = Join-Path $RuntimeDir "supervisor.log"
$PidPath = Join-Path $RuntimeDir "supervisor.pid"
$HeartbeatPath = Join-Path $RuntimeDir "supervisor.heartbeat.json"
$HeartbeatHistoryPath = Join-Path $RuntimeDir "supervisor.heartbeat.history.jsonl"
$SoakLedgerPath = Join-Path $RuntimeDir "soak_ledger.jsonl"
$SoakSummaryScriptPath = Join-Path $RepoRoot "scripts\summarize_soak_ledger.py"
$SoakAnomalyScriptPath = Join-Path $RepoRoot "scripts\analyze_soak_anomalies.py"
$TruthBoundaryAuditScriptPath = Join-Path $RepoRoot "scripts\audit_truth_boundaries.py"
$OperationalReadinessSnapshotScriptPath = Join-Path $RepoRoot "scripts\build_operational_readiness_snapshot.py"
$SoakRollupReportPath = Join-Path $RepoRoot "docs\reports\p22_soak_rollup.md"
$SoakAnomalyReportPath = Join-Path $RepoRoot "docs\reports\p22_soak_anomalies.md"
$TruthBoundaryAuditReportPath = Join-Path $RepoRoot "docs\reports\p22_truth_boundary_audit.md"
$OperationalReadinessSnapshotReportPath = Join-Path $RepoRoot "docs\reports\p22_operational_readiness_snapshot.md"
$HeartbeatStaleAfterSeconds = 300
$StopPath = Join-Path $RepoRoot "artifacts\status\STOP"
$QueuePath = Join-Path $RepoRoot "tasks\task_queue.json"
$OrchestratorStatePath = Join-Path $RepoRoot "artifacts\status\orchestrator_state.json"
$PacketLibraryLatestPath = Join-Path $RepoRoot "data\packages\LATEST.json"
$PacketDeficitDashboardPath = Join-Path $RepoRoot "artifacts\status\packet_deficit_dashboard.json"
$LibraryStatusPaths = @(
    (Join-Path $RepoRoot "artifacts\status\P6-T001.json"),
    (Join-Path $RepoRoot "artifacts\status\P6-T003.json")
)
$BenchmarkResultsDir = Join-Path $RepoRoot "runs\real_data_benchmark\full_results"
$BenchmarkReadmePath = Join-Path $BenchmarkResultsDir "README.md"
$BenchmarkRunSummaryPath = Join-Path $BenchmarkResultsDir "run_summary.json"
$BenchmarkSummaryPath = Join-Path $BenchmarkResultsDir "summary.json"
$BenchmarkCheckpointSummaryPath = Join-Path $BenchmarkResultsDir "checkpoint_summary.json"
$BenchmarkRunManifestPath = Join-Path $BenchmarkResultsDir "run_manifest.json"
$BenchmarkLiveInputsPath = Join-Path $BenchmarkResultsDir "live_inputs.json"
$BenchmarkSchemaPath = Join-Path $BenchmarkResultsDir "schema.json"
$LibraryMaterializedPaths = @(
    (Join-Path $BenchmarkResultsDir "summary_library.json"),
    (Join-Path $BenchmarkResultsDir "summary_library.latest.json"),
    (Join-Path $RepoRoot "artifacts\library\summary_library.json"),
    (Join-Path $RepoRoot "artifacts\library\summary_library.latest.json"),
    (Join-Path $RepoRoot "artifacts\status\summary_library.json"),
    (Join-Path $RepoRoot "artifacts\status\structure_unit_summary_library.json"),
    (Join-Path $RepoRoot "artifacts\status\intact_local_summary_library.json"),
    (Join-Path $RepoRoot "artifacts\status\reactome_local_summary_library.json"),
    (Join-Path $RepoRoot "artifacts\summary_library.json")
)

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null

function Read-JsonPayload {
    param(
        [string]$Path,
        $Default = $null
    )

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            exists = $false
            path = $Path
            data = $Default
            error = "missing input: $Path"
        }
    }

    try {
        $payload = Get-Content -Path $Path -Raw | ConvertFrom-Json
        return [pscustomobject]@{
            exists = $true
            path = $Path
            data = $payload
            error = $null
        }
    }
    catch {
        return [pscustomobject]@{
            exists = $true
            path = $Path
            data = $Default
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
        $payload = Get-Content -Path $Path -Raw
        return [pscustomobject]@{
            exists = $true
            path = $Path
            data = $payload
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

function Convert-ToCompactText {
    param([object]$Value)

    if ($null -eq $Value) {
        return "null"
    }
    if ($Value -is [string]) {
        return $Value
    }
    if ($Value -is [bool]) {
        return $Value.ToString().ToLower()
    }
    if ($Value -is [System.Collections.IDictionary] -or $Value -is [System.Collections.IEnumerable]) {
        return ($Value | ConvertTo-Json -Depth 8 -Compress)
    }
    return [string]$Value
}

function Write-Section {
    param(
        [string]$Title,
        [object]$Value
    )

    Write-Output $Title
    if ($Value -is [System.Collections.IDictionary] -or $Value.PSObject.Properties.Count -gt 0) {
        foreach ($property in $Value.PSObject.Properties) {
            Write-Output ("  {0}: {1}" -f $property.Name, (Convert-ToCompactText $property.Value))
        }
    }
    else {
        Write-Output ("  {0}" -f (Convert-ToCompactText $Value))
    }
}

function Get-SupervisorPid {
    if (-not (Test-Path $PidPath)) {
        return $null
    }
    $raw = (Get-Content $PidPath -Raw).Trim()
    if (-not $raw) {
        return $null
    }
    return [int]$raw
}

function Test-SupervisorRunning {
    $supervisorPid = Get-SupervisorPid
    if ($null -eq $supervisorPid) {
        return $false
    }
    $process = Get-Process -Id $supervisorPid -ErrorAction SilentlyContinue
    return $null -ne $process
}

function Ensure-SupervisorPidFile {
    if (-not (Test-Path $PidPath)) {
        Set-Content -Path $PidPath -Value $PID
        return
    }

    $existingPid = $null
    try {
        $existingPid = [int]((Get-Content $PidPath -Raw).Trim())
    }
    catch {
        $existingPid = $null
    }

    if ($existingPid -ne $PID) {
        Set-Content -Path $PidPath -Value $PID
    }
}

function Write-SupervisorHeartbeat {
    param(
        [int]$Iteration,
        [string]$Phase = "cycle"
    )

    $payload = [pscustomobject]@{
        supervisor_pid = $PID
        iteration = $Iteration
        phase = $Phase
        last_heartbeat_at = (Get-Date).ToUniversalTime().ToString("o")
        stale_after_seconds = $HeartbeatStaleAfterSeconds
        source = "supervisor_loop"
    }

    $payload | ConvertTo-Json -Depth 6 | Set-Content -Path $HeartbeatPath -Encoding utf8
    $payload | ConvertTo-Json -Depth 6 -Compress | Add-Content -Path $HeartbeatHistoryPath -Encoding utf8
}

function Get-SupervisorHeartbeatState {
    $heartbeatPayload = Read-JsonPayload -Path $HeartbeatPath -Default @{}
    $observedAt = (Get-Date).ToUniversalTime().ToString("o")
    $state = [pscustomobject]@{
        path = $heartbeatPayload.path
        exists = $heartbeatPayload.exists
        error = $heartbeatPayload.error
        status = "unavailable"
        observed_at = $observedAt
        last_heartbeat_at = $null
        age_seconds = $null
        stale_after_seconds = $HeartbeatStaleAfterSeconds
        is_stale = $null
        supervisor_pid = $null
        iteration = $null
        phase = $null
        source = $null
    }

    if (-not $heartbeatPayload.exists) {
        return $state
    }

    if ($null -eq $heartbeatPayload.data) {
        if (-not $state.error) {
            $state.error = "heartbeat payload unavailable"
        }
        return $state
    }

    $payload = $heartbeatPayload.data
    $heartbeatText = $null
    foreach ($candidateName in @("last_heartbeat_at", "heartbeat_at", "observed_at")) {
        if ($payload.PSObject.Properties.Name -contains $candidateName) {
            $candidateValue = [string]$payload.$candidateName
            if ($candidateValue) {
                $heartbeatText = $candidateValue
                break
            }
        }
    }

    if (-not $heartbeatText) {
        $state.error = "heartbeat timestamp missing"
        return $state
    }

    try {
        $heartbeatTimestamp = [datetimeoffset]::Parse($heartbeatText)
    }
    catch {
        $state.error = "heartbeat timestamp unreadable: $($_.Exception.Message)"
        return $state
    }

    $ageSeconds = [int][math]::Floor(([datetimeoffset]::UtcNow - $heartbeatTimestamp.ToUniversalTime()).TotalSeconds)
    if ($ageSeconds -lt 0) {
        $ageSeconds = 0
    }

    $state.last_heartbeat_at = $heartbeatTimestamp.ToUniversalTime().ToString("o")
    $state.age_seconds = $ageSeconds
    $state.is_stale = $ageSeconds -gt $HeartbeatStaleAfterSeconds
    $state.status = if ($state.is_stale) { "stale" } else { "healthy" }

    if ($payload.PSObject.Properties.Name -contains "supervisor_pid") {
        $state.supervisor_pid = [int]$payload.supervisor_pid
    }
    if ($payload.PSObject.Properties.Name -contains "iteration") {
        $state.iteration = [int]$payload.iteration
    }
    if ($payload.PSObject.Properties.Name -contains "phase") {
        $state.phase = [string]$payload.phase
    }
    if ($payload.PSObject.Properties.Name -contains "source") {
        $state.source = [string]$payload.source
    }

    return $state
}

function Get-SupervisorHeartbeatHistoryState {
    $state = [pscustomobject]@{
        path = $HeartbeatHistoryPath
        exists = Test-Path $HeartbeatHistoryPath
        error = $null
        entry_count = 0
        last_heartbeat_at = $null
    }

    if (-not $state.exists) {
        return $state
    }

    try {
        $lines = @(Get-Content -Path $HeartbeatHistoryPath | Where-Object { $_.Trim() })
        $state.entry_count = $lines.Count
        if ($lines.Count -gt 0) {
            $lastEntry = $lines[-1] | ConvertFrom-Json
            if ($lastEntry.PSObject.Properties.Name -contains "last_heartbeat_at") {
                $state.last_heartbeat_at = [string]$lastEntry.last_heartbeat_at
            }
        }
    }
    catch {
        $state.error = $_.Exception.Message
    }

    return $state
}

function Get-QueueState {
    $queuePayload = Read-JsonPayload -Path $QueuePath -Default @()
    $tasks = @($queuePayload.data)
    $statusCounts = @{}
    $readyTasks = @()
    $runningTasks = @()
    $dispatchedTasks = @()
    $blockedTasks = @()
    $completedTasks = @()

    foreach ($task in $tasks) {
        if ($null -eq $task) {
            continue
        }
        $status = [string]$task.status
        if (-not $status) {
            $status = "unknown"
        }
        $statusCounts[$status] = 1 + [int]($statusCounts[$status] | ForEach-Object { $_ })
        switch ($status) {
            "ready" { $readyTasks += [string]$task.id }
            "running" { $runningTasks += [string]$task.id }
            "dispatched" { $dispatchedTasks += [string]$task.id }
            "blocked" { $blockedTasks += [string]$task.id }
            "done" { $completedTasks += [string]$task.id }
            "reviewed" { $completedTasks += [string]$task.id }
        }
    }

    return [pscustomobject]@{
        path = $QueuePath
        exists = $queuePayload.exists
        error = $queuePayload.error
        task_count = $tasks.Count
        status_counts = $statusCounts
        ready_task_ids = @($readyTasks)
        running_task_ids = @($runningTasks)
        dispatched_task_ids = @($dispatchedTasks)
        blocked_task_ids = @($blockedTasks)
        completed_task_ids = @($completedTasks)
    }
}

function Get-LibraryState {
    $schemaStatusPayload = Read-JsonPayload -Path $LibraryStatusPaths[0]
    $builderStatusPayload = Read-JsonPayload -Path $LibraryStatusPaths[1]
    $libraryMaterialized = $null
    foreach ($candidatePath in $LibraryMaterializedPaths) {
        if (Test-Path $candidatePath) {
            $libraryMaterialized = Read-JsonPayload -Path $candidatePath
            break
        }
    }

    $materializedRecordCount = 0
    $materializedRecordTypes = @{}
    $materializedLibraryId = $null
    $materializedSourceManifestId = $null
    if ($null -ne $libraryMaterialized -and $libraryMaterialized.exists -and $null -ne $libraryMaterialized.data) {
        $payload = $libraryMaterialized.data
        $records = @()
        if ($payload.PSObject.Properties.Name -contains "records") {
            $records = @($payload.records)
        }
        elseif ($payload.PSObject.Properties.Name -contains "summary_records") {
            $records = @($payload.summary_records)
        }
        $materializedRecordCount = $records.Count
        foreach ($record in $records) {
            if ($null -eq $record) {
                continue
            }
            $recordType = [string]$record.record_type
            if (-not $recordType) {
                $recordType = [string]$record.type
            }
            if (-not $recordType) {
                $recordType = "unknown"
            }
            $materializedRecordTypes[$recordType] = 1 + [int]($materializedRecordTypes[$recordType] | ForEach-Object { $_ })
        }
        if ($payload.PSObject.Properties.Name -contains "library_id") {
            $materializedLibraryId = [string]$payload.library_id
        }
        if ($payload.PSObject.Properties.Name -contains "source_manifest_id") {
            $materializedSourceManifestId = [string]$payload.source_manifest_id
        }
    }

    $schemaDone = $schemaStatusPayload.exists -and $null -ne $schemaStatusPayload.data -and [string]$schemaStatusPayload.data.status -eq "done"
    $builderDone = $builderStatusPayload.exists -and $null -ne $builderStatusPayload.data -and [string]$builderStatusPayload.data.status -eq "done"

    return [pscustomobject]@{
        status_files = [pscustomobject]@{
            schema = [pscustomobject]@{
                path = $schemaStatusPayload.path
                exists = $schemaStatusPayload.exists
                error = $schemaStatusPayload.error
                status = if ($schemaStatusPayload.data) { [string]$schemaStatusPayload.data.status } else { $null }
                completed_at = if ($schemaStatusPayload.data) { [string]$schemaStatusPayload.data.completed_at } else { $null }
                summary = if ($schemaStatusPayload.data) { [string]$schemaStatusPayload.data.summary } else { $null }
            }
            builder = [pscustomobject]@{
                path = $builderStatusPayload.path
                exists = $builderStatusPayload.exists
                error = $builderStatusPayload.error
                status = if ($builderStatusPayload.data) { [string]$builderStatusPayload.data.status } else { $null }
                completed_at = if ($builderStatusPayload.data) { [string]$builderStatusPayload.data.completed_at } else { $null }
                summary = if ($builderStatusPayload.data) { [string]$builderStatusPayload.data.summary } else { $null }
            }
        }
        materialized = $null -ne $libraryMaterialized -and $libraryMaterialized.exists -and $null -ne $libraryMaterialized.data
        materialized_path = if ($null -ne $libraryMaterialized) { $libraryMaterialized.path } else { $null }
        materialized_error = if ($null -ne $libraryMaterialized) { $libraryMaterialized.error } else { $null }
        materialized_library_id = $materializedLibraryId
        materialized_source_manifest_id = $materializedSourceManifestId
        materialized_record_count = $materializedRecordCount
        materialized_record_types = $materializedRecordTypes
        schema_task_done = $schemaDone
        builder_task_done = $builderDone
        ready_for_materialization = $schemaDone -and $builderDone
    }
}

function Add-UniqueText {
    param(
        [System.Collections.Generic.List[string]]$List,
        [object]$Value
    )

    if ($null -eq $Value) {
        return
    }
    $text = [string]$Value
    if (-not $text) {
        return
    }
    if (-not $List.Contains($text)) {
        $null = $List.Add($text)
    }
}

function Get-BenchmarkState {
    $readmePayload = Read-TextPayload -Path $BenchmarkReadmePath
    $summaryPayload = Read-JsonPayload -Path $BenchmarkSummaryPath -Default @{}
    $runSummaryPayload = Read-JsonPayload -Path $BenchmarkRunSummaryPath -Default @{}
    $checkpointSummaryPayload = Read-JsonPayload -Path $BenchmarkCheckpointSummaryPath -Default @{}
    $runManifestPayload = Read-JsonPayload -Path $BenchmarkRunManifestPath -Default @{}
    $liveInputsPayload = Read-JsonPayload -Path $BenchmarkLiveInputsPath -Default @{}
    $schemaPayload = Read-JsonPayload -Path $BenchmarkSchemaPath -Default @{}

    $releaseBlockers = New-Object 'System.Collections.Generic.List[string]'
    $limitationBlockers = New-Object 'System.Collections.Generic.List[string]'
    $resultStatus = $null
    $benchmarkTask = $null
    $cohortStatus = $null
    $runtimeSurface = $null
    $selectedAccessionCount = $null
    $splitCounts = @{}
    $firstRun = $null
    $resumedRun = $null

    if ($null -ne $runSummaryPayload.data) {
        $payload = $runSummaryPayload.data
        if ($payload.PSObject.Properties.Name -contains "benchmark_task") {
            $benchmarkTask = [string]$payload.benchmark_task
        }
        if ($payload.PSObject.Properties.Name -contains "cohort_status") {
            $cohortStatus = [string]$payload.cohort_status
        }
        if ($payload.PSObject.Properties.Name -contains "runtime_surface") {
            $runtimeSurface = [string]$payload.runtime_surface
        }
        if ($payload.PSObject.Properties.Name -contains "selected_accession_count") {
            $selectedAccessionCount = [int]$payload.selected_accession_count
        }
        if ($payload.PSObject.Properties.Name -contains "split_counts") {
            $splitCounts = $payload.split_counts
        }
        if ($payload.PSObject.Properties.Name -contains "first_run") {
            $firstRun = $payload.first_run
        }
        if ($payload.PSObject.Properties.Name -contains "resumed_run") {
            $resumedRun = $payload.resumed_run
        }
        if ($payload.PSObject.Properties.Name -contains "remaining_gaps") {
            foreach ($gap in @($payload.remaining_gaps)) {
                Add-UniqueText -List $releaseBlockers -Value $gap
            }
        }
        if ($payload.PSObject.Properties.Name -contains "limitations") {
            foreach ($limitation in @($payload.limitations)) {
                Add-UniqueText -List $limitationBlockers -Value $limitation
            }
        }
    }
    if (-not $runSummaryPayload.exists) {
        Add-UniqueText -List $releaseBlockers -Value $runSummaryPayload.error
    }

    if ($null -ne $summaryPayload.data -and $summaryPayload.data.PSObject.Properties.Name -contains "status") {
        $resultStatus = [string]$summaryPayload.data.status
    }
    elseif ($null -ne $runSummaryPayload.data) {
        $payload = $runSummaryPayload.data
        if ($payload.PSObject.Properties.Name -contains "final_status") {
            $resultStatus = [string]$payload.final_status
        }
        elseif ($payload.PSObject.Properties.Name -contains "status") {
            $resultStatus = [string]$payload.status
        }
    }

    if ($null -ne $checkpointSummaryPayload.data) {
        $payload = $checkpointSummaryPayload.data
        if ($payload.PSObject.Properties.Name -contains "blocker_categories") {
            foreach ($category in @($payload.blocker_categories)) {
                Add-UniqueText -List $releaseBlockers -Value $category
            }
        }
        if ($payload.PSObject.Properties.Name -contains "limitations") {
            foreach ($limitation in @($payload.limitations)) {
                Add-UniqueText -List $limitationBlockers -Value $limitation
            }
        }
    }
    if (-not $checkpointSummaryPayload.exists) {
        Add-UniqueText -List $releaseBlockers -Value $checkpointSummaryPayload.error
    }

    if (-not $summaryPayload.exists) {
        Add-UniqueText -List $releaseBlockers -Value $summaryPayload.error
    }
    if (-not $runManifestPayload.exists) {
        Add-UniqueText -List $releaseBlockers -Value $runManifestPayload.error
    }
    if (-not $readmePayload.exists) {
        Add-UniqueText -List $releaseBlockers -Value $readmePayload.error
    }
    if (-not $liveInputsPayload.exists) {
        Add-UniqueText -List $releaseBlockers -Value $liveInputsPayload.error
    }
    if (-not $schemaPayload.exists) {
        Add-UniqueText -List $releaseBlockers -Value $schemaPayload.error
    }

    $operatorReleaseReady = $null
    $benchmarkReleaseBarClosed = $null
    if ($summaryPayload.data -and $summaryPayload.data.PSObject.Properties.Name -contains "release_target") {
        if ($summaryPayload.data.release_target.PSObject.Properties.Name -contains "operator_release_ready") {
            $operatorReleaseReady = [bool]$summaryPayload.data.release_target.operator_release_ready
        }
        if ($summaryPayload.data.release_target.PSObject.Properties.Name -contains "benchmark_release_bar_closed") {
            $benchmarkReleaseBarClosed = [bool]$summaryPayload.data.release_target.benchmark_release_bar_closed
        }
    }

    $releaseGradeStatus = if ($benchmarkReleaseBarClosed -eq $true -and $operatorReleaseReady -eq $false) {
        "closed_not_release_ready"
    }
    elseif ($releaseBlockers.Count -gt 0 -or $limitationBlockers.Count -gt 0) {
        "blocked"
    }
    elseif ($resultStatus) {
        $resultStatus
    }
    else {
        "unavailable"
    }

    $readyForRelease = if ($null -ne $operatorReleaseReady) {
        $operatorReleaseReady
    }
    else {
        ($releaseBlockers.Count -eq 0 -and $limitationBlockers.Count -eq 0 -and $resultStatus -eq "completed")
    }

    return [pscustomobject]@{
        exists = $runSummaryPayload.exists -or $checkpointSummaryPayload.exists -or $readmePayload.exists
        results_dir = $BenchmarkResultsDir
        readme = [pscustomobject]@{
            path = $readmePayload.path
            exists = $readmePayload.exists
            error = $readmePayload.error
            status = if ($readmePayload.exists -and $readmePayload.data -match 'Status:\s*`([^`]+)`') { $Matches[1] } else { $null }
        }
        run_summary = [pscustomobject]@{
            path = $runSummaryPayload.path
            exists = $runSummaryPayload.exists
            error = $runSummaryPayload.error
            status = if ($runSummaryPayload.data) { [string]$runSummaryPayload.data.status } else { $null }
        }
        checkpoint_summary = [pscustomobject]@{
            path = $checkpointSummaryPayload.path
            exists = $checkpointSummaryPayload.exists
            error = $checkpointSummaryPayload.error
            status = if ($checkpointSummaryPayload.data -and $checkpointSummaryPayload.data.PSObject.Properties.Name -contains "status") {
                [string]$checkpointSummaryPayload.data.status
            } else {
                $null
            }
        }
        benchmark_summary = [pscustomobject]@{
            path = $summaryPayload.path
            exists = $summaryPayload.exists
            error = $summaryPayload.error
            status = if ($summaryPayload.data -and $summaryPayload.data.PSObject.Properties.Name -contains "status") {
                [string]$summaryPayload.data.status
            } else {
                $null
            }
        }
        benchmark_task = $benchmarkTask
        cohort_status = $cohortStatus
        runtime_surface = $runtimeSurface
        selected_accession_count = $selectedAccessionCount
        split_counts = $splitCounts
        first_run = $firstRun
        resumed_run = $resumedRun
        run_manifest_path = $runManifestPayload.path
        live_inputs_path = $liveInputsPayload.path
        schema_path = $schemaPayload.path
        completion_status = $resultStatus
        release_grade_status = $releaseGradeStatus
        release_grade_blockers = @($releaseBlockers)
        limitation_blockers = @($limitationBlockers)
        release_ready = $readyForRelease
        benchmark_release_bar_closed = $benchmarkReleaseBarClosed
        truth_boundary = if ($schemaPayload.data -and $schemaPayload.data.PSObject.Properties.Name -contains "truth_boundary") {
            $schemaPayload.data.truth_boundary
        } else {
            $null
        }
    }
}

function Get-RuntimeState {
    $statePayload = Read-JsonPayload -Path $OrchestratorStatePath -Default @{}
    $activeWorkers = @()
    $dispatchQueue = @()
    $reviewQueue = @()
    $completedTasks = @()
    $blockedTasks = @()
    $heartbeatState = Get-SupervisorHeartbeatState
    $heartbeatHistory = Get-SupervisorHeartbeatHistoryState
    $soakSummary = Get-SoakSummaryState
    $soakAnomaly = Get-SoakAnomalyState
    $operationalReadiness = Get-OperationalReadinessSnapshotState
    $packetLibrary = Get-PacketLibraryState
    if ($null -ne $statePayload.data) {
        if ($statePayload.data.PSObject.Properties.Name -contains "active_workers") {
            $activeWorkers = @($statePayload.data.active_workers)
        }
        if ($statePayload.data.PSObject.Properties.Name -contains "dispatch_queue") {
            $dispatchQueue = @($statePayload.data.dispatch_queue)
        }
        if ($statePayload.data.PSObject.Properties.Name -contains "review_queue") {
            $reviewQueue = @($statePayload.data.review_queue)
        }
        if ($statePayload.data.PSObject.Properties.Name -contains "completed_tasks") {
            $completedTasks = @($statePayload.data.completed_tasks)
        }
        if ($statePayload.data.PSObject.Properties.Name -contains "blocked_tasks") {
            $blockedTasks = @($statePayload.data.blocked_tasks)
        }
    }

    $supervisorRunning = Test-SupervisorRunning
    $supervisorPid = Get-SupervisorPid
    if ((-not $supervisorRunning) -and $heartbeatState.status -eq "healthy") {
        $supervisorRunning = $true
        if ($null -eq $supervisorPid -and $null -ne $heartbeatState.supervisor_pid) {
            $supervisorPid = $heartbeatState.supervisor_pid
        }
    }

    return [pscustomobject]@{
        supervisor_running = $supervisorRunning
        supervisor_pid = $supervisorPid
        stop_signal_present = Test-Path $StopPath
        active_worker_count = $activeWorkers.Count
        active_workers = $activeWorkers
        dispatch_queue_count = $dispatchQueue.Count
        dispatch_queue = $dispatchQueue
        review_queue_count = $reviewQueue.Count
        review_queue = $reviewQueue
        completed_task_count = $completedTasks.Count
        blocked_task_count = $blockedTasks.Count
        state_path = $statePayload.path
        state_error = $statePayload.error
        last_task_generation_ts = if ($null -ne $statePayload.data -and $statePayload.data.PSObject.Properties.Name -contains "last_task_generation_ts") {
            $statePayload.data.last_task_generation_ts
        } else {
            $null
        }
        supervisor_heartbeat = $heartbeatState
        supervisor_heartbeat_history = $heartbeatHistory
        soak_summary = $soakSummary
        soak_anomaly = $soakAnomaly
        operational_readiness = $operationalReadiness
        packet_library = $packetLibrary
        supervisor_staleness = [pscustomobject]@{
            status = $heartbeatState.status
            is_stale = $heartbeatState.is_stale
            age_seconds = $heartbeatState.age_seconds
            stale_after_seconds = $heartbeatState.stale_after_seconds
            observed_at = $heartbeatState.observed_at
            last_heartbeat_at = $heartbeatState.last_heartbeat_at
            error = $heartbeatState.error
        }
    }
}

function Get-PacketLibraryState {
    $latestPayload = Read-JsonPayload -Path $PacketLibraryLatestPath -Default @{}
    $dashboardPayload = Read-JsonPayload -Path $PacketDeficitDashboardPath -Default @{}

    $state = [pscustomobject]@{
        latest_path = $latestPayload.path
        latest_exists = $latestPayload.exists
        latest_error = $latestPayload.error
        dashboard_path = $dashboardPayload.path
        dashboard_exists = $dashboardPayload.exists
        dashboard_error = $dashboardPayload.error
        run_id = $null
        status = $null
        packet_count = 0
        complete_count = 0
        partial_count = 0
        unresolved_count = 0
        modality_deficit_counts = @{}
        source_fix_candidate_count = 0
        top_source_fix_refs = @()
    }

    if ($null -ne $latestPayload.data) {
        $payload = $latestPayload.data
        if ($payload.PSObject.Properties.Name -contains "run_id") {
            $state.run_id = [string]$payload.run_id
        }
        if ($payload.PSObject.Properties.Name -contains "status") {
            $state.status = [string]$payload.status
        }
        if ($payload.PSObject.Properties.Name -contains "packet_count") {
            $state.packet_count = [int]$payload.packet_count
        }
        if ($payload.PSObject.Properties.Name -contains "complete_count") {
            $state.complete_count = [int]$payload.complete_count
        }
        if ($payload.PSObject.Properties.Name -contains "partial_count") {
            $state.partial_count = [int]$payload.partial_count
        }
        if ($payload.PSObject.Properties.Name -contains "unresolved_count") {
            $state.unresolved_count = [int]$payload.unresolved_count
        }
    }

    if ($null -ne $dashboardPayload.data) {
        $payload = $dashboardPayload.data
        if ($payload.PSObject.Properties.Name -contains "summary") {
            $summary = $payload.summary
            if ($summary.PSObject.Properties.Name -contains "modality_deficit_counts") {
                $state.modality_deficit_counts = $summary.modality_deficit_counts
            }
            if ($summary.PSObject.Properties.Name -contains "source_fix_candidate_count") {
                $state.source_fix_candidate_count = [int]$summary.source_fix_candidate_count
            }
            if ($summary.PSObject.Properties.Name -contains "highest_leverage_source_fixes") {
                $state.top_source_fix_refs = @(
                    $summary.highest_leverage_source_fixes |
                        Select-Object -First 5 |
                        ForEach-Object { [string]$_.source_ref }
                )
            }
        }
    }

    return $state
}

function Get-OperationalReadinessSnapshotState {
    $state = [pscustomobject]@{
        path = $OperationalReadinessSnapshotReportPath
        exists = Test-Path $OperationalReadinessSnapshotReportPath
        script_path = $OperationalReadinessSnapshotScriptPath
        script_exists = Test-Path $OperationalReadinessSnapshotScriptPath
        error = $null
        generated_at = $null
        supervisor = $null
        soak_summary = $null
        soak_anomaly = $null
        queue_drift = $null
        truth_audit = $null
        benchmark = $null
        release_gate = $null
    }

    if (-not $state.script_exists) {
        $state.error = "missing readiness snapshot script: $OperationalReadinessSnapshotScriptPath"
        return $state
    }

    try {
        $snapshotJson = (& python $OperationalReadinessSnapshotScriptPath `
            --queue $QueuePath `
            --state $OrchestratorStatePath `
            --heartbeat $HeartbeatPath `
            --ledger $SoakLedgerPath `
            --benchmark-summary $BenchmarkSummaryPath `
            --json) -join "`n"
        if ($LASTEXITCODE -ne 0) {
            throw "readiness snapshot command failed with exit code $LASTEXITCODE"
        }
        $snapshot = $snapshotJson | ConvertFrom-Json
        $state.generated_at = if ($snapshot.PSObject.Properties.Name -contains "generated_at") {
            [string]$snapshot.generated_at
        } else {
            $null
        }
        $state.supervisor = if ($snapshot.PSObject.Properties.Name -contains "supervisor") {
            $snapshot.supervisor
        } else {
            $null
        }
        $state.soak_summary = if ($snapshot.PSObject.Properties.Name -contains "soak_summary") {
            $snapshot.soak_summary
        } else {
            $null
        }
        $state.soak_anomaly = if ($snapshot.PSObject.Properties.Name -contains "soak_anomaly") {
            $snapshot.soak_anomaly
        } else {
            $null
        }
        $state.queue_drift = if ($snapshot.PSObject.Properties.Name -contains "queue_drift") {
            $snapshot.queue_drift
        } else {
            $null
        }
        $state.truth_audit = if ($snapshot.PSObject.Properties.Name -contains "truth_audit") {
            $snapshot.truth_audit
        } else {
            $null
        }
        $state.benchmark = if ($snapshot.PSObject.Properties.Name -contains "benchmark") {
            $snapshot.benchmark
        } else {
            $null
        }
        $state.release_gate = if ($snapshot.PSObject.Properties.Name -contains "release_gate") {
            $snapshot.release_gate
        } else {
            $null
        }
    }
    catch {
        $state.error = $_.Exception.Message
    }

    return $state
}

function Get-SoakSummaryState {
    $state = [pscustomobject]@{
        path = $SoakLedgerPath
        exists = Test-Path $SoakLedgerPath
        script_path = $SoakSummaryScriptPath
        script_exists = Test-Path $SoakSummaryScriptPath
        error = $null
        entry_count = 0
        observed_window_hours = $null
        observed_window_progress_ratio = $null
        remaining_hours_to_weeklong = $null
        estimated_weeklong_completion_at = $null
        incident_count = $null
        healthy_ratio = $null
        latest_queue_counts = @{}
        last_observed_at = $null
        truth_boundary = $null
    }

    if (-not $state.exists) {
        return $state
    }
    if (-not $state.script_exists) {
        $state.error = "missing summary script: $SoakSummaryScriptPath"
        return $state
    }

    try {
        $summaryJson = (& python $SoakSummaryScriptPath --input $SoakLedgerPath --json) -join "`n"
        $summary = $summaryJson | ConvertFrom-Json
        $state.entry_count = if ($summary.PSObject.Properties.Name -contains "entry_count") {
            [int]$summary.entry_count
        } else {
            0
        }
        $state.observed_window_hours = if ($summary.PSObject.Properties.Name -contains "observed_window_hours") {
            [double]$summary.observed_window_hours
        } else {
            $null
        }
        $state.observed_window_progress_ratio = if ($summary.PSObject.Properties.Name -contains "observed_window_progress_ratio") {
            [double]$summary.observed_window_progress_ratio
        } else {
            $null
        }
        $state.remaining_hours_to_weeklong = if ($summary.PSObject.Properties.Name -contains "remaining_hours_to_weeklong") {
            [double]$summary.remaining_hours_to_weeklong
        } else {
            $null
        }
        $state.estimated_weeklong_completion_at = if ($summary.PSObject.Properties.Name -contains "estimated_weeklong_completion_at") {
            [string]$summary.estimated_weeklong_completion_at
        } else {
            $null
        }
        $state.incident_count = if ($summary.PSObject.Properties.Name -contains "incident_count") {
            [int]$summary.incident_count
        } else {
            $null
        }
        $state.healthy_ratio = if ($summary.PSObject.Properties.Name -contains "healthy_ratio") {
            [double]$summary.healthy_ratio
        } else {
            $null
        }
        $state.latest_queue_counts = if ($summary.PSObject.Properties.Name -contains "latest_queue_counts") {
            $summary.latest_queue_counts
        } else {
            @{}
        }
        $state.last_observed_at = if ($summary.PSObject.Properties.Name -contains "last_observed_at") {
            [string]$summary.last_observed_at
        } else {
            $null
        }
        $state.truth_boundary = if ($summary.PSObject.Properties.Name -contains "truth_boundary") {
            $summary.truth_boundary
        } else {
            $null
        }
    }
    catch {
        $state.error = $_.Exception.Message
    }

    return $state
}

function Get-SoakAnomalyState {
    $state = [pscustomobject]@{
        path = $SoakLedgerPath
        exists = Test-Path $SoakLedgerPath
        script_path = $SoakAnomalyScriptPath
        script_exists = Test-Path $SoakAnomalyScriptPath
        error = $null
        entry_count = 0
        incident_count = $null
        incident_status_counts = @{}
        longest_healthy_streak = $null
        current_healthy_streak = $null
        queue_transition_count = $null
        truth_boundary = $null
    }

    if (-not $state.exists) {
        return $state
    }
    if (-not $state.script_exists) {
        $state.error = "missing anomaly script: $SoakAnomalyScriptPath"
        return $state
    }

    try {
        $anomalyJson = (& python $SoakAnomalyScriptPath --input $SoakLedgerPath --json) -join "`n"
        $report = $anomalyJson | ConvertFrom-Json
        $state.entry_count = if ($report.PSObject.Properties.Name -contains "entry_count") {
            [int]$report.entry_count
        } else {
            0
        }
        $state.incident_count = if ($report.PSObject.Properties.Name -contains "incident_count") {
            [int]$report.incident_count
        } else {
            $null
        }
        $state.incident_status_counts = if ($report.PSObject.Properties.Name -contains "incident_status_counts") {
            $report.incident_status_counts
        } else {
            @{}
        }
        $state.longest_healthy_streak = if ($report.PSObject.Properties.Name -contains "longest_healthy_streak") {
            [int]$report.longest_healthy_streak
        } else {
            $null
        }
        $state.current_healthy_streak = if ($report.PSObject.Properties.Name -contains "current_healthy_streak") {
            [int]$report.current_healthy_streak
        } else {
            $null
        }
        $state.queue_transition_count = if ($report.PSObject.Properties.Name -contains "queue_transition_count") {
            [int]$report.queue_transition_count
        } else {
            $null
        }
        $state.truth_boundary = if ($report.PSObject.Properties.Name -contains "truth_boundary") {
            $report.truth_boundary
        } else {
            $null
        }
    }
    catch {
        $state.error = $_.Exception.Message
    }

    return $state
}

function Get-OperatorState {
    return [pscustomobject]@{
        queue = Get-QueueState
        library = Get-LibraryState
        benchmark = Get-BenchmarkState
        runtime = Get-RuntimeState
    }
}

function Write-OperatorState {
    param(
        [object]$State,
        [string]$Title = "Operator state"
    )

    if ($AsJson) {
        $State | ConvertTo-Json -Depth 12
        return
    }

    Write-Output $Title
    Write-Section -Title "Queue" -Value $State.queue
    Write-Section -Title "Library" -Value $State.library
    Write-Section -Title "Benchmark" -Value $State.benchmark
    Write-Section -Title "Runtime" -Value $State.runtime
}

function Write-QueueState {
    $state = Get-QueueState
    if ($AsJson) {
        $state | ConvertTo-Json -Depth 12
        return
    }
    Write-Section -Title "Queue" -Value $state
}

function Write-LibraryState {
    $state = Get-LibraryState
    if ($AsJson) {
        $state | ConvertTo-Json -Depth 12
        return
    }
    Write-Section -Title "Library" -Value $state
}

function Write-RuntimeState {
    $state = Get-RuntimeState
    if ($AsJson) {
        $state | ConvertTo-Json -Depth 12
        return
    }
    Write-Section -Title "Runtime" -Value $state
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogPath -Value "[$timestamp] $Message"
}

function Invoke-SupervisorCycle {
    param([int]$Iteration)

    Push-Location $RepoRoot
    try {
        Write-Log "Cycle $Iteration starting."
        Write-SupervisorHeartbeat -Iteration $Iteration -Phase "cycle_start"
        python scripts\orchestrator.py --once | Tee-Object -FilePath $LogPath -Append | Out-Null
        python scripts\reviewer_loop.py --once | Tee-Object -FilePath $LogPath -Append | Out-Null
        if ($FullSweepEvery -gt 0 -and ($Iteration % $FullSweepEvery) -eq 0) {
            Write-Log "Running periodic full verification sweep."
            python -m pytest | Tee-Object -FilePath $LogPath -Append | Out-Null
            python -m ruff check scripts tests connectors core execution features normalization datasets `
                | Tee-Object -FilePath $LogPath -Append | Out-Null
        }
        python scripts\monitor.py | Tee-Object -FilePath $LogPath -Append | Out-Null
        Write-SupervisorHeartbeat -Iteration $Iteration -Phase "cycle_complete"
        $soakLedgerOutput = python scripts\capture_soak_ledger.py
        $soakLedgerOutput | Tee-Object -FilePath $LogPath -Append
        if (Test-Path $SoakSummaryScriptPath) {
            python $SoakSummaryScriptPath --input $SoakLedgerPath --markdown-output $SoakRollupReportPath `
                | Tee-Object -FilePath $LogPath -Append | Out-Null
        }
        if (Test-Path $SoakAnomalyScriptPath) {
            python $SoakAnomalyScriptPath --input $SoakLedgerPath --markdown-output $SoakAnomalyReportPath `
                | Tee-Object -FilePath $LogPath -Append | Out-Null
        }
        if (Test-Path $TruthBoundaryAuditScriptPath) {
            python $TruthBoundaryAuditScriptPath --queue $QueuePath --markdown-output $TruthBoundaryAuditReportPath `
                | Tee-Object -FilePath $LogPath -Append | Out-Null
        }
        if (Test-Path $OperationalReadinessSnapshotScriptPath) {
            python $OperationalReadinessSnapshotScriptPath --queue $QueuePath --state $OrchestratorStatePath `
                --heartbeat $HeartbeatPath --ledger $SoakLedgerPath --benchmark-summary $BenchmarkSummaryPath `
                --markdown-output $OperationalReadinessSnapshotReportPath `
                | Tee-Object -FilePath $LogPath -Append | Out-Null
        }
        Write-Log "Cycle $Iteration complete."
    }
    finally {
        Pop-Location
    }
}

function Start-Supervisor {
    if (Test-SupervisorRunning) {
        Write-Output "Supervisor already running with PID $(Get-SupervisorPid)."
        return
    }

    if (Test-Path $StopPath) {
        Remove-Item $StopPath -Force
    }

    $argList = @(
        "-NoProfile"
        "-ExecutionPolicy", "Bypass"
        "-File", $PSCommandPath
        "-Mode", "loop"
        "-PollSeconds", $PollSeconds
        "-FullSweepEvery", $FullSweepEvery
    )

    $process = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -PassThru -WindowStyle Hidden
    Set-Content -Path $PidPath -Value $process.Id
    Write-Log "Supervisor started with PID $($process.Id)."
    Write-Output "Supervisor started with PID $($process.Id)."
}

function Stop-Supervisor {
    $supervisorPid = Get-SupervisorPid
    if ($null -eq $supervisorPid) {
        Write-Output "Supervisor is not running."
        return
    }

    New-Item -ItemType File -Path $StopPath -Force | Out-Null
    Start-Sleep -Seconds 2
    $process = Get-Process -Id $supervisorPid -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        Stop-Process -Id $supervisorPid -Force
    }
    if (Test-Path $PidPath) {
        Remove-Item $PidPath -Force
    }
    Write-Log "Supervisor stopped."
    Write-Output "Supervisor stopped."
}

function Show-Status {
    Push-Location $RepoRoot
    try {
        $running = Test-SupervisorRunning
        $supervisorPid = Get-SupervisorPid
        $heartbeatState = Get-SupervisorHeartbeatState
        if ($running) {
            Write-Output "Supervisor: running (PID $supervisorPid)"
        }
        elseif ($heartbeatState.status -eq "healthy") {
            $heartbeatPid = if ($null -ne $heartbeatState.supervisor_pid) {
                $heartbeatState.supervisor_pid
            }
            else {
                "unknown"
            }
            Write-Output "Supervisor: running (heartbeat-only, PID $heartbeatPid)"
        }
        else {
            Write-Output "Supervisor: stopped"
        }
        python scripts\monitor.py
        Write-Output ""
        Write-Section -Title "Benchmark release" -Value (Get-BenchmarkState)
        if (Test-Path $LogPath) {
            Write-Output ""
            Write-Output "Recent log:"
            Get-Content $LogPath -Tail 15
        }
    }
    finally {
        Pop-Location
    }
}

switch ($Mode) {
    "start" {
        Start-Supervisor
    }
    "stop" {
        Stop-Supervisor
    }
    "status" {
        Show-Status
    }
    "queue" {
        Write-QueueState
    }
    "library" {
        Write-LibraryState
    }
    "runtime" {
        Write-RuntimeState
    }
    "state" {
        Write-OperatorState -State (Get-OperatorState)
    }
    "run-once" {
        Invoke-SupervisorCycle -Iteration 1
        Show-Status
    }
    "loop" {
        Set-Content -Path $PidPath -Value $PID
        $iteration = 1
        while ($true) {
            Ensure-SupervisorPidFile
            if (Test-Path $StopPath) {
                Remove-Item $StopPath -Force
                if (Test-Path $PidPath) {
                    Remove-Item $PidPath -Force
                }
                Write-Log "Stop signal observed. Exiting supervisor loop."
                break
            }
            Invoke-SupervisorCycle -Iteration $iteration
            $iteration += 1
            Start-Sleep -Seconds $PollSeconds
        }
    }
}
