#!/usr/bin/env python3
"""T_OOS2 data B: Vision SPOT ETHUSDT klines 1d, hai doan: S1 2017-08..2019-12 (ngay 2017-08-17..2019-12-31) va S2 2021-01..2025-12 (ngay 2021-01-01..2025-12-31).
KHONG BAO GIO tai/doc thang 2020 (assert). Kiem sha256 theo .CHECKSUM, du ngay, khong trung; ngay thieu moi doan <= 3 -> ffill close ngay truoc (ghi lai), > 3 => DUNG.
Khong in gia. Co che selftest: --selftest SYMBOL FIRSTMONTH LASTMONTH (vi du BTCUSDT 2025-10 2025-11) chi de kiem parser (khong ghi vao ket qua).
Usage: python3 -I t_oos2_data_eth.py RAWDIR OUTDIR [--selftest SYMBOL M1 M2]"""
import hashlib
import io
import json
import logging
import os
import sys
import urllib.request
import zipfile

import pandas as pd

log = logging.getLogger("toos2eth")
URL = "https://data.binance.vision/data/spot/monthly/klines/%s/1d/%s-1d-%s.zip"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "qvol", "trades", "tbase", "tquote", "ignore"]
SEGS = [
    dict(name="eth_seg1", m1="2017-08", m2="2019-12", first="2017-08-17", last="2019-12-31"),
    dict(name="eth_seg2", m1="2021-01", m2="2025-12", first="2021-01-01", last="2025-12-31"),
]


def get(url):
    with urllib.request.urlopen(url, timeout=90) as r:
        return r.read()


def fetch_seg(sym, seg, rawdir, selftest=False):
    months = [m.strftime("%Y-%m") for m in pd.period_range(seg["m1"], seg["m2"], freq="M")]
    assert not any(m.startswith("2020") for m in months), "THANG 2020 BI CAM"
    frames, files = [], {}
    for ym in months:
        url = URL % (sym, sym, ym)
        z = get(url)
        chk = get(url + ".CHECKSUM").decode().split()[0].lower()
        h = hashlib.sha256(z).hexdigest()
        assert h == chk, "checksum sai %s" % ym
        os.makedirs(os.path.join(rawdir, seg["name"]), exist_ok=True)
        open(os.path.join(rawdir, seg["name"], "%s-1d-%s.zip" % (sym, ym)), "wb").write(z)
        with zipfile.ZipFile(io.BytesIO(z)) as zf:
            names = zf.namelist()
            assert len(names) == 1
            raw = pd.read_csv(zf.open(names[0]), header=None, names=COLS, dtype=str)
        if not raw["open_time"].iloc[0].strip().isdigit():       # co header
            raw = raw.iloc[1:]
        ot = raw["open_time"].astype("int64")
        ot = ot.where(ot < 10**14, ot // 1000)                    # 2025+ la micro-giay
        ts = pd.to_datetime(ot, unit="ms")
        assert (ts.dt.hour == 0).all() and (ts.dt.minute == 0).all(), "open_time khong 00:00 UTC %s" % ym
        assert (ts.dt.year != 2020).all(), "NAM 2020"
        assert (ts.dt.strftime("%Y-%m") == ym).all(), "ngay ngoai thang %s" % ym
        d = pd.DataFrame({"date": ts.dt.date, "close": raw["close"].astype(float)})
        files[ym] = dict(rows=len(d), sha256=h)
        frames.append(d)
        log.info("%s %s rows=%d checksum_ok", seg["name"], ym, len(d))
    d = pd.concat(frames).sort_values("date")
    dup = int(d["date"].duplicated().sum())
    d = d.drop_duplicates("date", keep="last")
    d = d[(d["date"].astype(str) >= seg["first"]) & (d["date"].astype(str) <= seg["last"])]
    full = pd.date_range(seg["first"], seg["last"], freq="D").date
    missing = sorted(set(full) - set(d["date"]))
    rep = dict(symbol=sym, months=len(months), checksum_ok=len(months), files=files, duplicates=dup, expected_days=len(full), rows=len(d),
               first=str(d["date"].min()), last=str(d["date"].max()), missing_days=[str(x) for x in missing], filled=False)
    log.info("%s expected=%d rows=%d dup=%d missing=%s", seg["name"], len(full), len(d), dup, rep["missing_days"])
    if missing:
        assert len(missing) <= 3, "qua 3 ngay thieu - DUNG theo prereg"
        d = d.set_index("date").reindex(full).ffill().rename_axis("date").reset_index()
        rep["filled"] = True
    assert d["close"].notna().all() and (d["close"] > 0).all()
    assert all(str(x)[:4] != "2020" for x in d["date"])
    return d.reset_index(drop=True), rep


def main():
    rawdir, outdir = sys.argv[1:3]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    os.makedirs(outdir, exist_ok=True)
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        sym, m1, m2 = sys.argv[i + 1:i + 4]
        assert m1 >= "2021-01"
        a = pd.Timestamp(m1 + "-01").date()
        b = (pd.Timestamp(m2 + "-01") + pd.offsets.MonthEnd(0)).date()
        seg = dict(name="selftest", m1=m1, m2=m2, first=str(a), last=str(b))
        d, rep = fetch_seg(sym, seg, rawdir, True)
        log.info("SELFTEST_OK rows=%d first=%s last=%s", len(d), d["date"].min(), d["date"].max())
        return
    allrep = {}
    for seg in SEGS:
        d, rep = fetch_seg("ETHUSDT", seg, rawdir)
        p = os.path.join(outdir, seg["name"] + "_1d_clean.csv")
        d.to_csv(p, index=False)
        rep["clean_sha256"] = hashlib.sha256(open(p, "rb").read()).hexdigest()
        allrep[seg["name"]] = rep
        log.info("%s DATA_DONE clean_sha256=%s", seg["name"], rep["clean_sha256"])
    json.dump(allrep, open(os.path.join(outdir, "eth_data_report.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
