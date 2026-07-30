#!/bin/bash
# stage2_frozen_ab.sh — Stage-2 of "frozen leakage-free genome" experiment (R-vs-M, Probe C step-2).
# Waits for stage1 (STAGE1_DONE), derives element-wise MEDIAN of the pre-2023 bestGenome vectors
# (w0-3), FORCES MIN_MOMENTUM_15M=0.010, writes frozen CSV (names[] order), then runs:
#   Branch A = FROZEN leakage-free genome (WFO_FROZEN_GENOME, N=1) over windows 0-16.
#   Branch B = baseline production defaults (NO frozen, N=1) over windows 0-16.
# Both: rank-K8, DCA off, MOM15=0.010, funding-on (SIM_APPLY_FUNDING=true), TICKER_SOURCE=file.
# Detached via `ce bg_run`. Markers: STAGE2_GENOME / BRANCHA_WIN <w> / BRANCHA_DONE / BRANCHB_WIN <w> /
#   BRANCHB_DONE / STAGE2_DONE / STAGE2_ABORT / STAGE2_ERROR. Report uses w4-16.
set -u
STAGE1LOG=/home/ubuntu/claudedata/.run/stage1_frozen.log
GENOME=/home/ubuntu/claudedata/frozen_genome_pre2023.csv
JAR=/home/ubuntu/java/simulator/binance-lf-frozen-1.0.0.jar
DS=wfo_ds_ret2wf_4h_ff
OUTA=/home/ubuntu/claudedata/.run/stage2_branchA.log
OUTB=/home/ubuntu/claudedata/.run/stage2_branchB.log
cd /home/ubuntu/java/simulator || { echo "STAGE2_ERROR cd fail"; exit 1; }

# --- wait for stage1 DONE (max ~3h, poll 30s) ---
echo "STAGE2_WAIT_STAGE1 $(date -u +%FT%TZ)"
for i in $(seq 1 360); do
  if grep -q STAGE1_DONE "$STAGE1LOG" 2>/dev/null; then break; fi
  sleep 30
done
grep -q STAGE1_DONE "$STAGE1LOG" || { echo "STAGE2_ABORT stage1 timeout (khong thay STAGE1_DONE)"; exit 1; }

# --- derive median genome, force MOM15=0.010 ---
python3 - "$STAGE1LOG" "$GENOME" <<'PY'
import sys, json, re, statistics
log, out = sys.argv[1], sys.argv[2]
names = ["MIN_MOMENTUM_15M","PREDICT_SYMBOL_RATE_MAX_THRESHOLD","AI_DYNAMIC_MULTIPLIER",
         "AI_DYNAMIC_MIN","HARD_RISK_LIMIT_4H","MS_DOWN_BIG_AVG","DCA_LOSS_BIG_DOWN",
         "DCA_TIME_BIG_DOWN","RATE_PROFIT_STOP_MARKET","TS_PROFIT_MULTIPLIER","TS_DYNAMIC_K",
         "TS_MAX_GAP","TS_MAX_GAP_WEAK","TS_WEAK_MOMENTUM_THRES","BUDGET_MARGIN_RATIO_1",
         "BUDGET_MARGIN_RATIO_2","BUDGET_DIVIDER_2"]
genomes = []
for line in open(log):
    m = re.search(r'RESULT_JSON (\{.*\})', line)
    if not m:
        continue
    r = json.loads(m.group(1))
    bg = r.get("bestGenome")
    if bg:
        genomes.append(bg)
if not genomes:
    sys.exit("STAGE2_ERROR: khong parse duoc bestGenome tu stage1 log")
med = {}
for n in names:
    vals = [g[n] for g in genomes if n in g]
    med[n] = statistics.median(vals)
med["MIN_MOMENTUM_15M"] = 0.010
open(out, "w").write(",".join(repr(med[n]) for n in names) + "\n")
print("N_WINDOWS_USED %d" % len(genomes))
PY
[ -s "$GENOME" ] || { echo "STAGE2_ERROR derive genome fail"; exit 1; }
echo "STAGE2_GENOME $(cat $GENOME)"

COMMON="WFO_N_SAMPLES=1 SELECTOR_RANK_TOPK=8 WFO_DISABLE_DCA=1 SIM_MIN_MOMENTUM_15M=0.010 SIM_APPLY_FUNDING=true TICKER_SOURCE=file WFO_DATA_DIR=$DS"

# --- Branch A: FROZEN leakage-free genome ---
: > "$OUTA"
echo "BRANCHA_BEGIN $(date -u +%FT%TZ)" | tee -a "$OUTA"
for W in $(seq 0 16); do
  env $COMMON WFO_FROZEN_GENOME=$GENOME java -Xmx8g -cp "$JAR" \
    com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow "$W" > /tmp/A_w${W}.log 2>&1
  RC=$?
  echo "BRANCHA_WIN $W rc=$RC $(grep -a RESULT_JSON /tmp/A_w${W}.log | tail -1)" | tee -a "$OUTA"
done
echo "BRANCHA_DONE $(date -u +%FT%TZ)" | tee -a "$OUTA"

# --- Branch B: baseline production defaults (no frozen) ---
: > "$OUTB"
echo "BRANCHB_BEGIN $(date -u +%FT%TZ)" | tee -a "$OUTB"
for W in $(seq 0 16); do
  env $COMMON java -Xmx8g -cp "$JAR" \
    com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow "$W" > /tmp/B_w${W}.log 2>&1
  RC=$?
  echo "BRANCHB_WIN $W rc=$RC $(grep -a RESULT_JSON /tmp/B_w${W}.log | tail -1)" | tee -a "$OUTB"
done
echo "BRANCHB_DONE $(date -u +%FT%TZ)" | tee -a "$OUTB"
echo "STAGE2_DONE $(date -u +%FT%TZ)"
