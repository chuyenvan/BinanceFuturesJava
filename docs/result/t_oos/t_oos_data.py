#!/usr/bin/env python3
"""T_OOS data prep: tai Vision SPOT BTCUSDT klines 1d 2017-08..2019-12 (CHI cac thang nay; KHONG co 2020), kiem sha256 theo .CHECKSUM,
kiem du ngay, ghi CSV sach (date, close). Khong in gia. Usage: python3 t_oos_data.py rawdir out.csv report.json"""
import hashlib
import io
import json
import logging
import sys
import urllib.request
import zipfile

import pandas as pd

log = logging.getLogger("toosdata")
BASE = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-%s.zip"
MONTHS = [m.strftime("%Y-%m") for m in pd.period_range("2017-08", "2019-12", freq="M")]
FIRST, LAST = "2017-08-17", "2019-12-31"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "qvol", "trades", "tbase", "tquote", "ignore"]


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def main():
    raw, out, rep_path = sys.argv[1:4]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    assert MONTHS[-1] == "2019-12" and all(m < "2020" for m in MONTHS)
    frames, rep = [], dict(months=len(MONTHS), checksum_ok=0, files={})
    for ym in MONTHS:
        url = BASE % ym
        z = get(url)
        chk = get(url + ".CHECKSUM").decode().split()[0].lower()
        h = hashlib.sha256(z).hexdigest()
        ok = h == chk
        assert ok, "checksum sai %s" % ym
        rep["checksum_ok"] += 1
        open("%s/BTCUSDT-1d-%s.zip" % (raw, ym), "wb").write(z)
        with zipfile.ZipFile(io.BytesIO(z)) as zf:
            names = zf.namelist()
            assert len(names) == 1
            d = pd.read_csv(zf.open(names[0]), header=None, names=COLS)
        ot = d["open_time"].astype("int64")
        ot = ot.where(ot < 10**14, ot // 1000)           # 2017-2019 la ms; phong truong hop us
        d["date"] = pd.to_datetime(ot, unit="ms").dt.date
        assert (pd.to_datetime(ot, unit="ms").dt.hour == 0).all(), "open_time khong 00:00 UTC %s" % ym
        rep["files"][ym] = dict(rows=len(d), sha256=h)
        frames.append(d[["date", "close"]])
        log.info("%s rows=%d checksum_ok", ym, len(d))
    d = pd.concat(frames).sort_values("date")
    dup = int(d["date"].duplicated().sum())
    d = d.drop_duplicates("date", keep="last")
    d = d[(d["date"].astype(str) >= FIRST) & (d["date"].astype(str) <= LAST)]
    assert str(d["date"].max()) < "2020-01-01"
    full = pd.date_range(FIRST, LAST, freq="D").date
    missing = sorted(set(full) - set(d["date"]))
    rep.update(duplicates=dup, expected_days=len(full), rows=len(d), first=str(d["date"].min()), last=str(d["date"].max()),
               missing_days=[str(x) for x in missing])
    log.info("expected=%d rows=%d dup=%d missing=%s", len(full), len(d), dup, rep["missing_days"])
    if missing:
        # quy tac prereg: ngay thieu duoc ffill close ngay truoc (ngay phang), ghi lai; > 3 ngay thieu => dung, bao MASTER
        assert len(missing) <= 3, "qua 3 ngay thieu - dung theo prereg"
        d = d.set_index("date").reindex(full).ffill().rename_axis("date").reset_index()
        rep["filled"] = True
    d["close"] = d["close"].astype(float)
    assert d["close"].notna().all() and (d["close"] > 0).all()
    d.to_csv(out, index=False)
    rep["clean_sha256"] = hashlib.sha256(open(out, "rb").read()).hexdigest()
    json.dump(rep, open(rep_path, "w"), indent=1)
    log.info("DATA_DONE clean_sha256=%s", rep["clean_sha256"])


if __name__ == "__main__":
    main()
