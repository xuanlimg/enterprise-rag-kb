$ErrorActionPreference = "Stop"

$Project = "E:\Codex\UE5\enterprise-rag-kb"
$Python = Join-Path $Project ".venv\Scripts\python.exe"
$Url = "http://127.0.0.1:8000/?v=15"
$LogDir = Join-Path $env:TEMP "rag-launcher"
$OutLog = Join-Path $LogDir "uvicorn.out.log"
$ErrLog = Join-Path $LogDir "uvicorn.err.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Test-DockerEngine {
    try {
        docker info --format "{{.ServerVersion}}" *> $null
        return $true
    } catch {
        return $false
    }
}

Write-Host "1/5 检查 Docker Desktop..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "未找到 docker 命令，请先安装 Docker Desktop。"
    exit 1
}

if (-not (Test-DockerEngine)) {
    Write-Host "Docker 引擎未启动，正在打开 Docker Desktop..."
    $dockerDesktop = "C:\Users\30506\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
    if (Test-Path -LiteralPath $dockerDesktop) {
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
    }
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        if (Test-DockerEngine) {
            break
        }
    }
}

if (-not (Test-DockerEngine)) {
    Write-Host "Docker 引擎启动失败，请手动打开 Docker Desktop 后重试。"
    exit 1
}

Write-Host "2/5 启动 PostgreSQL + pgvector..."
Set-Location -LiteralPath $Project
docker compose up -d db

Write-Host "3/5 停止旧后端进程..."
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

Write-Host "4/5 启动 FastAPI 后端..."
Remove-Item -LiteralPath $OutLog,$ErrLog -Force -ErrorAction SilentlyContinue
Start-Process -FilePath $Python -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $Project -WindowStyle Hidden -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog

Write-Host "5/5 等待服务就绪..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
    }
}

if ($ready) {
    Write-Host "服务已启动，正在打开浏览器..."
    Start-Process $Url
} else {
    Write-Host "服务启动超时，正在打开错误日志..."
    if (Test-Path -LiteralPath $ErrLog) {
        Start-Process notepad.exe $ErrLog
    } else {
        Write-Host "日志文件不存在：$ErrLog"
    }
}
