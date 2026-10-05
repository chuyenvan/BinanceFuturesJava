#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loc buffer gate rolling GRR1 (run/gate_ratio_live.bin cua LiveGateRollingRatio) — bo ban ghi ts < cutoff.

Dinh dang (doc tu GateRatioPersist.java): file = noi tiep cac chunk, KHONG header file.
  chunk = MAGIC(int BE 0x47525231 "GRR1") | LEN(int BE, so byte nen) | CRC32(int BE, CRC32 cua BYTES NEN)
          | Snappy.compress(RAW)  (xerial Snappy block/raw, KHONG framing)
  RAW   = record 12B: ts (long BE) | r (float BE, floatToIntBits)
Java load (GateRatioPersist.load): magic sai/CRC lech => IOException => LiveGateRollingRatio coi persist RONG
  => seedHistory + writeFresh (GHI DE file). Chunk cuoi thieu byte / <12B header thua => bo qua IM LANG.
  KHONG sort; bulkAdd gia dinh ts tang (computeQ cat dau theo head).
Phan vi (GateRatioBuffer.computeQ): cua so [h - days*DAY, ...), k = min(m-1, max(0, floor((double)pct_f32*(m-1)))),
  q = phan tu nho thu k (0-based) cua r float32; warm-up: (h - firstTs) < 7 ngay => fallback base (0.008).
Script nay: doc STRICT (bao moi chunk hong, tu choi neu co), bo ts < cutoff, ghi lai cung format
  (giu ranh gioi chunk goc, moi chunk <= --max-chunk ban ghi, giu thu tu), tu kiem lai file ra,
  ghi <out>.sha256 + report json (n, ts min/max, q truoc/sau, arm, du kien seedHistory).
Chay tren Oracle (can python-snappy, numpy); KHONG cai gi len 242.
Usage:
  python3 trim_gate_buffer.py --in IN.bin --out OUT.bin --cutoff "2026-10-01 13:00" --tz +07:00 [--dry-run]
          [--restart-at "2026-10-07 10:00"] [--allow-truncated-tail] [--report R.json]
  python3 trim_gate_buffer.py --in IN.bin --out OUT.bin --no-cut      (round-trip, test)
Exit: 0 OK | 2 file hong / kiem lai FAIL | 3 tu choi (out ton tai / out==in) | 4 thieu python-snappy
"""
import argparse
import datetime as dt
import hashlib
import json
import logging
import math
import os
import struct
import sys
import zlib

import numpy as np

LOG = logging.getLogger("trim_gate_buffer")
MAGIC = 0x47525231
HDR = 12
REC = np.dtype([("ts", ">i8"), ("r", ">f4")])
HOUR, DAY = 3_600_000, 86_400_000
WARMUP = 7 * DAY
FALLBACK_BASE = 0.008   # Configs.MIN_MOMENTUM_15M (env 242 SIM_MIN_MOMENTUM_15M=0.008)
TOLERATED = ("trailing_header", "truncated_tail")   # Java bo qua im lang 2 loai nay


def _snappy():
    try:
        import snappy  # python-snappy
    except ImportError:
        LOG.error("thieu python-snappy — chay script tren Oracle (KHONG cai len 242)")
        sys.exit(4)
    return snappy


def parse_tz(s):
    sign = -1 if s.startswith("-") else 1
    hh, mm = s.lstrip("+-").split(":")
    return dt.timezone(sign * dt.timedelta(hours=int(hh), minutes=int(mm)))


def parse_time(s, tz):
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return int(dt.datetime.strptime(s, f).replace(tzinfo=tz).timestamp() * 1000)
        except ValueError:
            pass
    raise ValueError("thoi gian sai dinh dang: %r" % s)


def fmt(t, tz):
    return dt.datetime.fromtimestamp(t / 1000, tz).strftime("%Y-%m-%d %H:%M:%S%z") if t is not None else None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_chunks(path):
    """Doc STRICT, mirror GateRatioPersist.load. Tra (chunks, anomalies); dung o anomaly dau tien."""
    snappy = _snappy()
    raw = open(path, "rb").read()
    off, chunks, anomalies = 0, [], []
    while off < len(raw):
        if off + HDR > len(raw):
            anomalies.append({"kind": "trailing_header", "offset": off, "bytes": len(raw) - off})
            break
        magic, ln, crc = struct.unpack(">iiI", raw[off:off + HDR])
        if magic != MAGIC:
            anomalies.append({"kind": "bad_magic", "offset": off, "chunk": len(chunks)})
            break
        if ln < 0 or off + HDR + ln > len(raw):
            anomalies.append({"kind": "truncated_tail", "offset": off, "len": ln, "have": len(raw) - off - HDR})
            break
        comp = raw[off + HDR:off + HDR + ln]
        if (zlib.crc32(comp) & 0xffffffff) != crc:
            anomalies.append({"kind": "bad_crc", "offset": off, "chunk": len(chunks)})
            break
        u = snappy.uncompress(comp)
        if len(u) % REC.itemsize:
            anomalies.append({"kind": "partial_record", "offset": off, "chunk": len(chunks), "bytes": len(u)})
        a = np.frombuffer(u[:len(u) // REC.itemsize * REC.itemsize], dtype=REC)
        chunks.append({"offset": off, "len": ln, "ts": a["ts"].astype(np.int64), "r": a["r"].astype(np.float32)})
        off += HDR + ln
    return chunks, anomalies, len(raw)


def encode_chunk(ts, r):
    snappy = _snappy()
    a = np.empty(len(ts), dtype=REC)
    a["ts"], a["r"] = ts, r
    comp = snappy.compress(a.tobytes())
    return struct.pack(">iiI", MAGIC, len(comp), zlib.crc32(comp) & 0xffffffff) + comp


def q_java(ts, r, h, pct_f32, days):
    """GateRatioBuffer.computeQ tai moc gio h (buffer nap toan bo ts < h, cat ts < h - days)."""
    sel = r[(ts >= h - days * DAY) & (ts < h)]
    m = len(sel)
    if m == 0:
        return None, 0, None
    k = min(m - 1, max(0, int(math.floor(float(pct_f32) * (m - 1)))))
    return float(np.partition(sel, k)[k]), m, k


def summarize(ts, r, pct_f32, days, tz, restart_ms=None):
    if len(ts) == 0:
        return {"n": 0}
    first, last = int(ts[0]), int(ts[-1])
    h_ref = (last // HOUR + 1) * HOUR                    # gio dau tien sau ban ghi cuoi (restart ngay sau)
    h_arm = -(-(first + WARMUP) // HOUR) * HOUR          # gio dau tien (h - firstTs) >= 7d
    h_eval = max(h_ref, h_arm)
    q_ref, m_ref, _ = q_java(ts, r, h_ref, pct_f32, days)
    q_eval, m_eval, k_eval = q_java(ts, r, h_eval, pct_f32, days)
    out = {"n": int(len(ts)), "ticks": int(len(np.unique(ts))), "ts_min": fmt(int(ts.min()), tz),
           "ts_max": fmt(int(ts.max()), tz), "first_ts": fmt(first, tz), "last_ts": fmt(last, tz),
           "first_ts_ms": first, "last_ts_ms": last, "days_span": round((last - first) / DAY, 3),
           "unsorted_pairs": int(np.sum(np.diff(ts) < 0)), "n_nan": int(np.isnan(r).sum()),
           "r_max": float(np.nanmax(r)), "r_p50": float(np.nanmedian(r)),
           "h_ref": fmt(h_ref, tz), "armed_at_h_ref": bool(h_ref - first >= WARMUP),
           "q_live_at_h_ref": (q_ref if h_ref - first >= WARMUP else FALLBACK_BASE),
           "arm_hour": fmt(h_arm, tz), "h_eval": fmt(h_eval, tz), "h_eval_ms": h_eval,
           "q_at_h_eval": q_eval, "q_at_h_eval_f32_bits": int(np.float32(q_eval).view(np.int32)) if q_eval is not None else None,
           "m_at_h_eval": m_eval, "k_at_h_eval": k_eval, "warmup_7d_ok_by_last_ts": bool(last - first >= WARMUP)}
    if restart_ms is not None:
        min_ts = restart_ms - days * DAY
        kept = ts[ts >= min_ts]
        pstart = int(kept[0]) if len(kept) else restart_ms
        out["restart_at"] = fmt(restart_ms, tz)
        out["restart_persisted_start"] = fmt(pstart, tz)
        # LiveGateRollingRatio.loadPersistedAndSeed: persistedStart > now - 7d => seedHistory [now-90d, persistedStart) + writeFresh
        out["restart_seed_history_called"] = bool(pstart > restart_ms - WARMUP)
        out["restart_armed_if_seed_empty"] = bool((restart_ms // HOUR) * HOUR - pstart >= WARMUP)
    return out



def main():
    ap = argparse.ArgumentParser(description="Loc buffer GRR1 (gate_ratio_live.bin) bo ts < cutoff")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cutoff", help='vd "2026-10-01 13:00" (giu ts >= cutoff)')
    ap.add_argument("--tz", default="+07:00")
    ap.add_argument("--no-cut", action="store_true", help="round-trip: ghi lai KHONG cat (test)")
    ap.add_argument("--dry-run", action="store_true", help="khong ghi --out/.sha256 (van ghi --report neu co)")
    ap.add_argument("--allow-truncated-tail", action="store_true",
                    help="chap nhan chunk cuoi ghi do (Java cung bo qua) — chi cho ban scp luc app dang chay")
    ap.add_argument("--restart-at", help='gio du kien start lai app (tz --tz) => du doan seedHistory/arm')
    ap.add_argument("--pct", default="0.999950829", help="LIVE_GATE_ROLLING_PCT (parse float32 nhu Java)")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--max-chunk", type=int, default=4096, help="so ban ghi toi da / chunk (FLUSH_BATCH)")
    ap.add_argument("--report", help="report json (mac dinh <out>.report.json khi khong dry-run)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    tz = parse_tz(a.tz)
    pct_f32 = np.float32(a.pct)
    if a.no_cut == bool(a.cutoff):
        LOG.error("can dung MOT trong --cutoff / --no-cut")
        return 3
    if os.path.realpath(a.inp) == os.path.realpath(a.out):
        LOG.error("tu choi: --out trung --in (%s)", a.inp)
        return 3
    if os.path.exists(a.out) or os.path.exists(a.out + ".sha256"):
        LOG.error("tu choi: --out da ton tai (%s) — khong ghi de", a.out)
        return 3
    cutoff = None if a.no_cut else parse_time(a.cutoff, tz)
    restart_ms = parse_time(a.restart_at, tz) if a.restart_at else None

    chunks, anomalies, nbytes = read_chunks(a.inp)
    for x in anomalies:
        LOG.error("chunk hong: %s", x)
    bad = [x for x in anomalies if x["kind"] not in TOLERATED or not a.allow_truncated_tail]
    if bad:
        LOG.error("tu choi: %d chunk hong (Java: bad_magic/bad_crc => load FAIL => seed + GHI DE file; "
                  "truncated_tail => bo qua). Dung --allow-truncated-tail neu chi la duoi ghi do.", len(bad))
        return 2
    ts_in = np.concatenate([c["ts"] for c in chunks]) if chunks else np.zeros(0, np.int64)
    r_in = np.concatenate([c["r"] for c in chunks]) if chunks else np.zeros(0, np.float32)
    sizes = [len(c["ts"]) for c in chunks]
    LOG.info("in %s: %d byte, %d chunk (ban ghi/chunk min %s max %s), %d ban ghi", a.inp, nbytes, len(chunks),
             min(sizes) if sizes else "-", max(sizes) if sizes else "-", len(ts_in))

    # cat + chia chunk (giu ranh gioi chunk goc, giu thu tu)
    blobs, ts_parts, r_parts = [], [], []
    for c in chunks:
        keep = np.ones(len(c["ts"]), bool) if cutoff is None else (c["ts"] >= cutoff)
        ts_k, r_k = c["ts"][keep], c["r"][keep]
        for i in range(0, len(ts_k), a.max_chunk):
            blobs.append(encode_chunk(ts_k[i:i + a.max_chunk], r_k[i:i + a.max_chunk]))
        ts_parts.append(ts_k)
        r_parts.append(r_k)
    ts_out = np.concatenate(ts_parts) if ts_parts else np.zeros(0, np.int64)
    r_out = np.concatenate(r_parts) if r_parts else np.zeros(0, np.float32)

    rep = {"tool": "research/parity/trim_gate_buffer.py", "in": os.path.abspath(a.inp), "in_bytes": nbytes,
           "in_sha256": sha256(a.inp), "in_chunks": len(chunks), "in_chunk_sizes_min_max": [min(sizes), max(sizes)] if sizes else None,
           "anomalies": anomalies, "cutoff": fmt(cutoff, tz), "cutoff_ms": cutoff, "pct_f32": float(pct_f32), "days": a.days,
           "dropped": int(len(ts_in) - len(ts_out)), "out_chunks": len(blobs),
           "before": summarize(ts_in, r_in, pct_f32, a.days, tz, restart_ms),
           "after": summarize(ts_out, r_out, pct_f32, a.days, tz, restart_ms), "dry_run": a.dry_run}
    if cutoff is not None and len(ts_out) and int(ts_out.min()) < cutoff:
        LOG.error("BUG: con ban ghi ts < cutoff")
        return 2
    for side in ("before", "after"):
        s = rep[side]
        if s.get("n"):
            LOG.info("%s: n=%d %s..%s (%.2f ngay) unsorted=%d nan=%d | arm %s | q(h_eval %s)=%.7f m=%d | q live tai %s = %s",
                     side, s["n"], s["first_ts"], s["last_ts"], s["days_span"], s["unsorted_pairs"], s["n_nan"],
                     s["arm_hour"], s["h_eval"], s["q_at_h_eval"], s["m_at_h_eval"], s["h_ref"], s["q_live_at_h_ref"])
            if "restart_at" in s:
                lvl = logging.WARNING if s["restart_seed_history_called"] else logging.INFO
                LOG.log(lvl, "%s: restart %s => persistedStart %s => seedHistory %s; arm ngay neu seed rong: %s",
                        side, s["restart_at"], s["restart_persisted_start"],
                        "CO (seed [now-90d, persistedStart) roi writeFresh GHI LAI file)" if s["restart_seed_history_called"] else "khong",
                        s["restart_armed_if_seed_empty"])

    if not a.dry_run:
        with open(a.out, "xb") as f:
            for b in blobs:
                f.write(b)
        chk, anom2, nb2 = read_chunks(a.out)
        ts_chk = np.concatenate([c["ts"] for c in chk]) if chk else np.zeros(0, np.int64)
        r_chk = np.concatenate([c["r"] for c in chk]) if chk else np.zeros(0, np.float32)
        same = (not anom2 and np.array_equal(ts_chk, ts_out)
                and np.array_equal(r_chk.view(np.int32), r_out.view(np.int32)))
        rep.update({"out": os.path.abspath(a.out), "out_bytes": nb2, "out_sha256": sha256(a.out),
                    "out_verify_records_bit_identical": bool(same),
                    "out_chunk_sizes_min_max": [min(len(c["ts"]) for c in chk), max(len(c["ts"]) for c in chk)] if chk else None,
                    "out_byte_identical_to_in": bool(nb2 == nbytes and rep["in_sha256"] == sha256(a.out))})
        with open(a.out + ".sha256", "x") as f:
            f.write("%s  %s\n" % (rep["out_sha256"], os.path.basename(a.out)))
        LOG.info("out %s: %d byte, %d chunk, sha256 %s, kiem lai ban ghi %s, byte-identical voi in: %s", a.out, nb2,
                 len(chk), rep["out_sha256"], "OK" if same else "FAIL", rep["out_byte_identical_to_in"])
        if not same:
            return 2
    rpath = a.report or (None if a.dry_run else a.out + ".report.json")
    if rpath:
        with open(rpath, "w") as f:
            json.dump(rep, f, indent=1, ensure_ascii=False)
        LOG.info("report %s", rpath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
