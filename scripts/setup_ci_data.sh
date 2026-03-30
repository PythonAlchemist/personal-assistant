#!/usr/bin/env bash
set -euo pipefail

# Create data directory structure
mkdir -p data/tokens

# Write .env with API tokens
cat > data/.env << EOF
TODOIST_API_TOKEN=${TODOIST_API_TOKEN}
EOF

# Write Google OAuth2 credentials
echo "${GOOGLE_CREDENTIALS_JSON}" > data/google_credentials.json

# Write cached Google tokens
echo "${GOOGLE_TOKEN_PERSONAL}" > data/tokens/token_personal.json
echo "${GOOGLE_TOKEN_CROSSFIT}" > data/tokens/token_crossfit.json

# Create empty database (init_db will set up schema)
touch data/assistant.db

echo "CI data directory configured."
