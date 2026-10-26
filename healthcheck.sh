#!/bin/sh
# Local container health check. When API keys are enabled, send a valid
# key rather than exempting all loopback requests from authentication.
set -eu

url="http://127.0.0.1:${PORT:-8001}/api/v2/system/health"
case "${API_KEY_ENABLED:-false}" in
  1|[Tt][Rr][Uu][Ee])
    key="${API_KEYS%%,*}"
    [ -n "$key" ] || exit 1
    exec curl -fsS --max-time 4 -o /dev/null \
      -H "${API_KEY_HEADER:-X-API-Key}: $key" "$url"
    ;;
esac

exec curl -fsS --max-time 4 -o /dev/null "$url"
