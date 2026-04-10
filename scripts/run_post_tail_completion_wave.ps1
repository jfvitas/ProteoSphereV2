param(
    [switch]$Resume,
    [string]$UniRefSource = "C:\Users\jfvit\Downloads\uniref100.xml.gz",
    [string]$UniRefDest = "C:\CSTEMP\ProteoSphereV2_overflow\protein_data_scope_seed\uniprot\uniref100.xml.gz"
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $PSScriptRoot "run_post_tail_completion_wave.py"
$summaryPath = Join-Path $repoRoot "artifacts\status\post_tail_completion_summary.json"
$statePath = Join-Path $repoRoot "artifacts\runtime\post_tail_completion_state.json"
$logPath = Join-Path $repoRoot "artifacts\runtime\post_tail_completion_wave.log"

$runnerArgs = @(
    $runner,
    "--execute",
    "--allow-c-overflow-authority",
    "--uniref-source", $UniRefSource,
    "--uniref-dest", $UniRefDest
)
if ($Resume) {
    $runnerArgs += "--resume"
}
else {
    $runnerArgs += "--resume"
}

$python = "python"
$output = & $python @runnerArgs 2>&1
$output | Tee-Object -FilePath $logPath -Append | Out-Null

if (Test-Path $summaryPath) {
    $summary = Get-Content $summaryPath -Raw | ConvertFrom-Json
    Write-Host "Post-tail completion summary:"
    Write-Host "  status: $($summary.status)"
    Write-Host "  executed_step_count: $($summary.summary.executed_step_count)"
    Write-Host "  failed_step_count: $($summary.summary.failed_step_count)"
    Write-Host "  strict_governing_training_view_count: $($summary.summary.strict_governing_training_view_count)"
    Write-Host "  validation_status: $($summary.summary.validation_status)"
    Write-Host "  restart_hint: $($summary.restart_hint)"
    Write-Host "  summary_path: $summaryPath"
}

if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
    Write-Host "Current runner state:"
    Write-Host "  current_step: $($state.current_step)"
    Write-Host "  last_successful_step: $($state.last_successful_step)"
    Write-Host "  restart_hint: $($state.restart_hint)"
}
