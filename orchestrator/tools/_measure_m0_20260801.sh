#!/usr/bin/env bash
# M0 (spec §5) — A/B đo cơ chế trailing + DCA, HARNESS-FREE (đọc raw PnL/maxDD/held, bỏ verdict).
# Tuan tu, 1 JVM/luot (an toan RAM box 23G). Ghi ket qua append vao OUT.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CE="$HERE/../ce.sh"
JAR=/home/ubuntu/java/simulator/gatecount.jar
DS=/home/ubuntu/claudedata/wfo_ds_oiz75
OUT=/tmp/m0_results.tsv
COMMON="WFO_N_SAMPLES=1,SIM_APPLY_FUNDING=true,WFO_JAR=$JAR"

# config theo TEN -> extra_env (khong dau phay TRONG gia tri -> dung SCALAR cho grid)
cfg_env () {
  case "$1" in
    B0)      echo "" ;;                                              # DCA cu + trailing min/cap (baseline)
    Tfloor)  echo "TS_GIVEBACK_FLOOR=true,TS_MIN_GAP=0.01" ;;        # chi doi trailing: max/floor
    Doff)    echo "WFO_DISABLE_DCA=1" ;;                             # tat DCA hoan toan
    Dgrid)   echo "DCA_GRID_ENABLED=true,DCA_GRID_SCALAR=true,DCA_GRID_L1=-0.50,DCA_GRID_STEP=0.20,DCA_GRID_LEGS=3,DCA_GRID_W_RATIO=2.0,DCA_GRID_SCALE=8,SIM_BREAKER_MODE=OFF,DCA_TIER_MARGIN_ENABLED=true,DCA_TIER_CAP_BASE=0.50,DCA_TIER_CAP_STEP=0.10" ;;
  esac
}

echo -e "# M0 start $(date -u +%FT%TZ)\twindow\tconfig\tsummary\tBT_metrics\ttier" > "$OUT"
for W in 15 13; do
  for name in B0 Tfloor Doff Dgrid; do
    extra="$(cfg_env "$name")"
    env="$COMMON"; [ -n "$extra" ] && env="$COMMON,$extra"
    log="/tmp/m0_${W}_${name}.log"
    echo "[run] w$W $name ..." >&2
    bash "$CE" wfo_verify "$DS" "$W" "$env" > "$log" 2>&1
    summ="$(grep -oE '"summary": "[^"]*"' "$log" | head -1 | sed 's/"summary": //')"
    bt="$(grep -oE 'note=[A-Z_]+ trades=[0-9]+ pnl=[-0-9.]+ ddPct=[-0-9.]+ maxDD=[-0-9.]+ held>7d=[0-9.]+' "$log" | tail -1)"
    tier="$(grep -oE 'blockCount=[0-9]+' "$log" | tail -1)"
    printf '%s\tw%s\t%s\t%s\t%s\t%s\n' "$(date -u +%T)" "$W" "$name" "${summ:-NA}" "${bt:-NA}" "${tier:-NA}" >> "$OUT"
  done
done
echo "ALL_DONE $(date -u +%FT%TZ)" >> "$OUT"
