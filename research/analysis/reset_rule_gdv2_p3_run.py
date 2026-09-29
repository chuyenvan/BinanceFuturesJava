#!/usr/bin/env python3
"""GDV2_P3 runner — G0s (R4 @stress, parity 84402b57) + G2s (GDV2 W90 @stress) len Kaggle.

DUNG LAI jar GDV2 (dataset sim-jar-gdv2, sha256 7368be46…). KHONG build lai, KHONG merge.
@stress = SIM_SLIPPAGE_RATE 0.000067 -> 0.000259 (SIM_RATE_FEE giu 0.000982) => 0.150%/vong.
G2s giu pct=0.99995083 window=90 (giong @base).

KHONG chay Java tren Oracle. Sim tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-gdv2"
END = "20251231"
SHA = "2b4dcbd+cp1db0613"   # prereg commit + cherry-pick gd92 code (module HEAD)

PROFILE = "r4_kg0_k16_f015_g155"
PCT = 0.99995083

JOBS = {
    "g0s": dict(tag="gdv2-g0-stress",
                overrides={"SIM_SLIPPAGE_RATE": 0.000259}),
    "g2s": dict(tag="gdv2-g2-stress",
                overrides={"SIM_GATE_ROLLING_MODE": "ratio",
                           "SIM_GATE_ROLLING_PCT": PCT,
                           "SIM_GATE_ROLLING_DAYS": 90,
                           "SIM_SLIPPAGE_RATE": 0.000259}),
}


def run(names):
    refs = []
    for n in names:
        j = JOBS[n]
        ref = ks.submit(j["tag"], PROFILE, dict(j["overrides"]), bundle_ds=BUNDLE, jar_ds=JAR_DS,
                        sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-3s -> %s overrides=%s" % (n, ref, json.dumps(j["overrides"])), flush=True)
        refs.append(ref)
    print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        out = ks.fetch(JOBS[n]["tag"])
        print("FETCH %-3s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    run(sys.argv[1:] or ["g0s", "g2s"])
