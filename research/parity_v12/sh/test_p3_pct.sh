# [ADD17] test P3 PCT float32: (1) k(m=1260874)=1260810; (2) replay q 11-08 khop log <=1e-6 moi gio (scratch);
# (3) P3 11-06, 11-07 khong doi (scratch, so voi p3 chinh thuc). Chay BEN TRONG 1 flock oracle_heavy (khong long).
export LIVE_IS_SHADOW_HOST=true
W=$HOME/claude_master/parity_v12w; P=$HOME/claude_master/vz_e1_wt/research/parity_v12/py; S=$W/scratch_dump1108
ok=1
python3 -c "
import numpy as np
p=float(np.float32(0.999950829)); m=1260874; k=int(np.floor(p*(m-1)))
print('k', k); assert k==1260810" || ok=0
for D in 2026-11-03 2026-11-04 2026-11-05 2026-11-06 2026-11-07; do
  mkdir -p $S/d/$D; [ -e $S/d/$D/live ] || ln -s $W/d/$D/live $S/d/$D/live
  rm -rf $S/d/$D/work; cp -a $W/d/$D/work $S/d/$D/work
done
for D in 2026-11-03 2026-11-04 2026-11-05 2026-11-06 2026-11-07 2026-11-08; do
  PV_ROOT=$S PV_DAY=$D python3 $P/day_eval.py p3 > $S/p3_add17_$D.log 2>&1 || { echo "p3 $D LOI"; ok=0; }
  python3 - $D <<'EOF' || ok=0
import json, os, sys
D = sys.argv[1]; t = D.replace("-", "")
W = os.path.expanduser("~/claude_master/parity_v12w/")
new = json.load(open(W + "scratch_dump1108/d/%s/work/p3_%s.json" % (D, t)))
offp = W + "d/%s/work/p3_%s.json" % (D, t)
old = json.load(open(offp)) if os.path.exists(offp) else None
print(D, "moi: n_rel>1e-6 =", new["n_rel_gt_1e-6"], "max_rel=%.3g" % new["max_rel"], "PASS", new["PASS"],
      "| cu:", (old["n_rel_gt_1e-6"], "%.3g" % old["max_rel"], old["PASS"]) if old else "chua cham chinh thuc")
if D == "2026-11-08":
    assert new["n_rel_gt_1e-6"] == 0, "11-08 van lech"
if D in ("2026-11-06", "2026-11-07"):
    assert old["n_rel_gt_1e-6"] == new["n_rel_gt_1e-6"] == 0 and abs(old["max_rel"] - new["max_rel"]) < 1e-9, "11-06/07 doi"
EOF
done
[ $ok -eq 1 ] && echo "TEST_P3_PCT PASS" || echo "TEST_P3_PCT FAIL"
