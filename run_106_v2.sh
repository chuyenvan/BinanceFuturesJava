#!/usr/bin/env bash
# ============================================================================
# run_106_v2.sh — Giao CCD HEADLESS chay TASK-106 (per-month distributed),
#                 LOG REALTIME (stream-json -> formatter) + luu day du.
# Chay GIT BASH:   bash run_106_v2.sh
#   (KHONG dan trong phien `claude` interactive; KHONG chay 2 instance cung luc.)
#
# 3 KENH log:
#   - man hinh + $READABLE : tung buoc dep ([say]/[tool]/-> ket qua/[END])
#   - $RAW                 : nguyen stream-json (soi lai day du khi can)
#   - /d/claudedata/agent106.log : nhat ky moc-buoc do CHINH agent ghi (tail -f rieng)
# ============================================================================
set -uo pipefail
REPO="/e/educa/source/github/20260415/BinanceFuturesJava"
DATA="/d/claudedata"; mkdir -p "$DATA"
RAW="$DATA/run106-stream.jsonl"
READABLE="$DATA/run106-readable.log"
FMT="$DATA/stream_fmt.py"

command -v claude >/dev/null 2>&1 || { echo "KHONG thay 'claude' tren PATH."; exit 1; }
command -v python >/dev/null 2>&1 || { echo "KHONG thay 'python'."; exit 1; }
cd "$REPO" || { echo "KHONG cd duoc $REPO"; exit 1; }

# --- formatter: doc stream-json tu stdin, in dep realtime ---
cat > "$FMT" <<'PY'
import sys, json
def short(x, n):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    s = " ".join(s.split())
    return s[:n]
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: e = json.loads(line)
    except Exception: print(line, flush=True); continue
    t = e.get("type")
    if t == "system" and e.get("subtype") == "init":
        print(f">> START model={e.get('model')} cwd={e.get('cwd')}", flush=True)
    elif t == "assistant":
        for c in e.get("message", {}).get("content", []):
            if c.get("type") == "text" and c.get("text", "").strip():
                print("[say] " + short(c["text"], 500), flush=True)
            elif c.get("type") == "tool_use":
                print(f"[tool] {c.get('name')}  {short(c.get('input', {}), 200)}", flush=True)
    elif t == "user":
        for c in e.get("message", {}).get("content", []):
            if c.get("type") == "tool_result":
                r = c.get("content", "")
                if isinstance(r, list):
                    r = " ".join(x.get("text", "") for x in r if isinstance(x, dict))
                print("   -> " + short(r, 200), flush=True)
    elif t == "result":
        print(f"[END] {e.get('subtype')} {e.get('duration_ms')}ms turns={e.get('num_turns')} cost=${e.get('total_cost_usd')}", flush=True)
    elif t == "rate_limit_event":
        ri = e.get("rate_limit_info", {})
        print(f"[rate_limit] {ri.get('status')} ({ri.get('rateLimitType')})", flush=True)
PY

PROMPT=$(cat <<'PROMPT'
Ban la CCD headless chay doc lap, TU QUYET theo spec, KHONG hoi giua chung (gom cau hoi cuoi).
DOC TRUOC (cwd hien tai): docs/CORE.md + docs/index.md + docs/KAGGLE_RULES.md + docs/rules/code.md + docs/rules/task-workflow.md + docs/db/index.md.
THUC THI task: tasks/106-reexport-features-with-filter.md (doc ky, lam dung tung buoc B1..B7).

QUAN TRONG - chay 2 PHA:
- Pha A (B1-B3): build jar + VIET code ExportFundingMaster/Worker (generalize tu research/oibackfill/BackfillOiMaster+Worker) + smoke 1 thang (202101) + VALIDATE CHAT 8 diem (gom recompute tay tu Aerospike 226, no-leak, filter dong nhat).
- CHI sang Pha B (B4-B7: enqueue full 66 thang + 5 worker tu claim + tai ve local + validate tong) KHI B3 validate PASS.
- B3 FAIL bat ky diem nao -> DUNG pha A, ghi report, sua roi smoke lai. KHONG enqueue full khi smoke chua PASS.

GHI LOG DAY (de nguoi theo doi): moi khi bat dau/ket thuc 1 buoc nho, ghi 1 dong co timestamp vao /d/claudedata/agent106.log (vd: build start/done, push kernel X, poll done N/66, validate diem (a)..(h) pass/fail). Ghi truoc khi lam, khong doi xong moi ghi.

TUAN TUYET DOI docs/CORE.md: cam ghi o C (dung /d/claudedata); sanitize config/PrivateConfig.java truoc moi upload Kaggle; 226 READ-ONLY cho feature (khong dung live BinanceDataIngestor/BinanceOrderTradingManager, Redis, 242, HPO user); khong pkill/killall (chi kill PID minh spawn); System.exit(0) cuoi main tool batch; SLF4J khong System.out.

Cuoi cung ghi docs/reports/106.md + commit (Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>) + push origin module.
KET THUC report bang block:
=== RESULT ===
STATUS: DONE|REVIEW|NEEDS_HUMAN|FAILED
COMMIT: <hash|->
ARTIFACTS: <path|->
VERIFY: <so doi chieu|->
DECISIONS: <|->
QUESTIONS: <|->
=== END ===
PROMPT
)

echo "$(date '+%H:%M:%S') === KHOI DONG headless TASK-106 (per-month) ==="
echo "Log dep: man hinh + $READABLE | Raw: $RAW | Agent moc-buoc: /d/claudedata/agent106.log"
: > "$RAW"

# stream-json (bat buoc kem --verbose) -> tach raw ra file + format dep len man hinh & file readable
printf '%s\n' "$PROMPT" \
  | claude -p --verbose --output-format stream-json --dangerously-skip-permissions 2>>"$DATA/run106-stderr.log" \
  | tee "$RAW" \
  | python "$FMT" | tee -a "$READABLE"

echo "$(date '+%H:%M:%S') === headless ket thuc. Doc docs/reports/106.md + $READABLE (raw: $RAW) ==="
