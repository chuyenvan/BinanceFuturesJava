"""TRAIL-CAP-1030 runner — day 2 chan cua docs/prereg/PREREG_TRAIL_CAP_1030.md len Kaggle.

  par : profile x1_gs_t170 NGUYEN BAN + SIM_TRAIL_TRACE=1 => CONG PARITY (md5 efb793e2, n=1089)
        (trace la do-luong-only: KHONG duoc doi printDone)
  cap : profile x1_gs_t170_cap1030 (TS_MAX_GAP_WEAK 0.03->0.10, TS_MAX_GAP 0.08->0.30)
        + SIM_TRAIL_TRACE=1 => chan variant

KHONG sua code, KHONG build lai jar: ca 2 cap da doc duoc qua override profile tu 2026-09-03
(Configs.java:801-802). jar dataset `sim-jar-cap1030` chua DUNG jar hien tai
(sha256 70066fca33d347c3b6212dfd613f3a6694ca3684e7aece188790b183dfba24ff)
+ prof_x1_gs_t170_cap1030.properties.

Dung: python3 research/analysis/trailcap1030_run.py <par|cap|all>
KHONG chay Java tren Oracle. Moi sim chay tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-cap1030"
END = "20251231"
SHA = "066ec4e"          # commit pre-reg (code khong doi tu dca07ce)

TRACE = {"SIM_TRAIL_TRACE": 1}

JOBS = {
    "par": dict(tag="tc-par", profile="x1_gs_t170",          overrides=dict(TRACE), jar_ds=JAR_DS),
    "cap": dict(tag="tc-cap", profile="x1_gs_t170_cap1030",  overrides=dict(TRACE), jar_ds=JAR_DS),
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
        print("FETCH %-4s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    if a == ["all"]:
        a = ["par", "cap"]
    run(a)
