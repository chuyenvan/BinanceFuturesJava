"""MASTER 10-12: ban sao GRR1 bo chunk hong (CRC/len sai), resync toi magic 'GRR1' ke tiep. Chi doc file goc."""
import logging
import struct
import sys
import zlib

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("grrfix")
src, dst = sys.argv[1], sys.argv[2]
raw = open(src, "rb").read()
out, off, drop, keep = bytearray(), 0, 0, 0
while off + 12 <= len(raw):
    magic, ln, crc = struct.unpack(">iiI", raw[off:off + 12])
    ok = magic == 0x47525231 and 0 <= ln <= len(raw) - off - 12
    if ok:
        comp = raw[off + 12:off + 12 + ln]
        ok = (zlib.crc32(comp) & 0xffffffff) == crc
    if ok:
        out += raw[off:off + 12 + ln]
        keep += 1
        off += 12 + ln
        continue
    drop += 1
    nxt = raw.find(b"GRR1", off + 1)
    if nxt < 0:
        break
    off = nxt
open(dst, "wb").write(bytes(out))
LOG.info("src=%d dst=%d keep=%d dropped=%d", len(raw), len(out), keep, drop)
