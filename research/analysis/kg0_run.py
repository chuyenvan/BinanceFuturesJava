"""KG0 runner — day 8 chan cua docs/PREREG_GATESCALE_KEEPLEG0.md len Kaggle CPU kernel.

Nen = PRODUCTION FLATGRID KEEPLEG0 (= prof_x1_gs_t170 + DUNG 2 dong
DCA_GRID_WEIGHTS=1,1,1,1 / DCA_GRID_SCALE=6.0).

  nhom (1): kg0-g170 (OFF, = moc + cong parity P2) | kg0-cap (+CONC_CAP_PERCOIN 15%)
  nhom (2): kg0-g155 / kg0-g140 / kg0-g125 / kg0-g110 / kg0-g100 (+SIM_GATE_DYN_SCALE)
  nhom (3): kg0-cap-s<v>  (CAP + scale s* theo LUAT CHOT TRUOC trong pre-reg §2.3)

Bundle `sim-x1-2021-bundle` (snapshot: chi co 3 profile) => bien the dien dat bang OVERRIDE tren
prof_x1_gs_t170 (tuong duong 1 file profile co them dung cac dong do; kernel luu lai
prof_run.properties lam bang chung). KHONG jar_ds => dung jar mac dinh cua bundle (= jar da tao ra
t170-x1-2021 md5 efb793e2). Cua so DEV 2021-07-01..2025-12-31. Chi phi Kaggle = 0.
KHONG chay Java/sim tren Oracle.

Dung: python3 research/analysis/kg0_run.py <g170|cap|g155|g140|g125|g110|g100|w1|w2|all|s*>
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
END = "20251231"
SHA = "2350f47+prereg-gatescale-keepleg0"

# KEEPLEG0 = x1_gs_t170 + DUNG 2 dong (docs/DECISION_SHADOW_FLATGRID_KEEPLEG0.md)
KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}
CAP = {"CONC_CAP_PERCOIN_ENABLED": 1, "CONC_CAP_PERCOIN_PCT": 0.15}


def _ov(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o


def gs(v):
    return {"SIM_GATE_DYN_SCALE": v}


JOBS = {
    "g170": dict(tag="kg0-g170", profile="x1_gs_t170", overrides=_ov(KEEP)),
    "cap":  dict(tag="kg0-cap",  profile="x1_gs_t170", overrides=_ov(KEEP, CAP)),
    "g155": dict(tag="kg0-g155", profile="x1_gs_t170", overrides=_ov(KEEP, gs(1.55))),
    "g140": dict(tag="kg0-g140", profile="x1_gs_t170", overrides=_ov(KEEP, gs(1.40))),
    "g125": dict(tag="kg0-g125", profile="x1_gs_t170", overrides=_ov(KEEP, gs(1.25))),
    "g110": dict(tag="kg0-g110", profile="x1_gs_t170", overrides=_ov(KEEP, gs(1.10))),
    "g100": dict(tag="kg0-g100", profile="x1_gs_t170", overrides=_ov(KEEP, gs(1.00))),
}
ALIAS = {"w1": ["g170", "cap", "g155", "g140", "g125"],
         "w2": ["g110", "g100"],
         "all": ["g170", "cap", "g155", "g140", "g125", "g110", "g100"]}


def submit_one(name):
    j = JOBS[name]
    ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=BUNDLE,
                    sim_end_date=END, code_sha=SHA)
    print("SUBMIT %-6s -> %s profile=%s overrides=%s" % (
        name, ref, j["profile"], json.dumps(j["overrides"])), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(JOBS[name]["tag"])
    print("FETCH  %-6s %s" % (name, json.dumps(out["result"])), flush=True)
    print("       printDone=%s" % out["print_done"], flush=True)


def run(names, do_wait=True, do_fetch=True):
    refs = [submit_one(n) for n in names]
    if do_wait:
        print("STATUS", ks.wait(refs), flush=True)
    if do_fetch:
        for n in names:
            fetch_one(n)


def cap_at(scale, key="s"):
    """Nhom (3): KEEPLEG0 + CAP + gate-scale = scale (tag kg0-cap-<key>)."""
    tag = "kg0-%s-s%s" % (key, ("%.2f" % scale).replace(".", ""))
    ref = ks.submit(tag, "x1_gs_t170", _ov(KEEP, CAP, gs(scale)), bundle_ds=BUNDLE,
                    sim_end_date=END, code_sha=SHA)
    print("SUBMIT %s -> %s overrides=%s" % (
        tag, ref, json.dumps(_ov(KEEP, CAP, gs(scale)))), flush=True)
    print("STATUS", ks.wait([ref]), flush=True)
    print("FETCH  %s" % json.dumps(ks.fetch(tag)["result"]), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    names = []
    for x in a:
        names.extend(ALIAS.get(x, [x]))
    run(names)
