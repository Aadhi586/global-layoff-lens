$ErrorActionPreference = 'SilentlyContinue'
$RuntimeDir = Join-Path $PSScriptRoot '.runtime'
foreach ($name in @('web.pid','api.pid')) {
    $pidFile = Join-Path $RuntimeDir $name
    if (Test-Path -LiteralPath $pidFile) {
        $processId = [int](Get-Content -LiteralPath $pidFile -Raw)
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
        if ($process -and $process.CommandLine -like "*$PSScriptRoot*") {
            Stop-Process -Id $processId -Force
        }
        Remove-Item -LiteralPath $pidFile -Force
    }
}
Write-Host 'Global Layoff Lens has been stopped.'
