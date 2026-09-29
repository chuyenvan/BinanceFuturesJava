"""GD92_R4 runner — day 3 chan D0/D1/D2 len Kaggle (docs/prereg/PREREG_GD92_R4.md).

  d0 : profile r4_kg0_k16_f015_g155 NGUYEN BAN, KHONG key rolling => cong parity md5 06fd6e9a
  d1 : R4 + SIM_GATE_ROLLING_PCT=0.92 + SIM_GATE_ROLLING_DAYS=90 (giu GATE_DYN_SCALE 1.55)
  d2 : R4 + SIM_GATE_ROLLING_PCT=0.92 + SIM_GATE_ROLLING_DAYS=90 + SIM_GATE_DYN_SCALE=1.00

KHONG chay Java tren Oracle. Sim tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-gd92r4"     # dataset chua sim.jar (code GD92) + prof_r4_kg0_k16_f015_g155.properties
END = "20251231"
SHA = "2a759de+cp1db0613"

GD92 = {"SIM_GATE_ROLLING_PCT": 0.92, "SIM_GATE_ROLLING_DAYS": 90}

JOBS = {
    "d0": dict(tag="gd92-r4-d0", profile="r4_kg0_k16_f015_g155", overrides={},
               jar_ds=JAR_DS, bundle_ds=BUNDLE),
    "d1": dict(tag="gd92-r4-d1", profile="r4_kg0_k16_f015_g155", overrides=dict(GD92),
               jar_ds=JAR_DS, bundle_ds=BUNDLE),
    "d2": dict(tag="gd92-r4-d2", profile="r4_kg0_k16_f015_g155",
               overrides=dict(GD92, SIM_GATE_DYN_SCALE=1.00),
               jar_ds=JAR_DS, bundle_ds=BUNDLE),
}


def run(names):
    refs = []
    for n in names:
        j = JOBS[n]
        ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=j["bundle_ds"],
                        jar_ds=j["jar_ds"], sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-3s -> %s profile=%s overrides=%s" % (
            n, ref, j["profile"], json.dumps(j["overrides"])), flush=True)
        refs.append(ref)
    print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        out = ks.fetch(JOBS[n]["tag"])
        print("FETCH %-3s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:] or ["d0", "d1", "d2"]
    run(a)
