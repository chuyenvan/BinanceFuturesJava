"""TICKBLK runner — day 4 chan cua docs/prereg/PREREG_TICK_BLOCK.md len Kaggle.

  par     : x1_gs_t170 nguyen ban + jar MOI, co OFF  — md5 phai = efb793e2468ca3a7318da0f0ad23d4fc
  depth   : V1  SIM_TICK_BLOCK_IND=DEPTH    (rateDownAvg, chan nhom "it am nhat")
  breadth : V2  SIM_TICK_BLOCK_IND=BREADTH  (%coin rot 1M <= -3%, chan nhom "thap nhat")
  drop15  : V3  SIM_TICK_BLOCK_IND=DROP15M  (rateDown15MAvg, chan nhom "it am nhat")

Dung: python3 research/analysis/tickblk_run.py <par|depth|breadth|drop15|all>
KHONG chay Java tren Oracle. Moi sim chay tren Kaggle CPU kernel (chi phi 0). KHONG push.
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-tickblk"          # dataset rieng chi chua sim.jar (co TickWeakBlock)
PROFILE = "x1_gs_t170"
END = "20251231"
SHA_COMMON = "b98c9ff"              # commit PREREG_TICK_BLOCK (chot truoc khi chay)

# [FIX 2026-09-23] Ban chay 1 (tag `tickblk-*`, jar sha d14129bf) CO LOI: `new float[]` cua Java
#   = 0.0 (khong phai NaN) => warm-up 14 ngay bi VO HIEU (nguong = 0.0 tu ngay 1) => chan them
#   9.656 phut trong 2021-07-01..2021-09-17 (do bang ban tai lap Python doc lap). Da sua (jar sha
#   715043ed) va CHAY LAI toan bo duoi tag `tickblk2-*`. So cong bo la cua ban da sua.
JOBS = {
    "par":     dict(tag="tickblk2-par",     overrides={}, jar_ds=JAR_DS),
    "depth":   dict(tag="tickblk2-depth",   overrides={"SIM_TICK_BLOCK_IND": "DEPTH"}, jar_ds=JAR_DS),
    "breadth": dict(tag="tickblk2-breadth", overrides={"SIM_TICK_BLOCK_IND": "BREADTH"}, jar_ds=JAR_DS),
    "drop15":  dict(tag="tickblk2-drop15",  overrides={"SIM_TICK_BLOCK_IND": "DROP15M"}, jar_ds=JAR_DS),
}


def run(names):
    refs = []
    for n in names:
        j = JOBS[n]
        ref = ks.submit(j["tag"], PROFILE, j["overrides"], bundle_ds=BUNDLE, jar_ds=j["jar_ds"],
                        sim_end_date=END, code_sha=SHA_COMMON + "+tickblk-jar")
        print("SUBMIT %s -> %s %s" % (n, ref, json.dumps(j["overrides"])), flush=True)
        refs.append(ref)
    print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        out = ks.fetch(JOBS[n]["tag"])
        print("FETCH %-8s %s" % (n, json.dumps(out["result"])), flush=True)
        print("       printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    if a == ["all"]:
        a = ["par", "depth", "breadth", "drop15"]
    run(a)
