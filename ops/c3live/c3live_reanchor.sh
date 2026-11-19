#!/usr/bin/env bash
# =============================================================================
# c3live_reanchor.sh — OWNER dat lai MOC doi chieu equity c3_live (C9) tren 242, sau khi NAP/RUT tien co chu dich
# luc user stream khong ghi nhan (lech > 1 % => bot chan mo moi). Ghi 1 file yeu cau; bot ap dung trong <= 5 s.
#   bash ~/claude_master/deploy/c3live_reanchor.sh        # DRY: in dong doi chieu gan nhat, khong ghi gi
#   DRY=0 bash ~/claude_master/deploy/c3live_reanchor.sh  # ghi yeu cau: go YES
# KHONG dung de "lam im" lech khong ro nguyen nhan — gui log cho MASTER truoc.
# =============================================================================
set -uo pipefail
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
DRY=${DRY:-1}
echo "== doi chieu equity gan nhat (242):"
$SSH_242 "cd $A && grep -a '\[C3-LIVE-RECON\]' logs/full.log | grep -a 'equity\|EQUITY\|moc' | tail -4 | cut -c1-400" || { echo "DUNG: ssh loi"; exit 1; }
# [V12 R4b §13] c3_live R4+ doi chieu theo QTY c3 (tai khoan chinh, khong co moc equity/tmb) => TU CHOI
# [OPS5_FIX 8a] nhan dong khoi dong: jar cu "tai_khoan=CHINH(pham vi c3)" | jar W3A muc 2 "recon=QTY(pham vi c3)" (ca 2 => TU CHOI)
QM=$($SSH_242 "cd $A && L=\$(grep -a -n 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager' logs/full.log | tail -1 | cut -d: -f1); tail -n +\${L:-1} logs/full.log | grep -a -c -F -e 'tai_khoan=CHINH(pham vi c3)' -e 'recon=QTY(pham vi c3)'" 2>/dev/null)
case "$QM" in ''|*[!0-9]*) QM=0;; esac
if [ "$QM" -gt 0 ]; then
  echo "TU CHOI: c3_live (R4+) doi chieu theo QTY c3 tren tai khoan chinh — khong co moc equity/tmb de dat lai."
  echo "         Lech qty c3 / chan EQUITY_MISMATCH => gui log cho MASTER (khong dung reanchor)."
  exit 4
fi
[ "$DRY" != 0 ] && { echo "== DRY: khong ghi gi. Ghi yeu cau: DRY=0 bash $0"; exit 0; }
read -r -p "Da nap/rut tien co chu dich va MASTER dong y? Go YES: " ANS
[ "$ANS" = "YES" ] || { echo "== Huy."; exit 3; }
$SSH_242 "cd $A && printf '{\"by\":\"owner\",\"at_ms\":%s}\n' \$(( \$(date +%s) * 1000 )) > run/c3live_reanchor.req.tmp && mv -f run/c3live_reanchor.req.tmp run/c3live_reanchor.req && echo 'da ghi run/c3live_reanchor.req'"
for i in $(seq 1 "${REANCHOR_WAIT:-20}"); do
  $SSH_242 "[ -f $A/run/c3live_reanchor.req ]" || { echo "== Bot da ap dung."; break; }
  sleep 2
done
$SSH_242 "cd $A && grep -a 'dat moc doi chieu' logs/full.log | tail -1 | cut -c1-300"
