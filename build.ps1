<#
.SYNOPSIS
    Скрипт автоматизированной сборки дистрибутива «Рейс-Проверка» для Windows 10/11 (x64).

.DESCRIPTION
    Последовательно запускает uv sync, проверки качества (Ruff, basedpyright, pytest),
    сборку портативного каталога PyInstaller и компиляцию инсталлятора Inno Setup.

.PARAMETER SkipTests
    Пропустить запуск тестов и линтеров (ускоренная dev-сборка).

.PARAMETER NoInstaller
    Собрать только портативный каталог без вызова Inno Setup.

.PARAMETER Clean
    Предварительно очистить каталоги build/, dist/ и dist_installer/.

.EXAMPLE
    .\build.ps1
    .\build.ps1 -SkipTests
    .\build.ps1 -Clean -NoInstaller
#>

[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$NoInstaller,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

# Подгрузка актуального PATH (включая mise shims)
$env:PATH = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

# Проверка наличия uv
$uvCmd = Get-Command "uv" -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Error "Утилита 'uv' не найдена в PATH. Убедитесь, что uv установлен (например, через mise или astral-sh)."
    exit 1
}

$buildArgs = @("run", "python", "scripts/build.py")
if ($SkipTests) { $buildArgs += "--skip-tests" }
if ($NoInstaller) { $buildArgs += "--no-installer" }
if ($Clean) { $buildArgs += "--clean" }

Write-Host ">>> Запуск процесса сборки «Рейс-Проверка»..." -ForegroundColor Cyan
& uv @buildArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Сборка завершилась с ошибкой (код $LASTEXITCODE)."
    exit $LASTEXITCODE
}
