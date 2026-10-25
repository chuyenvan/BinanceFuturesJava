#!/bin/bash
# ops/killsw_reset.sh — [V12 SAFE C8] OWNER mo latch kill-switch c3_live (NO_NEW_ENTRY / FLATTEN).
# KHONG restart JVM, KHONG goi san, KHONG can python. Chi ghi 1 file yeu cau; bot (engine) tu ap dung trong ~15 s
# (hoac luc khoi dong ke tiep neu bot dang tat), roi doi ten file yeu cau thanh .done_<ms>.
#
# Cach chay (tu thu muc chay bot, noi co run/):
#   bash ops/killsw_reset.sh                 # DRY=1 mac dinh: chi xem trang thai latch, KHONG ghi gi
#   DRY=0 bash ops/killsw_reset.sh           # mo latch: phai go YES
#   DRY=0 RESET_PEAK=1 bash ops/killsw_reset.sh   # + dat lai dinh equity A40 (CHI khi da nap/rut von co chu dich)
# Bien tuy chon: RUN_DIR (mac dinh run), LIVE_KILLSW_LATCH_FILE, LIVE_KILLSW_RESET_FILE (phai TRUNG env cua bot),
#   KILLSW_RESET_LOG (mac dinh $RUN_DIR/killsw_reset.log), WAIT_S (cho bot ap dung, mac dinh 30; 0 = khong cho).
set -euo pipefail
RUN_DIR=${RUN_DIR:-run}
LATCH=${LIVE_KILLSW_LATCH_FILE:-$RUN_DIR/killsw_latch.json}
REQ=${LIVE_KILLSW_RESET_FILE:-$RUN_DIR/killsw_reset.req}
LOGF=${KILLSW_RESET_LOG:-$RUN_DIR/killsw_reset.log}
DRY=${DRY:-1}
RESET_PEAK=${RESET_PEAK:-0}
WAIT_S=${WAIT_S:-30}
case "$RESET_PEAK" in 0|1) ;; *) echo "RESET_PEAK phai la 0 hoac 1"; exit 2;; esac

echo "== kill-switch c3_live: file latch = $LATCH"
if [ -f "$LATCH" ]; then
  STATE=$(grep -o '"latch":"[A-Z_]*"' "$LATCH" | head -1 | cut -d'"' -f4 || true)
  CODES=$(grep -o '"codes":\[[^]]*\]' "$LATCH" | head -1 || true)
  echo "   trang thai: latch=${STATE:-?} ${CODES}"
  echo "   noi dung  : $(cat "$LATCH")"
else
  STATE="(chua co file)"
  echo "   chua co file latch (bot chua tung latch, hoac duong dan sai — kiem LIVE_KILLSW_LATCH_FILE cua bot)"
fi
if [ -f "$REQ" ]; then
  echo "   CANH BAO: da co yeu cau reset CHUA ap dung: $REQ ($(cat "$REQ")) — bot dang tat hoac duong dan sai?"
fi

if [ "$DRY" != "0" ]; then
  echo "== DRY=1: KHONG ghi gi. Muon mo latch: DRY=0 bash ops/killsw_reset.sh (go YES)."
  exit 0
fi

echo "== Mo latch se: latch -> NONE, xoa danh sach ma + su kien C2 trong 24h$( [ "$RESET_PEAK" = 1 ] && echo ', DAT LAI dinh equity A40')."
echo "   Dieu kien con dat (vd van mat du lieu / DD van <= -40 %) => bot latch LAI ngay."
read -r -p "Go YES de xac nhan: " ANS
if [ "$ANS" != "YES" ]; then
  echo "== Huy (khong go YES). Khong ghi gi."
  exit 3
fi

NOW_MS=$(( $(date +%s) * 1000 ))
BY=$(id -un 2>/dev/null | tr -cd 'A-Za-z0-9._-')
BY=${BY:-unknown}
mkdir -p "$(dirname "$REQ")" "$(dirname "$LOGF")"
TMP="$REQ.tmp.$$"
printf '{"reset_at_ms":%s,"reset_by":"%s","reset_peak":%s}\n' "$NOW_MS" "$BY" "$RESET_PEAK" > "$TMP"
mv -f "$TMP" "$REQ"
printf '%s by=%s reset_peak=%s latch_truoc=%s req=%s\n' "$(date -u +%FT%TZ)" "$BY" "$RESET_PEAK" "$STATE" "$REQ" >> "$LOGF"
echo "== Da ghi yeu cau $REQ ; log: $LOGF"

if [ "$WAIT_S" -gt 0 ] 2>/dev/null; then
  for _ in $(seq 1 "$WAIT_S"); do
    [ -f "$REQ" ] || break
    sleep 1
  done
  if [ -f "$REQ" ]; then
    echo "== Bot CHUA ap dung sau ${WAIT_S}s (bot tat? sai thu muc?). Yeu cau van cho; bot se ap dung khi chay."
  else
    echo "== Bot da ap dung. Trang thai moi: $(cat "$LATCH" 2>/dev/null || echo '?')"
  fi
fi
