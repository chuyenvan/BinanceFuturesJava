    _gset = set(_grid.tolist())
    _miss_bad = [t for t in _miss if t in _gset]
    LOG.info("FUND_REBUILD_CHECK old_missing_not_in_new_grid=%d old_missing_in_grid=%d", len(_miss) - len(_miss_bad), len(_miss_bad))
    if not _pre_ok or _miss_bad or _diff:
        LOG.error("FUND_REBUILD_FAIL"); sys.exit(1)
    del _rn, _ro
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
            _ml2.append("fundingCount=%d\n" % (_npre + _nnew))
        elif _ln.startswith("marketCount="):
            _ml2.append("marketCount=%d\n" % _nm)
        else:
            _ml2.append(_ln)
    assert _nr2 == 1, _nr2
    with open(os.path.join(_ovf, "manifest.txt"), "w") as _f:
        _f.writelines(_ml2)
    LOG.info("FUND_REBUILD_OK md5_funding=%s -> WFO_DATA_DIR %s", FUND_MD5_NEW, _ovf)
    DS = _ovf
