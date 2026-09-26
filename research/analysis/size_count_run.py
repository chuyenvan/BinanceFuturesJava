"""SIZE-COUNT runner — docs/prereg/PREREG_SIZE_COUNT_HARNESS.md.

Truc "GIAM MARGIN / TANG SO LENH" duoi TRAN GROSS 70% CUNG.

Nen (KHONG doi): KEEPLEG0 (= prof x1_gs_t170 + DCA_GRID_WEIGHTS=1,1,1,1 + DCA_GRID_SCALE=6.0)
+ nhip THIET KE (`SIM_ENTRY_SAMPLE_MIN=15`). Bundle `sim-x1-2021-bundle`, jar `sim-jar-cadence`
(code 3b6c6e9/8aedde8 — KHONG sua Java). Cua so DEV 2021-07-01..2025-12-31.

2 knob (da co san trong code, chi khai qua profile/override — KHONG rebuild):
  size/lenh  : SIM_F_BASE = F_BASE (default 0,03) ; 0,03 * size_mult
  rank-topk  : SELECTOR_RANK_TOPK = K (file = 8)

Arms (chot TRUOC):
  B0  size x1   K=8   -> tag `cd-sel15`  (DUNG LAI, khong chay moi)
  B1  size x0,5 K=8   -> sc-b1
  B2  size x0,5 K=16  -> sc-b2
  B3  size x0,25 K=32 -> sc-b3
  B4  size x0,5 K=32  -> sc-b4
  PAR size x1   K=8   -> sc-par  (khai TUONG MINH ca 2 knob = default => phai byte-identical cd-sel15)

Chi phi Kaggle = 0. KHONG chay Java/sim tren Oracle. KHONG push git.
Dung:
  python3 research/analysis/size_count_run.py arms          # B1..B4 + PAR
  python3 research/analysis/size_count_run.py b1 b2         # chon tung chan
  python3 research/analysis/size_count_run.py --size-mult 0.4 --rank-topk 12 --arm probe9
  (them --no-wait de chi push; --fetch de chi lay ket qua)
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE = "sim-x1-2021-bundle"
JAR_DS = "sim-jar-cadence"
END = "20251231"
TICKER_MIN = 1826
SHA = "3b6c6e9+prereg-size-count"
F_BASE0 = 0.03

KEEP = {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0}
CADENCE = {"SIM_ENTRY_SAMPLE_MIN": 15}

# name -> (size_mult, rank_topk)
ARMS = {
    "b1": (0.5, 8),
    "b2": (0.5, 16),
    "b3": (0.25, 32),
    "b4": (0.5, 32),
    "par": (1.0, 8),   # khai tuong minh default => cung parity voi cd-sel15
}
# B0 = nen, dung lai (khong submit)
B0_TAG = "cd-sel15"
B0_MD5 = "1317191624d316d955223311ae693228"


def overrides(size_mult, k):
    """Override = KEEPLEG0 + cadence + 2 knob khai TUONG MINH (thay gia tri profile, khong trung key)."""
    o = dict(KEEP)
    o.update(CADENCE)
    o["SIM_F_BASE"] = round(F_BASE0 * float(size_mult), 6)
    o["SELECTOR_RANK_TOPK"] = int(k)
    return o


def tag_of(name):
    return "sc-" + name


def submit_one(name, size_mult, k, push=True):
    tag = tag_of(name)
    ov = overrides(size_mult, k)
    ref = ks.submit(tag, "x1_gs_t170", ov, bundle_ds=BUNDLE, jar_ds=JAR_DS,
                    sim_end_date=END, ticker_min_days=TICKER_MIN, code_sha=SHA, push=push)
    print("SUBMIT %-6s -> %s size=%s K=%d overrides=%s" % (
        name, ref, size_mult, k, json.dumps(ov)), flush=True)
    return ref


def fetch_one(name):
    out = ks.fetch(tag_of(name))
    print("FETCH  %-6s %s" % (name, json.dumps(out["result"])), flush=True)
    print("       printDone=%s" % out["print_done"], flush=True)
    return out


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    do_wait = "--no-wait" not in sys.argv
    only_fetch = "--fetch" in sys.argv

    # ad-hoc: --size-mult S --rank-topk K --arm NAME
    jobs = []
    if "--size-mult" in sys.argv:
        def _val(flag):
            i = sys.argv.index(flag)
            return sys.argv[i + 1]
        name = _val("--arm") if "--arm" in sys.argv else "adhoc"
        jobs.append((name, float(_val("--size-mult")), int(_val("--rank-topk"))))
    else:
        names = []
        for x in (a or ["arms"]):
            if x == "arms":
                names.extend(["b1", "b2", "b3", "b4", "par"])
            elif x == "b0":
                print("B0 = %s (dung lai, md5 %s) — KHONG submit." % (B0_TAG, B0_MD5), flush=True)
            else:
                names.append(x)
        jobs = [(n, *ARMS[n]) for n in names]

    print("free_slots=%d | jobs=%s" % (ks.free_slots(), [j[0] for j in jobs]), flush=True)
    if only_fetch:
        for n, _, _ in jobs:
            fetch_one(n)
        return
    refs = [submit_one(n, s, k) for (n, s, k) in jobs]
    if do_wait:
        print("STATUS", ks.wait(refs), flush=True)
    for n, _, _ in jobs:
        fetch_one(n)


if __name__ == "__main__":
    main()
