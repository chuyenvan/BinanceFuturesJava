"""GATE-SCALE SWEEP runner — day 4 chan MOI cua docs/PREREG_GATESCALE_SWEEP.md len Kaggle.

Thang chot {1.70, 1.55, 1.40, 1.25, 1.10, 1.00}:
  1.70 = kaggle_sim/out/t170-x1-2021   -> TAI SU DUNG (md5 efb793e2468ca3a7318da0f0ad23d4fc)
  1.00 = kaggle_sim/out/hn-t100        -> TAI SU DUNG (md5 dc16e4da6ff6cb7b8d41c592bc3d9c45)
  1.55 / 1.40 / 1.25 / 1.10            -> CHAY MOI (4 kernel, day la file nay)

Moi chan: profile = x1_c3_full + DUNG 1 key SIM_GATE_DYN_SCALE=<v> (da commit thanh
profiles/x1_gs_t1*.properties). Bundle sim-x1-2021-bundle (= wfo_ds_x1_2021, 2021-07-01..
2025-12-31). KHONG override key nao khac. KHONG jar_ds => dung sim.jar mac dinh trong bundle
(dung CHINH jar da tao ra t170-x1-2021). Chi phi Kaggle = 0.

Dung: python3 research/analysis/gatescale_run.py [t155|t140|t125|t110|all]
KHONG chay Java/sim tren Oracle.
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
SHA = "dc5aecc+prereg-gatescale-sweep"

# [!] BUNDLE LA MOT SNAPSHOT (docs/KAGGLE_SIM.md §0.4): sim-x1-2021-bundle chi chua 3 profile
#   (`prof_x1_c3_full`, `prof_x1_gs_t170`, `prof_x1_c3_full_regime_brc`) — KHONG chua 4 profile
#   MOI `x1_gs_t155/140/125/110` (them sau khi bundle duoc tao 2026-09-21). Push kernel voi
#   profile do => kernel exit "MISSING /kaggle/input/**/prof_x1_gs_t155.properties" (da gap
#   that 2026-09-24, tag sim-gs-t155 vu 1). => DUNG DUONG OVERRIDE (khuon `exithighn_run.py`):
#   profile `x1_c3_full` + 1 override `SIM_GATE_DYN_SCALE=<v>`. Kernel COPY profile roi ghi
#   override => `prof_run.properties` ra DUNG bang noi dung `profiles/x1_gs_t1*.properties`
#   (tru `WFO_FUNDING_PRED_DIR` bi tro vao mount Kaggle) — kiem lai duoc tu output tung chan.
JOBS = {
    "t155": dict(tag="gs-t155", profile="x1_c3_full", overrides={"SIM_GATE_DYN_SCALE": 1.55}),
    "t140": dict(tag="gs-t140", profile="x1_c3_full", overrides={"SIM_GATE_DYN_SCALE": 1.40}),
    "t125": dict(tag="gs-t125", profile="x1_c3_full", overrides={"SIM_GATE_DYN_SCALE": 1.25}),
    "t110": dict(tag="gs-t110", profile="x1_c3_full", overrides={"SIM_GATE_DYN_SCALE": 1.10}),
}
ALIAS = {"all": ["t155", "t140", "t125", "t110"]}


def run(names):
    refs = []
    for n in names:
        j = JOBS[n]
        ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE,
                        sim_end_date=END, code_sha=SHA)
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
