"""EXIT-HIGH-N runner — day 9 chan cua docs/prereg/PREREG_EXIT_HIGH_N.md len Kaggle.

  par1 : profile x1_gs_t170 NGUYEN BAN, khong key rolling       => cong parity 1 (efb793e2)
  t100 : profile x1_c3_full                                     => cong parity 2 (dc16e4da) + baseline nen T
  g92  : (G) GD92 = x1_c3_full + SIM_GATE_ROLLING_PCT/DAYS      => tai lap 2632/133944 + baseline nen G
  g-{hi,la,cp} : nen GD92  x {HINGE V3, LADDER L1, CAP 10/30}
  t-{hi,la,cp} : nen T100  x {HINGE V3, LADDER L1, CAP 10/30}

Tat ca chan deu + SIM_TRAIL_TRACE=1 (do-luong-only; tien le tl-par == tl-part byte-identical).

Dung: python3 research/analysis/exithighn_run.py <par1|t100|g92|g-hi|...|par|all> ...
KHONG chay Java tren Oracle. Moi sim chay tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-exithighn"      # dataset chi chua sim.jar (code rolling cherry-pick -n 1db0613)
END = "20251231"
SHA = "b50833f+cp1db0613"

TRACE = {"SIM_TRAIL_TRACE": 1}
GD92 = {"SIM_GATE_ROLLING_PCT": 0.92, "SIM_GATE_ROLLING_DAYS": 90}
HINGE_V3 = {"SIM_TS_PNOPUMP_WEAK_THR": 0.17}
LADDER_L1 = {"TS_LADDER": 1,
             "TS_LADDER_LO": "0.00,0.10,0.25,0.50,1.00",
             "TS_LADDER_GAPS": "0.04,0.08,0.15,0.25,0.35"}
CAP1030 = {"SIM_TS_MAX_GAP": 0.30, "SIM_TS_MAX_GAP_WEAK": 0.10}


def _ov(*ds):
    o = dict(TRACE)
    for d in ds:
        o.update(d)
    return o


JOBS = {
    "par1":   dict(tag="hn-par1", profile="x1_gs_t170", overrides=_ov()),
    "t100":   dict(tag="hn-t100", profile="x1_c3_full", overrides=_ov()),
    "g92":    dict(tag="hn-g92",  profile="x1_c3_full", overrides=_ov(GD92)),
    "g-hi":   dict(tag="hn-g-hi", profile="x1_c3_full", overrides=_ov(GD92, HINGE_V3)),
    "g-la":   dict(tag="hn-g-la", profile="x1_c3_full", overrides=_ov(GD92, LADDER_L1)),
    "g-cp":   dict(tag="hn-g-cp", profile="x1_c3_full", overrides=_ov(GD92, CAP1030)),
    "t-hi":   dict(tag="hn-t-hi", profile="x1_c3_full", overrides=_ov(HINGE_V3)),
    "t-la":   dict(tag="hn-t-la", profile="x1_c3_full", overrides=_ov(LADDER_L1)),
    "t-cp":   dict(tag="hn-t-cp", profile="x1_c3_full", overrides=_ov(CAP1030)),
}

ALIAS = {"par": ["par1", "t100", "g92"],
         "wave1": ["par1", "t100", "g92", "g-hi", "g-la"],
         "wave2": ["g-cp", "t-hi", "t-la", "t-cp"],
         "all": ["par1", "t100", "g92", "g-hi", "g-la", "g-cp", "t-hi", "t-la", "t-cp"]}


def run(names):
    refs = []
    for n in names:
        j = JOBS[n]
        ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE,
                        jar_ds=JAR_DS, sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-6s -> %s profile=%s overrides=%s" % (
            n, ref, j["profile"], json.dumps(j["overrides"])), flush=True)
        refs.append(ref)
    print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        out = ks.fetch(JOBS[n]["tag"])
        print("FETCH %-6s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    names = []
    for x in a:
        names.extend(ALIAS.get(x, [x]))
    run(names)
