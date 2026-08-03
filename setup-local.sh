#!/bin/bash
# Local Development Setup Script
# Ensures Python 3.11 is used (required for camel-oasis)

set -e

echo "=== ASKTHEPEOPLE Local Setup ==="
echo ""

# Check if pyenv is available
if command -v pyenv &> /dev/null; then
    echo "✓ pyenv detected"
    
    # Check if Python 3.11 is installed
    if pyenv versions | grep -q "3.11"; then
        echo "✓ Python 3.11 found"
        pyenv local 3.11
    else
        echo "Installing Python 3.11..."
        pyenv install 3.11.9
        pyenv local 3.11.9
    fi
else
    echo "⚠ pyenv not found. Please install Python 3.11 manually:"
    echo "  - Download from: https://www.python.org/downloads/release/python-3119/"
    echo "  - Or install pyenv: https://github.com/pyenv/pyenv#installation"
    exit 1
fi

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

echo ""
echo "Current Python: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -lt 10 ] || [ "$PYTHON_MINOR" -gt 11 ]; then
    echo "❌ ERROR: Python 3.10 or 3.11 required (you have $PYTHON_VERSION)"
    echo "   camel-oasis requires Python <3.12"
    exit 1
fi

echo "✓ Python version compatible"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
cd backend
python -m venv .venv
source .venv/Scripts/activate || source .venv/bin/activate

echo "✓ Virtual environment created"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e .

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the environment:"
echo "  cd backend"
echo "  source .venv/Scripts/activate  # Git Bash"
echo "  .venv\\Scripts\\activate        # Windows CMD"
echo ""
echo "To run the backend:"
echo "  flask run"
echo ""
