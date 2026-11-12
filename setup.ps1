
# HalloweenScanner Windows Setup Script

# Exit on error, undefined variables, and command failures
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Colors for output
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Blue"
$NC = "White"

# Configuration
$MIN_DISK_SPACE = 500000  # 500MB
$MIN_MEMORY = 1000000000  # 1GB
$PYTHON_VERSION = "3.11"
$REQUIRED_DIRS = @("photos", "background/patterns")

# Progress tracking
$total_steps = 8
$current_step = 0

# Logging
$LOG_FILE = "setup.log"

# Clear existing log
if (Test-Path $LOG_FILE) {
    Clear-Content $LOG_FILE
}

Start-Transcript -Path $LOG_FILE -Append | Out-Null

# Function to show progress
function show_progress {
    param([string]$Message)

    $script:current_step++
    Write-Host "[$script:current_step/$script:total_steps] $Message" -ForegroundColor Green
}

# Function to show error and exit
function error_exit {
    param([string]$Message)

    Write-Host "Error: $Message" -ForegroundColor Red
    Write-Host "Check $LOG_FILE for details"

    Stop-Transcript | Out-Null
    exit 1
}

# Function to show warning
function show_warning {
    param([string]$Message)

    Write-Host "Warning: $Message" -ForegroundColor Yellow
}

# Function to check if a command exists
function command_exists {
    param([string]$Command)

    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

# Function to check if XQuartz is installed
function xquartz_installed {

    # Windows uses native graphics support instead of XQuartz
    return $true
}

# Function to check system requirements
function check_system_requirements {

    show_progress "Checking system requirements..."

    # Check disk space
    $drive = (Get-Location).Drive.Name

    $available_space = (Get-CimInstance Win32_LogicalDisk |
        Where-Object { $_.DeviceID -eq "${drive}:" }).FreeSpace

    if ($available_space -lt ($MIN_DISK_SPACE * 1KB)) {
        error_exit "Not enough disk space (need at least 500MB)"
    }

    # Check memory
    $available_memory = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory

    if ($available_memory -lt $MIN_MEMORY) {
        error_exit "Not enough memory (need at least 1GB)"
    }

    # Check network connectivity
    if (-not (Test-Connection github.com -Count 1 -Quiet)) {
        error_exit "No internet connection"
    }

    # Check required directories
    foreach ($dir in $REQUIRED_DIRS) {
        if (-not (Test-Path $dir -PathType Container)) {
            error_exit "Required directory '$dir' not found"
        }
    }
}

# Function to setup shell profile
function setup_shell_profile {

    show_progress "Setting up shell profile..."

    $profile = $PROFILE
    $updated = $false

    # Create profile if it doesn't exist
    if (-not (Test-Path $profile)) {
        New-Item -ItemType File -Path $profile -Force | Out-Null
    }

    # Add DISPLAY export if needed
    if ((Get-Content $profile -Raw) -notmatch 'DISPLAY') {
        Add-Content $profile '$env:DISPLAY = "localhost:0"'
        $updated = $true
    }

    if ($updated) {
        show_warning "Shell profile updated. You'll need to restart your terminal or run: . `$PROFILE"
    }
}

# Function to install/update package manager
function setup_homebrew {

    show_progress "Setting up package manager..."

    if (-not (command_exists "winget")) {
        error_exit "Windows Package Manager (winget) not found. Install App Installer."
    }

    echo "Updating package manager..."

    winget source update

    if ($LASTEXITCODE -ne 0) {
        show_warning "Failed to update package manager"
    }
}

# Function to install system dependencies
function install_dependencies {

    show_progress "Installing system dependencies..."

    # Install packages
    $packages = @(
        "Python.Python.3.11",
        "glfw.glfw",
        "FreeGLUT.FreeGLUT"
    )

    foreach ($package in $packages) {

        Write-Host "Installing $package..." -ForegroundColor Blue

        winget install --id $package --exact `
            --accept-package-agreements `
            --accept-source-agreements

        if ($LASTEXITCODE -ne 0) {
            error_exit "Failed to install $package"
        }
    }

    # Install Windows graphics support
    if (-not (xquartz_installed)) {
        echo "Installing graphics support..."
    }
}

# Function to setup Python environment
function setup_python {

    show_progress "Setting up Python environment..."

    # Verify Python version
    if (-not (command_exists "py")) {
        error_exit "Python 3.11 not found."
    }

    $version = & py -3.11 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'

    if ($version -ne $PYTHON_VERSION) {
        error_exit "Wrong Python version: $version (expected $PYTHON_VERSION)"
    }

    # Remove existing venv if present
    if (Test-Path "venv") {
        echo "Removing existing virtual environment..."
        Remove-Item "venv" -Recurse -Force
    }

    # Create and activate virtual environment
    echo "Creating virtual environment..."

    & py -3.11 -m venv venv

    if ($LASTEXITCODE -ne 0) {
        error_exit "Failed to create virtual environment"
    }

    # Activate virtual environment
    $activate = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"

    . $activate

    if (-not $env:VIRTUAL_ENV) {
        error_exit "Failed to activate virtual environment"
    }

    # Upgrade pip
    echo "Upgrading pip..."

    python -m pip install --upgrade pip

    if ($LASTEXITCODE -ne 0) {
        show_warning "Failed to upgrade pip"
    }

    # Install Python dependencies
    echo "Installing Python dependencies..."

    python -m pip install -r requirements.txt

    if ($LASTEXITCODE -ne 0) {
        error_exit "Failed to install Python dependencies"
    }
}

# Function to verify installation
function verify_installation {

    show_progress "Verifying installation..."

    # Check if virtual environment is active
    if ($env:VIRTUAL_ENV -notlike "*venv*") {
        error_exit "Virtual environment not active"
    }

    # Check if all required packages are installed
    python -c "import numpy, cv2, OpenGL, glfw"

    if ($LASTEXITCODE -ne 0) {
        error_exit "Missing required Python packages"
    }

    # Check if Windows graphics support is available
    if (-not (Test-Path "$env:SystemRoot\System32\opengl32.dll")) {
        show_warning "Windows OpenGL support was not found."
    }
}

# Main installation process
function main {

    Write-Host "🎃 Setting up HalloweenScanner..." -ForegroundColor Blue
    echo "Installation log will be saved to $LOG_FILE"

    # Run installation steps
    check_system_requirements
    setup_shell_profile
    setup_homebrew
    install_dependencies
    setup_python
    verify_installation

    # Final instructions
    show_progress "Setup complete!"

    Write-Host "✨ HalloweenScanner has been successfully installed!" -ForegroundColor Green

    echo ""
    echo "To start using HalloweenScanner:"
    echo "1. Run .\run.ps1 to start the application"
    echo ""
    echo "For troubleshooting, check:"
    echo "- Setup log: $LOG_FILE"
    echo "- Troubleshooting guide: TROUBLESHOOTING.md"
}

# Run main installation
try {
    main
}
catch {
    error_exit $_.Exception.Message
}
finally {
    if ($transcriptStarted) {
        Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
    }
}

