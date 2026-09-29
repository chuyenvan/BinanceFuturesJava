#!/usr/bin/env python3
"""GDV2_EVEN runner — day G0 (parity, do rho) -> G1 (W30) / G2 (W90) len Kaggle.

  g0 : profile r4_kg0_k16_f015_g155 NGUYEN BAN (key MODE khong khai) => parity md5 06fd6e9a + do rho.
  g1 : R4 + SIM_GATE_ROLLING_MODE=ratio + SIM_GATE_ROLLING_PCT=1-rho + SIM_GATE_ROLLING_DAYS=30
  g2 : R4 + SIM_GATE_ROLLING_MODE=ratio + SIM_GATE_ROLLING_PCT=1-rho + SIM_GATE_ROLLING_DAYS=90

KHONG chay Java tren Oracle. Sim tren Kaggle CPU kernel (chi phi 0).
PCT duoc KHOÁ sau khi doc rho tu g0 (docs/prereg/PREREG_GDV2_EVEN.md muc 1.4).
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

JOBS = {
    "g0": dict(tag="gdv2-g0", overrides={}),
    "g1": dict(tag="gdv2-g1", overrides={"SIM_GATE_ROLLING_MODE": "ratio",
                                          "SIM_GATE_ROLLING_DAYS": 30}),   # PCT set separately
    "g2": dict(tag="gdv2-g2", overrides={"SIM_GATE_ROLLING_MODE": "ratio",
                                          "SIM_GATE_ROLLING_DAYS": 90}),
}


def run(names, pct=None):
    refs = []
    for n in names:
        j = dict(JOBS[n])
        ov = dict(j["overrides"])
        if pct is not None:
            ov["SIM_GATE_ROLLING_PCT"] = pct
        ref = ks.submit(j["tag"], PROFILE, ov, bundle_ds=BUNDLE, jar_ds=JAR_DS,
                        sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-3s -> %s overrides=%s" % (n, ref, json.dumps(ov)), flush=True)
        refs.append(ref)
    print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        out = ks.fetch(JOBS[n]["tag"])
        print("FETCH %-3s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    pct = None
    if "--pct" in a:
        i = a.index("--pct")
        pct = float(a[i + 1])
        a = a[:i] + a[i + 2:]
    names = a or ["g0"]
    run(names, pct)
