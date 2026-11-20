"""fetch_reduce.py - tai aggTrades Binance Vision THEO LO cho cac cum mau da chot (sample.csv, sha256 da commit), kiem .CHECKSUM,
doc CSV, mo phong NGAY (tl_engine THROUGH + TOUCH) cho moi don vi cua cum, dung nen 1 phut cho cac phut trong cua so (W2/W3),
giu giao dich THO trong cua so CHI cho cum audit (W4/W5), roi XOA file tho. Checkpoint theo cum (khoi dong lai an toan).
PREREG_GRIDV2_S2 muc 4, 6, 10. KHONG chay tren du lieu that trong pha dev (chi --head-only voi tap nho da duyet).

Dung:
  python3 fetch_reduce.py --sample sample.csv --sample-sha SHA --events EVDIR --out OUT [--head-only] [--workers 6]
Hang so prereg: MISS_MAX_FRAC 0,03 (W6, theo nua), RETRY 2, MIN_FREE_GB 15, MAX_TEMP_GB 2 (an toan dia Oracle).
Mo hinh: THROUGH, TOUCH (luat) + THROUGH_LAT5S (chi bao cao).
"""
import argparse
import glob
import hashlib
import io
import json
import logging
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tl_engine as E  # noqa: E402
import sample as SM  # noqa: E402

log = logging.getLogger("fetch_reduce")
VISION = "https://data.binance.vision"
PATH_FMT = "/data/futures/um/daily/aggTrades/%s/%s-aggTrades-%s.zip"
MISS_MAX_FRAC = 0.03
RETRY = 2
MIN_FREE_GB = 15.0
MAX_TEMP_GB = 2.0
DAY = 86400000
MIN = 60000
SEAL_DATE = "2026-01-01"
AGG_COLS = ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"]


def day_ms(date):
    return int(pd.Timestamp(date, tz="UTC").value // 10**6)


def url_of(base, sym, date):
    if date >= SEAL_DATE:
        raise RuntimeError("W0: ngay %s >= 2026-01-01 - NIEM PHONG, DUNG" % date)
    return base.rstrip("/") + PATH_FMT % (sym, sym, date)


def head_size(url):
    rq = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(rq, timeout=30) as r:
            return r.status, int(r.headers.get("Content-Length", -1))
    except urllib.error.HTTPError as e:
        return e.code, -1
    except Exception:  # noqa
        return -1, -1


def _get(url, dest=None):
    with urllib.request.urlopen(url, timeout=120) as r:
        if dest is None:
            return r.read()
        with open(dest, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    return None


def disk_ok(path, need_bytes, min_free_gb, tmp_dir, max_temp_gb):
    free = shutil.disk_usage(path).free
    used_tmp = sum(os.path.getsize(p) for p in glob.glob(os.path.join(tmp_dir, "*")) if os.path.isfile(p))
    return free - need_bytes >= min_free_gb * 1e9 and used_tmp + need_bytes <= max_temp_gb * 1e9


def download(base, sym, date, tmp_dir, cfg):
    """Tai zip + .CHECKSUM, kiem sha256. Tra dict trang thai (status ok / missing_404 / checksum / neterr / disk)."""
    url = url_of(base, sym, date)
    dest = os.path.join(tmp_dir, "%s_%s.zip" % (sym, date))
    rec = dict(sym=sym, date=date, url=url, status=None, bytes=0, sha256=None, tries=0)
    for att in range(RETRY + 1):
        rec["tries"] = att + 1
        try:
            if not disk_ok(cfg["out"], 0, cfg["min_free_gb"], tmp_dir, cfg["max_temp_gb"]):
                rec["status"] = "disk"
                return rec
            ck = _get(url + ".CHECKSUM").decode("ascii", "replace").split()
            _get(url, dest)
        except urllib.error.HTTPError as e:
            rec["status"] = "missing_404" if e.code == 404 else "neterr_%d" % e.code
            if e.code == 404:
                return rec
            time.sleep(2 + 3 * att)
            continue
        except (urllib.error.URLError, OSError) as e:
            if isinstance(getattr(e, "reason", None), FileNotFoundError) or isinstance(e, FileNotFoundError):
                rec["status"] = "missing_404"
                return rec
            rec["status"] = "neterr"
            time.sleep(2 + 3 * att)
            continue
        h = hashlib.sha256(open(dest, "rb").read()).hexdigest()
        rec["bytes"] = os.path.getsize(dest)
        rec["sha256"] = h
        if ck and ck[0].lower() == h:
            rec["status"] = "ok"
            rec["path"] = dest
            return rec
        rec["status"] = "checksum"
        os.remove(dest)
    return rec


def parse_zip(path, date):
    """Doc CSV aggTrades (co / khong tieu de). Tra (t, aid, p, ibm, kiem toan ven)."""
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise RuntimeError("zip khong dung 1 csv: %s" % names)
        raw = z.read(names[0])
    first = raw[:200].split(b"\n", 1)[0]
    header = 0 if first[:1].isalpha() else None
    df = pd.read_csv(io.BytesIO(raw), header=header, names=None if header == 0 else AGG_COLS,
                     dtype={"is_buyer_maker": str})
    if header == 0:
        df.columns = [c.strip().lower() for c in df.columns]
        if list(df.columns) != AGG_COLS:
            raise RuntimeError("cot aggTrades la: %s" % list(df.columns))
    t = df.transact_time.to_numpy(np.int64)
    us = bool(t.size and t.max() > 10**14)
    if us:
        t = t // 1000
    aid = df.agg_trade_id.to_numpy(np.int64)
    p = df.price.to_numpy(np.float64)
    ibm = df.is_buyer_maker.astype(str).str.strip().str.lower().map({"true": True, "false": False})
    if ibm.isna().any():
        raise RuntimeError("is_buyer_maker la")
    ibm = ibm.to_numpy(bool)
    d0 = day_ms(date)
    o = np.argsort(aid, kind="stable")
    ida = aid[o]
    chk = dict(n_rows=int(t.size), us_converted=us, id_gaps=int(np.sum(np.diff(ida) != 1)) if ida.size > 1 else 0,
               id_first=int(ida[0]) if ida.size else -1, id_last=int(ida[-1]) if ida.size else -1,
               n_time_back=int(np.sum(np.diff(t[o]) < 0)) if t.size > 1 else 0,
               n_outside_day=int(np.sum((t < d0) | (t >= d0 + DAY))), t_min=int(t.min()) if t.size else -1,
               t_max=int(t.max()) if t.size else -1)
    if t.size and int(t.max()) >= E.SEAL_MS:
        raise RuntimeError("W0: giao dich >= 2026 trong file %s - DUNG" % path)
    return t, aid, p, ibm, chk


def load_events_index(ev_dir):
    ev, shas = SM.load_events(ev_dir)
    fu = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(ev_dir, "funding_ev_s*.parquet")))],
                   ignore_index=True) if glob.glob(os.path.join(ev_dir, "funding_ev_s*.parquet")) else pd.DataFrame(
        columns=["sym", "ts", "rate"])
    fu = fu.drop_duplicates(["sym", "ts"]).sort_values(["sym", "ts"])
    fmap = {s: (g.ts.to_numpy(np.int64), g.rate.to_numpy(np.float64)) for s, g in fu.groupby("sym")}
    return ev, fmap, shas


def process_cluster(cl, files, evg, fmap, audit_dir):
    """cl: dong sample; files: {date: (t, aid, p, ibm)} da tai du. Tra (bang ket qua don vi, bang nen, thong tin)."""
    sym, date = cl.sym, cl.date
    dates = cl.files.split(";")
    t = np.concatenate([files[d][0] for d in dates])
    aid = np.concatenate([files[d][1] for d in dates])
    p = np.concatenate([files[d][2] for d in dates])
    ibm = np.concatenate([files[d][3] for d in dates])
    data_start = day_ms(dates[0])
    data_end = day_ms(dates[-1]) + DAY
    keep = (t >= data_start) & (t < data_end)
    t, aid, p, ibm = t[keep], aid[keep], p[keep], ibm[keep]
    MS = E.collapse_ms(t, aid, p, ibm)
    u = evg[(sym, date)].sort_values(["t0_ms", "side"], ascending=[True, False])
    U = dict(t0=u.t0_ms.to_numpy(np.int64), side=u.side.to_numpy(np.int64), L=u.L.to_numpy(np.float64),
             X=u.X.to_numpy(np.float64), tick=u.tick.to_numpy(np.float64), W=u.W.to_numpy(np.int64),
             T=u["T"].to_numpy(np.int64), slip=u.slip.to_numpy(np.float64), dl_end=u.dl_end_ms.to_numpy(np.int64))
    ft, fr = fmap.get(sym, (np.zeros(0, np.int64), np.zeros(0)))
    res = []
    for m in E.MODELS + E.DIAG_MODELS:
        o = E.simulate(MS, U, m, data_start, data_end, ft, fr)
        df = pd.DataFrame({k: o[k] for k in E.OUT_COLS})
        df["model"] = m
        df["sym"], df["date"], df["t0_ms"], df["side"] = sym, date, U["t0"], U["side"]
        df["data_start"], df["data_end"] = data_start, data_end
        res.append(df)
    res = pd.concat(res, ignore_index=True)
    bars = E.minute_bars(MS)
    t0m = (U["t0"] - E.DATA_START_MS) // MIN
    need = np.zeros(0, np.int64)
    if t0m.size:
        need = np.unique(np.concatenate([np.arange(a - 61, a + int(w) + int(tt) + 62) for a, w, tt in zip(t0m, U["W"], U["T"])]))
    k = np.isin(bars["mi"], need)
    bdf = pd.DataFrame({c: bars[c][k] for c in ("mi", "o", "h", "l", "c", "n")})
    bdf["sym"], bdf["date"] = sym, date
    info = dict(n_ms=int(MS["t"].size), n_trades=int(t.size), data_start=data_start, data_end=data_end)
    if bool(cl.audit):
        r0 = max(data_start, int(U["t0"].min()) - E.GAP_MS - MIN)
        r1 = min(data_end, int(U["t0"].max()) + (int(U["W"].max()) + int(U["T"].max()) + 62) * MIN + E.GAP_MS)
        kk = (t >= r0) & (t < r1)
        np.savez_compressed(os.path.join(audit_dir, "%s_%s.npz" % (sym, date)), t=t[kk], aid=aid[kk], p=p[kk], ibm=ibm[kk],
                            r0=np.int64(r0), r1=np.int64(r1), data_start=np.int64(data_start), data_end=np.int64(data_end))
        info["audit_trades"] = int(kk.sum())
    return res, bdf, info


def run(args):
    fr, sha = SM.read_csv(args.sample, args.sample_sha)
    out = args.out
    cfg = dict(out=out, min_free_gb=args.min_free_gb, max_temp_gb=args.max_temp_gb)
    if args.min_free_gb < MIN_FREE_GB and not args._test:
        raise RuntimeError("min_free_gb < 15 khong cho phep")
    for d in ("res", "bars", "audit", "tmp"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    tmp_dir = os.path.join(out, "tmp")
    sel = fr[fr.selected].sort_values(["sym", "date"])
    if args.head_only:
        tot, n404, rows = 0, 0, []
        uniq = sorted({(r.sym, d) for r in sel.itertuples() for d in r.files.split(";")})
        for s, d in uniq:
            st, sz = head_size(url_of(args.base_url, s, d))
            rows.append(dict(sym=s, date=d, status=st, bytes=sz))
            tot += max(sz, 0)
            n404 += int(st != 200)
        json.dump(dict(n_files=len(uniq), total_bytes=tot, n_not_200=n404, rows=rows), open(os.path.join(out, "head.json"), "w"))
        log.info("HEAD %d file, %.2f GB, khong 200: %d", len(uniq), tot / 1e9, n404)
        return dict(n_files=len(uniq), total_bytes=tot, n_not_200=n404)
    ev, fmap, ev_sha = load_events_index(args.events)
    evg = {k: g for k, g in ev.groupby(["sym", "date"])}
    stp = os.path.join(out, "state.json")
    state = json.load(open(stp)) if os.path.exists(stp) else dict(sample_sha=sha, done={}, subs=[], part=0, events_sha=ev_sha)
    if state["sample_sha"] != sha:
        raise RuntimeError("checkpoint thuoc mau khac - DUNG")
    used = set(state["done"]) | {s["sub"] for s in state["subs"]}
    reserve = {st_: list(g.sort_values("rank").itertuples()) for st_, g in fr[~fr.selected].groupby("stratum")}
    queue = [r for r in sel.itertuples() if "%s|%s" % (r.sym, r.date) not in state["done"]]
    for s in state["subs"]:
        if s["sub"] not in state["done"]:
            sym, date = s["sub"].split("|")
            queue.append(next(r for r in fr.itertuples() if r.sym == sym and r.date == date))
    flog = open(os.path.join(out, "files.jsonl"), "a")
    while queue:
        batch, queue = queue[:args.batch], queue[args.batch:]
        need = sorted({(r.sym, d) for r in batch for d in r.files.split(";")})
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            recs = list(ex.map(lambda sd: download(args.base_url, sd[0], sd[1], tmp_dir, cfg), need))
        if any(r["status"] == "disk" for r in recs):
            raise RuntimeError("gioi han dia (MIN_FREE_GB / MAX_TEMP_GB) - DUNG, checkpoint giu nguyen")
        got = {}
        for r in recs:
            if r["status"] == "ok":
                try:
                    t, aid, p, ibm, chk = parse_zip(r["path"], r["date"])
                    r.update(chk)
                    got[(r["sym"], r["date"])] = (t, aid, p, ibm)
                except RuntimeError:
                    raise
                except Exception as e:  # noqa
                    r["status"] = "parse_error"
                    r["error"] = repr(e)[:200]
            flog.write(json.dumps({k: v for k, v in r.items() if k != "path"}) + "\n")
        res_l, bar_l = [], []
        for r in batch:
            key = "%s|%s" % (r.sym, r.date)
            ds = r.files.split(";")
            if all((r.sym, d) in got for d in ds):
                rs, bd, info = process_cluster(r, {d: got[(r.sym, d)] for d in ds}, evg, fmap, os.path.join(out, "audit"))
                rs["stratum"], rs["half"], rs["audit"] = r.stratum, r.half, bool(r.audit)
                res_l.append(rs)
                bar_l.append(bd)
                state["done"][key] = dict(status="ok", **info)
            else:
                miss = [d for d in ds if (r.sym, d) not in got]
                state["done"][key] = dict(status="missing", missing=miss)
                cand = [c for c in reserve.get(r.stratum, []) if "%s|%s" % (c.sym, c.date) not in used]
                if cand:
                    c = cand[0]
                    ck = "%s|%s" % (c.sym, c.date)
                    used.add(ck)
                    state["subs"].append(dict(missing=key, sub=ck, stratum=r.stratum))
                    queue.append(c)
                else:
                    state["subs"].append(dict(missing=key, sub=None, stratum=r.stratum))
        for r in recs:
            if r.get("path") and os.path.exists(r["path"]):
                os.remove(r["path"])
        state["part"] += 1
        if res_l:
            pd.concat(res_l, ignore_index=True).to_parquet(os.path.join(out, "res", "part_%05d.parquet" % state["part"]), index=False)
            pd.concat(bar_l, ignore_index=True).to_parquet(os.path.join(out, "bars", "part_%05d.parquet" % state["part"]), index=False,
                                                          compression="zstd")
        json.dump(state, open(stp + ".tmp", "w"))
        os.replace(stp + ".tmp", stp)
        flog.flush()
        log.info("lo %d: %d cum, con %d; tai %d file %.1f MB", state["part"], len(batch), len(queue),
                 sum(r["status"] == "ok" for r in recs), sum(r.get("bytes", 0) for r in recs) / 1e6)
    flog.close()
    w6 = w6_eval(fr, state)
    state["W6"] = w6
    json.dump(state, open(stp, "w"))
    log.info("W6 %s", w6)
    return state


def w6_eval(fr, state):
    """W6: ti le cum DA CHON thieu file theo nua (cum du phong thieu khong tinh vao mau so, chi dem)."""
    sel = fr[fr.selected]
    out = dict(ok=True)
    for h, g in sel.groupby("half"):
        keys = ["%s|%s" % (s, d) for s, d in zip(g.sym, g.date)]
        miss = sum(state["done"].get(k, {}).get("status") == "missing" for k in keys)
        nsub_none = sum(1 for s in state["subs"] if s["sub"] is None and s["missing"] in set(keys))
        frac = miss / max(len(keys), 1)
        out[h] = dict(n_selected=len(keys), n_missing=int(miss), frac=frac, unreplaced=int(nsub_none))
        out["ok"] = bool(out["ok"] and frac <= MISS_MAX_FRAC)
    selk = {"%s|%s" % (s, d) for s, d in zip(sel.sym, sel.date)}
    out["n_reserve_missing"] = int(sum(1 for k, v in state["done"].items() if v.get("status") == "missing" and k not in selk))
    return out


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--sample-sha", required=True)
    ap.add_argument("--events", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-url", default=VISION)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--min-free-gb", type=float, default=MIN_FREE_GB)
    ap.add_argument("--max-temp-gb", type=float, default=MAX_TEMP_GB)
    ap.add_argument("--head-only", action="store_true")
    return ap


def main(argv=None, _test=False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    args = build_parser().parse_args(argv)
    args._test = _test
    return run(args)


if __name__ == "__main__":
    main()
