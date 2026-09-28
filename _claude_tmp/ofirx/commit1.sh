#!/bin/bash
set -e
W=/home/ubuntu/claude_audit_0928/ofirx
R=/home/ubuntu/src/BinanceFuturesJava
cd $R
while [ -f .git/index.lock ]; do echo "index.lock - cho 30s"; sleep 30; done
cp $W/PREREG_OFI_MONEY_REORIENT.md docs/prereg/
cp $W/ofi_money_score_v2.py $W/ofi_money_ext_v2.py $W/ofi_ext_trades_build.py research/analysis/
git add docs/prereg/PREREG_OFI_MONEY_REORIENT.md research/analysis/ofi_money_score_v2.py research/analysis/ofi_money_ext_v2.py research/analysis/ofi_ext_trades_build.py
git commit -q -F - <<'MSG'
prereg(ofi-money-reorient): chot TRUOC khi tinh so — chay lai OFI_MONEY voi DUNG CHIEU DIEM (ORIENT=-1)

Loi: pred_ofi_*_v2/pred_baseline_fresh la score=-pred (THAP=TOT) nhung ofi_money_score.py:149,165 va
ofi_money_ext.py:106 chon top-K bang argsort(-score) => chon nham coin TE NHAT. Buoc 0 (khong phai ket qua
tien): mean-rank top-8 trong P32 chieu cu 25,1-26,4 -> chieu sua 3,89-4,32 (3 doi tuong x 4 seed + ensemble).
Thiet ke giu nguyen PREREG_OFI_MONEY (4948795); thay doi duy nhat ORIENT=-1; AMENDMENT: chi so quyet dinh
khong ap tran (errata GROSS_ASYMMAP 09-27). Code v2 (ban cu khong sua): ofi_money_score_v2.py,
ofi_money_ext_v2.py (--orient, mac dinh -1), ofi_ext_trades_build.py (dung file ung vien B2).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UB8kzRC92bexwHufMuBegW
MSG
git log --oneline -1
git show --stat HEAD | tail -6
