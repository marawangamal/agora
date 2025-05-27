#!/bin/bash

# Install Node.js and npm via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Install Node LTS
nvm install --lts
nvm use --lts
echo "Done.
# nvm alias default lts/*

# echo "Done. Node/npm ready in this session."
# echo "For new terminals, run: source ~/.bashrc && source .venv/bin/activate"

# nvm use --lts