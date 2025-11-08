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
$gitCryptKeysDir = "$HOME\.ssh\git-crypt-keys"

# Ensure ~/.ssh/gpg directory exists
if (-not (Test-Path $sshGpgHome)) {
    Write-Host "`nCreating GPG keyring directory in ~/.ssh/gpg..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $sshGpgHome -Force | Out-Null
}

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
        Write-Host "  Your GPG keyring may not sync properly across machines" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To fix this automatically:" -ForegroundColor White
        Write-Host "  1. Backup .gnupg: cp -r ~/.gnupg ~/.gnupg.backup" -ForegroundColor Gray
        Write-Host "  2. Delete .gnupg: rm -rf ~/.gnupg" -ForegroundColor Gray
        Write-Host "  3. Run this script again to create the junction" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Or fix manually with PowerShell:" -ForegroundColor White
        Write-Host "  Remove-Item -Path `"$defaultGpgHome`" -Recurse -Force" -ForegroundColor Gray
        Write-Host "  New-Item -ItemType Junction -Path `"$defaultGpgHome`" -Target `"$sshGpgHome`"" -ForegroundColor Gray
    }
} elseif (Test-Path $defaultGpgHome) {
    Write-Host "`n⚠ GPG keyring is in default location (.gnupg)" -ForegroundColor Yellow
    Write-Host "  To enable cross-machine syncing, move it to ~/.ssh/gpg" -ForegroundColor White
    Write-Host ""
    Write-Host "To migrate to ~/.ssh/gpg:" -ForegroundColor White
    Write-Host "  1. Move keyring: mv ~/.gnupg ~/.ssh/gpg" -ForegroundColor Gray
    Write-Host "  2. Run this script again to create the junction" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or with PowerShell:" -ForegroundColor White
    Write-Host "  Move-Item -Path `"$defaultGpgHome`" -Destination `"$sshGpgHome`"" -ForegroundColor Gray
    Write-Host "  New-Item -ItemType Junction -Path `"$defaultGpgHome`" -Target `"$sshGpgHome`"" -ForegroundColor Gray
}

# Import git-crypt GPG keys if they exist in ~/.ssh/git-crypt-keys/
Write-Host "`nChecking for git-crypt GPG keys in ~/.ssh/git-crypt-keys/..." -ForegroundColor Cyan
$privateKeyPath = "$gitCryptKeysDir\git-crypt-private-key.asc"
$publicKeyPath = "$gitCryptKeysDir\git-crypt-public-key.asc"

if (Test-Path $privateKeyPath) {
    Write-Host "✓ Found git-crypt GPG key backup" -ForegroundColor Green

    # Check if key is already imported
    $keyFingerprint = "BEF464A08DC846D83764059CAFA2D36EE32CB632"
    $existingKey = & gpg --list-keys $keyFingerprint 2>&1

    if ($existingKey -match "pub\s+") {
        Write-Host "✓ GPG key already imported into keyring" -ForegroundColor Green
    } else {
        Write-Host "Importing git-crypt GPG key..." -ForegroundColor Yellow

        try {
            # Import the private key
            & gpg --import $privateKeyPath 2>&1 | Out-Null

            # Trust the key ultimately (needed for git-crypt)
            # This creates a trust entry in the GPG database
            $trustCommand = "${keyFingerprint}:6:"
            $trustCommand | & gpg --import-ownertrust 2>&1 | Out-Null

            Write-Host "✓ GPG key imported and trusted" -ForegroundColor Green
        } catch {
            Write-Host "⚠ Warning: Failed to import GPG key: $_" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "⚠ No git-crypt GPG key backup found in ~/.ssh/git-crypt-keys/" -ForegroundColor Yellow
    Write-Host "  On the primary machine, export the key with:" -ForegroundColor White
    Write-Host "    gpg --export-secret-keys --armor <KEY-ID> > ~/.ssh/git-crypt-keys/git-crypt-private-key.asc" -ForegroundColor Gray
}

# Check if git-crypt is available (check both PATH and direct installation)
$gitCryptAvailable = $false
$gitCryptCmd = $null

if (Get-Command git-crypt -ErrorAction SilentlyContinue) {
    $gitCryptAvailable = $true
    $gitCryptCmd = "git-crypt"
} elseif (Test-Path "$env:LOCALAPPDATA\git-crypt\git-crypt.exe") {
    # Binary exists but not in current session PATH
    $gitCryptAvailable = $true
    $gitCryptCmd = "$env:LOCALAPPDATA\git-crypt\git-crypt.exe"
    Write-Host "`n⚠ git-crypt installed but not in current session PATH" -ForegroundColor Yellow
    Write-Host "  Please restart your shell for full PATH integration" -ForegroundColor White
    Write-Host "  (Using direct path for now)" -ForegroundColor Gray
}

if ($gitCryptAvailable) {
    Write-Host "`n✓ All tools ready!" -ForegroundColor Green

    # Check if in a git-crypt enabled repository
    if (Test-Path ".git-crypt") {
        Write-Host "`nThis repository uses git-crypt." -ForegroundColor White

        # Check if repository is already unlocked by checking for encrypted files
        $gitCryptStatus = & $gitCryptCmd status 2>&1 | Out-String
        $hasEncryptedFiles = $gitCryptStatus -match "encrypted:"

        if (-not $hasEncryptedFiles -and $LASTEXITCODE -eq 0) {
            Write-Host "✓ Repository already unlocked" -ForegroundColor Green
        } else {
            if ($hasEncryptedFiles) {
                Write-Host "Repository is locked (encrypted files detected)" -ForegroundColor Yellow
            }
            Write-Host "Attempting to unlock repository..." -ForegroundColor Yellow

            try {
                $unlockOutput = & $gitCryptCmd unlock 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✓ Repository unlocked successfully!" -ForegroundColor Green
                    Write-Host "  Encrypted files (.env, etc.) are now accessible" -ForegroundColor Gray
                } else {
                    Write-Host "⚠ Failed to unlock repository" -ForegroundColor Yellow
                    Write-Host "  Error: $unlockOutput" -ForegroundColor Gray
                    Write-Host ""
                    Write-Host "  Troubleshooting:" -ForegroundColor White
                    Write-Host "  1. Ensure your GPG key is imported: gpg --list-secret-keys" -ForegroundColor Gray
                    Write-Host "  2. Check key fingerprint matches: BEF464A08DC846D83764059CAFA2D36EE32CB632" -ForegroundColor Gray
                    Write-Host "  3. Try manual unlock: git-crypt unlock" -ForegroundColor Gray
                }
            } catch {
                Write-Host "⚠ Error unlocking repository: $_" -ForegroundColor Yellow
                Write-Host "  Try manually: git-crypt unlock" -ForegroundColor White
            }
        }
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
    Write-Host "`n❌ git-crypt installation failed" -ForegroundColor Red
    Write-Host "See error messages above or try manual installation:" -ForegroundColor White
    Write-Host "  https://github.com/AGWA/git-crypt/releases" -ForegroundColor Gray
}
Write-Host ""
