# Скрипт для запуска бота
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Остановка всех запущенных процессов Python, которые могут быть ботом
Write-Host "🔍 Проверка запущенных процессов Python..." -ForegroundColor Cyan
$pythonProcesses = Get-Process python,pythonw -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "⚠️  Обнаружены запущенные процессы Python. Проверяем, не является ли один из них ботом..." -ForegroundColor Yellow
    Write-Host "💡 Если бот запущен в другом терминале, остановите его вручную (Ctrl+C)" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "✓ Запущенных процессов Python не обнаружено" -ForegroundColor Green
}

Write-Host "🔍 Активация виртуального окружения..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

Write-Host "🚀 Запуск бота..." -ForegroundColor Green
python bot.py



