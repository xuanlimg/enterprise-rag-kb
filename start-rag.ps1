# 一键启动脚本：拉起 PostgreSQL(pgvector) 容器并启动 FastAPI 后端
# 用法：在项目根目录执行 .\start-rag.ps1
# 说明：脚本会自动识别项目路径、虚拟环境与 Docker Desktop 位置，不依赖固定盘符。

$ErrorActionPreference = "Stop"

$Project = $PSScriptRoot
$Url = "http://127.0.0.1:8000/"
$LogDir = Join-Path $env:TEMP "rag-launcher"
$OutLog = Join-Path $LogDir "uvicorn.out.log"
$ErrLog = Join-Path $LogDir "uvicorn.err.log"
$PidFile = Join-Path $LogDir "uvicorn.pid"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Test-DockerEngine {
    try {
        docker info --format "{{.ServerVersion}}" *> $null
        return $true
    } catch {
        return $false
    }
}

function Get-PythonExe {
    # 优先使用项目虚拟环境，其次回退到 PATH 中的 python
    $venvPython = Join-Path $Project ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) { return $venvPython }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Get-DockerDesktopPath {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"),
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

Write-Host "1/5 检查 Docker 环境..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "未找到 docker 命令，请先安装 Docker Desktop。"
    exit 1
}

if (-not (Test-DockerEngine)) {
    Write-Host "Docker 引擎未启动，尝试启动 Docker Desktop..."
    $dockerDesktop = Get-DockerDesktopPath
    if ($dockerDesktop) {
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
    }
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        if (Test-DockerEngine) { break }
    }
}

if (-not (Test-DockerEngine)) {
    Write-Host "Docker 引擎启动失败，请手动打开 Docker Desktop 后重试。"
    exit 1
}

Write-Host "2/5 启动 PostgreSQL + pgvector..."
Set-Location -LiteralPath $Project
docker compose up -d db

Write-Host "3/5 停止上次启动的后端进程..."
if (Test-Path -LiteralPath $PidFile) {
    $oldPid = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500

Write-Host "4/5 启动 FastAPI 后端..."
$pythonExe = Get-PythonExe
if (-not $pythonExe) {
    Write-Host "未找到 Python，请先创建虚拟环境：python -m venv .venv"
    exit 1
}

Remove-Item -LiteralPath $OutLog, $ErrLog -Force -ErrorAction SilentlyContinue
$process = Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $Project -WindowStyle Hidden -PassThru -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog
$process.Id | Set-Content -LiteralPath $PidFile

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
    Write-Host "服务已启动：$Url"
    Start-Process $Url
} else {
    Write-Host "服务启动超时，正在打开错误日志..."
    if (Test-Path -LiteralPath $ErrLog) {
        Start-Process notepad.exe $ErrLog
    } else {
        Write-Output "日志文件不存在：$ErrLog"
    }
}
