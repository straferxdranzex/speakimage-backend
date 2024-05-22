#!/bin/bash

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Add Rust to PATH
source $HOME/.cargo/env

# Upgrade pip
pip install --upgrade pip

# Install dependencies without building maturin from source
PIP_NO_BINARY=maturin pip install --disable-pip-version-check --target . --upgrade -r requirements.txt
