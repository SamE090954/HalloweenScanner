
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
$PYTHON_VERSION = "3.11"
$XQUARTZ_TIMEOUT = 10
$LOG_FILE = "halloweenscanner.log"
$REQUIRED_DIRS = @("photos", "background/patterns")

# Logging setup
if (Test-Path $LOG_FILE) {
    Clear-Content $LOG_FILE
}

Start-Transcript -Path $LOG_FILE -Append | Out-Null

# Function to show progress
function show_progress {
    param([string]$Message)

    Write-Host $Message -ForegroundColor Blue
}

# Function to show error and exit
function error_exit {
    param([string]$Message)

    Write-Host "Error: $Message" -ForegroundColor Red
    Write-Host "Check $LOG_FILE for details"

    throw $Message
}

# Function to show warning
function show_warning {
    param([string]$Message)

    Write-Host "Warning: $Message" -ForegroundColor Yellow
}

# Function to check if XQuartz is running
function is_xquartz_running {

    # Windows uses native graphics instead of XQuartz
    return $true
}

# Function to check if virtual environment exists and is valid
function check_venv {

    return (
        (Test-Path "venv" -PathType Container) -and
        (Test-Path "venv\Scripts\Activate.ps1") -and
        (Test-Path "venv\Scripts\python.exe")
    )
}

# Function to check Python version
function check_python_version {

    $version = & ".\venv\Scripts\python.exe" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'

    return ($version -eq $PYTHON_VERSION)
}

# Function to check OpenGL
function check_opengl {

    & ".\venv\Scripts\python.exe" -c "import OpenGL.GL" 2>$null

    return ($LASTEXITCODE -eq 0)
}

# Function to check required directories
function check_directories {

    foreach ($dir in $REQUIRED_DIRS) {

        if (-not (Test-Path $dir -PathType Container)) {
            error_exit "Required directory '$dir' not found"
        }
    }
}

# Function to start XQuartz
function start_xquartz {

    # Windows uses native OpenGL support
    if (-not (Test-Path "$env:SystemRoot\System32\opengl32.dll")) {
        show_warning "Windows OpenGL library not found."
        return $false
    }

    return $true
}

# Main function
function main {

    show_progress "🎃 Starting HalloweenScanner..."
    Write-Host "Log file: $LOG_FILE"

    # Check if we're in the right directory
    if (-not (Test-Path "main_halloween.py" -PathType Leaf)) {
        error_exit "main_halloween.py not found. Please run this script from the HalloweenScanner directory"
    }

    # Check required directories
    check_directories

    # Check virtual environment
    if (-not (check_venv)) {
        error_exit "Virtual environment not found or invalid. Please run .\setup.ps1 first"
    }

    # Activate virtual environment
    $activate = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"

    try {
        . $activate
    }
    catch {
        error_exit "Failed to activate virtual environment. Please run .\setup.ps1 to recreate it"
    }

    # Verify Python version
    if (-not (check_python_version)) {
        error_exit "Wrong Python version (expected $PYTHON_VERSION). Please run .\setup.ps1 to fix Python environment"
    }

    # Verify OpenGL
    if (-not (check_opengl)) {
        error_exit "OpenGL not working properly. Please check your Windows graphics drivers and FreeGLUT installation."
    }

    # Start XQuartz
    if (-not (start_xquartz)) {
        error_exit "Failed to initialize Windows graphics support"
    }

    # Set display for OpenGL
    # Native Windows OpenGL does not require DISPLAY

    # Run the application
    show_progress "Starting HalloweenScanner application..."

    & ".\venv\Scripts\python.exe" "main_halloween.py"

    $exit_code = $LASTEXITCODE

    # Exit code 0 means normal termination (ESC pressed)
    if ($exit_code -eq 0) {

        Write-Host "`nThanks for using HalloweenScanner!" -ForegroundColor Green

        return
    }
    else {

        Write-Host "`nHalloweenScanner encountered an error (exit code: $exit_code)" -ForegroundColor Red

        throw "Application exited with code $exit_code"
    }
}

# Run main function
try {
    main
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
finally {
    Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
}

