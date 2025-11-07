#!/usr/bin/env pwsh
# Generate GPG key with keyring stored in ~/.ssh directory

$ErrorActionPreference = "Stop"

Write-Host "=== GPG Key Generation ===" -ForegroundColor Cyan

# Use default GPG home but create junction/symlink to ~/.ssh/gpg
$defaultGpgHome = "$HOME\.gnupg"
$sshGpgHome = "$HOME\.ssh\gpg"

# Check if .gnupg exists and is not a junction
if ((Test-Path $defaultGpgHome) -and -not ((Get-Item $defaultGpgHome).Attributes -match "ReparsePoint")) {
    Write-Host "Moving existing GPG directory to ~/.ssh/gpg..." -ForegroundColor Yellow
    if (Test-Path $sshGpgHome) {
        Write-Host "❌ Both .gnupg and .ssh\gpg exist. Please manually resolve." -ForegroundColor Red
        exit 1
    }
    Move-Item -Path $defaultGpgHome -Destination $sshGpgHome -Force
}

# Create ~/.ssh/gpg if it doesn't exist
if (-not (Test-Path $sshGpgHome)) {
    Write-Host "Creating GPG keyring directory: $sshGpgHome" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $sshGpgHome -Force | Out-Null
}

# Create junction from .gnupg to .ssh\gpg
if (-not (Test-Path $defaultGpgHome)) {
    Write-Host "Creating junction: .gnupg -> .ssh\gpg" -ForegroundColor Yellow
    New-Item -ItemType Junction -Path $defaultGpgHome -Target $sshGpgHome -Force | Out-Null
}

Write-Host "✓ GPG keyring location: $sshGpgHome" -ForegroundColor Green
Write-Host "✓ Linked from: $defaultGpgHome" -ForegroundColor Green

Write-Host "`nChecking for existing keys..." -ForegroundColor Cyan
$existingKeys = & gpg --list-keys 2>&1
if ($existingKeys -match "pub\s+") {
    Write-Host "✓ GPG keys already exist" -ForegroundColor Green
    & gpg --list-keys
    exit 0
}

Write-Host "No existing keys found. Generating new GPG key..." -ForegroundColor Yellow
Write-Host "`nYou will be prompted for:" -ForegroundColor White
Write-Host "  - Name (e.g., 'Your Name')" -ForegroundColor Gray
Write-Host "  - Email (e.g., 'you@example.com')" -ForegroundColor Gray
Write-Host "  - Passphrase (recommended but optional)" -ForegroundColor Gray
Write-Host ""

# Generate key with batch mode for consistency
$name = Read-Host "Enter your name"
$email = Read-Host "Enter your email"
$passphrase = Read-Host "Enter passphrase (or leave empty for no passphrase)" -AsSecureString
$passphraseText = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($passphrase))

Write-Host "`nGenerating GPG key (this may take a moment)..." -ForegroundColor Yellow

# Create batch file for key generation
$batchContent = @"
%echo Generating GPG key
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: $name
Name-Email: $email
Expire-Date: 0
"@

if ($passphraseText) {
    $batchContent += "`nPassphrase: $passphraseText"
} else {
    $batchContent += "`n%no-protection"
}

$batchContent += "`n%commit`n%echo Done"

$batchFile = "$sshGpgHome\keygen-batch.txt"
$batchContent | Out-File -FilePath $batchFile -Encoding ASCII

try {
    & gpg --batch --generate-key $batchFile
    
    Write-Host "`n✓ GPG key generated successfully!" -ForegroundColor Green
    Write-Host "`nYour keys:" -ForegroundColor White
    & gpg --list-keys
    
    # Get the key ID
    $keyInfo = & gpg --list-keys --keyid-format LONG $email 2>&1
    $keyId = ($keyInfo | Select-String -Pattern "pub\s+\w+/([A-F0-9]+)" | ForEach-Object { $_.Matches.Groups[1].Value })
    
    if ($keyId) {
        Write-Host "`nKey ID: $keyId" -ForegroundColor Green
        Write-Host "`nTo use this key with git-crypt:" -ForegroundColor White
        Write-Host "  git-crypt init" -ForegroundColor Gray
        Write-Host "  git-crypt add-gpg-user $keyId" -ForegroundColor Gray
    }
    
    # Export for backup
    Write-Host "`n=== Backup Instructions ===" -ForegroundColor Cyan
    Write-Host "Your GPG keyring is stored in: $sshGpgHome" -ForegroundColor White
    Write-Host "Linked from default location: $defaultGpgHome" -ForegroundColor White
    Write-Host "This directory should be synced with your other machines." -ForegroundColor White
    Write-Host "`nOptionally, export your private key for additional backup:" -ForegroundColor Yellow
    if ($keyId) {
        Write-Host "  gpg --export-secret-keys --armor $keyId > ~/.ssh/gpg-private-key.asc" -ForegroundColor Gray
        Write-Host "  (Keep this file VERY secure!)" -ForegroundColor Red
    }
    
} finally {
    # Clean up batch file
    if (Test-Path $batchFile) {
        Remove-Item $batchFile -Force
    }
}

Write-Host ""
