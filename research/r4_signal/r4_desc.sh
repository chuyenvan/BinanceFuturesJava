#!/bin/bash
# R4: MO TA (KHONG CHAM) fwd72 THEM-BOT cho ca 3 arm du da LOAI o quota (prereg §4 "bao kem"). Khong doi ket luan.
set -e
S=/home/ubuntu/claude_master/vz_e1_wt/research/r4_signal/r4_score.py
D=/home/ubuntu/claude_master/res1109/r4_signal/screen
O=/home/ubuntu/claude_master/vz_e1_wt/docs/result/r4_signal
mkdir -p $O
sed -e 's|^        if e.get("LOAI"):|        if False:  # MO TA: bo qua LOAI|' \
    -e "s|^DOC = .*|DOC = \"$O/R4_SIGNAL_SCREEN_MOTA.md\"|" \
    -e 's|G + "r4_screen.json"|G + "r4_screen_mota.json"|' \
    -e 's|tự sinh bởi research/r4_signal/r4_score.py|MÔ TẢ, KHÔNG CHẤM (cả 3 arm đã LOẠI ở quota; cột KẾT bỏ qua điều kiện quota)|' \
    $S > $D/r4_score_mota.py
grep -c 'if False:  # MO TA' $D/r4_score_mota.py
python3 $D/r4_score_mota.py > $D/score_mota.log 2>&1
cp -f $D/r4_screen_mota.json $O/
cat $O/R4_SIGNAL_SCREEN_MOTA.md
