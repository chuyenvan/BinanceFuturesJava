cd ~/claude_master/b15
while ! grep -q "B15 RUN XONG" run.log; do sleep 30; done
python3 b15_feat.py b15-ho-x14-s2024 > feat_h4.log 2>&1 < /dev/null
python3 b15_score.py ho > score_ho.log 2>&1 < /dev/null
echo HO_EXIT=$? >> score_ho.log
python3 b15_tab.py > tab.log 2>&1 < /dev/null
echo TAB_EXIT=$? >> tab.log
