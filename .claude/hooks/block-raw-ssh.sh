#!/usr/bin/env bash
# PreToolUse hook (DRAFT - chua wire vao settings.json, xem README.md cung thu muc).
# Chan Bash raw ssh/scp toi Oracle khong qua ce.cmd => chong dot token + chong PowerShell nuot quote.
# Giao thuc Claude Code: doc JSON tu stdin; exit 2 = BLOCK (stderr hien cho agent).
payload="$(cat)"
python3 - "$payload" <<'PY'
import sys, json, re
try:
    d = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)  # khong parse duoc -> khong chan
if d.get("tool_name") != "Bash":
    sys.exit(0)
cmd = ((d.get("tool_input") or {}).get("command") or "").lower()
if re.search(r'\bce(\.cmd)?\b', cmd):     # di qua wrapper ce -> cho phep
    sys.exit(0)
if re.search(r'\b(ssh|scp)\b', cmd):
    sys.stderr.write(
        "BLOCKED: cam ssh/scp raw. Dung `orchestrator/ce.cmd <nut>` "
        "(xem docs/rules/ce-buttons.md). Can nut moi -> them vao mcp_tools-v3.py, "
        "dung tu che ssh.\n")
    sys.exit(2)
sys.exit(0)
PY
