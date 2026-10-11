"""HO4-P1 ADDENDUM-7(a): do anh huong 8 cap id mapper trung (843-850) o MUC FEATURE (khong sim).
Kernel exporter = ho4p1_exp_kernel.KX + 3 hook (chi them, khong doi buoc cu):
  - dup_pairs: so phut ca 2 symbol cung co kline (sau luat settle-tail) cho moi cap;
  - pre0=remap_dups: ghi lai symbol_mapper/global_id_map trong Aerospike RIENG cua kernel, cap id moi
    (max+1..) cho symbol thu 2 cua moi cap (A = mapper goc, B = mapper khong trung);
  - dupfx: so sanh gateA vs gateB (chuoi CSV chinh xac, tung cot) + md5 market A vs B.
Usage: python3 ho4p1_dupfx.py submit|status|fetch"""
import importlib.util, json, logging, os, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("dupfx")
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/"
W = "/home/ubuntu/claude_master/1011/ho4p1/"
TAG = "ho4p1-dupfx"
PAIRS = [["MUUUSDT", "XBIUSDT"], ["BNCUSDT", "SOXSUSDT"], ["FWDIUSDT", "TZAUSDT"], ["MINIMAXUSDT", "VRTUSDT"],
         ["SNOWUSDT", "ZHIPUUSDT"], ["APPUSDT", "SHAZUSDT"], ["GEVUSDT", "SOFIUSDT"], ["PANWUSDT", "SKHYUSDT"]]
_sp = importlib.util.spec_from_file_location("ho4p1_exp_kernel", A + "ho4p1_exp_kernel.py")
EK = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(EK)
H1A = 'del KL                                           # giai phong RAM'
H1 = '''if CFG.get("dupfx"):                             # ADDENDUM-7(a): phut ca 2 symbol cua cap id trung cung co kline
    _P = {}
    for _a, _b in CFG["dupfx"]["pairs"]:
        _ta = KL[_a][0] if _a in KL else np.zeros(0, np.int64)
        _tb = KL[_b][0] if _b in KL else np.zeros(0, np.int64)
        _P[_a + "/" + _b] = dict(n_a=int(len(_ta)), n_b=int(len(_tb)), both=int(len(np.intersect1d(_ta, _tb))),
                                 first_a=int(_ta[0]) if len(_ta) else None, first_b=int(_tb[0]) if len(_tb) else None)
    RES["steps"]["dup_pairs"] = _P
    LOG.info("DUP_PAIRS %s", _P)
'''
H2A = '    if t.get("pre") == "truncate_market":       # HO4b'
H2 = '''    if t.get("pre0") == "remap_dups":           # ADDENDUM-7(a): B = mapper khong trung (chi trong Aerospike kernel)
        _k = ("test", "symbol_mapper", "global_id_map")
        _m = {str(s): int(i) for s, i in dict(CL.get(_k)[2]["data"]).items()}
        _by = {}
        for _s, _i in _m.items():
            _by.setdefault(_i, []).append(_s)
        _nx, _rm = max(_m.values()), {}
        for _i in sorted(_by):
            for _s in sorted(_by[_i])[1:]:
                _nx += 1
                _m[_s] = _nx
                _rm[_s] = [_i, _nx]
        CL.put(_k, {"data": _m}, policy=WP)
        RES["steps"]["remap_dups"] = _rm
        LOG.info("REMAP_DUPS %s", _rm)
'''
H3A = '''try:
    CL.close()
except Exception:
    pass
asp.terminate()'''
H3 = '''if CFG.get("dupfx"):                             # ADDENDUM-7(a): gateA (mapper goc) vs gateB (khong trung)
    try:
        import pandas as pd
        _ga = pd.read_csv(OUTD + "/gate/gateA.csv.gz", dtype=str, keep_default_na=False)
        _gb = pd.read_csv(OUTD + "/gate/gateB.csv.gz", dtype=str, keep_default_na=False)
        _tc = _ga.columns[0]
        _mg = _ga.merge(_gb, on=_tc, how="outer", suffixes=("_a", "_b"), indicator=True)
        _bo = _mg[_mg["_merge"] == "both"].reset_index(drop=True)
        _ts = _bo[_tc].astype("int64").to_numpy()
        D = dict(rows=[len(_ga), len(_gb)], only_a=int((_mg["_merge"] == "left_only").sum()),
                 only_b=int((_mg["_merge"] == "right_only").sum()), n_cols=len(_ga.columns) - 1, cols={})
        _any = np.zeros(len(_bo), bool)
        for c in _ga.columns[1:]:
            _d = (_bo[c + "_a"] != _bo[c + "_b"]).to_numpy()
            if _d.any():
                _x = pd.to_numeric(_bo[c + "_a"][_d], errors="coerce").to_numpy(float)
                _y = pd.to_numeric(_bo[c + "_b"][_d], errors="coerce").to_numpy(float)
                _ad = np.abs(_x - _y)
                _sc = np.nanmedian(np.abs(pd.to_numeric(_bo[c + "_a"], errors="coerce").to_numpy(float)))
                D["cols"][c] = dict(n=int(_d.sum()), first_ts=int(_ts[_d][0]),
                                    med_abs=float(np.nanmedian(_ad)) if np.isfinite(_ad).any() else None,
                                    max_abs=float(np.nanmax(_ad)) if np.isfinite(_ad).any() else None,
                                    col_med_abs=float(_sc) if np.isfinite(_sc) else None)
            _any |= _d
        D["n_rows_diff"] = int(_any.sum())
        D["n_cols_diff"] = len(D["cols"])
        D["first_diff_ts"] = int(_ts[_any][0]) if _any.any() else None
        _mon = {}
        for t_ in _ts[_any]:
            k_ = datetime.datetime.fromtimestamp(t_ / 1000, TZ7).strftime("%Y-%m")
            _mon[k_] = _mon.get(k_, 0) + 1
        D["rows_diff_by_month"] = _mon
        D["rows_by_month"] = {}
        for t_ in _ts:
            k_ = datetime.datetime.fromtimestamp(t_ / 1000, TZ7).strftime("%Y-%m")
            D["rows_by_month"][k_] = D["rows_by_month"].get(k_, 0) + 1
        D["market_md5"] = [md5f(OUTD + "/market_A.bin"), md5f(OUTD + "/market_B.bin")]
        D["gate_md5"] = [md5f(OUTD + "/gate/gateA.csv.gz"), md5f(OUTD + "/gate/gateB.csv.gz")]
        RES["steps"]["dupfx"] = D
        LOG.info("DUPFX rows_diff=%d cols_diff=%d/%d market_eq=%s", D["n_rows_diff"], D["n_cols_diff"], D["n_cols"],
                 D["market_md5"][0] == D["market_md5"][1])
    except Exception as e:  # noqa: BLE001
        RES["steps"]["dupfx"] = dict(error=repr(e))
        LOG.error("DUPFX loi %r", e)
    save()
'''


def kx():
    s = EK.KX
    for a, b in ((H1A, H1 + H1A), (H2A, H2 + H2A), (H3A, H3 + H3A)):
        assert s.count(a) == 1, a[:60]
        s = s.replace(a, b)
    return s


def cfg():
    c = json.load(open(W + "cfg_ho4p1-x26-q3.json"))
    c["tag"] = TAG
    c["ingest"] = ["20260701", "20261003"]
    mk = dict(cls="com.binance.chuyennd.research.ExportMarketData2File", args=[], mkdirs=[], cfg={"TIME_RUN": "20260701"},
              post="market", timeout_s=7200)
    gt = dict(cls="com.binance.chuyennd.ai_ml.features.export.gate.ExportGateDataset", mkdirs=["@OUT/gate"])
    c["tasks"] = [dict(mk, name="mktA", out_glob="market_A.bin", dump="market_A.bin", mkey="A"),
                  dict(gt, name="gateA", args=["20260710", "20261001", "@OUT/gate/gateA.csv.gz"], out_glob="gate/gateA*"),
                  dict(mk, name="mktB", out_glob="market_B.bin", dump="market_B.bin", mkey="B",
                       pre0="remap_dups", pre="truncate_market"),
                  dict(gt, name="gateB", args=["20260710", "20261001", "@OUT/gate/gateB.csv.gz"], out_glob="gate/gateB*")]
    c["dupfx"] = {"pairs": PAIRS}
    return c


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd in ("submit", "dry"):
        p = W + "cfg_%s.json" % TAG
        json.dump(cfg(), open(p, "w"), indent=1)
        EK.KX = kx()
        compile(EK.KX, "kx", "exec")
        log.info("cfg %s, KX %d bytes", p, len(EK.KX))
        if cmd == "submit":
            EK.submit(p)
    elif cmd == "status":
        EK.status(TAG)
    elif cmd == "fetch":
        EK.fetch(TAG, r"^(result\.json|.*\.log)$")
