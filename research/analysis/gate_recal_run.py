"""GATE-RECAL runner — day cac chan cua docs/prereg/PREREG_GATE_RECAL.md len Kaggle CPU kernel.

Nen = PRODUCTION FLATGRID KEEPLEG0 (= prof_x1_gs_t170 + DUNG 2 dong
DCA_GRID_WEIGHTS=1,1,1,1 / DCA_GRID_SCALE=6.0), cua so DEV 2021-07-01..2025-12-31.

Jar: dataset RIENG `chuyendinh/sim-jar-gate-recal` (jar build tu commit fec652e — them 2 key
SIM_GATE_P15_Q / SIM_ENTRY_SAMPLE_MIN). KHONG tao lai bundle; profile dien dat bang OVERRIDE tren
prof_x1_gs_t170 (kernel luu prof_run.properties lam bang chung).

  VIEC 2 parity (TAT = y nguyen):
    par-t170 : x1_gs_t170 (khong override)           -> md5 efb793e2468ca3a7318da0f0ad23d4fc / n1089 / eq111070
    par-kg0  : KEEPLEG0 (2 dong DCA)                 -> md5 99e42b75cf1a2142f9cd14dc72e371ba / n1085 / eq103083
  VIEC 3 arms (nhip 1 phut):
    kg0-tat  == par-kg0 (dung lai lam baseline, KHONG chay lai)
    q995 / q998 / q999 : KEEPLEG0 + SIM_GATE_P15_Q = 0.995 / 0.998 / 0.999
  VIEC 4 nhip:
    q998-15m : KEEPLEG0 + SIM_GATE_P15_Q=0.998 + SIM_ENTRY_SAMPLE_MIN=15 (96 co hoi/ngay)

Chi phi Kaggle = 0. KHONG chay Java/sim tren Oracle. KHONG push git.
Dung: python3 research/analysis/gate_recal_run.py <name|all|arms|par> [--no-wait]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
TICKER_MIN = 1826
SHA = "fec652e+prereg-gate-recal"
JAR_DS = "sim-jar-gate-recal"

KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


def q(v):
    return {"SIM_GATE_P15_Q": v}


JOBS = {
    "par-t170": dict(tag="gr-par-t170", profile="x1_gs_t170", overrides={}),
    "par-kg0":  dict(tag="gr-par-kg0",  profile="x1_gs_t170", overrides=_ov(KEEP)),
    "q995":     dict(tag="gr-kg0-q995", profile="x1_gs_t170", overrides=_ov(KEEP, q(0.995))),
    "q998":     dict(tag="gr-kg0-q998", profile="x1_gs_t170", overrides=_ov(KEEP, q(0.998))),
    "q999":     dict(tag="gr-kg0-q999", profile="x1_gs_t170", overrides=_ov(KEEP, q(0.999))),
    "q998-15m": dict(tag="gr-kg0-q998-15m", profile="x1_gs_t170",
                     overrides=_ov(KEEP, q(0.998), {"SIM_ENTRY_SAMPLE_MIN": 15})),
}
ALIAS = {"par": ["par-t170", "par-kg0"],
         "arms": ["q995", "q998", "q999"],
         "all": ["par-t170", "par-kg0", "q995", "q998", "q999", "q998-15m"]}


def submit_one(name, push=True):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                    sim_end_date=END, ticker_min_days=TICKER_MIN, code_sha=SHA, push=push)
    print("SUBMIT %-9s -> %s profile=%s overrides=%s" % (
        name, ref, j["profile"], json.dumps(j["overrides"])), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    print("FETCH  %-9s %s" % (name, json.dumps(out["result"])), flush=True)
    print("       printDone=%s" % out["print_done"], flush=True)
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
