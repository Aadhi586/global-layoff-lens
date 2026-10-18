$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot 'frontend'
$RuntimeDir = Join-Path $ProjectRoot '.runtime'
$ApiOut = Join-Path $RuntimeDir 'api.out.log'
$ApiErr = Join-Path $RuntimeDir 'api.err.log'
$WebOut = Join-Path $RuntimeDir 'web.out.log'
$WebErr = Join-Path $RuntimeDir 'web.err.log'
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

function Test-PortInUse([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try { $client.Connect('127.0.0.1', $Port); return $true }
    catch { return $false }
    finally { $client.Dispose() }
}

$apiAlreadyRunning = Test-PortInUse 8000
$webAlreadyRunning = Test-PortInUse 3000
if ($apiAlreadyRunning) {
    try { $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; if ($health.status -ne 'ok') { throw 'unexpected API response' } }
    catch { throw 'Port 8000 is occupied, but the Layoff Lens API is not responding there. Close that process, then run start.bat again.' }
}
if ($webAlreadyRunning) {
    try { $page = Invoke-WebRequest 'http://127.0.0.1:3000/' -TimeoutSec 2 -UseBasicParsing; if ($page.StatusCode -ne 200) { throw 'unexpected website response' } }
    catch { throw 'Port 3000 is occupied by another app. Close it, then run start.bat again.' }
}

if (-not (Test-Path -LiteralPath $Python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv (Join-Path $ProjectRoot '.venv') }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv (Join-Path $ProjectRoot '.venv') }
    else { throw 'Python 3 is required. Install Python 3.10 or newer, then run start.bat again.' }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}

& $Python -m pip install -r (Join-Path $ProjectRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Installing Python dependencies failed.' }

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules'))) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node.js 20 or newer is required. Install Node.js, then run start.bat again.' }
    Push-Location $FrontendDir
    try { & npm install; if ($LASTEXITCODE -ne 0) { throw 'Installing frontend dependencies failed.' } }
    finally { Pop-Location }
}

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
& $Python -m backend.services.data_cleaner
if ($LASTEXITCODE -ne 0) { throw 'Preparing the dataset failed; see the message above.' }

if (-not $apiAlreadyRunning) {
    $api = Start-Process -FilePath $Python -ArgumentList @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $ProjectRoot -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr -PassThru
    Set-Content -LiteralPath (Join-Path $RuntimeDir 'api.pid') -Value $api.Id
    $apiReady = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        try { $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; if ($health.status -eq 'ok') { $apiReady = $true; break } } catch { }
    }
    if (-not $apiReady) { throw "The API did not start. Check $ApiErr" }
}

if (-not $webAlreadyRunning) {
    $web = Start-Process -FilePath $env:ComSpec -ArgumentList @('/c', 'npm run dev -- --hostname 127.0.0.1') -WorkingDirectory $FrontendDir -RedirectStandardOutput $WebOut -RedirectStandardError $WebErr -PassThru
    Set-Content -LiteralPath (Join-Path $RuntimeDir 'web.pid') -Value $web.Id
    $webReady = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 1
        try { $response = Invoke-WebRequest 'http://127.0.0.1:3000/' -TimeoutSec 2 -UseBasicParsing; if ($response.StatusCode -eq 200) { $webReady = $true; break } } catch { }
    }
    if (-not $webReady) { throw "The website did not start. Check $WebErr" }
}

Write-Host 'Global Layoff Lens is ready at http://127.0.0.1:3000' -ForegroundColor Green
Write-Host 'The API is running at http://127.0.0.1:8000. Keep this launcher open while using the site.'
Start-Process 'http://127.0.0.1:3000'
