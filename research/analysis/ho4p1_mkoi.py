#!/usr/bin/env python3
"""HO4-P1: sinh ho4p1_oi_kernel.py tu ho4_oi_kernel.py (ADDENDUM-6): ghi OI ts in [2025-06-01, 2026-10-04) UTC (lat DEV P3-DET
+ 2026), LAST_DATE 2026-10-03, gz mtime=0 + md5 raw (P3-DET). Usage: python3 ho4p1_mkoi.py"""
import logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/"
s = open(A + "ho4_oi_kernel.py").read()
R = [('"""HO4-P3 (ADDENDUM-5 §5.3 cong O, 31e3c9e7): kernel Kaggle `ho4-dev-oi`',
      '"""HO4-P1 (ADDENDUM-6; sinh boi ho4p1_mkoi.py, cua so ghi [2025-06-01, 2026-10-04) UTC). Goc HO4-P3: kernel `ho4-dev-oi`'),
     ('WD = "/home/ubuntu/claude_master/1010/ho4/kaggle"', 'WD = "/home/ubuntu/claude_master/1011/ho4p1/kaggle"'),
     ("""'EMIT_HI = int(pd.Timestamp("2026-01-01", tz="UTC").value // 10**6)'""",
      """'EMIT_HI = int(pd.Timestamp("2026-10-04", tz="UTC").value // 10**6)'"""),
     ("""'LAST_DATE = "2025-12-31"'""", """'LAST_DATE = "2026-10-03"'"""),
     ('''with gzip.open(WORK + "/out/oi_rebuilt.bin.gz", "wb", 6) as fo:
    fo.write(RB.astype(ODT).tobytes())''',
      '''_raw = RB.astype(ODT).tobytes()
with open(WORK + "/out/oi_rebuilt.bin.gz", "wb") as _f, gzip.GzipFile(filename="", mode="wb", fileobj=_f, compresslevel=6, mtime=0) as fo:
    fo.write(_raw)
RES["md5_raw"] = hashlib.md5(_raw).hexdigest()
h5 = hashlib.md5()
with open(WORK + "/out/oi_rebuilt.bin.gz", "rb") as _f:
    for _b in iter(lambda: _f.read(1 << 22), b""):
        h5.update(_b)
RES["md5_gz"] = h5.hexdigest()
del _raw'''),
     ('RES = dict(prereg="ADDENDUM-5 31e3c9e7", emit=[EMIT_LO, EMIT_HI], last_date=LAST_DATE)',
      'RES = dict(prereg="ADDENDUM-6", emit=[EMIT_LO, EMIT_HI], last_date=LAST_DATE)')]
for a, b in R:
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)
compile(s, "x", "exec")
open(A + "ho4p1_oi_kernel.py", "w").write(s)
logging.info("MKOI_OK")
