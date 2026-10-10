#!/usr/bin/env python3
"""HO4-P3 (ADDENDUM-5 §5.3 cong O, 31e3c9e7): kernel Kaggle `ho4-dev-oi` dung lai OI per-coin tu Vision daily metrics
(TOAN lich su moi coin; port ho3b_oi_rebuild = VisionMetricsClient.parseDay + quy uoc create_time theo (symbol, ngay) +
ExportFundingOiPerCoin.writeCoin), ghi ban ghi ts in [2025-06-01, 2026-01-01) UTC -> out/oi_rebuilt.bin.gz (BE ts i64, sym i16,
5 x f32), roi so voi file ghim e3887f63 (dataset funding-oi-percoin) tren lat S: phan bo lech theo cot/thang (khong nguong).
Usage: ho4_oi_kernel.py submit <tag> | status <tag> | fetch <tag>"""
import json, logging, os, re, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4_oi")
USER = "chuyendinh"
WD = "/home/ubuntu/claude_master/1010/ho4/kaggle"
SRC = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/ho3b_oi_rebuild.py"
PIN_SHA = "e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec"
S_LO, S_HI = 1751302800000, 1767200400000


def rebuild_src():
    s = open(SRC).read()
    rep = [('EMIT_LO = int(pd.Timestamp("2025-12-29", tz="UTC").value // 10**6)', 'EMIT_LO = int(pd.Timestamp("2025-06-01", tz="UTC").value // 10**6)'),
           ('EMIT_HI = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)', 'EMIT_HI = int(pd.Timestamp("2026-01-01", tz="UTC").value // 10**6)'),
           ('LAST_DATE = "2026-09-30"', 'LAST_DATE = "2025-12-31"'),
           ('if not dates or dates[-1] < "2025-12-28":', 'if not dates or dates[-1] < "2025-05-31":'),
           ('pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")', 'pd.read_csv(SMAP)'),
           ('if __name__ == "__main__":\n    main()', '')]
    for a, b in rep:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    return s


KX = r'''"""HO4 OI kernel — SINH TU ho4_oi_kernel.py (ADDENDUM-5 31e3c9e7)"""
import glob, gzip, hashlib, json, logging, os, sys, time, datetime
import numpy as np
IN, WORK = "/kaggle/input", "/kaggle/working"
os.makedirs(WORK + "/out", exist_ok=True)
SMAP = [p for p in glob.glob(IN + "/**/symbol_map.csv", recursive=True) if "/funding-oi-percoin/" in p][0]
PIN = [p for p in glob.glob(IN + "/**/oi_percoin_full.bin", recursive=True) if "/funding-oi-percoin/" in p][0]
S_LO, S_HI = __S_LO__, __S_HI__
PIN_SHA = "__PIN_SHA__"
exec(compile(__REBUILD_SRC__, "ho3b_oi_rebuild_ho4", "exec"))
LG = logging.getLogger("ho4-oi")
RES = dict(prereg="ADDENDUM-5 31e3c9e7", emit=[EMIT_LO, EMIT_HI], last_date=LAST_DATE)
def save():
    json.dump(RES, open(WORK + "/result.json", "w"), indent=1)
h = hashlib.sha256()
with open(PIN, "rb") as f:
    for b in iter(lambda: f.read(1 << 24), b""):
        h.update(b)
RES["pin_sha256"] = h.hexdigest(); RES["pin_ok"] = RES["pin_sha256"] == PIN_SHA
LG.info("PIN sha ok=%s", RES["pin_ok"]); save()
if not RES["pin_ok"]:
    sys.exit(1)
t0 = time.time()
sys.argv = ["x", "/tmp/oi", "4", "16"]
os.makedirs("/tmp/oi", exist_ok=True)
main()
RES["rebuild_secs"] = round(time.time() - t0)
RES["summary"] = json.load(open("/tmp/oi/SUMMARY.json"))["total"]
fs = sorted(glob.glob("/tmp/oi/*.bin"))
RB = np.concatenate([np.fromfile(f, dtype=ODT) for f in fs]) if fs else np.zeros(0, ODT)
with gzip.open(WORK + "/out/oi_rebuilt.bin.gz", "wb", 6) as fo:
    fo.write(RB.astype(ODT).tobytes())
RES["rebuilt_rows"] = int(len(RB)); RES["rebuilt_files"] = len(fs); save()
LG.info("rebuilt %d dong, %d file (%ds)", len(RB), len(fs), RES["rebuild_secs"])
# ---- cong O (mo ta): rebuilt vs ghim tren S ----
def key(a):
    return a["ts"].astype(np.int64) * 4096 + a["sym"].astype(np.int64)
n = os.path.getsize(PIN) // ODT.itemsize
parts = []
for k in range(0, n, 10_000_000):
    c = np.fromfile(PIN, dtype=ODT, count=min(10_000_000, n - k), offset=k * ODT.itemsize)
    t = c["ts"].astype(np.int64)
    parts.append(c[(t >= S_LO) & (t < S_HI)].copy())
P = np.concatenate(parts); del parts
t = RB["ts"].astype(np.int64)
Q = RB[(t >= S_LO) & (t < S_HI)]
kp, kq = key(P), key(Q)
RES["pin_dup_keys"] = int(len(kp) - len(np.unique(kp))); RES["reb_dup_keys"] = int(len(kq) - len(np.unique(kq)))
com, ia, ib = np.intersect1d(kp, kq, return_indices=True)
O = dict(pin_rows=int(len(P)), reb_rows=int(len(Q)), common=int(len(com)), pin_only=int(len(P) - len(com)), reb_only=int(len(Q) - len(com)))
NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
a = P["oi"][ia].astype(np.float64); b = Q["oi"][ib].astype(np.float64)
ts_c = P["ts"][ia].astype(np.int64)
day_of = (ts_c + 7 * 3600000) // 86400000          # ngay +07
ud = np.unique(day_of)
mlab = np.array([datetime.datetime.utcfromtimestamp(int(d) * 86400).strftime("%Y-%m") for d in ud])
dmap = dict(zip(ud.tolist(), mlab.tolist()))
mon_full = mlab[np.searchsorted(ud, day_of)]
cols = {}
for j, nm in enumerate(NAMES):
    x, y = a[:, j], b[:, j]
    bothnan = np.isnan(x) & np.isnan(y)
    bit = (x == y) | bothnan
    rel = bit | (np.abs(x - y) <= 1e-6 * np.maximum(1.0, np.abs(y)))
    cols[nm] = dict(bit=float(bit.mean()), rel1e6=float(rel.mean()), nan_pin_only=int((np.isnan(x) & ~np.isnan(y)).sum()),
                    nan_reb_only=int((~np.isnan(x) & np.isnan(y)).sum()))
    if mon_full is not None:
        bym = {}
        for mm in sorted(set(dmap.values())):
            sel = mon_full == mm
            bym[mm] = round(float(rel[sel].mean()), 6) if sel.any() else None
        cols[nm]["rel1e6_by_month"] = bym
O["cols"] = cols
RES["gate_O"] = O
save()
LG.info("CONG O: %s", json.dumps({k: v for k, v in O.items() if k != "cols"}))
for nm in NAMES:
    LG.info("  %s bit=%.6f rel=%.6f", nm, cols[nm]["bit"], cols[nm]["rel1e6"])
LG.info("OI_DONE")
'''


def submit(tag):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ho4_exp_kernel as E
    act = E.active()
    if len(act) >= 2:
        log.error("DA CO %d kernel dang chay %s — khong day", len(act), act)
        sys.exit(3)
    ref = "%s/%s" % (USER, E.slug(tag))
    fol = os.path.join(WD, E.slug(tag))
    os.makedirs(fol, exist_ok=True)
    code = (KX.replace("__REBUILD_SRC__", repr(rebuild_src())).replace("__S_LO__", str(S_LO)).replace("__S_HI__", str(S_HI))
            .replace("__PIN_SHA__", PIN_SHA))
    compile(code, "k", "exec")
    open(os.path.join(fol, "run.py"), "w").write(code)
    md = {"id": ref, "title": E.slug(tag), "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [USER + "/funding-oi-percoin"], "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(os.path.join(fol, "kernel-metadata.json"), "w"), indent=1)
    r = E.api().kernels_push(fol)
    log.info("PUSHED %s %s (active truoc: %s)", ref, getattr(r, "url", r), act)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ho4_exp_kernel as E
    if sys.argv[1] == "submit":
        submit(sys.argv[2])
    elif sys.argv[1] == "status":
        E.status(sys.argv[2])
    else:
        E.fetch(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else r".")
