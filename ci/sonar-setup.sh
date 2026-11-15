#!/usr/bin/env bash
# Configure an (ephemeral) SonarQube instance: admin password, strict Quality Gate, analysis token.
# Usage: SONAR_HOST_URL=http://localhost:9000 SONAR_ADMIN_PASSWORD=... ./ci/sonar-setup.sh
# Prints the analysis token on the last line of stdout.
set -euo pipefail
HOST="${SONAR_HOST_URL:-http://localhost:9000}"
NEW_PWD="${SONAR_ADMIN_PASSWORD:?SONAR_ADMIN_PASSWORD is required}"
GATE="TP2-Strict-Gate"

echo "Waiting for SonarQube at $HOST ..." >&2
for _ in $(seq 1 90); do
  status=$(curl -s "$HOST/api/system/status" | sed -n 's/.*"status":"\([A-Z_]*\)".*/\1/p')
  [ "$status" = "UP" ] && break
  sleep 5
done
[ "$status" = "UP" ] || { echo "SonarQube not UP (status=$status)" >&2; exit 1; }

# First boot: rotate the default admin/admin credentials
curl -s -o /dev/null -u admin:admin -X POST "$HOST/api/users/change_password" \
  --data-urlencode "login=admin" --data-urlencode "previousPassword=admin" \
  --data-urlencode "password=$NEW_PWD" || true
AUTH="admin:$NEW_PWD"
api() { curl -sf -u "$AUTH" -X POST "$HOST/api/$1" "${@:2}"; }

# Strict Quality Gate (overall code + new code)
api qualitygates/create --data-urlencode "name=$GATE" >/dev/null || true
cond() { api qualitygates/create_condition --data-urlencode "gateName=$GATE" \
  --data-urlencode "metric=$1" --data-urlencode "op=$2" --data-urlencode "error=$3" >/dev/null || true; }
cond coverage                       LT 85
cond new_coverage                   LT 85
cond security_hotspots_reviewed     LT 100
cond new_security_hotspots_reviewed LT 100
cond duplicated_lines_density       GT 3
cond new_duplicated_lines_density   GT 3
cond bugs                           GT 0
cond vulnerabilities                GT 0
api qualitygates/set_as_default --data-urlencode "name=$GATE" >/dev/null
echo "Quality Gate '$GATE' configured and set as default" >&2

api user_tokens/revoke --data-urlencode "name=ci-token" >/dev/null 2>&1 || true
token=$(api user_tokens/generate --data-urlencode "name=ci-token" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
[ -n "$token" ] || { echo "token generation failed" >&2; exit 1; }
echo "$token"
