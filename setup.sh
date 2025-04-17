#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Homebrew on macOS
install_homebrew() {
    if ! command_exists brew; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "Homebrew is already installed"
    fi
}

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected macOS"
    
    # Install Homebrew if not installed
    install_homebrew
    
    # Install Python 3.11 if not installed
    if ! command_exists python3.11; then
        echo "Installing Python 3.11..."
        brew install python@3.11
    else
        echo "Python 3.11 is already installed"
    fi
    
    # Install Tesseract
    if ! command_exists tesseract; then
        echo "Installing Tesseract OCR..."
        brew install tesseract
    else
        echo "Tesseract OCR is already installed"
    fi
    
    # Install Ollama if not installed
    if ! command_exists ollama; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "Ollama is already installed"
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "Detected Linux"
    
    # Update package list
    sudo apt-get update
    
    # Install Python 3.11 if not installed
    if ! command_exists python3.11; then
        echo "Installing Python 3.11..."
        sudo apt-get install -y python3.11 python3.11-venv
    else
        echo "Python 3.11 is already installed"
    fi
    
    # Install Tesseract
    if ! command_exists tesseract; then
        echo "Installing Tesseract OCR..."
        sudo apt-get install -y tesseract-ocr
    else
        echo "Tesseract OCR is already installed"
    fi
    
    # Install Ollama if not installed
    if ! command_exists ollama; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "Ollama is already installed"
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install uv package manager
echo "Installing uv package manager..."
pip install uv

# Install requirements using uv
echo "Installing project requirements..."
uv pip install -r requirements.txt

# Start Ollama service in the background
echo "Starting Ollama service..."
ollama serve > /dev/null 2>&1 &
OLLAMA_PID=$!
echo "Waiting for Ollama service to initialize..."
sleep 5  # Give Ollama time to start up

# Pull Llama 3.2 model
echo "Pulling Llama 3.2 model..."
ollama pull llama3.2

echo "Setup complete!"


