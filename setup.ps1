# Run as administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {  
    Write-Warning "Please run this script as Administrator!"
    break
}

# Function to check if a command exists
function Test-CommandExists {
    param ($command)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'stop'
    try {
        if (Get-Command $command) { return $true }
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

# Install Chocolatey if not installed
if (-not (Test-CommandExists choco)) {
    Write-Host "Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    refreshenv
} else {
    Write-Host "Chocolatey is already installed"
}

# Install Python 3.11 if not installed
if (-not (Test-CommandExists python)) {
    Write-Host "Installing Python 3.11..."
    choco install python311 -y
    refreshenv
} else {
    Write-Host "Python is already installed"
}

# Install Tesseract OCR
if (-not (Test-CommandExists tesseract)) {
    Write-Host "Installing Tesseract OCR..."
    choco install tesseract -y
    refreshenv
} else {
    Write-Host "Tesseract OCR is already installed"
}

# Install Ollama if not installed
if (-not (Test-CommandExists ollama)) {
    Write-Host "Installing Ollama..."
    Invoke-WebRequest -Uri "https://ollama.com/download/ollama-windows.zip" -OutFile "ollama-windows.zip"
    Expand-Archive -Path "ollama-windows.zip" -DestinationPath "C:\Program Files\Ollama" -Force
    Remove-Item "ollama-windows.zip"
    # Add Ollama to PATH
    $env:Path += ";C:\Program Files\Ollama"
    [Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)
    refreshenv
} else {
    Write-Host "Ollama is already installed"
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
.\venv\Scripts\Activate.ps1

# Install uv package manager
Write-Host "Installing uv package manager..."
python -m pip install uv

# Install requirements using uv
Write-Host "Installing project requirements..."
uv pip install -r requirements.txt

# Pull Llama 3.2 model
Write-Host "Pulling Llama 3.2 model..."
ollama pull llama3.2

Write-Host "Setup complete!"

# Add note about PATH
Write-Host "`nIMPORTANT: You may need to restart your PowerShell/terminal for the PATH changes to take effect."
Write-Host "After restart, verify installation with: tesseract --version" 
