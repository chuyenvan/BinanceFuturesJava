"""EXIT-STRUCT runner — docs/prereg/PREREG_EXIT_STRUCT.md.

Bo time-stop 168h + DCA phan xa "toi chet", tren NEN sel15 (RESULT_SIM_CADENCE_MATCH).

  A0 = cd-sel15   : KEEPLEG0 + SIM_ENTRY_SAMPLE_MIN=15                       (DA CO, dung lai)
  A1 = xs-a1      : A0 + SIM_LOSER_TIME_STOP_HOURS=0                         (bo time-stop 168h)
  A2 = xs-a2      : A1 + DCA_GRID_ENABLED=false                              (DCA toi chet) <- chinh
  A3 = xs-a3      : A0 + DCA_GRID_ENABLED=false                              (phan xa + giu TS168)

Jar: TAI DUNG sim-jar-cadence (commit 3b6c6e9) — KHONG sua code, KHONG build lai.
Chi phi Kaggle = 0. KHONG chay Java/sim tren Oracle. KHONG push git.
Usage: python3 research/analysis/exit_struct_run.py <name|all> [--no-wait]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
TICKER_MIN = 1826
SHA = "3b6c6e9+prereg-exit-struct"
JAR_DS = "sim-jar-cadence"

KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}
SEL15 = {"SIM_ENTRY_SAMPLE_MIN": 15}
OFF_TS = {"SIM_LOSER_TIME_STOP_HOURS": 0}
REACTIVE = {"DCA_GRID_ENABLED": False}


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


JOBS = {
    "a1": dict(tag="xs-a1", profile="x1_gs_t170", overrides=_ov(KEEP, SEL15, OFF_TS)),
    "a2": dict(tag="xs-a2", profile="x1_gs_t170", overrides=_ov(KEEP, SEL15, OFF_TS, REACTIVE)),
    "a3": dict(tag="xs-a3", profile="x1_gs_t170", overrides=_ov(KEEP, SEL15, REACTIVE)),
}
ALIAS = {"all": ["a1", "a2", "a3"]}


def submit_one(name, push=True):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                    sim_end_date=END, ticker_min_days=TICKER_MIN, code_sha=SHA, push=push)
    print("SUBMIT %-4s -> %s overrides=%s" % (name, ref, json.dumps(j["overrides"])), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    print("FETCH  %-4s %s" % (name, json.dumps(out["result"])), flush=True)
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
