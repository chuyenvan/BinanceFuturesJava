#!/usr/bin/env bash
# =============================================================================
# gridtest_watch.sh - [GRIDTEST] CHI DOC 242 (+ gia CONG KHAI premiumIndex, khong ky) va PHANH. Cron Oracle 1' (cai/go boi gridtest_on/off,
#   dong co '# GRIDTEST_WATCH'); chay tay bat ky luc nao: bash gridtest_watch.sh
#   Dem tu luc pha A len (log full.log[.1] loc theo moc thoi gian 242): leg0 (SUBMIT legIdx=0), leg DCA (legIdx>=1), tong SUBMIT, KHAN;
#   so c3 (run/c3live_book.json) + gia mark => notional mo + lo chua thuc hien. In bang T1-T10 so bo.
#   PHANH (dat run/KILL_SWITCH token 'gridtest_watch <TS_A> <ly do>' NEU CHUA CO KS + Telegram KHAN, 1 tin/30'/ly do):
#     leg0 > GT_HARD_LEG0(3) | SUBMIT > GT_HARD_SUBMIT(12) | notional c3 > GT_HARD_NOTIONAL(300) | lo chua thuc hien < GT_HARD_UPNL(-30)
#     | dong KHAN trong log tu pha A | doc 242 loi >= 5 luot lien tiep | lay gia loi >= 5 luot lien tiep (fail-closed).
#   Nhac (1 lan): pha A du leg0 >= 2 => chay gridtest_phase_b.sh; pha A/B qua ${GT_PHASE_A_MAX_H} h.
#   Khong bao gio go KILL_SWITCH, khong restart, khong doi env. Dong cuoi: WATCH_OK ... | WATCH_ERR ...
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/gridtest_common.sh"
gt_manifest_check "$0" || { mkdir -p "$GT_SDIR"; date > "$GT_SDIR/WATCH_BROKEN"; echo "WATCH_ERR manifest"; exit 1; }
rm -f "$GT_SDIR/WATCH_BROKEN" 2>/dev/null
NM=gridtest_watch; TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S); LOG=$GT_SDIR/watch_cron.log
[ "${GT_WATCH_ONCE:-0}" = 1 ] || exec > >(trap '' HUP INT TERM PIPE; sed -u -E "$GT_SED") 2>&1
GL_SSH_TRIES=${GT_W_SSH_TRIES:-1}; GL_SSH_TIMEOUT_S=${GT_W_SSH_TIMEOUT_S:-25}
PH=$(gt_sv GT_PHASE)
case "$PH" in A|B) ;; *) echo "WATCH_OK khong co phien dang chay (GT_PHASE=${PH:-chua_co})"; exit 0;; esac
TSA=$(gt_sv GT_TS_A); SINCE=$(gt_sv GT_SINCE_A)
[[ "$SINCE" =~ ^[0-9]{14}$ ]] || { echo "WATCH_ERR state thieu GT_SINCE_A"; exit 1; }
mkdir -p "$GT_SDIR"; touch "$GT_SDIR/watch_heartbeat"
ttg() {   # $1 khoa (1 tin/30'/khoa), $2 noi dung
  local k=GT_TG_$1 now last; now=$(date +%s); last=$(gt_sv "$k"); [ -n "$last" ] && [ $((now - last)) -lt 1800 ] && return 0
  tg "[gridtest] $2" && gt_state_set "$k" "$now"
}
brake() {   # $1 ly do (chuoi ngan)
  local why; why=$(echo "$1" | tr -c 'A-Za-z0-9_.,:=+-' '_' | cut -c1-120)
  if s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo 'gridtest_watch $TSA $why' > run/KILL_SWITCH; } && [ -e run/KILL_SWITCH ]"; then
    say "PHANH: run/KILL_SWITCH DANG DAT ($why) - chan leg0 + DCA; trailing/stop van chay"
    [ -n "$(gt_sv GT_BRAKE)" ] || { gt_state_set GT_BRAKE "$why"; gt_state_set GT_BRAKE_T "$(date +%s)"; }
    ttg BRAKE "KHAN PHANH pha $PH: $why => run/KILL_SWITCH. Owner: xem gridtest_watch.sh, dong cum theo prereg (U1) roi gridtest_off.sh"
  else
    say "!! PHANH ($why) nhung KHONG dat/xac nhan duoc KILL_SWITCH (ssh?)"
    ttg BRAKEFAIL "KHAN PHANH pha $PH: $why nhung KHONG dat duoc KILL_SWITCH (ssh?) => owner: MODE=drain bash $GT_OPS/golive_live_off.sh NGAY"
  fi
}
R=$(s242in "bash -s -- $A $SINCE" <<'EOF'
A=$1; S=$2; cd "$A" || { echo "ERR=cd"; echo END_W; exit 0; }
F1=""; FK=$(head -n 1 logs/full.log 2>/dev/null | awk '{d=$1;t=$2; print substr(d,7,4) substr(d,4,2) substr(d,1,2) substr(t,1,2) substr(t,4,2) substr(t,7,2)}')
{ [ -z "$FK" ] || [ "$FK" \> "$S" ]; } && F1=logs/full.log.1
X=$(grep -ahF -e '[C3-LIVE] SUBMIT' -e 'KHAN' $F1 logs/full.log 2>/dev/null | grep -av 'Telegram respon' | grep -av 'DRY tren tai khoan chinh' \
  | awk -v S="$S" '{d=$1;t=$2; k=substr(d,7,4) substr(d,4,2) substr(d,1,2) substr(t,1,2) substr(t,4,2) substr(t,7,2); if (k >= S) print}')
echo "$X" | grep -aF '[C3-LIVE] SUBMIT' | awk '{for(i=1;i<=NF;i++){ if($i ~ /^legIdx=/){split($i,a,"="); li=a[2]} if($i ~ /^notional=/){split($i,b,"="); n+=b[2]} } if(li=="0") l0++; else if(li!="") dc++; tot++}
  END{printf "LEG0=%d\nDCA=%d\nSUBMIT=%d\nNOT_SUB=%.2f\n", l0, dc, tot, n}'
echo "$X" | grep -aF '[C3-LIVE] SUBMIT' | awk '{for(i=1;i<=NF;i++) if($i ~ /^cid=/) print "CID=" substr($i,5) " " $1 " " $2}' | tail -n 30
echo "KHAN_N=$(echo "$X" | grep -aF 'KHAN' | grep -c .)"
echo "KHAN1=$(echo "$X" | grep -aF 'KHAN' | head -1 | cut -c1-170 | tr -c 'A-Za-z0-9_ .,:=/()+-' '_')"
echo "KS=$( [ -e run/KILL_SWITCH ] && head -c 70 run/KILL_SWITCH | tr -c 'A-Za-z0-9_ .:=-' '_' || echo NONE)"
echo "NPROC=$(pgrep -fc '[B]inanceOrderTradingManager')"
echo "PUSH=$(grep -aF 'PUSH doi trang thai' logs/full.log 2>/dev/null | tail -1 | grep -aoE '(ON|OFF) \(' | cut -c1-3)"
[ -f run/c3live_book.json ] && echo "BOOK=$(base64 -w0 run/c3live_book.json)" || echo "BOOK=NONE"
echo END_W
EOF
) || R="ERR=ssh"
if ! echo "$R" | grep -qx END_W || echo "$R" | grep -q '^ERR='; then
  n=$(( $(gsn GT_WFAIL) + 1 )); gt_state_set GT_WFAIL "$n"
  say "!! doc 242 loi ($(echo "$R" | grep '^ERR=' | head -1)) luot lien tiep $n/5"
  [ "$n" -ge 5 ] && brake "doc_242_loi_${n}_luot"
  echo "WATCH_ERR doc_242 n=$n"; exit 1
fi
gt_state_set GT_WFAIL 0
w() { echo "$R" | sed -n "s/^$1=//p" | head -1; }
L0N=$(w LEG0); DCN=$(w DCA); SUBN=$(w SUBMIT); NSUB=$(w NOT_SUB); KHN=$(w KHAN_N); KSV=$(w KS)
# so c3 + gia mark (CONG KHAI) => notional mo, lo chua thuc hien
PRICES=$(if [ -n "${GT_PRICE_CMD:-}" ]; then eval "$GT_PRICE_CMD"; else curl -s -m 10 "$GT_PRICE_URL"; fi 2>/dev/null)
CALC=$(printf '%s\n%s\n' "$(w BOOK)" "$PRICES" | python3 -I -c '
import sys, json, base64
bk_b64 = sys.stdin.readline().strip(); pr = sys.stdin.read()
cl = []
if bk_b64 and bk_b64 != "NONE":
    try: cl = json.loads(base64.b64decode(bk_b64)).get("clusters") or []
    except Exception: print("BOOK_ERR=1"); cl = []
mk = {}
try:
    for p in json.loads(pr): mk[p["symbol"]] = float(p["markPrice"])
    pok = 1
except Exception: pok = 0
nc = 0; notm = 0.0; note = 0.0; upnl = 0.0; miss = []; rows = []
for c in cl:
    s = c.get("symbol"); q = 0.0; cost = 0.0; nl = 0
    for l in c.get("legs") or []:
        if l.get("state") == "CONFIRMED":
            eq = float(l.get("exec_qty") or 0); q += eq; cost += eq * float(l.get("avg_px") or 0); nl += 1
    if c.get("adj_qty") not in (None, ""): q = float(c["adj_qty"]); cost = q * float(c.get("adj_avg") or (cost / q if q else 0))
    ex = float(c.get("exit_qty") or 0); avg = cost / q if q > 0 else 0.0; qo = max(0.0, q - ex)
    nc += 1; note += qo * avg
    m = mk.get(s)
    if m is None: miss.append(s); m = avg
    notm += qo * m; upnl += qo * (m - avg)
    rows.append("%s:legs=%d:qty=%g:avg=%g:mark=%g:arm=%s" % (s, nl, qo, avg, m, str(c.get("armed")).lower()))
print("CUM=%d" % nc); print("NOT_ENTRY=%.2f" % note); print("NOT_MARK=%.2f" % notm); print("UPNL=%.2f" % upnl)
print("PRICE_OK=%d" % (1 if (pok and not miss) or nc == 0 else 0)); print("PRICE_MISS=" + ",".join(miss[:8]))
for r in rows[:20]: print("ROW=" + r)
' 2>&1)
cv() { echo "$CALC" | sed -n "s/^$1=//p" | head -1; }
CUM=$(cv CUM); NOTM=$(cv NOT_MARK); NOTE=$(cv NOT_ENTRY); UPNL=$(cv UPNL); POK=$(cv PRICE_OK)
[[ "$CUM" =~ ^[0-9]+$ ]] || { say "!! tinh so c3 loi: $(echo "$CALC" | head -3 | tr '\n' ' ')"; CUM=?; }
if [ "$POK" = 1 ]; then gt_state_set GT_PFAIL 0; else n=$(( $(gsn GT_PFAIL) + 1 )); gt_state_set GT_PFAIL "$n"; say "!! gia mark loi/thieu ($(cv PRICE_MISS)) luot $n/5 - notional dung gia vao"; fi
NOTX=$NOTM; [ "$POK" = 1 ] || NOTX=$NOTE
say "pha=$PH (A tu $TSA, moc 242 $SINCE) | leg0=$L0N leg_DCA=$DCN SUBMIT=$SUBN (notional gui $NSUB) | so: cum=$CUM notional_mo=${NOTX:-?} (gia vao ${NOTE:-?}) lo_chua_TH=${UPNL:-?} | KHAN=$KHN | KS=$KSV | process=$(w NPROC) PUSH=$(w PUSH)"
echo "$CALC" | sed -n 's/^ROW=/   cum: /p'
echo "$R" | sed -n 's/^CID=/   submit: /p' | tail -n 12
# ---- bang T so bo (chi tu log/so; T3-T8 day du: gridtest_report.sh)
say "T1 leg0 sizing: $L0N leg0 (cham +-2 %: gridtest_report.sh) | T2 DCA: $DCN leg (legIdx>=1) | T6 arm: $(echo "$CALC" | grep -c 'arm=true') cum | T9 KS: $KSV | T10 LEGACY: hau kiem moi restart"
REASON=""
[ "${L0N:-0}" -gt "$GT_HARD_LEG0" ] 2>/dev/null && REASON="$REASON leg0_${L0N}_gt_$GT_HARD_LEG0"
[ "${SUBN:-0}" -gt "$GT_HARD_SUBMIT" ] 2>/dev/null && REASON="$REASON submit_${SUBN}_gt_$GT_HARD_SUBMIT"
awk -v a="${NOTX:-0}" -v b="$GT_HARD_NOTIONAL" 'BEGIN{exit !(a+0 > b+0)}' && REASON="$REASON notional_${NOTX}_gt_$GT_HARD_NOTIONAL"
awk -v a="${UPNL:-0}" -v b="$GT_HARD_UPNL" 'BEGIN{exit !(a+0 < b+0)}' && REASON="$REASON lo_${UPNL}_lt_$GT_HARD_UPNL"
[ "${KHN:-0}" -gt 0 ] 2>/dev/null && REASON="$REASON KHAN_${KHN}"
[ "$(gsn GT_PFAIL)" -ge 5 ] 2>/dev/null && REASON="$REASON gia_loi_5_luot"
[ "$CUM" = "?" ] && REASON="$REASON so_c3_khong_doc_duoc"
if [ -n "$REASON" ]; then
  [ "${KHN:-0}" -gt 0 ] 2>/dev/null && say "KHAN dau tien: $(w KHAN1)"
  if [ "$KSV" = NONE ]; then brake "$REASON"; else say "VUOT NGUONG ($REASON) - KILL_SWITCH DA CO ('$KSV') - khong ghi de"; ttg VUOT "pha $PH vuot nguong:$REASON (KS da co: $KSV)"; fi
fi
NOW=$(date +%s)
if [ "$PH" = A ]; then
  [ "${L0N:-0}" -ge "$GT_N_LEG0" ] 2>/dev/null && [ -z "$(gt_sv GT_N_DULEG0)" ] && { say ">>> DU leg0 ($L0N >= $GT_N_LEG0): owner chay NGAY  DRY=0 bash $GT_HERE/gridtest_phase_b.sh"; tg "[gridtest] DU leg0=$L0N: owner chay gridtest_phase_b.sh (DRY=1 truoc)" && gt_state_set GT_N_DULEG0 1; }
  TA=$(gt_sv GT_T_A); [ -n "$TA" ] && [ $((NOW - TA)) -gt $((GT_PHASE_A_MAX_H * 3600)) ] && [ -z "$(gt_sv GT_N_HANA)" ] && { tg "[gridtest] pha A qua ${GT_PHASE_A_MAX_H} h (leg0=$L0N): chay gridtest_phase_b.sh (neu co cum) hoac gridtest_off.sh (0 cum)" && gt_state_set GT_N_HANA 1; }
else
  TB=$(gt_sv GT_T_B); [ -n "$TB" ] && [ $((NOW - TB)) -gt $((GT_PHASE_B_MAX_H * 3600)) ] && [ -z "$(gt_sv GT_N_HANB)" ] && { tg "[gridtest] pha B qua ${GT_PHASE_B_MAX_H} h (cum=$CUM): owner quyet dong/giu (prereg muc 7) roi gridtest_off.sh" && gt_state_set GT_N_HANB 1; }
fi
echo "WATCH_OK pha=$PH leg0=$L0N dca=$DCN submit=$SUBN cum=$CUM notional=${NOTX:-?} upnl=${UPNL:-?} khan=$KHN ks=$KSV phanh=${REASON:-khong}"
