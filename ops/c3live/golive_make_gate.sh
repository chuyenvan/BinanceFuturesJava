#!/usr/bin/env bash
# =============================================================================
# golive_make_gate.sh — [WAVE1 16/11 B-08] MASTER tao file gate G-MICRO (deploy/gates/GOLIVE_GATE_MICRO.ok) TU KET QUA, khong go tay.
#   bash golive_make_gate.sh <prereg_commit> [report_G-MICRO]     # DRY=1: chi in noi dung, khong ghi
# Doc (CHI DOC): parity_v12w/gmicro_target.json (target_md5 PHAI = NJ_MD5 pin golive_lib, smoke_start_ms co) + report G-MICRO
#   (mac dinh report_*.out moi nhat trong parity_v12w; dong "G-MICRO: <ket qua> sach= [...]"). TU CHOI neu: ket qua != DAT,
#   report cu > GATE_MAX_AGE_S, target_md5 != pin, thieu smoke_start_ms, prereg_commit khong phai hex 7-40.
# Ghi (umask 077, ban cu => .bak_<ts>): jar_md5, ingestor_md5, created_ms, expires_ms (= created + 48 h), gmicro_i, gmicro_ii, smoke,
#   prereg_commit, report + report_sha256, by. golive_micro_on.sh kiem DU cac dong + han (gl_gate strict).
# Ma thoat: 0 da ghi (hoac DRY in) | 1 TU CHOI.
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
PW=${PARITY_W:-/home/ubuntu/claude_master/parity_v12w}
GMICRO_TARGET=${GMICRO_TARGET:-$PW/gmicro_target.json}
PRC=${1:-}; REP=${2:-$(ls -t "$PW"/report_*.out 2>/dev/null | head -1)}
G=$GATE_DIR/GOLIVE_GATE_MICRO.ok
no() { echo "TU CHOI: $*"; exit 1; }
[[ "$PRC" =~ ^[0-9a-f]{7,40}$ ]] || no "prereg_commit '$PRC' khong hop le (hex 7-40). Dung: bash $0 <prereg_commit> [report]"
[ -s "$REP" ] || no "khong co report G-MICRO ($REP)"
AGE=$(( $(date +%s) - $(stat -c %Y "$REP") )); [ "$AGE" -le "$GATE_MAX_AGE_S" ] || no "report $REP cu ${AGE}s > ${GATE_MAX_AGE_S}s"
GL=$(grep -a '^G-MICRO:' "$REP" | tail -1)
[ -n "$GL" ] || no "report $REP khong co dong 'G-MICRO:'"
echo "$GL" | grep -qE '^G-MICRO: DAT( |$)' || no "G-MICRO chua DAT: $GL"
TJ=$(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("target_md5",""), d.get("smoke_start_ms",""), d.get("target_jar",""), d.get("prereg",""))' "$GMICRO_TARGET" 2>/dev/null) || no "khong doc duoc $GMICRO_TARGET"
read -r TMD5 SMS TJAR TPRE <<< "$TJ"
[ "$TMD5" = "$NJ_MD5" ] || no "gmicro_target target_md5=$TMD5 != jar pin $NJ_MD5"
[[ "$SMS" =~ ^[0-9]{13}$ ]] || no "gmicro_target thieu smoke_start_ms"
NS=$(echo "$GL" | grep -oE "sach= \[[^]]*\]" | grep -oE "'[0-9-]+'" | wc -l)
NOW=$(( $(date +%s) * 1000 )); EXP=$(( NOW + GATE_MAX_AGE_S * 1000 ))
BODY="# G-MICRO gate — golive_make_gate.sh $(TZ=Asia/Ho_Chi_Minh date '+%F %T') (+07)
jar_md5=$NJ_MD5
ingestor_md5=$ING_FIN_MD5
created_ms=$NOW
expires_ms=$EXP
gmicro_i=DAT n_sach=$NS
gmicro_ii=DAT
smoke=DAT smoke_start_ms=$SMS target_jar=$TJAR prereg_target=$TPRE
prereg_commit=$PRC
report=$REP
report_sha256=$(sha256sum < "$REP" | cut -c1-64)
by=MASTER golive_make_gate.sh"
echo "$BODY"
[ "${DRY:-0}" = 1 ] && { echo "DRY=1: KHONG ghi $G"; exit 0; }
mkdir -p "$GATE_DIR" || no "khong tao duoc $GATE_DIR"
[ -f "$G" ] && cp -p "$G" "$G.bak_$(date +%s)"
( umask 077; printf '%s\n' "$BODY" > "$G.tmp" ) && mv -f "$G.tmp" "$G" || no "khong ghi duoc $G"
R=$(gl_gate "$G" 1); echo "$R"; echo "$R" | grep -q '^OK' || no "gate vua ghi KHONG qua gl_gate strict (loi script)"
echo "=== XONG: $G (het han sau $((GATE_MAX_AGE_S / 3600)) h)"
