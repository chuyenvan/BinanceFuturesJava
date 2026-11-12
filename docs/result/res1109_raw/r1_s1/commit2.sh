set -e
cd ~/claude_master/res1109/r1_s1
python3 -c "import json;r=json.load(open('a3_bins/a3_report.json'));print({k:r[k] for k in r if k not in ('folds','a1_ids')});print([(f['fold'],f['pool_absent_in_bin']) for f in r['folds'] if f['pool_absent_in_bin']])"
WT=$HOME/claude_master/vz_e1_wt
echo WT=$WT
cp ADD2.md $WT/docs/prereg/PREREG_R1_S1_ABLATION_ADDENDUM2.md
cp r1_diag.py a3_build.py $WT/research/r1_s1/
cp a3_bins/a3_report.json $WT/research/r1_s1/a3_report.json
cd $WT
git add docs/prereg/PREREG_R1_S1_ABLATION_ADDENDUM2.md research/r1_s1/r1_diag.py research/r1_s1/a3_build.py research/r1_s1/a3_report.json
git commit -q -m "R1 prereg ADDENDUM2: G-FULL(b) mau so = key pool co trong bin net015 (truoc kernel)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KcMsGREpUAoabx788AKSqW"
git log --oneline -1
