#!/usr/bin/env bash
# ============================================================================
# run_106_rerun.sh — Giao CCD HEADLESS chay TASK-106 (per-month distributed),
#                    HIEN LOG realtime (khong im lang) + luu log.
# Chay trong GIT BASH:   bash run_106_rerun.sh
#   (KHONG dan trong phien `claude` interactive; KHONG chay 2 instance cung luc.)
# Theo doi tien trinh chi tiet cua chinh agent: tail -f /d/claudedata/agent106.log
# ============================================================================
set -uo pipefail
REPO="/e/educa/source/github/20260415/BinanceFuturesJava"
DATA="/d/claudedata"; mkdir -p "$DATA"
RUNLOG="$DATA/run106-headless.log"

command -v claude >/dev/null 2>&1 || { echo "❌ KHONG thay 'claude' tren PATH. Cai Claude Code CLI hoac dung duong dan day du."; exit 1; }
cd "$REPO" || { echo "❌ KHONG cd duoc $REPO"; exit 1; }

PROMPT=$(cat <<'PROMPT'
Ban la CCD headless chay doc lap, TU QUYET theo spec, KHONG hoi giua chung (gom cau hoi cuoi).
DOC TRUOC (cwd hien tai): docs/CORE.md + docs/index.md + docs/KAGGLE_RULES.md + docs/rules/code.md + docs/rules/task-workflow.md + docs/db/index.md.
THUC THI task: tasks/106-reexport-features-with-filter.md (doc ky, lam dung tung buoc B1..B7).

QUAN TRONG - chay 2 PHA:
- Pha A (B1-B3): build jar + VIET code ExportFundingMaster/Worker (generalize tu research/oibackfill/BackfillOiMaster+Worker) + smoke 1 thang (202101) + VALIDATE CHAT 8 diem (gom recompute tay tu Aerospike 226, no-leak, filter dong nhat).
- CHI sang Pha B (B4-B7: enqueue full 66 thang + 5 worker tu claim + tai ve local + validate tong) KHI B3 validate PASS.
- B3 FAIL bat ky diem nao -> DUNG pha A, ghi report, sua roi smoke lai. KHONG enqueue full khi smoke chua PASS.

TUAN TUYET DOI docs/CORE.md: cam ghi o C (dung /d/claudedata); sanitize config/PrivateConfig.java truoc moi upload Kaggle; 226 READ-ONLY cho feature (khong dung live BinanceDataIngestor/BinanceOrderTradingManager, Redis, 242, HPO user); khong pkill/killall (chi kill PID minh spawn); System.exit(0) cuoi main tool batch; SLF4J khong System.out.

Ghi tien trinh (moi buoc 1 dong + timestamp) vao /d/claudedata/agent106.log.
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

echo "$(date '+%H:%M:%S') === KHOI DONG headless TASK-106 (per-month) ===" | tee -a "$RUNLOG"
echo "Theo doi chi tiet agent: tail -f /d/claudedata/agent106.log" | tee -a "$RUNLOG"

# --verbose: in tung buoc/tool-use (khong im lang). Prompt qua stdin (tranh gioi han do dai arg Windows).
# tee: vua hien len man hinh vua luu $RUNLOG.
printf '%s\n' "$PROMPT" | claude -p --verbose --dangerously-skip-permissions 2>&1 | tee -a "$RUNLOG"

echo "$(date '+%H:%M:%S') === headless ket thuc. Doc docs/reports/106.md + $RUNLOG ===" | tee -a "$RUNLOG"
