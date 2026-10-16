import struct, zlib, datetime as dt
import numpy as np, snappy
PCT = 0.99995083
def load(p):
    b = open(p, "rb").read(); i = 0; ts = []; r = []; bad = 0
    while i + 12 <= len(b):
        mg, ln, crc = struct.unpack(">iiI", b[i:i+12])
        if mg != 0x47525231 or ln < 0 or i + 12 + ln > len(b): bad += 1; i += 1; continue
        c = b[i+12:i+12+ln]
        if zlib.crc32(c) & 0xffffffff != crc: bad += 1; i += 1; continue
        a = np.frombuffer(snappy.uncompress(c), dtype=np.dtype([("t", ">i8"), ("r", ">f4")]))
        ts.append(a["t"].astype(np.int64)); r.append(a["r"].astype(np.float64)); i += 12 + ln
    return np.concatenate(ts), np.concatenate(r), bad
def q_of(r):
    m = len(r); k = min(m-1, int(np.floor(PCT*(m-1)))); return float(np.sort(r)[k])
def ms(s):  # "MM-DD HH:MM" gio +07
    return int(dt.datetime.strptime("2026-" + s + " +0700", "%Y-%m-%d %H:%M %z").timestamp()*1000)
def f(t): return dt.datetime.utcfromtimestamp(t/1000 + 7*3600).strftime("%m-%d %H:%M")
