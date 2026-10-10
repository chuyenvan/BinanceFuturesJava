#!/usr/bin/env python3
"""HO3b: ghi ticker_YYYYMMDD.bin dung byte ObjectOutputStream Java cua ExportTickerDaily:
TreeMap<Long, HashMap<String, KlineObjectSimple>> voi HashMap tao bang new HashMap<>(n) (convertProtoMapToJavaMap),
chen theo thu tu wire cua record (protobuf LinkedHashMap), Long moi cho moi key/startTime, String moi moi phut.
Thu tu entry khi serialize = thu tu bucket HashMap (hash Java String ^ >>>16), trong bucket = thu tu chen.
encode_day(minutes): minutes = [(ts, [(sym, o, h, l, c, v), ...] theo thu tu chen)], ts tang dan."""
import struct

MAGIC = b"\xac\xed\x00\x05"
D_TREEMAP = (b"\x72\x00\x11java.util.TreeMap\x0c\xc1\xf6\x3e\x2d\x25\x6a\xe6\x03\x00\x01\x4c\x00\x0acomparator"
             b"\x74\x00\x16Ljava/util/Comparator;\x78\x70")
D_LONG = (b"\x72\x00\x0ejava.lang.Long\x3b\x8b\xe4\x90\xcc\x8f\x23\xdf\x02\x00\x01\x4a\x00\x05value\x78"
          b"\x72\x00\x10java.lang.Number\x86\xac\x95\x1d\x0b\x94\xe0\x8b\x02\x00\x00\x78\x70")
D_HASHMAP = (b"\x72\x00\x11java.util.HashMap\x05\x07\xda\xc1\xc3\x16\x60\xd1\x03\x00\x02\x46\x00\x0aloadFactor"
             b"\x49\x00\x09threshold\x78\x70")
D_KLINE = (b"\x72\x00\x30com.binance.chuyennd.object.sw.KlineObjectSimple\x48\xf0\x3c\x56\x07\x7d\xe7\x1c\x02\x00\x06"
           b"\x46\x00\x08maxPrice\x46\x00\x08minPrice\x46\x00\x0apriceClose\x46\x00\x09priceOpen\x46\x00\x09totalUsdt"
           b"\x4c\x00\x09startTime\x74\x00\x10Ljava/lang/Long;\x78\x70")
assert len("com.binance.chuyennd.object.sw.KlineObjectSimple") == 0x30
BASE = 0x7E0000


def jhash(s):
    h = 0
    u = s.encode("utf-16-be")
    for i in range(0, len(u), 2):
        h = (31 * h + ((u[i] << 8) | u[i + 1])) & 0xFFFFFFFF
    return h


def table_size_for(c):
    n = 1
    while n < c:
        n <<= 1
    return max(n, 1)


def hm_cap(n):
    cap = table_size_for(n)
    while n > int(cap * 0.75):
        cap <<= 1
    return cap


def encode_day(minutes):
    out = [MAGIC, b"\x73", D_TREEMAP]
    h = 3                                   # 0 TreeMap desc, 1 "Ljava/util/Comparator;", 2 TreeMap obj
    out.append(b"\x70")                     # comparator = null
    out.append(b"\x77\x04" + struct.pack(">i", len(minutes)))
    ref = {}
    pk_long = struct.Struct(">q").pack
    pk_kl = struct.Struct(">fffff").pack
    maxbin = 0

    def wlong(v):
        nonlocal h
        if "L" not in ref:
            out.append(b"\x73" + D_LONG)
            ref["L"] = h                    # Long desc; h+1 = Number desc
            h += 2
        else:
            out.append(b"\x73\x71" + struct.pack(">I", BASE + ref["L"]))
        h += 1                              # Long obj
        out.append(pk_long(v))

    prev = None
    for ts, ent in minutes:
        assert prev is None or ts > prev
        prev = ts
        wlong(ts)
        d = {}
        for e in ent:                       # LinkedHashMap: vi tri lan dau, gia tri lan cuoi
            d[e[0]] = e
        n = len(d)
        cap = hm_cap(n)
        bk = {}
        for sym in d:
            hv = jhash(sym)
            bk.setdefault((hv ^ (hv >> 16)) & (cap - 1), []).append(sym)
        if bk:
            maxbin = max(maxbin, max(len(v) for v in bk.values()))
        if "H" not in ref:
            out.append(b"\x73" + D_HASHMAP)
            ref["H"] = h
            h += 1
        else:
            out.append(b"\x73\x71" + struct.pack(">I", BASE + ref["H"]))
        h += 1                              # HashMap obj
        out.append(struct.pack(">fi", 0.75, int(cap * 0.75)))
        out.append(b"\x77\x08" + struct.pack(">ii", cap, n))
        for b in sorted(bk):
            for sym in bk[b]:
                e = d[sym]
                s, o, hi, lo, c, v = e[:6]
                st = e[6] if len(e) > 6 else ts
                sb = s.encode("utf-8")
                out.append(b"\x74" + struct.pack(">H", len(sb)) + sb)
                h += 1
                if "K" not in ref:
                    out.append(b"\x73" + D_KLINE)
                    ref["K"] = h            # Kline desc; h+1 = "Ljava/lang/Long;"
                    h += 2
                else:
                    out.append(b"\x73\x71" + struct.pack(">I", BASE + ref["K"]))
                h += 1                      # Kline obj
                out.append(pk_kl(hi, lo, c, o, v))
                wlong(st)
        out.append(b"\x78")
    out.append(b"\x78")
    assert maxbin < 8, ("bucket >= 8 => treeify, khong ho tro", maxbin)
    return b"".join(out)
