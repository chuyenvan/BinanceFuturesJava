#!/usr/bin/env bash
# =============================================================================
# install_cron_ing_qf_check.sh — [QF3, A1_QF2 MIN-E] cai cron Oracle (user ubuntu) cham PREREG_INGEST_QUICKFIX sau deploy. 1 lenh.
#   DRY=1 bash ~/claude_master/deploy/install_cron_ing_qf_check.sh   # in crontab moi, khong cai
#   bash ~/claude_master/deploy/install_cron_ing_qf_check.sh          # go YES; backup crontab; idempotent (da dung ban moi => khong doi)
#     [11-12] da co dong tag + '--vision' kieu cu => CHI thay dung dong do bang ban moi (D-2); in crontab TRUOC/SAU.
#   REMOVE=1 bash ...                                                  # go 2 dong ing_qf_check khoi crontab (backup truoc)
# Them: 23 * * * *  hourly (Q1,Q2,Q4-Q7,Q10,O1 tu log 242, CHI DOC)
#       41 9 * * *  --vision <D-2 UTC> (Q3 so Vision daily; [11-12] do thuc te: Vision ngay D co luc ~D+2 08:30 +07 —
#                   kiem D-1 luc 09:41 ra THIEU_SO_DO moi ngay tu 11-01)
# Ket qua: ~/claude_master/ing1030/qf_check.jsonl; log cron: ~/claude_master/ing1030/qf_check_cron.log
# =============================================================================
set -uo pipefail
PY=/home/ubuntu/claude_master/ing1030/qf_wt/research/ops/ing_qf_check.py
LOGC=/home/ubuntu/claude_master/ing1030/qf_check_cron.log
TAG="# ingqf3-check"
L1="23 * * * * cd /home/ubuntu/claude_master/ing1030 && /usr/bin/python3 $PY >> $LOGC 2>&1 $TAG"
L2="41 9 * * * cd /home/ubuntu/claude_master/ing1030 && /usr/bin/python3 $PY --vision \$(date -u -d '2 days ago' +\\%Y-\\%m-\\%d) >> $LOGC 2>&1 $TAG"
[ -f "$PY" ] || { echo "DUNG: khong co $PY"; exit 1; }
python3 -m py_compile "$PY" || { echo "DUNG: $PY loi cu phap"; exit 1; }
CUR=$(crontab -l 2>/dev/null || true)
TS=$(date +%Y%m%d_%H%M%S)
if [ "${REMOVE:-0}" = 1 ]; then
  NEW=$(printf '%s\n' "$CUR" | grep -vF "$TAG")
elif ! printf '%s\n' "$CUR" | grep -qF "$TAG"; then
  NEW=$(printf '%s\n%s\n%s\n' "$CUR" "$L1" "$L2" | sed '/^$/d')
else
  if printf '%s\n' "$CUR" | grep -qxF "$L2"; then echo "Da cai ban moi (dong --vision D-2) — khong doi gi."; exit 0; fi
  # CHI thay dong co tag + '--vision' (kieu cu) bang L2; moi dong khac giu nguyen; chua co dong vision => them L2
  NEW=$(printf '%s\n' "$CUR" | T="$TAG" L2="$L2" awk 'index($0, ENVIRON["T"]) && index($0, "--vision") { if (!d) print ENVIRON["L2"]; d = 1; next } { print }')
  printf '%s\n' "$NEW" | grep -qxF "$L2" || NEW=$(printf '%s\n%s\n' "$NEW" "$L2")
fi
echo "=== crontab TRUOC ==="; printf '%s\n' "$CUR"
echo "=== crontab SAU (moi) ==="; printf '%s\n' "$NEW"
[ "${DRY:-0}" = 1 ] && { echo "DRY=1: khong cai."; exit 0; }
echo ">>> Ghi crontab (backup ~/crontab_bak_ingqf3_$TS.txt)? Go YES:"
read -r ANS; [ "$ANS" = YES ] || { echo "Huy."; exit 1; }
printf '%s\n' "$CUR" > ~/crontab_bak_ingqf3_$TS.txt
printf '%s\n' "$NEW" | crontab - || { echo "LOI ghi crontab — khoi phuc"; crontab ~/crontab_bak_ingqf3_$TS.txt; exit 2; }
echo "=== crontab SAU khi ghi ==="; crontab -l
echo "XONG. Khoi phuc: crontab ~/crontab_bak_ingqf3_$TS.txt"
