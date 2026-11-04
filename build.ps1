<#
.SYNOPSIS
    Скрипт сборки дистрибутива «Рейс-Проверка» для Windows.

.DESCRIPTION
    Запускает проверку качества и сборку дистрибутива (PyInstaller и Inno Setup).

.PARAMETER SkipTests
    Пропустить запуск тестов и линтеров.

.PARAMETER NoInstaller
    Собрать только портативный каталог без вызова Inno Setup.

.PARAMETER Clean
    Очистить каталоги сборки перед запуском.

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

$env:PATH = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

$uvCmd = Get-Command "uv" -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Error "Утилита 'uv' не найдена в PATH. Убедитесь, что uv установлен."
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
