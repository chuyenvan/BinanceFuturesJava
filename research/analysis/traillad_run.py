"""TRAIL-LADDER runner — day cac chan cua docs/PREREG_TRAIL_LADDER.md len Kaggle.

  par   : profile x1_gs_t170 NGUYEN BAN, KHONG override => cong chan BUOC 0 (md5 efb793e2)
  part  : nhu par + SIM_TRAIL_TRACE=1 (do-luong-only; printDone phai VAN efb793e2)
  l1/l2/l3 : profile x1_tl_l1/l2/l3 (bang bac thang L1/L2/L3) + SIM_TRAIL_TRACE=1

Dung: python3 research/analysis/traillad_run.py <par|part|l1|l2|l3|all>
KHONG chay Java tren Oracle. Moi sim chay tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-trailladder"     # dataset rieng chi chua sim.jar (code TRAIL-LADDER) + prof_x1_tl_*
END = "20251231"
SHA = "TRAIL_LADDER"

TRACE = {"SIM_TRAIL_TRACE": 1}

JOBS = {
    "par":  dict(tag="tl-par",  profile="x1_gs_t170", overrides={},        jar_ds=JAR_DS),
    "part": dict(tag="tl-part", profile="x1_gs_t170", overrides=dict(TRACE), jar_ds=JAR_DS),
    "l1":   dict(tag="tl-l1",   profile="x1_tl_l1",   overrides=dict(TRACE), jar_ds=JAR_DS),
    "l2":   dict(tag="tl-l2",   profile="x1_tl_l2",   overrides=dict(TRACE), jar_ds=JAR_DS),
    "l3":   dict(tag="tl-l3",   profile="x1_tl_l3",   overrides=dict(TRACE), jar_ds=JAR_DS),
}


def run(names):
    refs = []
    for n in names:
        j = JOBS[n]
        ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE,
                        jar_ds=j["jar_ds"], sim_end_date=END, code_sha=SHA)
        print("SUBMIT %s -> %s %s %s" % (n, ref, j["profile"], json.dumps(j["overrides"])),
              flush=True)
        refs.append(ref)
    print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        out = ks.fetch(JOBS[n]["tag"])
        print("FETCH %-5s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    if a == ["all"]:
        a = ["par", "part", "l1", "l2", "l3"]
    run(a)
