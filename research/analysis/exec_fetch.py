#!/usr/bin/env python3
"""exec_fetch.py -- EXEC E1: tai aggTrades daily + kline 1m monthly tu data.binance.vision (KHONG REST) CHI cho (sym, ngay/thang)
co chan DEV (legs.pkl tu exec_legs.py), kiem sha256 voi .CHECKSUM, cat cua so quanh chan, XOA zip goc ngay.
Pre-reg: docs/prereg/PREREG_EXEC.md (c60048d9). Output: ~/claude_master/1012/exec/{agg,kl}/*.npz + fetch_status.json
Usage: exec_fetch.py kl|agg [workers]
"""
import hashlib
import io
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("exec_fetch")
W = "/home/ubuntu/claude_master/1012/exec"
TMP = W + "/tmp"
BASE = "https://data.binance.vision/data/futures/um"
H, D, MN = 3600000, 86400000, 60000
T26 = 1767200400000
DEC_OFF, WIN_PRE, WIN_POST = 66000, 2 * MN, 30 * MN
PATH_H = 169 * H + 31 * MN
CHUNK = 2_000_000


def get(url, dst=None, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                if dst is None:
                    return r.read()
                with open(dst, "wb") as f:
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            break
                        f.write(b)
                return dst
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            log.warning("HTTP %s %s (lan %d)", e.code, url, k + 1)
        except Exception as e:  # noqa: BLE001 - mang chap chon, thu lai
            log.warning("loi %s %s (lan %d)", type(e).__name__, url, k + 1)
        time.sleep(5 * (k + 1))
    raise RuntimeError("tai that bai: " + url)


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch_zip(url, tag):
    """tai zip + .CHECKSUM -> (duong dan, sha_ok) hoac (None, None) neu 404."""
    dst = TMP + "/" + tag + ".zip"
    if get(url, dst) is None:
        return None, None
    ck = get(url + ".CHECKSUM")
    ok = None
    if ck is not None:
        ok = ck.decode().split()[0].strip().lower() == sha256f(dst)
    return dst, ok


def iter_csv(zp, usecols, names):
    """doc CSV trong zip theo chunk; tu nhan header (dong dau khong bat dau bang so). Cot theo VI TRI."""
    with zipfile.ZipFile(zp) as z:
        nm = z.namelist()[0]
        with z.open(nm) as f:
            first = f.readline().decode().strip()
        hdr = 0 if (first and not first[0].isdigit()) else None
        with z.open(nm) as f:
            for ch in pd.read_csv(f, header=hdr, usecols=usecols, chunksize=CHUNK):
                ch.columns = names
                yield ch


def merge_iv(iv):
    iv = sorted(iv)
    out = [list(iv[0])]
    for a, b in iv[1:]:
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def in_iv(t, iv):
    m = np.zeros(len(t), bool)
    for a, b in iv:
        m |= (t >= a) & (t <= b)
    return m


def fix_ms(t):
    t = np.asarray(t, np.int64)
    return np.where(t > 10 ** 14, t // 1000, t)


def job_agg(arg):
    sym, day, iv = arg
    tag = "%sUSDT_%s" % (sym, day)
    out = W + "/agg/" + tag + ".npz"
    if os.path.exists(out):
        return dict(kind="agg", tag=tag, st="cached")
    url = "%s/daily/aggTrades/%sUSDT/%sUSDT-aggTrades-%s.zip" % (BASE, sym, sym, day)
    zp, ok = fetch_zip(url, tag)
    if zp is None:
        return dict(kind="agg", tag=tag, st="missing")
    zb = os.path.getsize(zp)
    T, P, Q, M, n = [], [], [], [], 0
    try:
        for ch in iter_csv(zp, [1, 2, 5, 6], ["p", "q", "t", "m"]):
            n += len(ch)
            t = fix_ms(ch["t"].to_numpy())
            k = in_iv(t, iv)
            if k.any():
                T.append(t[k])
                P.append(ch["p"].to_numpy(np.float64)[k])
                Q.append(ch["q"].to_numpy(np.float64)[k])
                M.append(ch["m"].astype(str).str.strip().str.lower().eq("true").to_numpy()[k])
    finally:
        os.remove(zp)
    cat = (lambda x, dt: np.concatenate(x) if x else np.zeros(0, dt))
    t, p, q, m = cat(T, np.int64), cat(P, np.float64), cat(Q, np.float64), cat(M, bool)
    o = np.argsort(t, kind="stable")
    np.savez_compressed(out, t=t[o], p=p[o], q=q[o], m=m[o])
    return dict(kind="agg", tag=tag, st="ok", sha_ok=ok, rows=n, kept=int(len(t)), zip_bytes=zb)


def job_kl(arg):
    sym, mon, iv = arg
    tag = "%sUSDT_%s" % (sym, mon)
    out = W + "/kl/" + tag + ".npz"
    if os.path.exists(out):
        return dict(kind="kl", tag=tag, st="cached")
    url = "%s/monthly/klines/%sUSDT/1m/%sUSDT-1m-%s.zip" % (BASE, sym, sym, mon)
    zp, ok = fetch_zip(url, tag)
    if zp is None:
        return dict(kind="kl", tag=tag, st="missing")
    try:
        ch = pd.concat(list(iter_csv(zp, [0, 1, 2, 3, 4, 5], ["t", "o", "h", "l", "c", "v"])), ignore_index=True)
    finally:
        os.remove(zp)
    t = fix_ms(ch["t"].to_numpy())
    k = in_iv(t, iv) & (t < T26)
    X = ch[["o", "h", "l", "c", "v"]].to_numpy(np.float64)[k]
    o = np.argsort(t[k], kind="stable")
    np.savez_compressed(out, t=t[k][o], x=X[o])
    return dict(kind="kl", tag=tag, st="ok", sha_ok=ok, rows=int(len(ch)), kept=int(k.sum()))


def build_jobs(kind):
    ev = pd.read_pickle(W + "/legs.pkl")["ev"]
    jobs = {}
    for sym, s in zip(ev["sym"], ev["s_ms"]):
        if kind == "agg":
            a, b = s + DEC_OFF - WIN_PRE, s + DEC_OFF + WIN_POST
            for t in (a, b):
                day = pd.Timestamp(int(t), unit="ms").strftime("%Y-%m-%d")
                d0 = int(pd.Timestamp(day).value // 10 ** 6)
                jobs.setdefault((sym, day), []).append((max(a, d0), min(b, d0 + D - 1)))
        else:
            a, b = s - WIN_PRE, min(T26 - 1, s + PATH_H)
            for m in pd.period_range(pd.Timestamp(a, unit="ms"), pd.Timestamp(b, unit="ms"), freq="M"):
                m0 = int(m.start_time.value // 10 ** 6)
                m1 = int((m + 1).start_time.value // 10 ** 6) - 1
                jobs.setdefault((sym, str(m)), []).append((max(a, m0), min(b, m1)))
    return [(k[0], k[1], merge_iv(v)) for k, v in sorted(jobs.items())]


def main():
    kind = sys.argv[1]
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    for d in (TMP, W + "/agg", W + "/kl"):
        os.makedirs(d, exist_ok=True)
    jobs = build_jobs(kind)
    fn = job_agg if kind == "agg" else job_kl
    log.info("%s: %d job, %d luong", kind, len(jobs), nw)
    t0, res = time.time(), []
    with ThreadPoolExecutor(nw) as ex, open(W + "/fetch_%s.jsonl" % kind, "a") as fo:
        for i, r in enumerate(ex.map(fn, jobs)):
            res.append(r)
            fo.write(json.dumps(r) + "\n")
            fo.flush()
            if i % 100 == 0:
                log.info("%s %d/%d %.0fs %s", kind, i, len(jobs), time.time() - t0, json.dumps(r))
    st = pd.Series([r["st"] for r in res]).value_counts().to_dict()
    bad_sha = [r["tag"] for r in res if r.get("sha_ok") is False]
    no_sha = [r["tag"] for r in res if r["st"] == "ok" and r.get("sha_ok") is None]
    summ = dict(kind=kind, n=len(jobs), st=st, bad_sha=bad_sha, no_sha=len(no_sha),
                missing=[r["tag"] for r in res if r["st"] == "missing"], secs=time.time() - t0)
    with open(W + "/fetch_%s_summary.json" % kind, "w") as f:
        json.dump(summ, f)
    log.info("XONG %s: %s bad_sha %d no_sha %d missing %d %.0fs", kind, st, len(bad_sha), len(no_sha),
             len(summ["missing"]), summ["secs"])


if __name__ == "__main__":
    main()
