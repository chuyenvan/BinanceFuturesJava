# [HO4 2026-10-10] FUND_REBUILD_HO4 (ADDENDUM-5 §5.3 cong sim): funding.bin tren LUOI market.bin moi (DS hien tai).
#   ts < S_LO va ts >= S_HI: COPY nguyen byte funding.bin bundle. ts in [S_LO, S_HI): logic ho1_funding_build (bins forwardFill
#   stale 15') voi bins fold 20250701/20251001 DUNG LAI (dataset rieng, md5 theo CFG). TU KIEM truoc: cung logic voi bins DEV
#   (bundle) tren luoi market bundle phai tai hien DUNG BYTE moi ban ghi funding bundle trong S (khong dat => DUNG truoc sim).
_FR = CFG.get("fund_rebuild_ho4") or {}
if _FR:
    import struct as _st, numpy as _np
    _lo, _hi = int(_FR["lo"]), int(_FR["hi"])
    _BD = os.path.dirname(manifest)
    _mf = {}
    for _ln in open(os.path.join(_BD, "manifest.txt")):
        if _ln.startswith("predictWf."):
            _k, _v = _ln.strip()[len("predictWf."):].split("=", 1)
            _mf[_k] = _v.split(";")[0].split(":")[1]
    _DT = _np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
    def _ldb(_paths):
        _T, _E = [], []
        for _b in _paths:
            _a = _np.fromfile(_b, dtype=_DT)
            _ts = _a["ts"].astype(_np.int64); _p = _a["p0"].astype(_np.float32); _ok = ~_np.isnan(_p)
            _sc = (_np.float32(1.0) - _p[_ok]).astype(_np.float32)
            _T.append(_ts[_ok]); _E.append((_a["sym"][_ok].astype(_np.int64) << 32) | _sc.view(_np.uint32).astype(_np.int64))
        _T, _E = _np.concatenate(_T), _np.concatenate(_E)
        _o = _np.argsort(_T, kind="stable"); _T, _E = _T[_o], _E[_o]
        _u, _s0, _cnt = _np.unique(_T, return_index=True, return_counts=True)
        return _u, _s0, _cnt, _E.astype(">i8").tobytes()
    def _recs(_grid, _B):
        _u, _s0, _cnt, _EB = _B
        _j = _np.searchsorted(_u, _grid, side="right") - 1
        _v = _j >= 0
        _keep = _v & ~(_v & ((_grid - _u[_np.clip(_j, 0, None)]) > 15 * 60000))
        _out = {}
        for _t, _jj in zip(_grid[_keep].tolist(), _j[_keep].tolist()):
            _out[_t] = _st.pack(">qi", _t, int(_cnt[_jj])) + _EB[_s0[_jj] * 8:(_s0[_jj] + _cnt[_jj]) * 8]
        return _out
    def _mgrid(_p):
        with open(_p, "rb") as _f:
            _nm = _st.unpack(">i", _f.read(4))[0]
            _g = _np.frombuffer(_f.read(20 * _nm), dtype=_np.dtype([("ts", ">i8"), ("v", "V12")]))["ts"].astype(_np.int64)
        return _g, _nm
    _devb = [os.path.join(PREDWF, _n) for _n in _FR["folds"]]
    for _b in _devb:
        if _md5(_b) != _mf[os.path.basename(_b)]:
            LOG.error("FUND_HO4_FAIL md5 bins DEV %s", _b); sys.exit(1)
    _nbc = [c for c in sorted(glob.glob(IN + "/**/predict_wf_*.bin", recursive=True)) if ("/" + _FR["bins_ds"] + "/") in c]
    _newb = []
    for _n in _FR["folds"]:
        _c = [c for c in _nbc if os.path.basename(c) == _n]
        if not _c or _md5(_c[0]) != _FR["bins_md5"][_n]:
            LOG.error("FUND_HO4_FAIL bins moi %s %s", _n, _c); sys.exit(1)
        _newb.append(_c[0])
    _oldf = os.path.realpath(os.path.join(_BD, "funding.bin"))
    _oraw = open(_oldf, "rb").read()
    _n_old = _st.unpack_from(">i", _oraw, 0)[0]
    _p, _npre = 4, 0
    while _p < len(_oraw):
        _t, _c = _st.unpack_from(">qi", _oraw, _p)
        if _t >= _lo:
            break
        _p += 12 + 8 * _c; _npre += 1
    _offlo = _p
    _ro = {}
    while _p < len(_oraw):
        _t, _c = _st.unpack_from(">qi", _oraw, _p)
        if _t >= _hi:
            break
        _ro[_t] = _oraw[_p:_p + 12 + 8 * _c]; _p += 12 + 8 * _c
    _offhi = _p
    _nsuf = 0
    while _p < len(_oraw):
        _t, _c = _st.unpack_from(">qi", _oraw, _p); _p += 12 + 8 * _c; _nsuf += 1
    if _npre + len(_ro) + _nsuf != _n_old:
        LOG.error("FUND_HO4_FAIL dem %d+%d+%d != %d", _npre, len(_ro), _nsuf, _n_old); sys.exit(1)
    _g0, _ = _mgrid(os.path.join(_BD, "market.bin"))
    _self = _recs(_g0[(_g0 >= _lo) & (_g0 < _hi)], _ldb(_devb))
    _sk = set(_self) == set(_ro); _sd = sum(1 for _t in _ro if _self.get(_t) != _ro[_t])
    LOG.info("FUND_HO4_SELFCHECK keys_equal=%s n_old=%d n_self=%d diff=%d", _sk, len(_ro), len(_self), _sd)
    if not _sk or _sd:
        LOG.error("FUND_HO4_FAIL selfcheck"); sys.exit(1)
    del _self
    _g1, _nm1 = _mgrid(os.path.join(DS, "market.bin"))
    _rn = _recs(_g1[(_g1 >= _lo) & (_g1 < _hi)], _ldb(_newb))
    _newf = "/tmp/ho4_fund/funding.bin"
    os.makedirs(os.path.dirname(_newf), exist_ok=True)
    with open(_newf, "wb") as _fo:
        _fo.write(_st.pack(">i", _npre + len(_rn) + _nsuf))
        _fo.write(_oraw[4:_offlo])
        for _t in sorted(_rn):
            _fo.write(_rn[_t])
        _fo.write(_oraw[_offhi:])
    _ncnt = _npre + len(_rn) + _nsuf
    _same = sum(1 for _t in _ro if _rn.get(_t) == _ro[_t])
    LOG.info("FUND_HO4 prefix=%d S_old=%d S_new=%d S_same_bytes=%d suffix=%d", _npre, len(_ro), len(_rn), _same, _nsuf)
    del _oraw, _ro, _rn
    _ovf = os.path.join(WORK, "wfo_ds_fund")
    os.makedirs(_ovf, exist_ok=True)
    for _nm2 in ("market.bin", "pred.bin"):
        if not os.path.lexists(os.path.join(_ovf, _nm2)):
            os.symlink(os.path.realpath(os.path.join(DS, _nm2)), os.path.join(_ovf, _nm2))
    if not os.path.lexists(os.path.join(_ovf, "funding.bin")):
        os.symlink(_newf, os.path.join(_ovf, "funding.bin"))
    FUND_MD5_NEW = _md5(_newf)
    _ml2, _nr2 = [], 0
    for _ln in open(os.path.join(DS, "manifest.txt")):
        if _ln.startswith("md5_funding="):
            _ml2.append("md5_funding=" + FUND_MD5_NEW + "\n"); _nr2 += 1
        elif _ln.startswith("fundingCount="):
            _ml2.append("fundingCount=%d\n" % _ncnt)
        elif _ln.startswith("marketCount="):
            _ml2.append("marketCount=%d\n" % _nm1)
        else:
            _ml2.append(_ln)
    assert _nr2 == 1, _nr2
    with open(os.path.join(_ovf, "manifest.txt"), "w") as _f:
        _f.writelines(_ml2)
    LOG.info("FUND_HO4_OK md5_funding=%s -> WFO_DATA_DIR %s", FUND_MD5_NEW, _ovf)
    DS = _ovf
