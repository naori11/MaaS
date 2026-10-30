#!/usr/bin/env bash
set -euo pipefail

# MaaS Identity and Session Flow Verification

BASE_URL="${1:-https://localhost}"
BASE_URL="${BASE_URL%/}"

# Create a secure temporary directory and ensure it is cleaned up on exit
TEMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'maas-auth')"
trap 'rm -rf "$TEMP_DIR"' EXIT

# Generate unique random ID for user isolation
if command -v uuidgen >/dev/null 2>&1; then
  RANDOM_ID=$(uuidgen | tr -d '-' | tr '[:upper:]' '[:lower:]')
elif [ -f /proc/sys/kernel/random/uuid ]; then
  RANDOM_ID=$(tr -d '-' < /proc/sys/kernel/random/uuid)
elif command -v openssl >/dev/null 2>&1; then
  RANDOM_ID=$(openssl rand -hex 16)
else
  RANDOM_ID="$$-${RANDOM}-${RANDOM}"
fi

EMAIL="slice2-${RANDOM_ID}@example.com"
BODY_FILE="$TEMP_DIR/request_body.json"

cat <<EOF > "$BODY_FILE"
{"email":"$EMAIL","password":"Password123!"}
EOF

# Helper function to invoke requests via curl
invoke_request() {
  local method="$1"
  local path="$2"
  local output_file="$3"
  local body_file="${4:-}"
  local bearer_token="${5:-}"

  local curl_args=(
    "-k"
    "-sS"
    "-X" "$method"
    "-o" "$output_file"
    "-w" "%{http_code}"
  )

  if [ -n "$body_file" ]; then
    curl_args+=("-H" "Content-Type: application/json" "--data-binary" "@$body_file")
  fi

  if [ -n "$bearer_token" ]; then
    curl_args+=("-H" "Authorization: Bearer $bearer_token")
  fi

  curl_args+=("${BASE_URL}${path}")

  local http_code
  http_code=$(curl "${curl_args[@]}")
  echo "$http_code"
}

assert_status() {
  local step="$1"
  local actual="$2"
  local expected="$3"
  local resp_file="$4"

  if [ "$actual" -ne "$expected" ]; then
    local body=""
    [ -f "$resp_file" ] && body=$(cat "$resp_file")
    echo "FAIL: $step expected HTTP $expected but received HTTP $actual: $body" >&2
    exit 1
  fi

  echo "PASS: $step (HTTP $expected)"
}

# Step 1: Register a new user
REGISTER_RESP="$TEMP_DIR/register_response.json"
STATUS=$(invoke_request "POST" "/api/v1/auth/register" "$REGISTER_RESP" "$BODY_FILE")
assert_status "Register a new user" "$STATUS" 201 "$REGISTER_RESP"

# Step 2: Log in and receive a JWT
LOGIN_RESP="$TEMP_DIR/login_response.json"
STATUS=$(invoke_request "POST" "/api/v1/auth/login" "$LOGIN_RESP" "$BODY_FILE")
assert_status "Log in and receive a JWT" "$STATUS" 200 "$LOGIN_RESP"

# Extract access_token (supports jq, python3, python, or fallback regex)
TOKEN=""
if command -v jq >/dev/null 2>&1; then
  TOKEN=$(jq -r '.access_token // empty' "$LOGIN_RESP")
elif command -v python3 >/dev/null 2>&1; then
  TOKEN=$(python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', '') or '')" < "$LOGIN_RESP")
elif command -v python >/dev/null 2>&1; then
  TOKEN=$(python -c "import sys, json; print(json.load(sys.stdin).get('access_token', '') or '')" < "$LOGIN_RESP")
else
  TOKEN=$(grep -o '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' "$LOGIN_RESP" | sed -E 's/.*"access_token"[[:space:]]*:[[:space:]]*"([^"]*)"/\1/')
fi
TOKEN="${TOKEN//$'\r'/}"

if [ -z "$TOKEN" ]; then
  echo "FAIL: Login returned HTTP 200 but did not include access_token." >&2
  exit 1
fi

# Step 3: Reject a protected request without a token
UNAUTH_RESP="$TEMP_DIR/unauth_response.json"
STATUS=$(invoke_request "GET" "/api/v1/ledger/transactions" "$UNAUTH_RESP")
assert_status "Reject a protected request without a token" "$STATUS" 401 "$UNAUTH_RESP"

# Step 4: Allow a protected request with the issued JWT
AUTH_RESP="$TEMP_DIR/auth_response.json"
STATUS=$(invoke_request "GET" "/api/v1/ledger/transactions" "$AUTH_RESP" "" "$TOKEN")
assert_status "Allow a protected request with the issued JWT" "$STATUS" 200 "$AUTH_RESP"
