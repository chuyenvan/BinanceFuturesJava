"""EXIT-STRUCT P6 runner — docs/prereg/PREREG_EXIT_STRUCT_P6.md.

Khu confound SIZE cua A2 (RESULT_EXIT_STRUCT.md §6): grid OFF tat luon DCA_GRID_SCALE=6,0
=> A2 chay ~1/6 size. Arm nay = A2 + SIM_F_BASE=0,18 (= 0,03 x 6) de khop size A0.

  A2      = xs-a2    : SEL15 + OFF_TS(0) + DCA_GRID_ENABLED=false            (DA CO)
  A2size  = xs-a2s6  : A2 + SIM_F_BASE=0.18                                  (chay moi)

Jar: TAI DUNG sim-jar-cadence (commit 3b6c6e9) — KHONG sua code, KHONG build lai.
Chi phi Kaggle = 0. KHONG chay Java/sim tren Oracle. KHONG push file du lieu.
Usage: python3 research/analysis/exit_struct_p6_run.py <name|all> [--no-wait]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
TICKER_MIN = 1826
SHA = "3b6c6e9+prereg-exit-struct-p6"
JAR_DS = "sim-jar-cadence"

KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}
SEL15 = {"SIM_ENTRY_SAMPLE_MIN": 15}
OFF_TS = {"SIM_LOSER_TIME_STOP_HOURS": 0}
REACTIVE = {"DCA_GRID_ENABLED": False}
F_BASE0 = 0.03
SIZE_MULT = 6.0                       # = DCA_GRID_SCALE cua A0


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


JOBS = {
    "a2s6": dict(tag="xs-a2s6", profile="x1_gs_t170",
                 overrides=_ov(KEEP, SEL15, OFF_TS, REACTIVE,
                               {"SIM_F_BASE": round(F_BASE0 * SIZE_MULT, 6)})),
}
ALIAS = {"all": ["a2s6"]}


def submit_one(name, push=True):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                    sim_end_date=END, ticker_min_days=TICKER_MIN, code_sha=SHA, push=push)
    print("SUBMIT %-5s -> %s overrides=%s" % (name, ref, json.dumps(j["overrides"])), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    print("FETCH  %-5s %s" % (name, json.dumps(out["result"])), flush=True)
    return out


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    do_wait = "--no-wait" not in sys.argv
    names = []
    for x in (a or ["all"]):
        names.extend(ALIAS.get(x, [x]))
    print("free_slots=%d" % ks.free_slots(), flush=True)
    refs = [submit_one(n) for n in names]
    if do_wait:
        print("STATUS", ks.wait(refs), flush=True)
    for n in names:
        fetch_one(n)
