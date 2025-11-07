#!/usr/bin/env pwsh
# Idempotent setup script for git-crypt and GPG tooling

$ErrorActionPreference = "Stop"

Write-Host "=== Git-Crypt and GPG Setup ===" -ForegroundColor Cyan

# Check if Chocolatey is installed
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Chocolatey is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Chocolatey found" -ForegroundColor Green

# Function to check if a package is installed
function Test-ChocoPackage {
    param([string]$PackageName)
    $installed = choco list --local-only --exact $PackageName 2>$null
    return $installed -match "^$PackageName\s"
}

# Install GPG (GnuPG)
Write-Host "`nChecking GnuPG..." -ForegroundColor Cyan
if (Get-Command gpg -ErrorAction SilentlyContinue) {
    $version = & gpg --version | Select-Object -First 1
    Write-Host "✓ GPG already installed: $version" -ForegroundColor Green
} elseif (Test-ChocoPackage "gpg4win") {
    Write-Host "✓ GPG (via Gpg4win) already installed" -ForegroundColor Green
} else {
    Write-Host "Installing GnuPG..." -ForegroundColor Yellow
    choco install gnupg -y
    Write-Host "✓ GnuPG installed" -ForegroundColor Green
}

# Install git-crypt
Write-Host "`nChecking git-crypt..." -ForegroundColor Cyan
if (Get-Command git-crypt -ErrorAction SilentlyContinue) {
    $version = & git-crypt --version 2>&1
    Write-Host "✓ git-crypt already installed: $version" -ForegroundColor Green
} else {
    Write-Host "Installing git-crypt from GitHub releases..." -ForegroundColor Yellow
    
    $gitCryptUrl = "https://github.com/AGWA/git-crypt/releases/download/0.7.0/git-crypt-0.7.0-x86_64.exe"
    $installDir = "$env:LOCALAPPDATA\git-crypt"
    $gitCryptPath = "$installDir\git-crypt.exe"
    
    try {
        # Create install directory if it doesn't exist
        if (-not (Test-Path $installDir)) {
            New-Item -ItemType Directory -Path $installDir -Force | Out-Null
        }
        
        # Download git-crypt
        Write-Host "  Downloading from $gitCryptUrl..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $gitCryptUrl -OutFile $gitCryptPath -UseBasicParsing
        
        # Add to PATH if not already there
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($userPath -notlike "*$installDir*") {
            Write-Host "  Adding to user PATH..." -ForegroundColor Gray
            [Environment]::SetEnvironmentVariable(
                "Path",
                "$userPath;$installDir",
                "User"
            )
            # Update current session PATH
            $env:Path = "$env:Path;$installDir"
        }
        
        Write-Host "✓ git-crypt installed to $gitCryptPath" -ForegroundColor Green
        Write-Host "  Note: Restart your shell for PATH changes to take full effect" -ForegroundColor Yellow
        
        # Verify installation
        if (Test-Path $gitCryptPath) {
            $version = & $gitCryptPath --version 2>&1
            Write-Host "  Version: $version" -ForegroundColor Gray
        }
    } catch {
        Write-Host "❌ Failed to install git-crypt: $_" -ForegroundColor Red
        Write-Host "`nManual installation options:" -ForegroundColor Yellow
        Write-Host "1. Download manually from: https://github.com/AGWA/git-crypt/releases" -ForegroundColor White
        Write-Host "2. Use WSL: wsl sudo apt install git-crypt" -ForegroundColor White
    }
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan

# Setup GPG environment for ~/.ssh/gpg keyring
$defaultGpgHome = "$HOME\.gnupg"
$sshGpgHome = "$HOME\.ssh\gpg"

# Check if GPG keyring is in ~/.ssh/gpg
if (Test-Path $sshGpgHome) {
    Write-Host "`n✓ GPG keyring found in ~/.ssh/gpg" -ForegroundColor Green
    
    # Check if junction exists
    if (-not (Test-Path $defaultGpgHome)) {
        Write-Host "Creating junction: .gnupg -> .ssh\gpg" -ForegroundColor Yellow
        New-Item -ItemType Junction -Path $defaultGpgHome -Target $sshGpgHome -Force | Out-Null
        Write-Host "✓ Junction created" -ForegroundColor Green
    } elseif ((Get-Item $defaultGpgHome).Attributes -match "ReparsePoint") {
        Write-Host "✓ Junction already exists: .gnupg -> .ssh\gpg" -ForegroundColor Green
    } else {
        Write-Host "⚠ Warning: .gnupg exists but is not a junction to .ssh\gpg" -ForegroundColor Yellow
        Write-Host "  Your GPG keyring may not sync properly" -ForegroundColor Yellow
    }
} elseif (Test-Path $defaultGpgHome) {
    Write-Host "`n⚠ GPG keyring is in default location (.gnupg)" -ForegroundColor Yellow
    Write-Host "  Consider running 'make setup-gpg' to move it to ~/.ssh/gpg for syncing" -ForegroundColor White
}

# Check if git-crypt is available
if (Get-Command git-crypt -ErrorAction SilentlyContinue) {
    Write-Host "`n✓ All tools ready!" -ForegroundColor Green
    
    # Check if in a git-crypt enabled repository
    if (Test-Path ".git-crypt") {
        Write-Host "`nThis repository uses git-crypt." -ForegroundColor White
        Write-Host "To decrypt files, run:" -ForegroundColor White
        Write-Host "   git-crypt unlock" -ForegroundColor Gray
        Write-Host "(Your GPG key from ~/.ssh/gpg will be used automatically)" -ForegroundColor Gray
    } else {
        Write-Host "`nTo set up git-crypt for a new repository:" -ForegroundColor White
        Write-Host "1. Initialize git-crypt:" -ForegroundColor White
        Write-Host "   git-crypt init" -ForegroundColor Gray
        Write-Host "2. Add your GPG key:" -ForegroundColor White
        Write-Host "   git-crypt add-gpg-user <KEY-ID>" -ForegroundColor Gray
        Write-Host "3. Configure .gitattributes for files to encrypt:" -ForegroundColor White
        Write-Host "   echo '.env filter=git-crypt diff=git-crypt' >> .gitattributes" -ForegroundColor Gray
    }
} else {
    Write-Host "`n⚠ GPG installed, but git-crypt needs manual installation" -ForegroundColor Yellow
    Write-Host "See instructions above for git-crypt installation options" -ForegroundColor White
}
Write-Host ""
