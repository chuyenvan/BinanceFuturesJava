#!/usr/bin/env bash
# =============================================================================
# golive_rebase_equity.sh — [ADD4 ERRATA 2 §5 / A1 MIN-1] OWNER chay tren ORACLE NGAY SAU KHI NAP / RUT von tk con co chu dich:
#   $OPS = thu muc chua script nay = worktree A1 duyet (HEAD co trong deploy/gates/A1_APPROVED_OPS.commit), vd ~/claude_master/fin1114/c3_w1c/ops/c3live
#   bash $OPS/golive_rebase_equity.sh <delta_usdt> "ly do"    # delta > 0 nap, < 0 rut; go YES
#   DRY=1 bash .../golive_rebase_equity.sh -500 "rut 500"                                       # chi kiem + in
# Lop phu golive_monitor: eq = C3_CAPITAL + (tmb - tmb0). Rebase THEO SO TIEN: tmb0 += delta, GIU dinh eq (KHONG xoa DD):
#   - delta phai khop bien dong tmb THAT: ton tai mau monitor (lich su ~/claude_master/deploy/c3sub_tmb_hist.txt, cung moc, sau lan
#     rebase / micro_on / pilot_on gan nhat, <= 24 h) voi |(tmb hien tai - tmb mau) - delta| <= 2 % |delta|; khong co => TU CHOI.
#   - dinh eq = dinh tai mau do (truoc nap/rut; dinh bi day len vi tien nap duoc tra ve), cung moc (base_id giu nguyen).
#   - TU CHOI khi run/KILL_SWITCH tren 242 do golive_monitor dat (xu ly KHAN truoc); chi khi co co micro/pilot.
#   - Reset dinh co chu dich CHI o pilot_on (log + Telegram).
# Doc san CHI DOC (v3/account + scope, ~90 weight), doc run/KILL_SWITCH 242 (chi doc). Ghi Oracle: c3sub_eq_base.txt (+ .bak_<TS>),
#   c3sub_tmb_peak (dinh), log c3sub_eq_base.log. KHONG ghi 242. Ma thoat 0 XONG | 1 DUNG.
# =============================================================================
set -uo pipefail
# [WAVE1c m1] pin NGOAI repo, kiem TRUOC khi source lib (lib khong tu chung nhan): HEAD repo chua script = 1 commit A1/MASTER
#   duyet trong A1_APPROVED_OPS (deploy/gates/A1_APPROVED_OPS.commit, 1 dong/commit, script CHI DOC) + thu muc script KHONG co sua chua commit.
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_manifest_check "$0" || exit 1   # [WAVE1b M5] script + lib + manifest khop md5 da commit, lech => TU CHOI truoc moi viec
DELTA=${1:-}; REASON=${2:-${REASON:-}}
REBASE_TOL=${REBASE_TOL:-0.02}
REBASE_MAX_AGE_S=${REBASE_MAX_AGE_S:-86400}
gl_init golive_rebase_equity
[[ "$DELTA" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] && awk -v d="$DELTA" 'BEGIN{exit !(d != 0)}' || die "can so tien delta (USDT, > 0 nap / < 0 rut, khac 0): bash $0 -500 \"rut 500\""
[ -n "$REASON" ] || die "can ly do: bash $0 $DELTA \"nap/rut ...\""
[ "$C3_ACCOUNT" = SUB ] || die "chi dung cho C3_ACCOUNT=SUB (ADD4)"
[ -f "$GL_MON_FLAG" ] || die "khong co co micro/pilot ($GL_MON_FLAG) — khong can rebase"
KSW=$(s242 "head -c 200 $A/run/KILL_SWITCH 2>/dev/null; true") || die "ssh toi 242 loi (doc run/KILL_SWITCH)"
case "$KSW" in golive_monitor\ *) die "run/KILL_SWITCH do golive_monitor dat ($(echo "$KSW" | head -1 | cut -c1-120)) — xu ly KHAN truoc, KHONG rebase";; esac
gl_read_state
CAP=$(sv ENV_C3_CAPITAL)
API=$(gl_api242 mon) || die "ssh toi 242 loi"
echo "$API" | grep -qx END_API || die "doc san khong tron ven"
TMB=$(av TMB); KS8=$(av KEY_SHA8)
[[ "$TMB" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "totalMarginBalance khong hop le ('$TMB')"
[ -n "$KS8" ] && [ "$KS8" != "$MAIN_KEY_SHA8" ] || die "key doc san = key tk chinh / thieu ($KS8)"
TB0=$(sed -n 's/^tmb0=//p' "$SUB_BASE_FILE" 2>/dev/null | head -1); CB=$(sed -n 's/^c3_capital=//p' "$SUB_BASE_FILE" 2>/dev/null | head -1)
KB=$(sed -n 's/^key_sha8=//p' "$SUB_BASE_FILE" 2>/dev/null | head -1); BID=$(sed -n 's/^base_id=//p' "$SUB_BASE_FILE" 2>/dev/null | head -1)
RT=$(sed -n 's/^rebase_t=//p' "$SUB_BASE_FILE" 2>/dev/null | head -1)
[[ "$TB0" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [[ "$CB" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [ "$KB" = "$KS8" ] && [ -n "$BID" ] || die "moc tmb0 hien tai khong hop le ($SUB_BASE_FILE) — owner/MASTER xem (micro_on / pilot_on ghi moc)"
[[ "$RT" =~ ^[0-9]+$ ]] || RT=0
[ "$CAP" = "$CB" ] || say "WARN C3_CAPITAL process ($CAP) khac moc ($CB) — giu C3_CAPITAL cua moc"
NOW=$(date +%s); MINT=$(( NOW - REBASE_MAX_AGE_S )); [ "$RT" -gt "$MINT" ] && MINT=$RT
# mau gan nhat (cung moc, sau lan dat moc gan nhat) co |(tmb - tmb_mau) - delta| <= tol * |delta|
REF=$(awk -v bid="$BID" -v mint="$MINT" -v t="$TMB" -v d="$DELTA" -v tol="$REBASE_TOL" \
  '$5 == bid && $1 >= mint { x = (t - $2) - d; if (x < 0) x = -x; ad = (d < 0 ? -d : d); if (x <= tol * ad) r = $0 } END { print r }' "$SUB_HIST_FILE" 2>/dev/null)
[ -n "$REF" ] || die "delta $DELTA KHONG khop bien dong tmb that (tmb hien tai $TMB; khong co mau monitor cung moc sau $(TZ=Asia/Ho_Chi_Minh date -d @$MINT '+%F %T') voi lech <= $(awk -v t="$REBASE_TOL" 'BEGIN{print t*100}') %) — TU CHOI"
read -r RTS RTMB REQ RPK RBID <<< "$REF"
NB0=$(awk -v b="$TB0" -v d="$DELTA" 'BEGIN{printf "%.2f", b + d}')
CPK=$(sed -n 's/^peak=//p' "$SUB_PEAK_FILE" 2>/dev/null | head -1)
EQN=$(awk -v c="$CB" -v t="$TMB" -v b="$NB0" 'BEGIN{printf "%.2f", c + t - b}')
say "mau truoc nap/rut: $(TZ=Asia/Ho_Chi_Minh date -d @$RTS '+%F %T') tmb=$RTMB eq=$REQ dinh=$RPK | hien tai tmb=$TMB (bien dong $(awk -v a="$TMB" -v b="$RTMB" 'BEGIN{printf "%.2f", a-b}') vs delta $DELTA)"
say "--- moc moi: tmb0 $TB0 -> $NB0 (delta $DELTA), C3_CAPITAL=$CB, base_id GIU $BID; dinh eq GIU = $RPK (dinh hien tai ${CPK:-?}); eq sau rebase = $EQN"
[ "$DRY" = 1 ] && { say "DRY=1: KHONG ghi. (DRY PASS)"; exit 0; }
gl_yes "REBASE theo so tien: tmb0 += $DELTA (ly do: $REASON). GIU dinh eq $RPK — DD KHONG bi xoa."
gl_eq_base_set "$NB0" "$CB" "$KS8" "golive_rebase_equity delta=$DELTA: $REASON" "$BID" || die "ghi moc loi"
printf 'peak=%s\nbase_id=%s\nts=%s\n' "$RPK" "$BID" "$TS" > "$SUB_PEAK_FILE.tmp" && mv -f "$SUB_PEAK_FILE.tmp" "$SUB_PEAK_FILE" || die "ghi dinh loi"
say "=== XONG: tmb0=$NB0 (delta $DELTA), dinh eq giu $RPK, eq=$EQN"
tg "[golive] REBASE eq tk con TS=$TS: tmb0 $TB0 -> $NB0 (delta $DELTA, khop tmb that), dinh GIU $RPK. Ly do: $REASON. Log $LOG"
exit 0
