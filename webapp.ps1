param([int]$Port = 8080)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
[Console]::OutputEncoding = [Text.Encoding]::UTF8

function Find-Ngrok {
  $c = Get-Command ngrok -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  $dir = Join-Path $env:LOCALAPPDATA "ngrok"
  foreach ($p in @((Join-Path $dir "ngrok.exe"), (Join-Path $root "ngrok.exe"), (Join-Path $env:USERPROFILE "Downloads\ngrok.exe"))) {
    if (Test-Path $p) { return $p }
  }
  return $null
}

$ngrok = Find-Ngrok
if (-not $ngrok) {
  Write-Host "ngrok не найден. Ставим официальный архив ngrok.com..."
  $dir = Join-Path $env:LOCALAPPDATA "ngrok"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $zip = Join-Path $env:TEMP "ngrok.zip"
  Invoke-WebRequest -Uri "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip" -OutFile $zip
  Expand-Archive -Path $zip -DestinationPath $dir -Force
  Remove-Item $zip -Force
  $ngrok = Join-Path $dir "ngrok.exe"
  if (-not (Test-Path $ngrok)) { throw "ngrok не распаковался" }
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  if ($userPath -notlike "*$dir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$dir", "User")
  }
}
Write-Host "ngrok: $ngrok"

$cfg = Join-Path $root ".ngrok.yml"
& $ngrok config check --config $cfg *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Нужен authtoken: https://dashboard.ngrok.com/get-started/your-authtoken"
  $tok = Read-Host "Вставьте authtoken"
  if (-not $tok) { throw "без authtoken ngrok не запустится" }
  & $ngrok config add-authtoken $tok --config $cfg
  if ($LASTEXITCODE -ne 0) { throw "токен не принят" }
}

$server = Start-Process -PassThru -NoNewWindow "py" -ArgumentList @("-u", "serve.py", "$Port")
$tunnel = Start-Process -PassThru -NoNewWindow $ngrok -ArgumentList @("http", "$Port", "--log=stdout", "--config", $cfg)

try {
  $url = ""
  for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 750
    try {
      $j = Invoke-RestMethod "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2
      $url = $j.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1 -ExpandProperty public_url
      if ($url) { break }
    } catch {}
  }
  if (-not $url) {
    Write-Host "Туннель не поднялся. Смотрите вывод ngrok выше."
    exit 2
  }
  $webappUrl = $url.TrimEnd("/") + "/"
  Set-Content -Encoding UTF8 (Join-Path $root ".webapp_url") $webappUrl
  Write-Host ""
  Write-Host "WebApp URL: $webappUrl"
  Write-Host "1) @BotFather -> /setmenubutton -> ваш бот -> вставьте этот URL"
  Write-Host "2) перезапустите start.cmd: ссылка подхватится из .webapp_url"
  Write-Host "Остановка: Ctrl+C"
  Wait-Process -Id $tunnel.Id
} finally {
  if ($tunnel -and -not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue }
  if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
}
