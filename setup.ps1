# Setup script for Result Analyser application
# This script installs all required dependencies

Write-Host "Installing Python dependencies..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host "`nInstalling Playwright browsers..." -ForegroundColor Green
python -m playwright install chromium

Write-Host "`nSetup complete! You can now run the application with:" -ForegroundColor Green
Write-Host "python .\app.py" -ForegroundColor Yellow
