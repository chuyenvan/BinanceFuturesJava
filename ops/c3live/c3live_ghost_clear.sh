#!/usr/bin/env bash
# =============================================================================
# c3live_ghost_clear.sh — OWNER go "CUM MA" cua c3_live tren 242 (V12 2e): cum con trong so + stop c3s- con NEW nhung vi the
# that da PHANG (vd owner dong tay / bi thanh ly luc mat user stream). Bot nhac Telegram moi 6h khi gap ca nay.
#   bash ~/claude_master/deploy/c3live_ghost_clear.sh XRPUSDT          # CHI XEM (khong ghi gi)
#   YES=1 bash ~/claude_master/deploy/c3live_ghost_clear.sh XRPUSDT    # GUI LENH go cum ma (1 lenh duy nhat)
# Bot (runtime c3_live, chinh jar dang chay + client tai khoan con, KHONG in key) doc LAI positionRisk + account().positions:
#   - CA HAI = 0  => huy moi stop c3s- con mo cua symbol + xoa cum khoi so (ly do GHOST_CLEAR_OWNER) => "OK ..."
#   - con vi the / doc loi / so khong giu symbol => TU CHOI, KHONG doi gi => "REFUSED <ly do>"
# Script KHONG goi san, KHONG doc key; chi ghi 1 file yeu cau run/c3live_ghost_clear.req va doc file ket qua .result.
# Bien test: SSH_242, APP_DIR, GHOST_WAIT (giay cho bot, mac dinh 30).
# =============================================================================
set -uo pipefail
SYM=${1:-}
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
YES=${YES:-0}
GHOST_WAIT=${GHOST_WAIT:-30}
case "$SYM" in
  ''|*[!A-Z0-9]*) echo "DUNG: can 1 SYMBOL chu IN HOA/so, vd: YES=1 bash $0 XRPUSDT"; exit 2;;
esac
echo "== $SYM: dong log gan nhat lien quan (242):"
$SSH_242 "cd $A && grep -a \"$SYM\" logs/full.log | grep -a 'C3-LIVE-FLAT\|C3-LIVE-STOPGUARD\|ghost_clear\|C3-LIVE-RECON' | tail -5 | cut -c1-300" \
  || { echo "DUNG: ssh loi"; exit 1; }
if [ "$YES" != 1 ]; then
  echo "== CHI XEM: khong ghi gi. Gui lenh go cum ma: YES=1 bash $0 $SYM"
  exit 0
fi
$SSH_242 "cd $A && rm -f run/c3live_ghost_clear.req.result && printf '%s\n' '$SYM' > run/c3live_ghost_clear.req.tmp && mv -f run/c3live_ghost_clear.req.tmp run/c3live_ghost_clear.req && echo 'da ghi run/c3live_ghost_clear.req'" \
  || { echo "DUNG: ssh loi khi ghi yeu cau"; exit 1; }
RES=""
for _ in $(seq 1 "$GHOST_WAIT"); do
  RES=$($SSH_242 "cat $A/run/c3live_ghost_clear.req.result 2>/dev/null" || true)
  [ -n "$RES" ] && break
  sleep 1
done
if [ -z "$RES" ]; then
  echo "== Bot CHUA xu ly sau ${GHOST_WAIT}s (bot tat? sai thu muc?). Yeu cau van cho; chay lai script (khong YES) de xem log."
  exit 5
fi
echo "== Ket qua bot: $RES"
case "$RES" in
  *" OK "*) exit 0;;
  *) echo "== TU CHOI: KHONG doi gi. Neu vi the that con => KHONG phai cum ma (giu nguyen). Gui log cho MASTER."; exit 4;;
esac
