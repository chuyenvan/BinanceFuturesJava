#!/usr/bin/env bash
# =============================================================================
# golive_make_gate_pilot.sh - [OPS6 T12b] MASTER tao file gate G-PILOT ($GATE_DIR/GOLIVE_GATE_PILOT.ok) TU BANG CHUNG (khong go tay).
#   $OPS = thu muc chua script nay (worktree A1 duyet: HEAD co trong deploy/gates/A1_APPROVED_OPS.commit). MOI tham so TUONG MINH, KHONG mac dinh:
#   PILOT_SIZE=10000|5000 OWNER_DECISION=<commit vz_e1_wt> \
#   G_EXEC="Q4_OWNER n=<so leg that> ref=<commit> <ghi chu>"  G_EXEC_EV=<file bang chung> \
#   G_EXIT="Q4_OWNER n=<so lenh thoat> ref=<commit> <ghi chu>" G_EXIT_EV=<file bang chung> \
#   MIEN_X14="MIEN|DA_SUA ref=<commit> <ghi chu>" MIEN_B2="MIEN|DA_SUA ref=<commit> ..." MIEN_C1="MIEN|DA_SUA ref=<commit> ..." \
#   [MIEN_MICRO7="MIEN ref=<commit> <ly do >= 10 ky tu>"  - CHI khi micro chua du 7 ngay] \
#     [DRY=1] bash $OPS/golive_make_gate_pilot.sh
# TU CHOI (exit 1, khong ghi) khi:
#   - PILOT_SIZE khong phai 5000 / 10000; thieu / sai dinh dang BAT KY tham so: G_EXEC, G_EXIT (TRUOT => khong pilot), MIEN_X14, MIEN_B2,
#     MIEN_C1, OWNER_DECISION; Q4_OWNER / RED_SIZE thieu n=<so mau thuc te> hoac ref=<commit>; ref / OWNER_DECISION khong phai commit trong
#     PREREG_REPO; OWNER_DECISION khong co OWNER_DECISION_FILE; file bang chung G_EXEC_EV / G_EXIT_EV thieu / rong.
#   - micro chua du 7 ngay lien tuc ke tu GL_MICRO_START (2026-11-19 09:31:00 +07, ADD1 s4.1) tru khi co MIEN_MICRO7 cua owner.
#   - 242 (CHI DOC): so process bot != 1; jar DANG chay != NJ_MD5 (golive_lib); latch != NONE (ke ca chua co file); adapter != live;
#     C3_CAPITAL dang chay >= size; boot guard T20 CHUA CAI (gl_bootguard242: md5 wrapper = c3_autodrain_prestart.sh repo + cron watchdog
#     WD_PRESTART + drop-in systemd).
# Lenh doc 242 (de audit): gl_state242 (pgrep, md5sum jar, /proc/<pid>/environ CHI cac khoa liet ke, sed env.sh, latch json, ls KS/PAUSE...),
#   gl_bootguard242 (md5sum wrapper, crontab -l, grep drop-in), dem lenh: nice grep -ah '[C3-LIVE-ORDER]' logs/full.log* | status=FILLED |
#   cid c3- (vao) / c3x- c3s- (thoat), uniq theo cid. KHONG ghi gi len 242.
# Ghi (umask 077, ban cu => .bak_<ts>): jar_md5, size, created_ms, expires_ms (+GATE_MAX_AGE_S 48 h), g_exec (+ev sha256), g_exit (+ev sha256),
#   mien_x14/b2/c1, owner_decision (commit 40 hex + sha256 file), micro_start/micro_days/micro7, so lenh that vao/thoat luc tao, latch, boot_guard,
#   c3_capital_luc_tao, dry_ts, by + ops_head, body_sha256 (dong CUOI = sha256 moi dong tren). golive_pilot_on.sh kiem bang gl_gate_pilot.
# Ma thoat: 0 da ghi (hoac DRY in) | 1 TU CHOI.
# =============================================================================
set -uo pipefail
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
gl_init golive_make_gate_pilot
PREREG_REPO=${PREREG_REPO:-/home/ubuntu/claude_master/vz_e1_wt}
OWNER_DECISION_FILE=${OWNER_DECISION_FILE:-docs/prereg/OWNER_DECISION_PILOT_1121_ADD1.md}
GL_MICRO_START=${GL_MICRO_START:-"2026-11-19 09:31:00 +07"}
MICRO_MIN_DAYS=7
G=$GATE_DIR/GOLIVE_GATE_PILOT.ok
no() { echo "TU CHOI: $*"; exit 1; }
WHY=""
need() { WHY="$WHY
  - $*"; }
one() { [[ "$1" != *$'\n'* ]] && [[ "$1" != *$'\r'* ]]; }
iscommit() { [[ "$1" =~ ^[0-9a-f]{7,40}$ ]] && git -C "$PREREG_REPO" cat-file -e "$1^{commit}" 2>/dev/null; }
refof() { printf '%s' "$1" | grep -oE '(^| )ref=[0-9a-f]{7,40}( |$)' | head -1 | sed -E 's/^ ?ref=//; s/ $//'; }
SIZE=${PILOT_SIZE:-}; GX=${G_EXEC:-}; GXE=${G_EXEC_EV:-}; GT=${G_EXIT:-}; GTE=${G_EXIT_EV:-}
MX=${MIEN_X14:-}; MB=${MIEN_B2:-}; MC=${MIEN_C1:-}; OD=${OWNER_DECISION:-}; M7=${MIEN_MICRO7:-}
echo "=== golive_make_gate_pilot $(TZ=Asia/Ho_Chi_Minh date '+%F %T') +07 DRY=${DRY:-0} ops_head=${_HC:0:12} jar pin NJ_MD5=$NJ_MD5"
# ---- tham so
case " $GL_PILOT_SIZES " in *" $SIZE "*) [ -n "$SIZE" ] || need "PILOT_SIZE thieu (chi nhan: $GL_PILOT_SIZES)";; *) need "PILOT_SIZE='$SIZE' khong hop le (chi nhan: $GL_PILOT_SIZES)";; esac
for v in "$GX" "$GT" "$MX" "$MB" "$MC" "$M7"; do one "$v" || need "tham so co ky tu xuong dong / CR"; done
if ! [[ "$GX" =~ ^(GREEN|AMBER|RED_SIZE|Q4_OWNER)\ [^\ ] ]]; then need "G_EXEC='$GX' thieu / sai (GREEN|AMBER|RED_SIZE|Q4_OWNER <dan chung>)"
elif [[ "$GX" =~ ^(Q4_OWNER|RED_SIZE) ]]; then
  [[ " $GX " =~ \ n=[0-9]+\  ]] || need "G_EXEC ${GX%% *} thieu n=<so leg that thuc te>"
  iscommit "$(refof "$GX")" || need "G_EXEC ${GX%% *} thieu ref=<commit quyet dinh owner trong $PREREG_REPO>"
fi
if [[ "$GT" =~ ^TRUOT ]]; then need "G_EXIT=TRUOT (ADD3: G-EXIT TRUOT => KHONG pilot)"
elif ! [[ "$GT" =~ ^(DAT|Q4_OWNER)\ [^\ ] ]]; then need "G_EXIT='$GT' thieu / sai (DAT|Q4_OWNER <median> <R> <n> <dan chung>)"
elif [[ "$GT" =~ ^Q4_OWNER ]]; then
  [[ " $GT " =~ \ n=[0-9]+\  ]] || need "G_EXIT Q4_OWNER thieu n=<so lenh thoat thuc te>"
  iscommit "$(refof "$GT")" || need "G_EXIT Q4_OWNER thieu ref=<commit quyet dinh owner trong $PREREG_REPO>"
fi
evsha() { [ -n "$1" ] && [ -s "$1" ] && [ -r "$1" ] && sha256sum < "$1" | cut -c1-64; }
GXS=$(evsha "$GXE") || need "G_EXEC_EV='$GXE' (file bang chung g_exec) thieu / rong"
GTS=$(evsha "$GTE") || need "G_EXIT_EV='$GTE' (file bang chung g_exit) thieu / rong"
for p in "MIEN_X14:$MX" "MIEN_B2:$MB" "MIEN_C1:$MC"; do
  n=${p%%:*}; v=${p#*:}
  if ! [[ "$v" =~ ^(MIEN|DA_SUA)\ ref=[0-9a-f]{7,40}(\ .*)?$ ]]; then need "$n='$v' thieu / sai - CHUA co quyet dinh owner (MIEN|DA_SUA ref=<commit> <ghi chu>), KHONG mac dinh"
  elif ! iscommit "$(refof "$v")"; then need "$n ref=$(refof "$v") khong phai commit trong $PREREG_REPO"; fi
done
ODF=""; ODS=""
if ! iscommit "$OD"; then need "OWNER_DECISION='$OD' khong phai commit trong $PREREG_REPO (quyet dinh owner pilot, vd 8cc2704f)"
elif ! git -C "$PREREG_REPO" cat-file -e "$OD:$OWNER_DECISION_FILE" 2>/dev/null; then need "OWNER_DECISION $OD khong co $OWNER_DECISION_FILE"
else ODF=$(git -C "$PREREG_REPO" rev-parse "$OD^{commit}"); ODS=$(git -C "$PREREG_REPO" show "$OD:$OWNER_DECISION_FILE" | sha256sum | cut -c1-64); fi
# ---- micro >= 7 ngay lien tuc
MS=$(date -d "$GL_MICRO_START" +%s 2>/dev/null) || no "GL_MICRO_START='$GL_MICRO_START' khong doc duoc"
NOWS=$(date +%s); MD=$(awk -v a="$NOWS" -v b="$MS" 'BEGIN{printf "%.2f", (a-b)/86400}')
if awk -v d="$MD" -v m="$MICRO_MIN_DAYS" 'BEGIN{exit !(d >= m)}'; then M7L="DU (>= $MICRO_MIN_DAYS ngay)"
elif [[ "$M7" =~ ^MIEN\ ref=[0-9a-f]{7,40}\ .{10,}$ ]] && iscommit "$(refof "$M7")"; then M7L="MIEN_OWNER $M7"
else need "micro moi $MD ngay < $MICRO_MIN_DAYS ke tu $GL_MICRO_START (som nhat $(TZ=Asia/Ho_Chi_Minh date -d @$((MS + MICRO_MIN_DAYS * 86400)) '+%F %T') +07); mien chi bang MIEN_MICRO7=\"MIEN ref=<commit> <ly do>\""; fi
[ "$GL_MICRO_START" = "2026-11-19 09:31:00 +07" ] || echo "!! CANH BAO: GL_MICRO_START ghi de = '$GL_MICRO_START' (khac moc ADD1 2026-11-19 09:31:00 +07) - ghi vao gate"
# ---- 242 CHI DOC
gl_read_state
for k in NPROC JAR_MD5 LATCH ENV_LIVE_ADAPTER ENV_C3_CAPITAL KILLSW_FILE PAUSE; do echo "   242: $k=$(sv $k)"; done
[ "$(sv NPROC)" = 1 ] || need "242: so process bot = $(sv NPROC) (can 1)"
[ "$(sv JAR_MD5)" = "$NJ_MD5" ] || need "242: jar DANG chay $(sv JAR_MD5) != NJ_MD5 $NJ_MD5"
[ "$(sv LATCH)" = NONE ] || need "242: latch kill-switch = $(sv LATCH) (can NONE)"
[ "$(sv ENV_LIVE_ADAPTER)" = live ] || need "242: process LIVE_ADAPTER=$(sv ENV_LIVE_ADAPTER) (can live)"
C0=$(sv ENV_C3_CAPITAL)
{ [[ "$C0" =~ ^[0-9]+$ ]] && [ -n "$SIZE" ] && [ "$C0" -lt "${SIZE:-0}" ] 2>/dev/null; } || need "242: C3_CAPITAL dang chay '$C0' khong < size '$SIZE'"
gl_bootguard242
echo "   242 boot guard: BG=$BG $BG_DETAIL"
[ "$BG" = CAI ] || need "boot guard T20 CHUA CAI ($BG: $BG_DETAIL) - owner: bash $_OPS/install_242_autodrain.sh"
NO=$(s242 "cd $A && nice -n 19 grep -ah '\[C3-LIVE-ORDER\]' logs/full.log* 2>/dev/null | grep -a 'status=FILLED' | grep -aoE 'cid=c3[xs]?-[^ ]+' | sort -u | awk '/^cid=c3-/{e++} /^cid=c3[xs]-/{x++} END{printf \"N_VAO=%d\\nN_THOAT=%d\\n\", e, x}'; echo END_NO") || NO=""
printf '%s\n' "$NO" | grep -qx END_NO || need "242: dem lenh that (log [C3-LIVE-ORDER]) loi / khong tron ven"
NV=$(printf '%s\n' "$NO" | sed -n 's/^N_VAO=//p'); NT=$(printf '%s\n' "$NO" | sed -n 's/^N_THOAT=//p')
echo "   242 lenh that FILLED (log, uniq cid): vao=${NV:-?} thoat=${NT:-?}"
DTS=$(sed -n 's/^dry_ts=//p' "$GL_MON_FLAG" 2>/dev/null | head -1)
[ -z "$WHY" ] || no "thieu / sai dieu kien G-PILOT:$WHY"
NOW=$(( NOWS * 1000 )); EXP=$(( NOW + GATE_MAX_AGE_S * 1000 ))
BODY="# G-PILOT gate - golive_make_gate_pilot.sh $(TZ=Asia/Ho_Chi_Minh date '+%F %T') (+07)
jar_md5=$NJ_MD5
size=$SIZE
created_ms=$NOW
expires_ms=$EXP
g_exec=$GX
g_exec_ev=$GXE sha256=$GXS
g_exit=$GT
g_exit_ev=$GTE sha256=$GTS
mien_x14=$MX
mien_b2=$MB
mien_c1=$MC
owner_decision=$ODF file=$OWNER_DECISION_FILE sha256=$ODS
micro_start=$GL_MICRO_START micro_days=$MD micro7=$M7L
so_lenh_that_luc_tao=vao_FILLED:$NV thoat_FILLED:$NT (log [C3-LIVE-ORDER] tren 242, uniq cid; tham khao - log co the da xoay)
latch=$(sv LATCH)
boot_guard=$BG $BG_DETAIL
c3_capital_luc_tao=$C0 dry_ts=${DTS:-khong_co}
by=MASTER golive_make_gate_pilot.sh ops_head=$_HC"
BODY="$BODY
body_sha256=$(printf '%s\n' "$BODY" | sha256sum | cut -c1-64)"
echo "$BODY"
[ "${DRY:-0}" = 1 ] && { echo "DRY=1: KHONG ghi $G"; exit 0; }
mkdir -p "$GATE_DIR" || no "khong tao duoc $GATE_DIR"
[ -f "$G" ] && cp -p "$G" "$G.bak_$(date +%s)"
( umask 077; printf '%s\n' "$BODY" > "$G.tmp" ) && mv -f "$G.tmp" "$G" || no "khong ghi duoc $G"
R=$(gl_gate_pilot "$G"); echo "$R"; echo "$R" | grep -q '^OK' || no "gate vua ghi KHONG qua gl_gate_pilot (loi script)"
echo "=== XONG: $G (het han sau $((GATE_MAX_AGE_S / 3600)) h). Tiep: DRY=1 bash $_OPS/golive_pilot_on.sh"
