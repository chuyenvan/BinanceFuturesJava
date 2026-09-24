"""CONC-CAP-HIGHN runner — day 4 chan cua docs/PREREG_CONC_CAP_HIGHN.md len Kaggle.

  par1 : profile x1_gs_t170 NGUYEN BAN (cap OFF)              => cong parity P1 (efb793e2)
  t100 : x1_c3_full                              + CONC_CAP  => doi chieu OFF hn-t100 (dc16e4da)
  g92  : x1_c3_full + SIM_GATE_ROLLING_PCT/DAYS  + CONC_CAP  => doi chieu OFF hn-g92  (cd913759)
  g-cp : x1_c3_full + rolling + CAP10/30         + CONC_CAP  => doi chieu OFF hn-g-cp (43fb90ee)

Moi chan + SIM_TRAIL_TRACE=1 (do-luong-only; hn-par1 co trace da cho md5 efb793e2 = T170 khong
trace => trace KHONG doi printDone) de profile ON/OFF chi khac DUNG 2 dong CONC_CAP_PERCOIN_*.

GD92 can code `GateRollingThreshold` KHONG co tren module => jar build tu `cherry-pick -n 1db0613`
(dataset `sim-jar-conccap`, sha256 c2b0c963...). KHONG merge.

Dung: python3 research/analysis/conccap_run.py <par1|t100|g92|g-cp|par|all> ...
KHONG chay Java tren Oracle. Moi sim chay tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-conccap"
END = "20251231"
SHA = "4850b03+cp1db0613"

TRACE = {"SIM_TRAIL_TRACE": 1}
GD92 = {"SIM_GATE_ROLLING_PCT": 0.92, "SIM_GATE_ROLLING_DAYS": 90}
CAP1030 = {"SIM_TS_MAX_GAP": 0.30, "SIM_TS_MAX_GAP_WEAK": 0.10}
CONC_CAP = {"CONC_CAP_PERCOIN_ENABLED": 1, "CONC_CAP_PERCOIN_PCT": 0.15}


def _ov(*ds):
    o = dict(TRACE)
    for d in ds:
        o.update(d)
    return o


JOBS = {
    "par1": dict(tag="cc-par1", profile="x1_gs_t170", overrides=_ov()),
    "t100": dict(tag="cc-t100", profile="x1_c3_full", overrides=_ov(CONC_CAP)),
    "g92":  dict(tag="cc-g92",  profile="x1_c3_full", overrides=_ov(GD92, CONC_CAP)),
    "g-cp": dict(tag="cc-g-cp", profile="x1_c3_full", overrides=_ov(GD92, CAP1030, CONC_CAP)),
}

ALIAS = {"par": ["par1"], "all": ["par1", "t100", "g92", "g-cp"]}


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
