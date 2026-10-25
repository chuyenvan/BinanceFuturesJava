#!/usr/bin/env python3
# [A1] doc lap: dem record khong huu han trong gate_ratio_live.bin (chunk GRR1 | LEN | CRC32 | snappy(raw)), raw = (>q ts, >f r)*
import gzip, glob, math, os, struct, zlib
import snappy
MAGIC = 0x47525231
for p in sorted(glob.glob(os.path.expanduser("~/claude_master/pull242/*/run/gate_ratio_live.bin.gz"))):
    b = gzip.open(p, "rb").read()
    off = n = bad = nan = pinf = ninf = 0
    tsmax = 0
    tsmin = None
    while off + 12 <= len(b):
        m, ln, crc = struct.unpack(">iii", b[off:off + 12])
        if m != MAGIC:
            j = b.find(struct.pack(">i", MAGIC), off + 1)
            bad += 1
            if j < 0:
                break
            off = j
            continue
        comp = b[off + 12: off + 12 + ln]
        if len(comp) != ln or (zlib.crc32(comp) & 0xffffffff) != (crc & 0xffffffff):
            bad += 1
            j = b.find(struct.pack(">i", MAGIC), off + 1)
            if j < 0:
                break
            off = j
            continue
        raw = snappy.decompress(comp)
        assert len(raw) % 12 == 0
        for i in range(0, len(raw), 12):
            ts, r = struct.unpack(">qf", raw[i:i + 12])
            n += 1
            if math.isnan(r): nan += 1
            elif r == math.inf: pinf += 1
            elif r == -math.inf: ninf += 1
            tsmax = max(tsmax, ts)
            tsmin = ts if tsmin is None else min(tsmin, ts)
        off += 12 + ln
    print(p.split("pull242/")[1], "n=", n, "nan=", nan, "+inf=", pinf, "-inf=", ninf, "bad_chunks=", bad, "ts=", tsmin, tsmax)
