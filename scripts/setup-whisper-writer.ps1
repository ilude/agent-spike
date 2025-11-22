# WhisperWriter Setup Script
# Sets up WhisperWriter with GPU server backend
#
# Prerequisites:
#   - Python 3.10+ installed
#   - GPU server running whisper API at http://192.168.16.241:8000
#
# Usage:
#   .\setup-whisper-writer.ps1

$ErrorActionPreference = "Stop"

$INSTALL_DIR = "$env:USERPROFILE\Apps\whisper-writer"
$GPU_SERVER = "192.168.16.241"
$WHISPER_PORT = "8000"

Write-Host "=== WhisperWriter Setup ===" -ForegroundColor Cyan

# Check if already installed
if (Test-Path $INSTALL_DIR) {
    Write-Host "WhisperWriter already exists at $INSTALL_DIR" -ForegroundColor Yellow
    $response = Read-Host "Update existing installation? (y/n)"
    if ($response -ne "y") {
        Write-Host "Aborted."
        exit 0
    }
    Set-Location $INSTALL_DIR
    git pull
} else {
    Write-Host "Cloning WhisperWriter to $INSTALL_DIR..."
    git clone https://github.com/savbell/whisper-writer $INSTALL_DIR
    Set-Location $INSTALL_DIR
}

# Create virtual environment and install dependencies
Write-Host "Setting up Python environment..."
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Start WhisperWriter:"
Write-Host "   cd $INSTALL_DIR"
Write-Host "   .\.venv\Scripts\Activate.ps1"
Write-Host "   python run.py"
Write-Host ""
Write-Host "2. Configure in the Settings window:"
Write-Host "   - activation_key: f13"
Write-Host "   - use_api: true (checked)"
Write-Host "   - base_url: http://${GPU_SERVER}:${WHISPER_PORT}/v1"
Write-Host "   - recording_mode: voice_activity_detection (or press_to_toggle)"
Write-Host ""
Write-Host "3. Set up mouse button (choose one):"
Write-Host ""
Write-Host "   Option A - Logitech Options+:"
Write-Host "     Open Logitech Options+ > M720 > Forward button > Keyboard Shortcut > F13"
Write-Host ""
Write-Host "   Option B - AutoHotkey:"
Write-Host "     Install AutoHotkey v2, then run:"
Write-Host "     C:\Projects\Personal\agent-spike\scripts\whisper-dictate.ahk"
Write-Host ""
Write-Host "4. Test the GPU server:"
Write-Host "   curl http://${GPU_SERVER}:${WHISPER_PORT}/health"
Write-Host ""
