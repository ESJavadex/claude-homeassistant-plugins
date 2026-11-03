#!/usr/bin/env bash
# Run the checkers over large public Home Assistant configs to hunt false
# positives before users do. Not part of CI (upstream repos change).
# Usage: bash homeassistant-config/tests/smoke_public_configs.sh [workdir]
# The clones are only parsed as YAML (safe loader), never executed.
set -uo pipefail
scripts=$(cd "$(dirname "$0")/../skills/homeassistant-config/scripts" && pwd)
work=${1:-$(mktemp -d)}
repos=(
  frenck/home-assistant-config CCOSTAN/Home-AssistantConfig geekofweek/homeassistant
  matt8707/hass-config basnijholt/home-assistant-config aneisch/home-assistant-config
  Burningstone91/smart-home-setup jazzyisj/home-assistant-config
  Petro31/home-assistant-config arsaboo/homeassistant-config
)
cd "$work" || exit 1
for r in "${repos[@]}"; do
  d=${r//\//_}
  [ -d "$d" ] || git clone -q --depth 1 "https://github.com/$r.git" "$d" || continue
  cfg=$(find "$d" -maxdepth 3 -name configuration.yaml | head -1)
  [ -n "$cfg" ] || continue
  root=$(dirname "$cfg")
  v=$(python3 "$scripts/validate_yaml.py" "$root" --quiet | python3 -c 'import json,sys; s=json.load(sys.stdin)["summary"]; print("E", s["errors"], "W", s["warnings"], "U", s["upcoming"], "skipped", (s.get("not_loaded") or {}).get("count", 0))')
  c=$(python3 "$scripts/check_config.py" "$root" | python3 -c 'import json,sys,collections; d=json.load(sys.stdin); print(dict(collections.Counter(i["type"] for i in d.get("issues") or [])))')
  printf '%-40s %s | check_config %s\n' "$r" "$v" "$c"
done
echo "Clones in $work. Read every error and warning: each must be real or become a test."
