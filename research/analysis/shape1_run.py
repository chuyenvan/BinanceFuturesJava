"""SHAPE1-EARLY-CUT runner — docs/prereg/PREREG_SHAPE1_EARLY_CUT.md.

Hinh dang #1: CAT LO SOM (3 gia tri CHUA THU). Nen (KHONG doi): KEEPLEG0 + nhip THIET KE
(`SIM_ENTRY_SAMPLE_MIN=15`) + 2 knob default khai TUONG MINH (SIM_F_BASE=0,03 / SELECTOR_RANK_TOPK=8,
da chung minh VO HAI: md5 == cd-sel15). Bundle `sim-x1-2021-bundle`, jar `sim-jar-cadence`.
Cua so DEV 2021-07-01..2025-12-31. 0 sim tren Oracle.

  S0 cd-sel15 (DUNG LAI)
  S1 sh1-s1-sl05    : SIM_PRE_ARM_SL=-0.05            (K=8)
  S2 sh1-s2-sl03k16 : SIM_PRE_ARM_SL=-0.03 + TOPK=16
  S3 sh1-s3-ts8     : SIM_LOSER_TIME_STOP_HOURS=8
  S4 sh1-s4-sl03    : SIM_PRE_ARM_SL=-0.03            (K=8)

Dung: python3 research/analysis/shape1_run.py arms|s1|s2|s3|s4 [--no-wait] [--fetch]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-cadence"
END = "20251231"
TICKER_MIN = 1826
SHA = "3b6c6e9+prereg-shape1-early-cut"

KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0,
        "SIM_ENTRY_SAMPLE_MIN": 15, "SIM_F_BASE": 0.03, "SELECTOR_RANK_TOPK": 8}


def ov(*extra):
    o = dict(KEEP)
    for d in extra:
        o.update(d)
    return o


JOBS = {
    "s1": ("sh1-s1-sl05", ov({"SIM_PRE_ARM_SL": -0.05})),
    "s2": ("sh1-s2-sl03k16", ov({"SIM_PRE_ARM_SL": -0.03, "SELECTOR_RANK_TOPK": 16})),
    "s3": ("sh1-s3-ts8", ov({"SIM_LOSER_TIME_STOP_HOURS": 8})),
    "s4": ("sh1-s4-sl03", ov({"SIM_PRE_ARM_SL": -0.03})),
}


def submit_one(name, push=True):
    tag, o = JOBS[name]
    ref = ks.submit(tag, "x1_gs_t170", o, bundle_ds=BUNDLE, jar_ds=JAR_DS,
                    sim_end_date=END, ticker_min_days=TICKER_MIN, code_sha=SHA, push=push)
    print("SUBMIT %-3s -> %-18s %s" % (name, ref, json.dumps(o)), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name][0])
    print("FETCH  %-3s %s" % (name, json.dumps(out["result"])), flush=True)
    return out


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    do_wait = "--no-wait" not in sys.argv
    only_fetch = "--fetch" in sys.argv
    names = []
    for x in (a or ["arms"]):
        names.extend(["s1", "s2", "s3", "s4"] if x == "arms" else [x])
    if not only_fetch:
        print("free_slots=%d" % ks.free_slots(), flush=True)
        refs = [submit_one(n) for n in names]
        if do_wait:
            print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        fetch_one(n)
