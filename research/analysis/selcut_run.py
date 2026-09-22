"""SELCUT runner — day 3 chan cua docs/PREREG_SELECTOR_LEG_CUT.md len Kaggle.

  parity  : x1_gs_t170 nguyen ban (cong chan BUOC 0) — md5 phai = efb793e2468ca3a7318da0f0ad23d4fc
  cutpar  : jar MOI (chua SELECTOR_LEG_CUT, default false) => cong parity rieng cho jar (muc 3.1)
  cut     : V1  SELECTOR_LEG_CUT=1        (CAT HAN leg selector)
  topk3   : V2  SELECTOR_RANK_TOPK=3      (GIOI HAN do phu; profile-only, jar cu)

Dung: python3 research/analysis/selcut_run.py <parity|cutpar|cut|topk3|all>
KHONG chay Java tren Oracle. Moi sim chay tren Kaggle CPU kernel (chi phi 0).
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-selcut"          # dataset rieng chi chua sim.jar (co SELECTOR_LEG_CUT)
PROFILE = "x1_gs_t170"
END = "20251231"
SHA_COMMON = "e566354"             # commit pre-reg + fix tool

JOBS = {
    "parity": dict(tag="selcut-par0", overrides={}, jar_ds=None,
                   code_sha=SHA_COMMON),
    "cutpar": dict(tag="selcut-cutpar", overrides={}, jar_ds=JAR_DS,
                   code_sha=SHA_COMMON + "+selcut-jar"),
    "cut":    dict(tag="selcut-cut", overrides={"SELECTOR_LEG_CUT": 1}, jar_ds=JAR_DS,
                   code_sha=SHA_COMMON + "+selcut-jar"),
    "topk3":  dict(tag="selcut-topk3", overrides={"SELECTOR_RANK_TOPK": 3}, jar_ds=None,
                   code_sha=SHA_COMMON),
}


def run(names):
    refs = []
    for n in names:
        j = JOBS[n]
        ref = ks.submit(j["tag"], PROFILE, j["overrides"], bundle_ds=BUNDLE, jar_ds=j["jar_ds"],
                        sim_end_date=END, code_sha=j["code_sha"])
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
        a = ["parity", "cutpar", "cut", "topk3"]
    run(a)
