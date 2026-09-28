#!/usr/bin/env python3
"""D3 driver — chay CONG CU D2 (reset_rule_score.py) o che do 'as-is' tren artifact THAT.

Khong viet lai thuat toan cham: import reset_rule_score roi
  - nap artifact cua dung muc phi (base / stress) tu /home/ubuntu/kaggle_sim/out/<tag>
  - goi nguyen main() cua cong cu voi TAGS = 5 arm (R0..R4) va B_STAR = R0 (cung muc phi)
  - COST_LEVELS/COSTS ep = 0.008 (legacy) => KHONG hieu chinh pnl => dung so THAT cua artifact
Doi moi tham so k = 5 (inflate 1.7941). Xuat JSON rieng cho tung muc phi.

Usage: python3 reset_rule_p2_driver.py <cost>   # cost in {base,stress}
"""
import sys, os, math, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reset_rule_score as R

ARMS = ["r0", "r1", "r2", "r3", "r4"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cost", choices=["base", "stress"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default=None)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    c = a.cost
    tags = ["p2-%s-%s" % (arm, c) for arm in ARMS]
    R.TAGS = [(t, R.KOUT) for t in tags]
    R.B_STAR = "p2-r0-%s" % c
    R.K_INFL = 5
    R.INFL = math.sqrt(2.0 * math.log(5.0))          # 1.7941
    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}  # ep 0.008 => as-is
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    # MTM_COSTS phai co du 3 key (legacy/base/stress) vi main() in/lap theo COSTS.keys();
    # ca 3 ep = 0.008 => duong equity MTM la NGUYEN TRANG artifact (as-is).
    R.MTM_COSTS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.EXP = {}                                        # tu kiem R0-legacy lam NGOAI driver
    js = a.json or "/home/ubuntu/rr_p2_%s.json" % c
    rp = a.report or "/home/ubuntu/rr_p2_%s.txt" % c
    sys.argv = ["reset_rule_score", "--json", js, "--report", rp,
                "--mtm-cache", "/home/ubuntu/rr_p2_%s_mtm.json" % c,
                "--workers", str(a.workers), "--chunk", "30"]
    R.main()
    print("DRIVER_DONE", c, js)


if __name__ == "__main__":
    main()
