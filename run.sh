#!/bin/bash

# Check if .env file exists, if not create it from example
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "Creating .env file from .env.example..."
        cp .env.example .env
        echo "Please edit .env to add your ESPN API credentials."
        exit 1
    else
        echo "Error: Neither .env nor .env.example found."
        exit 1
    fi
fi

# If python module isn't installed, install it in development mode
# if ! python -c "import ff" &> /dev/null; then
#     echo "Installing fantasy football package in development mode..."
#     pip install -e .
# fi

# Run the weekly report generator
python -m ff weekly --open