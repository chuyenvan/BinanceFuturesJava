#!/usr/bin/env python3
"""
feat_diff_pass1_ext.py — MO RONG feat_diff_live_vs_dev.py cho PASS 1.

Van de: DEV export ket thuc 2026-06-01, live la 2026-09-28 ⇒ KHONG the align cap (ts,symbol).
Script nay (theo PREREG_FEAT_DIFF_PASS1.md):
  1. report n/symbol/ts-range moi host (doc gz dang ghi, bo qua truncation)
  2. kiem instrument: 4 feature thoi gian phai khop ham xac dinh tu ts (calibrate tu DEV)
  3. kiem p15_out vs phan bo live da do (%; x100) + tuy chon: p15_out == fold_20(live feat)
  4. FALLBACK: so PHAN BO tung feature live vs 2 cua so DEV (recent 2026-03..06, w20 2025-10..06)
     => shift_sd, qmax_rel, tail_ratio => bang nghi pham
Dung lai V3FULL/QS/feature_table tu feat_diff_live_vs_dev.
Output cuc nho. KHONG ghi gi tren host LIVE.
"""
import argparse, glob, io, json, math, os, sys, zlib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feat_diff_live_vs_dev import V3FULL, QS  # nguon su that thu tu cot

MS_DAY = 86400_000
TZ = 7 * 3600_000  # Asia/Ho_Chi_Minh (+07)


# ---------- doc live dump dang duoc ghi (gzip truncated) ----------
def read_gz_partial(path):
    with open(path, "rb") as fh:
        data = fh.read()
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        out = d.decompress(data)
    except zlib.error:
        out = b""
    lines = out.decode("utf-8", errors="replace").split("\n")[:-1]
    if not lines:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO("\n".join(lines) + "\n"), on_bad_lines="skip")


def newest(d):
    fs = sorted(glob.glob(os.path.join(d, "feat_dump_*.csv.gz")))
    return fs[-1] if fs else None


# ---------- kiem feature thoi gian (calibrate tu DEV) ----------
def _hm(ts_ms):
    return pd.to_datetime(ts_ms + TZ, unit="ms", utc=True)


def time_candidates(ts_ms):
    dt = pd.DatetimeIndex(_hm(ts_ms))
    iso = dt.isocalendar()
    day = dt.day.to_numpy().astype(int)
    first_dow = dt.to_period("M").start_time.dayofweek.to_numpy()   # Mon=0..Sun=6
    w1 = (first_dow + 1) % 7                                        # Sun=0..Sat=6 cua ngay 1
    wom = ((day + w1 - 1) // 7) + 1                                 # Java Calendar WEEK_OF_MONTH (Sun-start)
    cand = {
        "hourOfDay": {"local_hour": dt.hour.to_numpy()},
        "monthOfYear": {"month": dt.month.to_numpy()},
        "dayOfWeek": {"cal_sun1": (iso["day"].to_numpy() % 7) + 1, "iso1_7": iso["day"].to_numpy(),
                      "iso0_6": iso["day"].to_numpy() - 1},
        "weekOfMonth": {"cal_sunstart": wom.astype(int),
                        "ceil_d7": np.ceil(day / 7).astype(int),
                        "floor_d1_d7": ((day - 1) // 7 + 1).astype(int)},
    }
    return cand


def calibrate_time(dev_sample):
    ts = dev_sample["timestamp"].to_numpy(dtype="int64")
    cand = time_candidates(ts)
    chosen = {}
    for f, opts in cand.items():
        actual = pd.to_numeric(dev_sample[f], errors="coerce").to_numpy()
        best, bestm = None, -1.0
        for name, arr in opts.items():
            m = float(np.mean(np.isclose(arr.astype(float), actual)))
            if m > bestm:
                best, bestm = name, m
        chosen[f] = {"formula": best, "match_dev": round(bestm, 6)}
    return chosen


def check_live_time(live, chosen):
    ts = live["ts"].to_numpy(dtype="int64")
    cand = time_candidates(ts)
    out = {}
    for f, info in chosen.items():
        arr = cand[f][info["formula"]].astype(float)
        actual = pd.to_numeric(live[f], errors="coerce").to_numpy()
        out[f] = {"formula": info["formula"], "match_live": round(float(np.mean(np.isclose(arr, actual))), 6),
                  "n": int(len(actual))}
    return out


# ---------- stats per feature ----------
def stats(a):
    a = np.asarray(a, dtype="float64")
    fin = np.isfinite(a)
    nan = 1.0 - fin.mean() if len(a) else 1.0
    if fin.sum() == 0:
        return dict(n=0, nan=1.0, mean=np.nan, std=np.nan, p5=np.nan, p50=np.nan, p95=np.nan, p99=np.nan, mx=np.nan)
    b = a[fin]
    q = np.quantile(b, QS)
    return dict(n=int(fin.sum()), nan=round(nan, 6), mean=float(b.mean()), std=float(b.std()),
                p5=float(q[0]), p50=float(q[2]), p95=float(q[4]), p99=float(q[5]), mx=float(b.max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shadow", default="/tmp/featdiff/live_oracle")
    ap.add_argument("--host242", default="/tmp/featdiff/live_242")
    ap.add_argument("--dev", default=os.path.expanduser("~/claudedata/gate15m_v2_full.csv"))
    ap.add_argument("--anchor", default="BTCUSDT")
    ap.add_argument("--onnx", default=os.path.expanduser("~/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx"))
    ap.add_argument("--no-onnx", action="store_true")
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()

    res = {"prereg": "docs/prereg/PREREG_FEAT_DIFF_PASS1.md"}
    lives = {}
    for tag, d in [("shadow", a.shadow), ("242", a.host242)]:
        p = newest(d)
        df = read_gz_partial(p) if p else pd.DataFrame()
        if not df.empty:
            df = df[df["symbol"] == a.anchor]
        lives[tag] = df
        res.setdefault("hosts", {})[tag] = {
            "file": os.path.basename(p) if p else None, "n": int(len(df)),
            "symbols": sorted(df["symbol"].unique().tolist()) if len(df) else [],
            "ts_min": int(df["ts"].min()) if len(df) else None,
            "ts_max": int(df["ts"].max()) if len(df) else None,
        }
    live = pd.concat([v.assign(_host=k) for k, v in lives.items() if len(v)], ignore_index=True)
    if live.empty:
        print("KHONG co dong live nao."); return 1
    live = live.sort_values("ts").reset_index(drop=True)
    n_live = len(live)
    res["live_n_total"] = n_live
    res["live_ts_range_local"] = [
        str(_hm(pd.Series([live['ts'].min()]))[0]), str(_hm(pd.Series([live['ts'].max()]))[0])]
    res["sufficient"] = bool(n_live >= 200)

    # --- DEV: doc 1 lan, lay 2 cua so + 1 mau calibrate ---
    W = {"recent": (pd.Timestamp("2026-03-01", tz="UTC").value // 10**6),
         "w20": (pd.Timestamp("2025-10-01", tz="UTC").value // 10**6)}
    usecols = ["timestamp"] + V3FULL
    parts = {k: [] for k in W}
    calib = None
    for ch in pd.read_csv(a.dev, usecols=usecols, chunksize=500_000):
        if calib is None:
            calib = ch.head(50_000).copy()
        for k, lo in W.items():
            s = ch[ch["timestamp"] >= lo]
            if len(s):
                parts[k].append(s)
    devw = {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}
    res["dev_windows"] = {k: {"n": int(len(v)), "ts_min": int(v["timestamp"].min()),
                              "ts_max": int(v["timestamp"].max())} for k, v in devw.items()}

    # --- VIEC: kiem feature thoi gian ---
    chosen = calibrate_time(calib)
    res["time_features"] = {"calibration": chosen, "live_check": check_live_time(live, chosen)}
    # cap khop (ts,symbol) — du kien 0
    dev_all_ts = set(int(x) for x in devw["w20"]["timestamp"].to_numpy())
    res["matched_ts_pairs"] = int(sum(1 for x in live["ts"].to_numpy() if int(x) in dev_all_ts))

    # --- VIEC: p15_out ---
    p15 = pd.to_numeric(live["p15_out"], errors="coerce").to_numpy()
    p15pct = p15 * 100.0
    res["p15_out"] = {"n": int(np.isfinite(p15pct).sum()), "raw_p50": float(np.nanmedian(p15)),
                      "pct_p50": float(np.nanmedian(p15pct)), "pct_min": float(np.nanmin(p15pct)),
                      "pct_max": float(np.nanmax(p15pct)),
                      "known_live_pct": {"p50": 0.910, "p99": 1.770, "max": 2.300, "src": "RESULT_P15_SOURCE.md §3.1"}}

    # --- VIEC: ONNX fold_20 tren live feature (neu co) ---
    if not a.no_onnx and os.path.exists(a.onnx):
        try:
            import onnxruntime as ort
            X = live[V3FULL].to_numpy(dtype="float32")
            sess = ort.InferenceSession(a.onnx, providers=["CPUExecutionProvider"])
            nm = sess.get_inputs()[0].name
            y = sess.run(None, {nm: X})[0].reshape(-1).astype("float64")
            d = np.abs(y - p15)
            res["onnx_check"] = {"model": a.onnx, "n": int(len(y)),
                                 "max_abs_diff_pct": float(np.nanmax(d) * 100),
                                 "corr": float(np.corrcoef(y, p15)[0, 1]) if np.std(y) > 0 else None,
                                 "model_p50_pct": float(np.median(y) * 100),
                                 "model_max_pct": float(np.max(y) * 100)}
        except Exception as e:
            res["onnx_check"] = {"error": str(e)[:200]}

    # --- FALLBACK: bang feature live vs DEV windows ---
    rows = []
    for f in V3FULL:
        sl = stats(pd.to_numeric(live[f], errors="coerce").to_numpy())
        sr = stats(devw["recent"][f].to_numpy()); sw = stats(devw["w20"][f].to_numpy())
        iqr = np.quantile(devw["w20"][f].to_numpy(), 0.75) - np.quantile(devw["w20"][f].to_numpy(), 0.25)
        shift = abs(sl["mean"] - sw["mean"]) / (sw["std"] + 1e-12)
        qmax = max(abs(sl["p5"] - sw["p5"]), abs(sl["p50"] - sw["p50"]),
                   abs(sl["p95"] - sw["p95"])) / (abs(iqr) + 1e-12)
        tail = sl["mx"] / (sw["p99"] + 1e-12)
        rows.append(dict(feature=f, live_mean=sl["mean"], live_std=sl["std"], live_p5=sl["p5"],
                         live_p50=sl["p50"], live_p95=sl["p95"], live_max=sl["mx"], live_nan=sl["nan"],
                         devw_mean=sw["mean"], devw_std=sw["std"], devw_p5=sw["p5"], devw_p50=sw["p50"],
                         devw_p95=sw["p95"], devw_p99=sw["p99"], devw_max=sw["mx"],
                         devr_mean=sr["mean"], devr_p50=sr["p50"], devr_max=sr["mx"],
                         shift_sd=shift, qmax_rel=qmax, tail_ratio=tail,
                         live_constant=bool(sl["std"] == 0)))
    t = pd.DataFrame(rows)
    t["suspect"] = (t.shift_sd > 0.5) | (t.qmax_rel > 1.0) | (t.live_nan > 0.01) | (t.live_constant) | (t.tail_ratio < 0.5)
    t = t.sort_values("shift_sd", ascending=False)
    res["feature_table"] = json.loads(t.round(6).to_json(orient="records"))
    res["suspects"] = t[t.suspect]["feature"].tolist()
    res["cut_suspects"] = t[t.tail_ratio < 0.5]["feature"].tolist()
    res["constant_features"] = t[t.live_constant]["feature"].tolist()

    # --- EXPLORATORY (khong pre-reg): so feature live voi DEV rows cho CUNG DAI p15 ---
    if "onnx_check" in res and "error" not in res["onnx_check"]:
        try:
            import onnxruntime as ort
            sess = ort.InferenceSession(a.onnx, providers=["CPUExecutionProvider"])
            nm = sess.get_inputs()[0].name
            band = float(np.median(p15))
            rows2 = []
            for k in ("w20", "recent"):
                Xd = devw[k][V3FULL].to_numpy(dtype="float32")
                yd = sess.run(None, {nm: Xd})[0].reshape(-1).astype("float64")
                sel = np.abs(yd - band) <= 0.0015   # cung dai p15 +-0,15pp
                sub = devw[k][V3FULL].to_numpy(dtype="float64")[sel]
                rows2.append(dict(window=k, n_band=int(sel.sum()),
                                  feats={f: dict(mean=float(np.nanmean(sub[:, i])), std=float(np.nanstd(sub[:, i])))
                                         for i, f in enumerate(V3FULL)}))
            band_dev = rows2[0]["feats"] if rows2[0]["n_band"] >= rows2[1]["n_band"] else rows2[1]["feats"]
            lb = rows2[0] if rows2[0]["n_band"] >= rows2[1]["n_band"] else rows2[1]
            tbl = []
            for f in V3FULL:
                m = float(np.nanmean(pd.to_numeric(live[f], errors="coerce").to_numpy()))
                d = band_dev[f]
                tbl.append(dict(feature=f, live_mean=m, dev_band_mean=d["mean"], dev_band_std=d["std"],
                                shift_sd_band=abs(m - d["mean"]) / (d["std"] + 1e-12)))
            tb = pd.DataFrame(tbl).sort_values("shift_sd_band", ascending=False)
            res["same_band_exploratory"] = {"band_pct": band * 100, "dev_window": lb["window"],
                                            "n_band": lb["n_band"], "top": json.loads(tb.head(6).round(6).to_json(orient="records"))}
        except Exception as e:
            res["same_band_exploratory"] = {"error": str(e)[:200]}

    # ---- in bang nho ----
    print(f"LIVE n={n_live} (shadow={len(lives['shadow'])},242={len(lives['242'])}) anchor={a.anchor} "
          f"ts {res['live_ts_range_local'][0]} -> {res['live_ts_range_local'][1]} | du>=200? {res['sufficient']}")
    print(f"DEV window n: " + ", ".join(f"{k}={v['n']}" for k, v in res["dev_windows"].items()) +
          f" | matched (ts,symbol) pairs = {res['matched_ts_pairs']}")
    tf = res["time_features"]
    print("time-feat match live: " + ", ".join(f"{k}={v['match_live']}" for k, v in tf["live_check"].items()))
    p = res["p15_out"]
    print(f"p15_out raw p50={p['raw_p50']:.5f} -> pct p50={p['pct_p50']:.3f}% min={p['pct_min']:.3f} max={p['pct_max']:.3f}%"
          f" | known live p50=0.910 max=2.300%")
    if "onnx_check" in res:
        oc = res["onnx_check"]
        print("onnx fold_20 vs p15_out: " + (json.dumps(oc) if "error" in oc else
              f"max|diff|={oc['max_abs_diff_pct']:.4f}pp corr={oc['corr']:.5f} model p50={oc['model_p50_pct']:.3f}% max={oc['model_max_pct']:.3f}%"))
    print("\ntop lech (shift_sd):")
    print(f"{'feature':<24}{'live_p50':>12}{'devw_p50':>12}{'shift_sd':>10}{'qmax_rel':>10}{'tail_rt':>9}{'nan%':>7}")
    for r in res["feature_table"][:8]:
        print(f"{r['feature']:<24}{r['live_p50']:>12.6g}{r['devw_p50']:>12.6g}{r['shift_sd']:>10.2f}"
              f"{r['qmax_rel']:>10.2f}{r['tail_ratio']:>9.3f}{100*r['live_nan']:>7.1f}")
    print("NGHI PHAM:", ", ".join(res["suspects"]) or "(khong)")
    print("CUT-DUOI (tail_ratio<0.5):", ", ".join(res["cut_suspects"]) or "(khong)")
    print("HANG SO live:", ", ".join(res["constant_features"]) or "(khong)")
    sb = res.get("same_band_exploratory", {})
    if sb and "error" not in sb and "top" in sb:
        print(f"\n[EXPLORATORY] live vs DEV rows cung dai p15={sb['band_pct']:.2f}% ({sb['dev_window']}, n_band={sb['n_band']}):")
        for r in sb["top"]:
            print(f"  {r['feature']:<24} live_mean={r['live_mean']:>12.6g} dev_band_mean={r['dev_band_mean']:>12.6g} shift_sd_band={r['shift_sd_band']:.2f}")
    if a.out_json:
        with open(a.out_json, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
