# [HO3b 2026-10-10] FUND_REBUILD (ADDENDUM-4 §4b/§4b-bis): funding.bin tren LUOI market.bin moi (DS hien tai).
#   Ban ghi ts < SEAL7: COPY nguyen byte funding.bin bundle. Ban ghi ts >= SEAL7: logic ho1_funding_build
#   (bins PREDWF co md5 = manifest, forwardFill stale 15', trim ts < end). Assert: phut co o ca funding cu VA luoi moi
#   => trung byte; phut cu vang mat chi khi khong co trong luoi moi. Khong dat => DUNG truoc sim.
_FR = CFG.get("fund_rebuild") or {}
if _FR:
    import struct as _st, numpy as _np, hashlib as _hf
    _seal7 = int(_FR["seal7"])
    _mf = {}
    for _ln in open(os.path.join(DS, "manifest.txt")):
        if _ln.startswith("predictWf."):
            _k, _v = _ln.strip()[len("predictWf."):].split("=", 1)
            _mf[_k] = _v.split(";")[0].split(":")[1]
    _bins = sorted(glob.glob(PREDWF + "/predict_wf_*.bin"))
    _bn = [os.path.basename(b) for b in _bins]
    _need = [n for n in _FR["need_bins"]]
    if any(n not in _bn for n in _need) or any(n not in _mf for n in _bn):
        LOG.error("FUND_REBUILD_FAIL bins %s need %s", _bn, _need); sys.exit(1)
    _DT = _np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
    _T, _E = [], []
    for _b in _bins:
        if os.path.basename(_b) not in _need:
            continue
        if _md5(_b) != _mf[os.path.basename(_b)]:
            LOG.error("FUND_REBUILD_FAIL md5 %s", _b); sys.exit(1)
        _a = _np.fromfile(_b, dtype=_DT)
        _ts = _a["ts"].astype(_np.int64)
        _p = _a["p0"].astype(_np.float32)
        _ok = ~_np.isnan(_p)
        _sc = (_np.float32(1.0) - _p[_ok]).astype(_np.float32)
        _T.append(_ts[_ok])
        _E.append((_a["sym"][_ok].astype(_np.int64) << 32) | _sc.view(_np.uint32).astype(_np.int64))
    _T, _E = _np.concatenate(_T), _np.concatenate(_E)
    _o = _np.argsort(_T, kind="stable"); _T, _E = _T[_o], _E[_o]
    _u, _s0, _cnt = _np.unique(_T, return_index=True, return_counts=True)
    _EB = _E.astype(">i8").tobytes()
    with open(os.path.join(DS, "market.bin"), "rb") as _f:
        _nm = _st.unpack(">i", _f.read(4))[0]
        _ma = _np.frombuffer(_f.read(20 * _nm), dtype=_np.dtype([("ts", ">i8"), ("v", "V12")]))
    _grid = _ma["ts"].astype(_np.int64)
    if not (_np.diff(_grid) > 0).all():
        LOG.error("FUND_REBUILD_FAIL market ts khong tang"); sys.exit(1)
    _g7 = _grid[_grid >= _seal7]
    _j = _np.searchsorted(_u, _g7, side="right") - 1
    _valid = _j >= 0
    _stale = _valid & ((_g7 - _u[_np.clip(_j, 0, None)]) > 15 * 60000)
    _keep = _valid & ~_stale & (_g7 < int(_FR["end"]))
    _oldf = os.path.realpath(os.path.join(DS, "funding.bin"))
    _oraw = open(_oldf, "rb").read()
    _n_old = _st.unpack_from(">i", _oraw, 0)[0]
    _p, _npre = 4, 0
    while _p < len(_oraw):
        _t, _c = _st.unpack_from(">qi", _oraw, _p)
        if _t >= _seal7:
            break
        _p += 12 + 8 * _c
        _npre += 1
    _off7 = _p
    _ro = {}
    while _p < len(_oraw):
        _t, _c = _st.unpack_from(">qi", _oraw, _p)
        _ro[_t] = _oraw[_p:_p + 12 + 8 * _c]
        _p += 12 + 8 * _c
    if _npre + len(_ro) != _n_old:
        LOG.error("FUND_REBUILD_FAIL dem funding cu %d+%d != %d", _npre, len(_ro), _n_old); sys.exit(1)
    _newf = "/tmp/ho3b_fund/funding.bin"
    os.makedirs(os.path.dirname(_newf), exist_ok=True)
    _rn = {}
    _nnew = int(_keep.sum())
    with open(_newf, "wb") as _fo:
        _fo.write(_st.pack(">i", _npre + _nnew))
        _fo.write(_oraw[4:_off7])
        for _t, _jj in zip(_g7[_keep].tolist(), _j[_keep].tolist()):
            _b = _st.pack(">qi", _t, int(_cnt[_jj])) + _EB[_s0[_jj] * 8:(_s0[_jj] + _cnt[_jj]) * 8]
            _fo.write(_b)
            _rn[_t] = _b
    del _oraw
    LOG.info("FUND_REBUILD prefix_rec=%d new_rec=%d before_first=%d stale=%d off_seal7=%d", _npre, _nnew,
             int((~_valid).sum()), int(_stale.sum()), _off7)
    _pre_ok = True
    _miss = [t for t in _ro if t not in _rn]
    _diff = [t for t in _ro if t in _rn and _rn[t] != _ro[t]]
    _extra = len(_rn) - (len(_ro) - len(_miss))
    LOG.info("FUND_REBUILD_CHECK h1_old=%d h1_new=%d old_missing=%d old_diff=%d new_extra=%d",
             len(_ro), len(_rn), len(_miss), len(_diff), _extra)
