#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Install development tools using winget (idempotent)

.DESCRIPTION
    Installs Git, GNU Make, curl, bun, Docker Desktop, Python 3.14, and SQLite CLI Tools using winget.
    Safe to run multiple times - winget will skip already-installed packages.

    Git is installed with:
    - Unix tools added to PATH
    - Windows Terminal integration
    - No shell integration (no "Git Bash Here" or "Git GUI Here" context menu entries)

.NOTES
    Package Manager Strategy:
    - Use winget if possible (preferred, official Windows package manager)
    - Fall back to chocolatey only if winget does not have the package you want
    - Search winget first: winget search <package-name>
    - If not found, use choco: choco install <package-name>

.EXAMPLE
    .\setup-dev-tools.ps1
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Color output helpers
function Write-Step {
    param([string]$Message)
    Write-Host ">>> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

# Check if winget is available
function Test-WingetAvailable {
    try {
        $null = Get-Command winget -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Install a package via winget (idempotent)
function Install-WingetPackage {
    param(
        [string]$PackageId,
        [string]$DisplayName,
        [string]$CustomParams = $null
    )

    Write-Step "Checking $DisplayName..."

    try {
        # Build winget command
        $wingetArgs = @(
            "install"
            "--id", $PackageId
            "--silent"
            "--accept-source-agreements"
            "--accept-package-agreements"
        )

        # Add custom parameters if provided
        if ($CustomParams) {
            $wingetArgs += "--override"
            $wingetArgs += $CustomParams
        }

        # winget install is idempotent - it won't reinstall if already present
        $result = & winget $wingetArgs 2>&1

        # Check if already installed
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$DisplayName is installed"
            return $true
        }
        elseif ($result -match "already installed") {
            Write-Success "$DisplayName is already installed"
            return $true
        }
        else {
            Write-Fail "Failed to install $DisplayName (exit code: $LASTEXITCODE)"
            Write-Host $result
            return $false
        }
    }
    catch {
        Write-Fail "Error installing ${DisplayName}: $_"
        return $false
    }
}

# Main installation flow
function Install-DevTools {
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Magenta
    Write-Host "  Development Tools Setup (winget)" -ForegroundColor Magenta
    Write-Host "=====================================" -ForegroundColor Magenta
    Write-Host ""

    # Check winget availability
    if (-not (Test-WingetAvailable)) {
        Write-Fail "winget is not available. Please install App Installer from Microsoft Store."
        exit 1
    }

    Write-Success "winget is available"
    Write-Host ""

    # Define packages to install
    $packages = @(
        @{
            Id = "Git.Git"
            Name = "Git"
            # Unix tools in PATH + no context menu entries
            # PathOption=CmdTools: Git + Unix tools in PATH
            # COMPONENTS: Exclude ext\shellhere and ext\guihere to disable context menu
            CustomParams = "/VERYSILENT /NORESTART /NOCANCEL /SP- /o:PathOption=CmdTools /COMPONENTS=`"icons,gitlfs,assoc,assoc_sh,autoupdate,windowsterminal`""
        },
        @{ Id = "GnuWin32.Make"; Name = "GNU Make" },
        @{ Id = "cURL.cURL"; Name = "curl" },
        @{ Id = "Oven-sh.Bun"; Name = "bun" },
        @{ Id = "Docker.DockerDesktop"; Name = "Docker Desktop" },
        @{ Id = "Python.Python.3.14"; Name = "Python 3.14" },
        @{ Id = "SQLite.SQLite"; Name = "SQLite CLI Tools" }
    )

    $results = @()
    foreach ($pkg in $packages) {
        if ($pkg.CustomParams) {
            $success = Install-WingetPackage -PackageId $pkg.Id -DisplayName $pkg.Name -CustomParams $pkg.CustomParams
        }
        else {
            $success = Install-WingetPackage -PackageId $pkg.Id -DisplayName $pkg.Name
        }
        $results += @{ Name = $pkg.Name; Success = $success }
    }

    # Summary
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Magenta
    Write-Host "  Installation Summary" -ForegroundColor Magenta
    Write-Host "=====================================" -ForegroundColor Magenta
    Write-Host ""

    $allSuccess = $true
    foreach ($result in $results) {
        if ($result.Success) {
            Write-Success $result.Name
        }
        else {
            Write-Fail $result.Name
            $allSuccess = $false
        }
    }

    Write-Host ""
    if ($allSuccess) {
        Write-Success "All tools installed successfully!"
        Write-Host ""

        # Call additional setup scripts (same order as 'make setup')
        Write-Host "=====================================" -ForegroundColor Magenta
        Write-Host "  Running Additional Setup Scripts" -ForegroundColor Magenta
        Write-Host "=====================================" -ForegroundColor Magenta
        Write-Host ""

        # 1. Setup git-crypt (installs GPG and git-crypt)
        $scriptPath = Join-Path $PSScriptRoot "setup-git-crypt.ps1"
        if (Test-Path $scriptPath) {
            Write-Step "Running setup-git-crypt.ps1..."
            try {
                & pwsh -ExecutionPolicy Bypass -File $scriptPath
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "git-crypt setup completed"
                }
                else {
                    Write-Warning "git-crypt setup returned exit code $LASTEXITCODE"
                }
            }
            catch {
                Write-Warning "git-crypt setup encountered an error: $_"
            }
        }
        else {
            Write-Warning "setup-git-crypt.ps1 not found, skipping"
        }

        Write-Host ""

        # 2. Setup GPG key (requires GPG from previous step)
        $scriptPath = Join-Path $PSScriptRoot "setup-gpg-key.ps1"
        if (Test-Path $scriptPath) {
            Write-Step "Running setup-gpg-key.ps1..."
            try {
                & pwsh -ExecutionPolicy Bypass -File $scriptPath
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "GPG key setup completed"
                }
                else {
                    Write-Warning "GPG key setup returned exit code $LASTEXITCODE"
                }
            }
            catch {
                Write-Warning "GPG key setup encountered an error: $_"
            }
        }
        else {
            Write-Warning "setup-gpg-key.ps1 not found, skipping"
        }

        Write-Host ""
        Write-Host "=====================================" -ForegroundColor Magenta
        Write-Host "  Setup Complete" -ForegroundColor Magenta
        Write-Host "=====================================" -ForegroundColor Magenta
        Write-Host ""
        Write-Warning "IMPORTANT: You may need to restart your terminal or machine for PATH changes to take effect."
        Write-Warning "Docker Desktop requires manual startup after installation."
        exit 0
    }
    else {
        Write-Fail "Some installations failed. See output above."
        exit 1
    }
}

# Run installation
Install-DevTools
