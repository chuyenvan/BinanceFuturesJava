#!/usr/bin/env python3
"""HO4-P1: sinh research/analysis/ho4p1_exp_kernel.py tu ho4_exp_kernel.py (ADDENDUM-6) bang thay chuoi co assert.
Thay doi: universe = bo loc LIVE (TickerIngestor2AerospikeNew: USDT, ^[A-Z0-9]+$, DIED_SYMBOLS BTCDOM/USDC) ∩ mapper;
duoi volume-0 >= 1440 phut keo toi kline cuoi = settle/delist => bo tu phut dau duoi; tai monthly + daily; ticker gz mtime=0;
CLOSES_1H tu 1m (close phut cuoi moi gio); lifecycle tu kline cua so (luat SymbolLifecycleBuilderLocal); MANIFEST md5.
Usage: python3 ho4p1_mkexp.py"""
import logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("mk")
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/"
s = open(A + "ho4_exp_kernel.py").read()
R = []
R.append(('"""HO4-P3 (ADDENDUM-5 §5.3, 31e3c9e7): kernel Kaggle `ho4-dev-x` dung lai lat DEV',
          '"""HO4-P1 (ADDENDUM-6; sinh boi ho4p1_mkexp.py tu ho4_exp_kernel.py). Goc: HO4-P3 kernel `ho4-dev-x` dung lai lat DEV'))
R.append(('WD = "/home/ubuntu/claude_master/1011/ho4b/kaggle"', 'WD = "/home/ubuntu/claude_master/1011/ho4p1/kaggle"'))
R.append(('"""HO4 exporter kernel — SINH TU ho4_exp_kernel.py (ADDENDUM-5 31e3c9e7)"""',
          '"""HO4-P1 exporter kernel — SINH TU ho4p1_exp_kernel.py (ADDENDUM-6)"""'))
R.append(('RES = dict(tag=CFG["tag"], prereg="ADDENDUM-5 31e3c9e7", steps={}, tasks=[])',
          'RES = dict(tag=CFG["tag"], prereg="ADDENDUM-6", steps={}, tasks=[])'))
R.append(('''def in_uni(s):
    return s.endswith("USDT") and "_" not in s and s in MAPPER''',
          '''DIED = {"BTCDOMUSDT", "USDCUSDT"}                 # DIED_SYMBOLS=BTCDOM,USDC (config live) -> Constants.diedSymbol
def in_uni(s):
    # bo loc LIVE TickerIngestor2AerospikeNew:83/313 (USDT, ^[A-Z0-9]+$, khong diedSymbol) + co trong mapper (quyet dinh 6)
    return s.endswith("USDT") and re.fullmatch(r"[A-Z0-9]+", s) is not None and s not in DIED and s in MAPPER'''))
NEWK = r'''DURL = "https://data.binance.vision/data/futures/um/daily/klines/{s}/1m/{s}-1m-{d}.zip"
def _parse(b):
    z = zipfile.ZipFile(io.BytesIO(b))
    rows = [ln.split(",") for ln in z.read(z.namelist()[0]).decode().splitlines()]
    rows = [r for r in rows if r and r[0].strip().isdigit()]
    if not rows:
        return None
    ts = np.array([int(r[0]) for r in rows], np.int64)
    # o,h,l,c,quote_volume -> float32 (parse double roi ep float32 nhu Java (float) Double.parseDouble)
    v = np.array([[float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[7])] for r in rows], np.float64).astype(np.float32)
    return ts, v
def kl(sym, m):
    b = http(KURL.format(s=urllib.parse.quote(sym), m=m))
    return sym, (None if b is None else _parse(b))
def kld(sym, d):
    b = http(DURL.format(s=urllib.parse.quote(sym), d=d))
    return sym, (None if b is None else _parse(b))
t0 = time.time()
DEVTK = CFG.get("dev_ticker_ds") or []
ksyms = [s for s in list_syms("data/futures/um/monthly/klines/") if in_uni(s)]
LOG.info("Vision klines listing: %d symbol trong universe (mapper %d)", len(ksyms), len(MAPPER))
day_stats, uni_month, PARTS = {}, {}, {}
jobs = [("m", m) for m in CFG["months"]] + [("d", d) for d in CFG.get("days", [])]
for kind, per in jobs:
    with ThreadPoolExecutor(CFG.get("dl_threads", 24)) as ex:
        got = list(ex.map((lambda s: kl(s, per)) if kind == "m" else (lambda s: kld(s, per)), ksyms))
    n = 0
    for s, r in got:
        if r is not None:
            PARTS.setdefault(s, []).append(r); n += 1
    uni_month[per] = sorted(s for s, r in got if r is not None)
    LOG.info("%s %s: %d symbol co du lieu (%.0fs)", kind, per, n, time.time() - t0)
KL = {}
for s in sorted(PARTS):
    ts = np.concatenate([p[0] for p in PARTS[s]]); v = np.concatenate([p[1] for p in PARTS[s]])
    o = np.argsort(ts, kind="stable"); ts, v = ts[o], v[o]
    keep = np.r_[True, np.diff(ts) > 0]                     # trung ts (monthly/daily) -> giu ban dau
    KL[s] = (ts[keep], v[keep])
del PARTS
# duoi settle/delist: chuoi quote_volume == 0 keo toi kline cuoi cua symbol, dai >= 1440 phut -> bo tu phut dau chuoi
TAIL = {}
for s in sorted(KL):
    ts, v = KL[s]
    nz = np.nonzero(v[:, 4] > 0)[0]
    cut = int(nz[-1]) + 1 if len(nz) else 0
    if len(ts) - cut >= CFG.get("tail_min", 1440):
        TAIL[s] = dict(from_ts=int(ts[cut]), n_rows=int(len(ts) - cut), last_trade_ts=int(ts[cut - 1]) if cut else None)
        if cut == 0:
            del KL[s]; continue
        KL[s] = (ts[:cut], v[:cut])
RES["steps"]["settle_tail"] = TAIL
LOG.info("duoi settle bo: %d symbol", len(TAIL))
'''
i0 = s.index("def kl(sym, m):")
i1 = s.index("    del D\n") + len("    del D\n")
old = s[i0:i1]
assert old.count("for m in ([] if DEVTK else CFG[\"months\"]):") == 1 and old.count("JWR.encode_day(mins)") == 1
NEWK += r'''def gz_det(path, raw):
    with open(path, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, compresslevel=6, mtime=0) as g:
        g.write(raw)
d = datetime.datetime.strptime(CFG["ingest"][0], "%Y%m%d").replace(tzinfo=UTC)
dEnd = datetime.datetime.strptime(CFG["ingest"][1], "%Y%m%d").replace(tzinfo=UTC)
TK_RAW_MD5 = {}
while d <= dEnd:
    lo = int(d.timestamp() * 1000); hi = lo + 86400000
    per = {}
    for s in sorted(KL):
        ts, v = KL[s]
        a, b = np.searchsorted(ts, lo), np.searchsorted(ts, hi)
        for i in range(a, b):
            per.setdefault(int(ts[i]), []).append((s, float(v[i, 0]), float(v[i, 1]), float(v[i, 2]), float(v[i, 3]), float(v[i, 4])))
    mins = [(t, per[t]) for t in sorted(per)]
    nm = "ticker_%s.bin" % d.strftime("%Y%m%d")
    if mins:
        raw = JWR.encode_day(mins)
        TK_RAW_MD5[nm] = hashlib.md5(raw).hexdigest()
        gz_det(OUTD + "/ticker/" + nm + ".gz", raw)
    day_stats[d.strftime("%Y%m%d")] = dict(n_min=len(mins), n_cells=sum(len(x[1]) for x in mins), n_sym=len({e[0] for x in mins for e in x[1]}))
    d += datetime.timedelta(days=1)
json.dump(TK_RAW_MD5, open(OUTD + "/ticker_raw_md5.json", "w"), indent=0, sort_keys=True)
# CLOSES_1H tu 1m Vision (quyet dinh MASTER #2): ts = gio dong (open+1h), close = close phut co mat MUON NHAT trong gio,
# symId theo symbol_map 863; sap (ts, ten symbol) nhu closes1h_build.py; BE [ts i64][sym i16][c f32].
CMAP = CFG["closes_map"]
crec = []
for s in sorted(KL):
    if s not in CMAP:
        continue
    ts, v = KL[s]
    hr = (ts // 3600000 + 1) * 3600000
    last = np.r_[np.nonzero(np.diff(hr))[0], len(hr) - 1]
    for i in last:
        crec.append((int(hr[i]), s, v[i, 3]))
crec.sort(key=lambda r: (r[0], r[1]))
CDT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
ca = np.zeros(len(crec), CDT)
ca["ts"] = [r[0] for r in crec]; ca["sym"] = [CMAP[r[1]] for r in crec]; ca["c"] = [r[2] for r in crec]
ca.tofile(OUTD + "/CLOSES_1H_vision1m.bin")
RES["steps"]["closes1h"] = dict(n=int(len(ca)), n_sym=len({r[1] for r in crec}))
# lifecycle (luat SymbolLifecycleBuilderLocal tren kline cua so sau loc): first = min(first ban sao local, first cua so),
# last = phut co mat muon nhat; LIVE neu (maxTicker - last) <= 3 ngay, nguoc lai DEAD + delist = last.
MAXT = max(int(KL[s][0][-1]) for s in KL)
LC_NEW = {}
for s in sorted(KL):
    LC_NEW[s] = [int(KL[s][0][0]), int(KL[s][0][-1])]
TKDIR = OUTD + "/ticker/"
'''
s = s[:i0] + NEWK + s[i1:]
# bo khoi DEVTK (chan doan D1 cu) — HO4-P1 luon Vision
j0 = s.index("TKDIR = OUTD + \"/ticker/\"\nif DEVTK:")
j1 = s.index('RES["steps"]["klines"] = dict(')
s = s[:j0] + s[j1:]
R.append(('''pickle.dump({"funding_data": fund_rows}, open(OUTD + "/funding_vision.pkl", "wb"), protocol=4)''',
          '''pickle.dump({"funding_data": fund_rows}, open(OUTD + "/funding_vision.pkl", "wb"), protocol=4)
NOF = sorted(s for s in KL if s not in V and bool(((KL[s][0] >= S_LO) & (KL[s][0] < S_HI)).any()))
RES["steps"]["no_funding_vision"] = NOF
json.dump(dict(no_funding_vision=NOF, settle_tail=TAIL, n_universe=len(KL)), open(OUTD + "/universe_excl.json", "w"), indent=1, sort_keys=True)
LOG.info("symbol co kline trong S nhung khong co funding Vision: %d %s", len(NOF), NOF[:20])'''))
R.append(('''    for k, bins in rows:
        CL.put(("test", st, k), bins, policy=WP)
    NLOAD[st] = len(rows)''',
          '''    if st == "symbol_lifecycle":                # HO4-P1: lifecycle tu kline cua so (luat SymbolLifecycleBuilderLocal)
        _loc = {k: dict(b) for k, b in rows}
        _rows = []
        for k in sorted(set(_loc) | set(LC_NEW)):
            b = dict(_loc.get(k) or {"sym": k})
            if k in LC_NEW:
                f0, l0 = LC_NEW[k]
                b["first"] = int(min(f0, b["first"])) if b.get("first") else int(f0)
                b["last"] = int(l0)
                b["status"], b["delist"] = ("LIVE", 0) if MAXT - l0 <= 3 * 86400000 else ("DEAD", int(l0))
            _rows.append((k, b))
        rows = _rows
        RES["steps"]["lifecycle"] = dict(n=len(rows), n_window=len(LC_NEW), max_ticker=MAXT,
                                         n_dead_window=sum(1 for k in LC_NEW if MAXT - LC_NEW[k][1] > 3 * 86400000))
        pickle.dump({"symbol_lifecycle": rows}, open(OUTD + "/lifecycle.pkl", "wb"), protocol=4)
    for k, bins in rows:
        CL.put(("test", st, k), bins, policy=WP)
    NLOAD[st] = len(rows)'''))
R.append(('''tk = sorted(glob.glob(OUTD + "/ticker/*.bin.gz"))
json.dump({os.path.basename(p): md5f(p) for p in tk}, open(OUTD + "/ticker_md5.json", "w"), indent=0)''',
          '''# MANIFEST (ADDENDUM-6 P3-DET): md5 MOI file du lieu trong out/, tru *.meta.json (chua thoi gian chay)
MAN = {}
for p in sorted(glob.glob(OUTD + "/**/*", recursive=True)):
    if os.path.isfile(p) and not p.endswith(".meta.json") and not p.endswith("MANIFEST.json"):
        MAN[os.path.relpath(p, OUTD)] = dict(md5=md5f(p), bytes=os.path.getsize(p))
json.dump(MAN, open(OUTD + "/MANIFEST.json", "w"), indent=0, sort_keys=True)
RES["manifest_n"] = len(MAN)'''))
for a, b in R:
    assert s.count(a) == 1, a[:80]
    s = s.replace(a, b)
assert "JWR.encode_day(mins)" in s and "DEVTK:" not in s.split("def api()")[0].replace("DEVTK = CFG", "")
compile(s, "ho4p1_exp_kernel", "exec")
open(A + "ho4p1_exp_kernel.py", "w").write(s)
log.info("MK_OK %d thay the + khoi kline", len(R))
