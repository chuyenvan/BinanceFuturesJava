#!/usr/bin/env python3
"""TS_MKT_EXT addendum 1 (737d9faa): HO 2026 W9. Dung lai ho4p1_queue (kernel/du lieu HO4) + jar sim-jar-tsx.
  flags : cờ 2026 tu ew_out/ew_2026.npz (+ V1 so khop index.npz 2025-10..12) -> ho_flags.json
  run   : P0 tsx-ho-p0-s42 (khong key) + 8 x tsx-ho-x14-s<seed>; MAXPAR kernel toan tai khoan; check sau moi run
  post  : V3 (TSX log, printDone truoc 2025-12-24 trung baseline)
"""
import glob, hashlib, json, logging, os, re, sys, time  # noqa: E401

import numpy as np
import pandas as pd

W = "/home/ubuntu/claude_master/tsx/ho"
JAR = "/home/ubuntu/src_wt_bcd/target/binance-java-sdk-1.2.4.jar"
WANT_JAR = open("/home/ubuntu/claude_master/tsx/jar.sha256").read().split()[0]
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
BASE_MD5_42 = "7cc8864ca12bdd69f0165c9c9d5c74c5"
MAXPAR, POLL = 5, 240
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsxho")
fh = logging.FileHandler(W + "/tsx_ho.log")
fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(fh)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def flags():
    a = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
    b = np.load(W + "/ew_out/ew_2026.npz")
    ta, ra, tb, rb = a["ew_ts"].astype(np.int64), a["ew_r"], b["ew_ts"].astype(np.int64), b["ew_r"]
    lo = int(pd.Timestamp("2025-10-01").value // 10**6)
    hi = int(pd.Timestamp("2026-01-01").value // 10**6)
    ma, mb = (ta >= lo) & (ta < hi), (tb >= lo) & (tb < hi)
    same_ts = bool(np.array_equal(ta[ma], tb[mb]))
    mx = float(np.max(np.abs(ra[ma] - rb[mb]))) if same_ts else None
    v1 = dict(same_ts=same_ts, n_a=int(ma.sum()), n_b=int(mb.sum()), max_abs=mx, ok=bool(same_ts and mx is not None and mx <= 1e-9))
    log.info("V1 %s", v1)
    if not v1["ok"]:
        raise SystemExit("V1 FAIL")
    ts = np.concatenate([ta[ta < hi], tb[tb >= hi]])
    r = np.concatenate([ra[ta < hi], rb[tb >= hi]])
    L = pd.Series(np.cumsum(r.astype(np.float64)), index=pd.to_datetime(ts, unit="ms"))
    eod = L.groupby(L.index.floor("D")).last()
    dd = np.exp(eod - eod.rolling(31, min_periods=1).max()) - 1
    fd = sorted(dd[dd <= -0.30].index + pd.Timedelta(days=1))
    dev = [d for d in fd if pd.Timestamp("2021-07-01") <= d <= pd.Timestamp("2025-12-31")]
    fd = [d for d in fd if pd.Timestamp("2026-01-01") <= d <= pd.Timestamp("2026-09-30")]
    dev_old = json.load(open("/home/ubuntu/claude_master/tsx/flags.json"))
    rng, st, pv = [], None, None
    for d in fd:
        if st is None:
            st = pv = d
        elif d == pv + pd.Timedelta(days=1):
            pv = d
        else:
            rng.append((st, pv))
            st = pv = d
    if st is not None:
        rng.append((st, pv))
    s = ",".join("%s-%s" % (x.strftime("%Y%m%d"), y.strftime("%Y%m%d")) for x, y in rng)
    dd26 = dd[(dd.index >= "2025-12-31") & (dd.index <= "2026-09-30")]
    out = dict(v1=v1, n_days=len(fd), n_ranges=len(rng), ranges=s, sha256=hashlib.sha256(s.encode()).hexdigest(),
               dev_days_recomputed=len(dev), dev_days_prereg=dev_old["n_days"],
               dd_min_2026=float(dd26.min()), dd_min_day=str(dd26.idxmin().date()),
               by_month=pd.Series(1, index=pd.DatetimeIndex(fd)).groupby(lambda x: x.month).sum().to_dict() if fd else {})
    out["by_month"] = {int(k): int(v) for k, v in out["by_month"].items()}
    json.dump(out, open(W + "/ho_flags.json", "w"), indent=1)
    log.info("FLAGS %s", json.dumps({k: v for k, v in out.items() if k != "ranges"}))
    log.info("RANGES %s", s)
    return out


def Q():
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import ho4p1_queue as q  # noqa: E402
    logging.getLogger().removeHandler(q._fh)
    q.JAR_DS = "sim-jar-tsx"
    q.JAR_SHA = sha256(JAR)
    assert q.JAR_SHA == WANT_JAR, (q.JAR_SHA, WANT_JAR)
    return q


def specs(q, fl):
    k24 = dict(q.CFGS["k24"])
    assert k24 == q.PARITY["ho4p1-c2"][0]
    sp = {"tsx-ho-p0-s42": (42, dict(k24))}
    for s in SEEDS:
        sp["tsx-ho-x14-s%d" % s] = (s, dict(k24, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=fl["ranges"]))
    return sp


def tsx_line(txt):
    m = re.findall(r"\[TSX\] extHours=(\d+) extDays=(\d+) deferTicks=(\d+) deferClusters=(\d+) cutAfterDefer=(\d+)", txt)
    return [int(x) for x in m[-1]] if m else None


def pd_rows(tag, cut="20251224"):
    p = "/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv" % tag
    d = pd.read_csv(p, index_col=False, dtype=str)
    return d[d["start"] < cut].sort_values(list(d.columns)).reset_index(drop=True)


def post(q, tag, seed, ov):
    ok, chk, md5, n = q.check(tag, ov, seed, True)
    txt = q.kernel_text(tag)
    tl = tsx_line(txt)
    r = dict(tag=tag, seed=seed, ok=ok, chk=chk, md5=md5, n=n, tsx=tl)
    if tag.startswith("tsx-ho-p0"):
        r["p0_md5_ok"] = md5 == BASE_MD5_42
        r["tsx_absent"] = tl is None or tl[0] == 0
        r["pass"] = bool(ok and r["p0_md5_ok"])
    else:
        a, b = pd_rows(tag), pd_rows("ho4-k24-b-s%d" % seed)
        r["pre2026_same"] = bool(a.equals(b))
        r["pre_rows"] = [len(a), len(b)]
        r["pass"] = bool(ok and tl is not None and tl[0] == 336 and r["pre2026_same"])
    log.info("POST %s pass=%s md5=%s n=%s tsx=%s chk=%s %s", tag, r["pass"], md5, n, tl, chk,
             {k: r[k] for k in ("p0_md5_ok", "pre2026_same", "pre_rows") if k in r})
    json.dump(r, open(W + "/res_%s.json" % tag, "w"), indent=1)
    return r


def run(fl):
    q = Q()
    ks = q.GA.ks_mod()
    sp = specs(q, fl)
    stp = W + "/state.json"
    st = json.load(open(stp)) if os.path.exists(stp) else {t: {"state": "TODO"} for t in sp}
    while True:
        for t in sp:
            if st[t]["state"] == "PUSHED":
                try:
                    k = ks._status(ks.kernel_ref(t))
                except Exception as e:  # noqa: BLE001
                    log.warning("status %s %s", t, str(e)[:100])
                    continue
                if k in ks.TERMINAL:
                    log.info("%s -> %s", t, k)
                    ks.fetch(t)
                    s, ov = sp[t]
                    r = post(q, t, s, ov)
                    st[t].update(state="DONE", kstatus=str(k), passed=r["pass"])
        try:
            busy = set(r for r, _ in q.running(ks)) | set(ks.kernel_ref(t) for t in sp if st[t]["state"] == "PUSHED")
        except Exception as e:  # noqa: BLE001
            log.warning("running %s", str(e)[:100])
            time.sleep(POLL)
            continue
        todo = [t for t in sp if st[t]["state"] == "TODO"]
        while todo and len(busy) < MAXPAR:
            t = todo.pop(0)
            s, ov = sp[t]
            try:
                q.push(ks, t, ov, s, "20261001", True)
                st[t].update(state="PUSHED", at=time.strftime("%F %T"))
                busy.add(ks.kernel_ref(t))
            except Exception as e:  # noqa: BLE001
                log.error("push %s %s", t, str(e)[:200])
                break
        json.dump(st, open(stp, "w"), indent=1)
        log.info("POLL busy=%d todo=%d done=%d", len(busy), len(todo), sum(st[t]["state"] == "DONE" for t in sp))
        if all(st[t]["state"] == "DONE" for t in sp):
            log.info("HO RUN XONG pass=%d/%d", sum(bool(st[t].get("passed")) for t in sp), len(sp))
            return
        time.sleep(POLL)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "flags":
        flags()
    elif cmd == "run":
        fl = json.load(open(W + "/ho_flags.json"))
        assert fl["v1"]["ok"] and fl["n_days"] > 0
        run(fl)
