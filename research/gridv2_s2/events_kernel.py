"""events_kernel.py - KERNEL KAGGLE xuat DANH SACH SU KIEN cho GRIDV2 S2 bang CODE S1 DA GHIM (klite, kref, stats, runner_kaggle
sha theo PREREG_GRIDV2_S1_ADD1 muc 3), KHONG sua / monkeypatch code S1.

Moi shard (GRIDV2S2_SHARD = i/5, chia symbol nhu S1: crc32(sym) mod 5): goi dung chuoi ham cua runner_kaggle.run() (find_inputs
allowlist 7 dataset, pass1, V0a/V0b, V2, build_tiers, cross_section, load_funding + V6, market_context) roi process_symbol(...,
collect_units=True) cho MOI symbol (y het lan chay S1), trich cac don vi thuoc o 20 = S_COND_A_c0.2_k2 (ck (0.2, 2), memb[20]) va xuat:
  events_s{i}.parquet   : 1 dong / don vi (BUY va SELL rieng): sym, day, date, t0_ms, side, m0, d, sigma_1d, tick, L, X, tier, s_hat,
                          slip, W, T, dl_end_ms, first_ms + ket qua S1 tung don vi duoi K_OPT (o_*) va K_PESS (p_*): filled, excl,
                          ok, f_ms, x_ms, kind, xpx, gross, fee, slipc, fund, net, n_maker.
  kline_win_s{i}.parquet: nen 1m LAKE (valid, O/H/L/C) cho moi phut trong [t0 - 61, t0 + W + T + 61] cua moi don vi (W2/W3).
  funding_ev_s{i}.parquet: moc funding (sym, ts, rate) trong cua so cac don vi.
  validate_s{i}.json / manifest_s{i}.json: V0a, V0b, V1, V2, V3 (feat pass1 = pass2), V6, E1a (tong theo ngay cua don vi trich ==
                          bang agg cua chinh process_symbol cho o 20, ca 2 mo hinh), sha code, sha input.
Che do:
  python3 events_kernel.py run                      (trong kernel; doc GRIDV2S2_INPUT=/kaggle/input, GRIDV2S2_OUT=/kaggle/working)
  python3 events_kernel.py build OUT_DIR S1_CODE_DIR (tao 5 thu muc kernel: wrapper nhung code ghim base64 + kiem sha; KHONG push)
"""
import base64
import hashlib
import json
import logging
import os
import sys
import time
import zlib

log = logging.getLogger("events_kernel")
CELL_ID = 20
CK_INDEX = 2
CELL_NAME = "S_COND_A_c0.2_k2"
S1_SHA = {"klite.py": "196f458489c5a808754d4afc39c2ad03f9149d57936de7f84c810074b8652680",
          "kref.py": "6de0e412633658f1d548d28c7a650ff9b0e43b1a5f6cc3e64dbe93c51c928ff2",
          "stats.py": "975f3a427cd52750018d615b664ab13f899ee216764e5f80fca82192976df3e4",
          "runner_kaggle.py": "23a788cf97f69c73aec663572d0f133136e6e872eb64c8251b9641ba0dd14ccf"}
DATASETS = ["chuyendinh/vz-kline1m-%d" % y for y in range(2021, 2026)] + ["chuyendinh/gridp-t1-funding", "chuyendinh/gridp-lifecycle"]
N_SHARDS = 5


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def extract_units(R_, klite, s, res, ctx, nday):
    """Trich don vi o 20 tu res['units'][(2, model)] (khong tinh lai mo phong). Tra (dict cot, kiem E1a)."""
    import numpy as np
    out = None
    e1 = dict(ok=True, n_days=0, max_abs=0.0)
    for model, pre in (("OPT", "o_"), ("PESS", "p_")):
        key = (CK_INDEX, model)
        if key not in res["units"]:
            return None, e1
        u = res["units"][key]
        m = u["memb"].get(CELL_ID)
        if m is None or not m.any():
            return None, e1
        idx = np.flatnonzero(m)
        Rm = u["R"]
        if out is None:
            side = u["side"][idx].astype(np.int64)
            d = u["d"][idx]
            tick = u["tick"][idx]
            Lb, Ls = Rm["Lb"][idx], Rm["Ls"][idx]
            X = np.where(side == 1, klite.ceil_tick(Lb * (1 + d), tick), klite.floor_tick(Ls * (1 - d), tick))
            D = u["D"][idx]
            tier = ctx["tier"][D].astype(np.int64)
            out = dict(t0_min=u["t0"][idx].astype(np.int64), side=side, m0=Rm["m0"][idx], d=d, sigma_1d=d / 0.2, tick=tick,
                       L=np.where(side == 1, Lb, Ls), X=X, tier=tier, slip=u["slip"][idx], day=D.astype(np.int64),
                       W=np.full(idx.size, u["T"], np.int64), T=np.full(idx.size, u["T"], np.int64))
        else:
            assert np.array_equal(out["t0_min"], u["t0"][idx]) and np.array_equal(out["side"], u["side"][idx])
        fl = Rm["filled"][idx]
        assert np.allclose(np.where(fl, Rm["X"][idx], 0.0), np.where(fl, out["X"], 0.0), rtol=0, atol=0)
        ok = u["ok"][idx]
        out[pre + "filled"] = fl.astype(np.int64)
        out[pre + "excl"] = Rm["excl"][idx].astype(np.int64)
        out[pre + "ok"] = ok.astype(np.int64)
        out[pre + "f_ms"] = np.where(Rm["f"][idx] >= 0, R_.DATA_START + Rm["f"][idx] * R_.MIN, -1)
        out[pre + "x_ms"] = np.where(Rm["x"][idx] >= 0, R_.DATA_START + Rm["x"][idx] * R_.MIN, -1)
        out[pre + "kind"] = Rm["kind"][idx].astype(np.int64)
        for c, c2 in (("xpx", "xpx"), ("gross", "gross"), ("fee", "fee"), ("slip", "slipc"), ("fund", "fund"), ("net", "net")):
            out[pre + c2] = Rm[c][idx]
        out[pre + "n_maker"] = Rm["n_maker"][idx].astype(np.int64)
        # E1a: tong theo ngay cua don vi trich == bang agg (o 20) cua chinh process_symbol
        ag = res["agg"]
        ag = ag[(ag.cell == CELL_ID) & (ag.model == model)].set_index("day")
        Du = out["day"]
        mine = dict(place=np.bincount(Du, minlength=nday).astype(float),
                    fill=np.bincount(Du, weights=ok.astype(float), minlength=nday),
                    net=np.bincount(Du, weights=np.where(ok, Rm["net"][idx], 0.0), minlength=nday),
                    gross=np.bincount(Du, weights=np.where(ok, Rm["gross"][idx], 0.0), minlength=nday))
        days = np.flatnonzero(mine["place"] > 0)
        if set(days.tolist()) != set(ag.index.astype(int).tolist()):
            e1["ok"] = False
        for c in ("place", "fill", "net", "gross"):
            ref = ag.reindex(days)[c].to_numpy(float)
            dif = np.nanmax(np.abs(ref - mine[c][days])) if days.size else 0.0
            e1["max_abs"] = max(e1["max_abs"], float(dif))
            if not np.isfinite(dif) or dif > 1e-6:
                e1["ok"] = False
        e1["n_days"] += int(days.size)
    return out, e1


def run_events(test_overrides=None):
    """test_overrides CHI cho test noi bo (tham so ham, khong co duong vao tu CLI / env): registry, mkt_sym, cond.
    Khi co: manifest prereg_constants = False va run_s2 tu choi shard (tru allow_test)."""
    import numpy as np
    import pandas as pd
    W_ = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, W_)
    for f, h in S1_SHA.items():
        got = sha256_file(os.path.join(W_, f))
        if got != h:
            raise RuntimeError("sha code S1 %s %s != ghim %s - DUNG" % (f, got, h))
    import runner_kaggle as R_
    import klite
    R_.check_env()
    tov = dict(test_overrides or {})
    registry = {int(k): v for k, v in tov.get("registry", R_.REGISTRY_REAL).items()}
    mkt_sym = tov.get("mkt_sym", R_.MARKET_SYM)
    CP = R_.cond_params(tov.get("cond"))
    inp = os.environ.get("GRIDV2S2_INPUT", "/kaggle/input")
    out = os.environ.get("GRIDV2S2_OUT", "/kaggle/working")
    os.makedirs(out, exist_ok=True)
    si, sk = [int(x) for x in os.environ.get("GRIDV2S2_SHARD", "0/5").split("/")]
    assert sk == N_SHARDS and 0 <= si < sk
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.path.join(out, "run_s%d.log" % si))],
                        force=True)
    t_start = time.time()
    assert R_.cells()[CELL_ID]["name"] == CELL_NAME and R_.CK_ALL[CK_INDEX] == (0.2, 2)
    assert R_.COND_PREREG == {"A": dict(z=2.5, vmult=3.0), "B": dict(ratio=1.5)} and R_.MARKET_SYM == "BTCUSDT"
    VS = R_.V()
    kl, fu, lpath = R_.find_inputs(inp)
    nday = (R_.SEAL - R_.DATA_START) // R_.DAY
    meta, meta_file = {}, {}
    import pyarrow.parquet as pq
    for (y, mo), p in kl.items():
        meta_file[(y, mo)] = pq.ParquetFile(p).metadata.num_rows
        meta[y] = meta.get(y, 0) + meta_file[(y, mo)]
    life = R_.load_life(lpath)
    qv, act, hc, rows = R_.pass1(kl, VS, nday)
    ok0a, ok0b, d0b = R_.v0_eval(meta_file, VS.v["V0"].get("files_opened", []), rows, registry,
                                R_.V0_SKIP_EXPECTED_REAL if registry == R_.REGISTRY_REAL else None)
    ok2, mx2, fr2 = R_.v2_eval(VS.v["V2"]["by_year"])
    if not ok2:
        raise RuntimeError("V2 FAIL - DUNG")
    tiers = R_.build_tiers(qv, act, life, nday)
    thr, er_p1, sg_p1 = R_.cross_section(tiers, hc, nday)
    syms = sorted(tiers)
    mine = [s for s in syms if zlib.crc32(s.encode()) % sk == si]
    log.info("universe %d sym, shard %d/%d -> %d sym", len(syms), si, sk, len(mine))
    v6frames = {}
    fund = R_.load_funding(fu, set(mine) | {mkt_sym}, v6frames)
    ok6, d6 = R_.v6_eval(v6frames)
    if not ok6:
        raise RuntimeError("V6 FAIL - DUNG")
    mkt = None
    if mkt_sym in qv:
        arrm = R_.load_symbol(kl, mkt_sym, nday)
        mkt = R_.market_context(arrm, R_.delist_index(mkt_sym, life, arrm[5]), nday)
    ev_parts, kw_parts, fu_parts = [], [], []
    feat_mism, e1_all = 0, dict(ok=True, n_days=0, max_abs=0.0, n_sym=0)
    for n_i, s in enumerate(mine):
        arr = R_.load_symbol(kl, s, nday)
        dl = R_.delist_index(s, life, arr[5])
        ctx = dict(nday=nday, tier=tiers[s], qvd=qv[s], fund=fund.get(s), dl=dl, first_ms=life[s]["first"], mkt=mkt,
                   mkt_sym=mkt_sym, thr=thr, CP=CP, er_p1=er_p1[s], sig_p1=sg_p1[s])
        res = R_.process_symbol(s, arr, ctx, collect_units=True)
        feat_mism += int(res["aux"]["feat_mismatch"])
        cols, e1 = extract_units(R_, klite, s, res, ctx, nday)
        if cols is None:
            continue
        e1_all["ok"] = e1_all["ok"] and e1["ok"]
        e1_all["n_days"] += e1["n_days"]
        e1_all["max_abs"] = max(e1_all["max_abs"], e1["max_abs"])
        e1_all["n_sym"] += 1
        feat = klite.daily_features(res["aux"]["G"], nday)
        spr = R_.shat_exante(feat["spread"])
        sh = R_.shat_fill(spr[cols["day"]], cols["tier"])
        slip_chk = np.maximum(np.array([klite.SLIP_TIER_FLOOR[int(t)] for t in cols["tier"]]), sh / 2.0)
        if not np.allclose(slip_chk, cols["slip"], rtol=0, atol=1e-15):
            raise RuntimeError("s_hat tinh lai khong khop truot S1 (%s) - DUNG" % s)
        df = pd.DataFrame(cols)
        df.insert(0, "sym", s)
        df["s_hat"] = sh
        df["t0_ms"] = R_.DATA_START + df.t0_min * R_.MIN
        df["date"] = pd.to_datetime(R_.DATA_START + df.day * R_.DAY, unit="ms").dt.strftime("%Y-%m-%d")
        df["dl_end_ms"] = (R_.DATA_START + (dl + 1) * R_.MIN) if dl >= 0 else -1
        df["first_ms"] = life[s]["first"]
        ev_parts.append(df)
        n = arr[5].size
        mask = np.zeros(n, bool)
        for a, w, t in zip(df.t0_min.to_numpy(), df.W.to_numpy(), df["T"].to_numpy()):
            mask[max(a - 61, 0):min(a + w + t + 62, n)] = True
        mi = np.flatnonzero(mask)
        v = arr[5][mi]
        kw_parts.append(pd.DataFrame(dict(sym=s, mi=mi.astype(np.int64), valid=v, o=np.where(v, arr[0][mi], np.nan),
                                          h=np.where(v, arr[1][mi], np.nan), l=np.where(v, arr[2][mi], np.nan),
                                          c=np.where(v, arr[3][mi], np.nan))))
        fs = fund.get(s)
        if fs is not None:
            ts = fs[0]
            lo = R_.DATA_START + df.t0_min.to_numpy() * R_.MIN
            hi = lo + (df.W.to_numpy() + df["T"].to_numpy() + 2) * R_.MIN
            keep = np.zeros(ts.size, bool)
            for a, b in zip(lo, hi):
                i0, i1 = np.searchsorted(ts, [a, b], "right")
                keep[i0:i1] = True
            fu_parts.append(pd.DataFrame(dict(sym=s, ts=ts[keep].astype(np.int64), rate=fs[1][keep])))
        log.info("sym %s (%d/%d) units %d %.0fs", s, n_i + 1, len(mine), len(df), time.time() - t_start)
    ev = pd.concat(ev_parts, ignore_index=True) if ev_parts else pd.DataFrame()
    assert len(ev) == 0 or (ev.t0_ms.max() < R_.SEAL)
    ev.to_parquet(os.path.join(out, "events_s%d.parquet" % si), index=False)
    (pd.concat(kw_parts, ignore_index=True) if kw_parts else pd.DataFrame(
        dict(sym=pd.Series(dtype=str), mi=pd.Series(dtype=np.int64), valid=pd.Series(dtype=bool), o=pd.Series(dtype=float),
             h=pd.Series(dtype=float), l=pd.Series(dtype=float), c=pd.Series(dtype=float)))).to_parquet(os.path.join(out, "kline_win_s%d.parquet" % si), index=False,
                                                      compression="zstd")
    (pd.concat(fu_parts, ignore_index=True) if fu_parts else pd.DataFrame(columns=["sym", "ts", "rate"])).to_parquet(
        os.path.join(out, "funding_ev_s%d.parquet" % si), index=False)
    v = VS.v
    val = dict(V0a=ok0a, V0b=ok0b, V0b_detail=d0b, V1_ok=(not v["V1"]["bad"]) and v["V1"]["ts_max"] is not None
               and v["V1"]["ts_max"] < R_.SEAL, V2_ok=ok2, V2_max_bad_frac=mx2, V3_feat_mismatch_days=feat_mism, V6_ok=ok6,
               E1a=e1_all)
    val["all_pass"] = bool(ok0a and ok0b and val["V1_ok"] and ok2 and feat_mism == 0 and ok6 and e1_all["ok"])
    man = dict(shard="%d/%d" % (si, sk), n_sym=len(mine), n_units=int(len(ev)), cell=CELL_NAME, prereg_constants=not tov,
               cond=CP, mkt_sym=mkt_sym,
               code={f: sha256_file(os.path.join(W_, f)) for f in list(S1_SHA) + ["events_kernel.py"]},
               inputs={os.path.basename(p): sha256_file(p) for p in [lpath] + list(fu.values())},
               seconds=round(time.time() - t_start, 1))
    json.dump(val, open(os.path.join(out, "validate_s%d.json" % si), "w"), indent=1, default=str)
    json.dump(man, open(os.path.join(out, "manifest_s%d.json" % si), "w"), indent=1, default=str)
    log.info("XONG all_pass=%s units=%d %.0fs", val["all_pass"], len(ev), time.time() - t_start)
    if not val["all_pass"]:
        raise RuntimeError("validate FAIL: %s" % {k: v_ for k, v_ in val.items() if k != "V0b_detail"})


WRAP = '''"""GRIDV2_S2 events wrapper shard %(i)d/5 - KHONG logic tinh toan. Ghi code ghim (base64), kiem sha256, goi events_kernel."""
import base64
import hashlib
import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%%(asctime)s WRAP %%(message)s")
log = logging.getLogger("wrap")
W = "/kaggle/working"
EXPECTED = %(exp)s
BLOBS = %(blobs)s
os.makedirs(W, exist_ok=True)
for name in sorted(BLOBS):
    path = os.path.join(W, name)
    with open(path, "wb") as fh:
        fh.write(base64.b64decode(BLOBS[name]))
    got = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if got != EXPECTED[name]:
        log.error("SHA MISMATCH %%s", name)
        sys.exit(1)
    log.info("sha ok %%s %%s", name, got)
env = dict(os.environ)
env["GRIDV2S2_SHARD"] = "%(i)d/5"
rc = subprocess.run([sys.executable, os.path.join(W, "events_kernel.py"), "run"], env=env, cwd=W).returncode
log.info("events_kernel exit %%d", rc)
sys.exit(rc)
'''


def build(out_dir, s1dir):
    exp, blobs = {}, {}
    for f, h in S1_SHA.items():
        b = open(os.path.join(s1dir, f), "rb").read()
        if hashlib.sha256(b).hexdigest() != h:
            raise RuntimeError("sha S1 %s khong khop ghim" % f)
        exp[f], blobs[f] = h, base64.b64encode(b).decode("ascii")
    me = open(os.path.abspath(__file__), "rb").read()
    exp["events_kernel.py"] = hashlib.sha256(me).hexdigest()
    blobs["events_kernel.py"] = base64.b64encode(me).decode("ascii")
    shas = {}
    for i in range(N_SHARDS):
        name = "gridv2-s2-events%d" % i
        d = os.path.join(out_dir, "kernel_e%d" % i)
        os.makedirs(d, exist_ok=True)
        src = WRAP % dict(i=i, exp=json.dumps(exp, indent=1), blobs=json.dumps(blobs, indent=1))
        open(os.path.join(d, name + ".py"), "w").write(src)
        meta = {"id": "chuyendinh/" + name, "title": name, "code_file": name + ".py", "language": "python",
                "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
                "enable_internet": False, "dataset_sources": DATASETS, "competition_sources": [], "kernel_sources": []}
        json.dump(meta, open(os.path.join(d, "kernel-metadata.json"), "w"), indent=1)
        shas[name] = hashlib.sha256(src.encode()).hexdigest()
    json.dump(dict(code=exp, wrappers=shas), open(os.path.join(out_dir, "kernels_sha.json"), "w"), indent=1)
    return exp, shas


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "run":
        run_events()
    elif len(sys.argv) == 4 and sys.argv[1] == "build":
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        log.info("%s", build(sys.argv[2], sys.argv[3]))
    else:
        raise SystemExit(__doc__)
