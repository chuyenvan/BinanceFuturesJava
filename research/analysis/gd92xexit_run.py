"""GD92 x EXIT runner — day cac chan cua docs/prereg/PREREG_GD92_X_EXIT.md len Kaggle.

  par1 : profile x1_gs_t170 NGUYEN BAN, KHONG key rolling => cong parity 1 (md5 efb793e2)
  par2 : profile x1_c3_full,  KHONG key rolling            => cong parity 2 (md5 dc16e4da)
  a    : (A) GD92-ONLY  = T170 + SIM_GATE_ROLLING_PCT=0.92 + SIM_GATE_ROLLING_DAYS=90
  b    : (B) GD92 + HINGE V3 (SIM_TS_PNOPUMP_WEAK_THR=0.17)
  c    : (C) GD92 + LADDER L1 (TS_LADDER=1 + LO/GAPS)
  d    : (D) GD92 + cap 10/30 (SIM_TS_MAX_GAP=0.30, SIM_TS_MAX_GAP_WEAK=0.10) — tuy chon

Moi chan deu + SIM_TRAIL_TRACE=1 (do-luong-only; tien le tl-par == tl-part byte-identical).

Dung: python3 research/analysis/gd92xexit_run.py <par1|par2|a|b|c|d|p1|p2|abc|all> ...
KHONG chay Java tren Oracle. Moi sim chay tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-gd92xexit"     # dataset chi chua sim.jar (code GD92) + prof_x1_c3_full.properties
END = "20251231"
SHA = "fc7065d+cp1db0613"

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
    "par1": dict(tag="gx-par1", profile="x1_gs_t170", overrides={}, jar_ds=JAR_DS,
                 bundle_ds=BUNDLE),
    "par2": dict(tag="gx-par2", profile="x1_c3_full", overrides={}, jar_ds=JAR_DS,
                 bundle_ds=BUNDLE),
    "a":    dict(tag="gx-a", profile="x1_gs_t170", overrides=_ov(GD92), jar_ds=JAR_DS,
                 bundle_ds=BUNDLE),
    "b":    dict(tag="gx-b", profile="x1_gs_t170", overrides=_ov(GD92, HINGE_V3), jar_ds=JAR_DS,
                 bundle_ds=BUNDLE),
    "c":    dict(tag="gx-c", profile="x1_gs_t170", overrides=_ov(GD92, LADDER_L1), jar_ds=JAR_DS,
                 bundle_ds=BUNDLE),
    "d":    dict(tag="gx-d", profile="x1_gs_t170", overrides=_ov(GD92, CAP1030), jar_ds=JAR_DS,
                 bundle_ds=BUNDLE),
}

# Cac chan parity chay TRUOC de kiem cong; neu FAIL thi DUNG (pre-reg §4).
ALIAS = {"p1": ["par1"], "p2": ["par2"], "abc": ["a", "b", "c"],
         "par": ["par1", "par2"], "all": ["par1", "par2", "a", "b", "c"]}


def run(names):
    refs = []
    for n in names:
        j = JOBS[n]
        ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=j["bundle_ds"],
                        jar_ds=j["jar_ds"], sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-5s -> %s profile=%s overrides=%s" % (
            n, ref, j["profile"], json.dumps(j["overrides"])), flush=True)
        refs.append(ref)
    print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        out = ks.fetch(JOBS[n]["tag"])
        print("FETCH %-5s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    names = []
    for x in a:
        names.extend(ALIAS.get(x, [x]))
    run(names)
