# [HO4-P1 2026-10-11] TICKER_HO4P1 (ADDENDUM-6 §6.5): ticker 2026 dung tu Vision (kernel copy) — md5 RAW (giai nen neu .gz)
#   phai == ticker_raw_md5.json cua kernel exporter quy: du 100%, 0 sai/thieu/thua; KHONG file ticker_2026* nao tu nguon khac.
_TK = CFG.get("tk_ho4p1") or {}
if _TK:
    import gzip as _gz
    _want = _TK["md5"]
    _all26 = [p for p in glob.glob(IN + "/**/ticker_2026*", recursive=True) if os.path.isfile(p)]
    _mine = {}
    for _p in _all26:
        if ("/" + _TK["src"] + "/") in _p:
            _mine[os.path.basename(_p).replace(".gz", "")] = _p
    _other = [p for p in _all26 if ("/" + _TK["src"] + "/") not in p]
    def _rawmd5(_p):
        _d = _gz.open(_p).read() if _p.endswith(".gz") else open(_p, "rb").read()
        return _h3.md5(_d).hexdigest()
    _tok = [n for n in sorted(_want) if n in _mine and _rawmd5(_mine[n]) == _want[n]]
    _tbad = [n for n in sorted(_want) if n in _mine and n not in _tok]
    _tmiss = [n for n in sorted(_want) if n not in _mine]
    _textra = sorted(n for n in _mine if n not in _want)
    LOG.info("TICKER_HO4P1 ok=%d bad=%d miss=%d extra=%d other=%d bad_list=%s miss_list=%s", len(_tok), len(_tbad), len(_tmiss),
             len(_textra), len(_other), _tbad[:5], _tmiss[:5])
    if len(_tok) != len(_want) or _tbad or _tmiss or _textra or _other:
        LOG.error("TICKER_HO4P1_FAIL")
        sys.exit(1)
