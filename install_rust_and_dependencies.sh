#!/bin/bash

# Ensure this script is executable
chmod +x $0

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Add Rust to PATH
source $HOME/.cargo/env

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install --disable-pip-version-check --target . --upgrade -r requirements.txt
