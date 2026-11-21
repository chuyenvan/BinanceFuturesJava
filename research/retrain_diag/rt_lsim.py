#!/usr/bin/env python3
"""[U4a fork rt_nsim.py -> rt_lsim.py, RT_LANE=p|s|m] HO5 luot 2 - Lane L 2026: kernel = run.py r1-a3 (r1_a3_driver.template, CHI import) + va mapper snapshot (ho5_k2.patch)
+ khoi HO5: (M) market.bin = bundle (<SEAL) + market chain-y26 (>=SEAL); (B) A3 bins = 16 DEV (r1-a3-bins, sha) + 3 bins A3 2026
(ho5-a3-data26) -> s3_funding; tu kiem: 2 301 065 ban ghi funding dau == md5 r1-a3 (50c4bc8d); (P) pred = gate-sb-<seed> (<SEAL)
+ p15 fold_20 2026; (T) ticker 2026 (HO4 tk block, 273 md5). SIM_END 20261001, HOLDOUT_UNSEAL (nhu HO4/tsx-ho),
TS_EXT = flags DEV + flags 2026 (ho_flags.json). Chay lien tuc tu 2021-07-01 (gate lan 90 ngay dung buffer 2025 = cach HO4).
Usage: gen|push <seed> | fetch <seed>"""
import json, logging, os, sys
sys.path.insert(0, "/home/ubuntu/claude_master/w3/ho5")
import ho5_k2 as K  # noqa: E402
os.environ.setdefault("HO5_FSNAP_SHA_FILE", "/home/ubuntu/claude_master/w3/ho5/fund/SNAP_SHA_V3")  # [luot4 ADD3] snapshot funding v3
import ho5_k3 as K3  # noqa: E402
R = K.R
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho5sim")
SEAL = 1767200400000
ARTS = json.load(open("/home/ubuntu/claude_master/1011/ho4p1/arts.json"))
LANE = os.environ["RT_LANE"].lower(); assert LANE in ("p", "s", "m", "ps", "pm", "sm")  # [U4a] lane chan doan
D26 = json.load(open("/home/ubuntu/claude_master/w3/retrain/out/lane/DATA26_%s.json" % LANE.upper()))  # du lieu 2026 lane
K.HOME = "/home/ubuntu/claude_master/w3/retrain/work/lane"  # RT fork: thu muc kernel (khong ghi vao w3/ho5)
FL26 = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))
UNSEAL = "I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026"
TK_BLK = open("/home/ubuntu/src/BinanceFuturesJava/research/analysis/ho4p1_tk_block.py").read()

MK_BLK = r'''
# [HO5 M] market 2026: bundle market.bin (ts < SEAL) + market.bin cua chain HO4 (ts >= SEAL)
H5C = CFG["ho5"]
HO5_INFO = {"unseal_ref": H5C.get("unseal_ref")}
LOG.info("HOLDOUT_UNSEAL_REF %s", H5C.get("unseal_ref"))
import struct as _st5
import numpy as _np5
_MDT5 = _np5.dtype([("ts", ">i8"), ("v", "V12")])
def _rmk5(_p):
    with open(_p, "rb") as _f:
        _n = _st5.unpack(">i", _f.read(4))[0]
        return _np5.frombuffer(_f.read(20 * _n), dtype=_MDT5)
_mc5 = [c for c in sorted(glob.glob(IN + "/**/market.bin", recursive=True)) if ("/" + H5C["mkt_src"] + "/") in c]
if len(_mc5) != 1:
    LOG.error("HO5_MKT_FAIL %s", _mc5); sys.exit(8)
_hm5 = _hl.md5(open(_mc5[0], "rb").read()).hexdigest()
if _hm5 != H5C["mkt_md5"]:
    LOG.error("HO5_MKT_FAIL md5 %s", _hm5); sys.exit(8)
_mb5, _mn5 = _rmk5(os.path.join(DS, "market.bin")), _rmk5(_mc5[0])
_tb5, _tn5 = _mb5["ts"].astype(_np5.int64), _mn5["ts"].astype(_np5.int64)
_dev_eq5 = bool(_np5.array_equal(_mb5[_tb5 < H5C["seal"]].tobytes(), _mn5[_tn5 < H5C["seal"]].tobytes()))
_out5 = _np5.concatenate([_mb5[_tb5 < H5C["seal"]], _mn5[_tn5 >= H5C["seal"]]]).astype(_MDT5)
_to5 = _out5["ts"].astype(_np5.int64)
assert (_np5.diff(_to5) > 0).all(), "HO5 market ts khong tang"
_MK5 = os.path.join(WORK, "ho5_mk")
os.makedirs(_MK5, exist_ok=True)
with open(os.path.join(_MK5, "market.bin"), "wb") as _f:
    _f.write(_st5.pack(">i", len(_out5))); _f.write(_out5.tobytes())
_mmd5 = _hl.md5(open(os.path.join(_MK5, "market.bin"), "rb").read()).hexdigest()
for _nm in ("pred.bin", "funding.bin"):
    if not os.path.lexists(os.path.join(_MK5, _nm)):
        os.symlink(os.path.realpath(os.path.join(DS, _nm)), os.path.join(_MK5, _nm))
_ml5 = []
for _ln in open(os.path.join(DS, "manifest.txt")):
    if _ln.startswith("md5_market="):
        _ln = "md5_market=" + _mmd5 + "\n"
    elif _ln.startswith("marketCount="):
        _ln = "marketCount=%d\n" % len(_out5)
    _ml5.append(_ln)
with open(os.path.join(_MK5, "manifest.txt"), "w") as _f:
    _f.writelines(_ml5)
HO5_INFO["market"] = dict(n_bundle_dev=int((_tb5 < H5C["seal"]).sum()), n_bundle_total=int(len(_mb5)),
                          n_2026=int((_tn5 >= H5C["seal"]).sum()), dev_part_equal_chain=_dev_eq5, md5=_mmd5,
                          ts_last=int(_to5.max()), bundle_ts_last=int(_tb5.max()))
LOG.info("HO5_MKT %s", HO5_INFO["market"])
DS = _MK5
del _mb5, _mn5, _out5
'''

FUND_CHK = r'''    # [HO5 B v2 luot5] tu kiem funding.bin (thay ban luot2: DEV r1-a3 funding.bin co 1 ban ghi ts == SEAL = ffill 15' tu 23:45).
    # (a) dung lai funding CHI tu 18 bins DEV (16 A3 + 2 moc 2021) tren CUNG market -> md5 ca file phai == r1-a3 (50c4bc8d);
    # (b) moi ban ghi ts < SEAL cua funding.bin HO5 phai TRUNG BYTE ban dung lai DEV (cung so ban ghi).
    import mmap as _mm5
    sys.path.insert(0, _HELP)
    import s3_funding as _s3
    _DB5 = os.path.join(WORK, "a3_bins_dev")
    os.makedirs(_DB5, exist_ok=True)
    for _p in _a3 + _m21:
        _d = os.path.join(_DB5, os.path.basename(_p))
        if not os.path.lexists(_d):
            os.symlink(_p, _d)
    _mk5 = _s3.read_market_keys(os.path.join(DS, "market.bin"))[0]
    _ko, _ec, _of, _gr = _s3.build_funding(_DB5, _mk5)[:4]
    _md_dev = _s3.write_funding(None, _ko, _ec, _of, _gr, md5_only=True)[0]
    _npre = int((_ko < H5C["seal"]).sum())
    _hp = _hl.md5()
    for _k in range(_npre):
        _g = int(_gr[_k])
        _hp.update(_st5.pack(">qi", int(_ko[_k]), int(_of[_g + 1] - _of[_g])) + _ec[_of[_g]:_of[_g + 1]].astype(">i8").tobytes())
    _hdev = _hp.hexdigest()
    _ndev = int(len(_ko))
    del _ko, _ec, _of, _gr, _mk5
    with open(os.path.join(A3_DSD, "funding.bin"), "rb") as _f:
        _fb5 = _mm5.mmap(_f.fileno(), 0, access=_mm5.ACCESS_READ)
        _ntot = _st5.unpack_from(">i", _fb5, 0)[0]
        _p5, _n5 = 4, 0
        while _p5 < len(_fb5):
            _t5, _c5 = _st5.unpack_from(">qi", _fb5, _p5)
            if _t5 >= H5C["seal"]:
                break
            _p5 += 12 + 8 * _c5; _n5 += 1
        _t_next5 = _st5.unpack_from(">q", _fb5, _p5)[0] if _p5 < len(_fb5) else None
        _hn = _hl.md5()
        for _q in range(4, _p5, 1 << 26):
            _hn.update(_fb5[_q:min(_p5, _q + (1 << 26))])
        _hnew = _hn.hexdigest()
        _fb5.close()
    HO5_INFO["funding"] = dict(n_total=_ntot, dev_rebuild_md5=_md_dev, want=H5C["fund_dev_md5"], dev_rebuild_n=_ndev, n_pre_dev=_npre,
                               n_pre_new=_n5, pre_md5_dev=_hdev, pre_md5_new=_hnew, next_ts=_t_next5)
    LOG.info("HO5_FUND_SELFCHECK_V2 %s", HO5_INFO["funding"])
    if _md_dev != H5C["fund_dev_md5"] or _ndev != H5C["fund_dev_n"] or _npre != _n5 or _hdev != _hnew or _t_next5 is None or _t_next5 < H5C["seal"]:
        LOG.error("HO5_FUND_FAIL"); sys.exit(8)
'''

PRED_BLK = r'''# [HO5 P] pred = gate-sb-<seed> (ts < SEAL) + p15 fold_20 2026 (dataset ho5-a3-data26)
_pp5 = [c for c in sorted(glob.glob(IN + "/**/pred_2026.bin", recursive=True)) if ("/" + H5C["d26_ds"] + "/") in c]
if len(_pp5) != 1 or _md5(_pp5[0]) != H5C["pred26_md5"]:
    LOG.error("HO5_PRED_FAIL %s", _pp5); sys.exit(8)
_RD5 = _np5.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])
def _rp5(_p):
    _r = open(_p, "rb").read()
    _n = _st5.unpack(">i", _r[:4])[0]
    assert 4 + 16 * _n == len(_r)
    return _np5.frombuffer(_r[4:], dtype=_RD5)
_a5, _b5 = _rp5(_pc[0]), _rp5(_pp5[0])
_ta5 = _a5["ts"].astype(_np5.int64)
_c5 = _np5.concatenate([_a5[_ta5 < H5C["seal"]], _b5]).astype(_RD5)
assert (_np5.diff(_c5["ts"].astype(_np5.int64)) > 0).all(), "HO5 pred ts khong tang"
_PF5 = os.path.join(WORK, "ho5_pred.bin")
with open(_PF5, "wb") as _f:
    _f.write(_st5.pack(">i", len(_c5))); _f.write(_c5.tobytes())
HO5_PRED_MD5 = _md5(_PF5)
HO5_INFO["pred"] = dict(src_md5=PRED_MD5_USED, n_src=int(len(_a5)), n_src_ge_seal=int((_ta5 >= H5C["seal"]).sum()),
                        n_dev=int((_ta5 < H5C["seal"]).sum()), n_2026=int(len(_b5)), md5=HO5_PRED_MD5,
                        nan_2026=int(_np5.isnan(_b5["p15"].astype(_np5.float64)).sum()))
LOG.info("HO5_PRED %s", HO5_INFO["pred"])
'''


A1_PRED = r'''# [HO5 P-A1 luot5] seed A1: pred goc = pred.bin cua bundle (md5 PRED0) -> override = goc (ts < SEAL) + p15 fold_20 2026
import hashlib as _h3
def _md5(_p):
    _m = _h3.md5()
    with open(_p, "rb") as _f:
        for _b in iter(lambda: _f.read(1 << 20), b""):
            _m.update(_b)
    return _m.hexdigest()
_pc = [os.path.realpath(os.path.join(DS, "pred.bin"))]
PRED_MD5_USED = _md5(_pc[0])
if PRED_MD5_USED != H5C["a1_pred_base"]:
    LOG.error("HO5_PRED_FAIL A1 base %s", PRED_MD5_USED); sys.exit(8)
''' + PRED_BLK + r'''_ovp = os.path.join(WORK, "wfo_ds_pred")
os.makedirs(_ovp, exist_ok=True)
for _nm in ("market.bin", "funding.bin"):
    if not os.path.lexists(os.path.join(_ovp, _nm)):
        os.symlink(os.path.join(DS, _nm), os.path.join(_ovp, _nm))
os.symlink(_PF5, os.path.join(_ovp, "pred.bin"))
_ml, _nrep = [], 0
for _ln in open(os.path.join(DS, "manifest.txt")):
    if _ln.startswith("md5_pred="):
        _ml.append("md5_pred=" + HO5_PRED_MD5 + "\n"); _nrep += 1
    else:
        _ml.append(_ln)
assert _nrep == 1, _nrep
with open(os.path.join(_ovp, "manifest.txt"), "w") as _f:
    _f.writelines(_ml)
LOG.info("HO5 A1 pred override -> %s md5_pred=%s", _ovp, HO5_PRED_MD5)
DS = _ovp
'''


def patches(code):
    def rep(c, old, new):
        assert c.count(old) == 1, ("anchor", c.count(old), old[:80])
        return c.replace(old, new)
    code = K3.fpatch(K.patch(code))  # [luot4] + overlay funding snapshot v3
    a = "# [R1 A3 2026-11-10] bins S1FULL+A1"
    code = rep(code, a, MK_BLK + a)
    code = rep(code, '''    if len(_a3) != 16 or len(_m21) != 2:
        LOG.error("A3_FAIL so file: a3=%d (can 16) moc21=%d (can 2)", len(_a3), len(_m21))
        sys.exit(7)
''', '''    _a26 = sorted(c for c in glob.glob(IN + "/**/predict_wf_2026*.bin", recursive=True) if ("/" + H5C["d26_ds"] + "/") in c)
    _a26ok = {os.path.basename(c): _hl.sha256(open(c, "rb").read()).hexdigest() for c in _a26}
    if len(_a3) != 16 or len(_m21) != 2 or _a26ok != H5C["bins26_sha"]:
        LOG.error("A3_FAIL so file: a3=%d (can 16) moc21=%d (can 2) a26=%s", len(_a3), len(_m21), _a26ok)
        sys.exit(7)
    HO5_INFO["bins26_sha"] = _a26ok
''')
    code = rep(code, "    for _p in _a3 + _m21:\n", "    for _p in _a3 + _m21 + _a26:\n")
    code = rep(code, "    _F = json.load(open(_fj))\n", FUND_CHK + "    _F = json.load(open(_fj))\n")
    if '_ovp = os.path.join(WORK, "wfo_ds_pred")\n' in code:
        code = rep(code, '_ovp = os.path.join(WORK, "wfo_ds_pred")\n', PRED_BLK + '_ovp = os.path.join(WORK, "wfo_ds_pred")\n')
        code = rep(code, '    os.symlink(_pc[0], os.path.join(_ovp, "pred.bin"))\n', '    os.symlink(_PF5, os.path.join(_ovp, "pred.bin"))\n')
        code = rep(code, '        _ml.append("md5_pred=" + PRED_MD5_USED + "\\n")\n', '        _ml.append("md5_pred=" + HO5_PRED_MD5 + "\\n")\n')
        code = rep(code, 'link = os.path.join(WORK, "kaggle_data_hpo")\n', TK_BLK + 'link = os.path.join(WORK, "kaggle_data_hpo")\n')
    else:  # [luot5] seed A1 (template khong co khoi pred_ds)
        code = rep(code, 'link = os.path.join(WORK, "kaggle_data_hpo")\n', A1_PRED + TK_BLK + 'link = os.path.join(WORK, "kaggle_data_hpo")\n')
    code = rep(code, 'res["ho5_mapper"] = HO5_MAPPER\n', 'res["ho5_mapper"] = HO5_MAPPER\nres["ho5"] = HO5_INFO\n')
    return code


def build(seed):
    tag = "rt-%s-l26-" % LANE + seed.lower()
    ov = dict(R.OV)
    ov["SIM_LOSER_TS_EXT_DAYS"] = R.OV["SIM_LOSER_TS_EXT_DAYS"] + "," + FL26["ranges"]
    h5 = {"seal": SEAL, "mkt_src": ARTS["chain_slug"], "mkt_md5": ARTS["market_md5"], "d26_ds": "rt-%s-data26" % LANE,
          "pred26_md5": D26["pred26_md5"], "bins26_sha": D26["bins26_sha"],
          "fund_dev_md5": "50c4bc8d9a8238e89c0a99467adac100", "fund_dev_n": 2301065,
          "unseal_ref": "HOLDOUT_UNSEAL_2026_1121 (U4a) OWNER_DECISION_PILOT_1121 c3a9f01b PREREG_RETRAIN_DIAG 436977c1",
          "a1_pred_base": R.GA.PRED0_MD5}
    extra = {"overrides": ov, "ho5": h5, "extra_env": {"HOLDOUT_UNSEAL": UNSEAL}, "ticker_min_days": 2099,
             "tk_ho4p1": {"src": ARTS["tk_slug"], "md5": ARTS["tk_md5"]}, "timeout_s": 10800,
             "want_fsnap_sha": K3.FSNAP_SHA, "want_fovl_sha": K3.FOVL_SHA}
    ks, folder, ref, cfg, code, dss = K.build(tag, seed, sim_end="20261001", extra_cfg=extra,
                                              extra_ds=[K.R.GA.ks_mod().USER + "/rt-%s-data26" % LANE, K.R.GA.ks_mod().USER + "/" + K3.FDS], code_override=patches)
    md = json.load(open(os.path.join(folder, "kernel-metadata.json")))
    md["kernel_sources"] = ["chuyendinh/" + ARTS["chain_slug"], "chuyendinh/" + ARTS["tk_slug"]]
    json.dump(md, open(os.path.join(folder, "kernel-metadata.json"), "w"), indent=1)
    compile(code, "k", "exec")
    log.info("tag=%s ref=%s ds=%s ks=%s", tag, ref, md["dataset_sources"], md["kernel_sources"])
    for f in os.listdir(folder):
        assert not any(x in f.lower() for x in ("env", "key", "privateconfig", "kaggle.json")), f
    return tag, folder, ref


if __name__ == "__main__":
    cmd, seed = sys.argv[1], sys.argv[2]
    if cmd == "gen":
        build(seed)
    elif cmd == "push":
        tag, folder, ref = build(seed)
        ks = R.GA.ks_mod()
        log.info("free_slots=%d FILES=%s", ks.free_slots(), os.listdir(folder))
        r = ks._api().kernels_push(folder)
        log.info("PUSHED %s -> %s", ref, getattr(r, "url", r))
    elif cmd == "fetch":
        raise SystemExit("RT fork: dung rt_fetch.py (tai chon loc)")
