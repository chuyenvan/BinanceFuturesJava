"""PEAK-CLOSE runner — day cac chan cua docs/PREREG_PEAK_CLOSE.md len Kaggle.

  par   : profile x1_gs_t170 NGUYEN BAN, KHONG override => CONG PARITY (md5 efb793e2, jar MOI)
  part  : nhu par + SIM_TRAIL_TRACE=1 (do-luong-only; printDone phai VAN efb793e2) + trace baseline
  close : profile x1_gs_t170_close (TS_PEAK_MODE=close) + SIM_TRAIL_TRACE=1 => chan F3

Dung: python3 research/analysis/peakclose_run.py <par|part|close|all>
KHONG chay Java tren Oracle. Moi sim chay tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-peakclose"       # dataset chi chua sim.jar (code PEAK-CLOSE) + prof_x1_gs_t170_close
END = "20251231"
SHA = "dca07ce"

TRACE = {"SIM_TRAIL_TRACE": 1}

JOBS = {
    "par":   dict(tag="pc-par",   profile="x1_gs_t170",       overrides={},          jar_ds=JAR_DS),
    "part":  dict(tag="pc-part",  profile="x1_gs_t170",       overrides=dict(TRACE), jar_ds=JAR_DS),
    "close": dict(tag="pc-close", profile="x1_gs_t170_close", overrides=dict(TRACE), jar_ds=JAR_DS),
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
        print("FETCH %-6s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    if a == ["all"]:
        a = ["par", "part", "close"]
    run(a)
