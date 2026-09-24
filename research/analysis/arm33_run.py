"""ARM3-3NEN runner — day 2 chan MOI cua docs/prereg/PREREG_ARM3_3NEN.md len Kaggle.

  t100a3 : B2 = T100 + arm 3%  = x1_c3_full + TRAIL_TRACE + SIM_RATE_PROFIT_STOP_MARKET=0.03
  g92a3  : C2 = GD92 + arm 3%  = x1_c3_full + TRAIL_TRACE + GATE_ROLLING(0.92/90) + arm 3%

Doi chieu moc: hn-t100 (md5 dc16e4da) va hn-g92 (md5 cd913759) — cung jar, cung bundle.
CHI doi DUY NHAT SIM_RATE_PROFIT_STOP_MARKET so voi moc.

Dung: python3 research/analysis/arm33_run.py <t100a3|g92a3|all>
KHONG chay Java tren Oracle. Sim chay tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-exithighn"      # jar sha bb282f40 = module b50833f + cherry-pick -n 1db0613
END = "20251231"
SHA = "fb047e1+cp1db0613"

TRACE = {"SIM_TRAIL_TRACE": 1}
GD92 = {"SIM_GATE_ROLLING_PCT": 0.92, "SIM_GATE_ROLLING_DAYS": 90}
ARM3 = {"SIM_RATE_PROFIT_STOP_MARKET": 0.03}


def _ov(*ds):
    o = dict(TRACE)
    for d in ds:
        o.update(d)
    return o


JOBS = {
    "t100a3": dict(tag="hn-t100-arm3", profile="x1_c3_full", overrides=_ov(ARM3)),
    "g92a3":  dict(tag="hn-g92-arm3",  profile="x1_c3_full", overrides=_ov(GD92, ARM3)),
}

ALIAS = {"all": ["t100a3", "g92a3"]}


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
