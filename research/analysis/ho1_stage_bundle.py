#!/usr/bin/env python3
"""HO1 B6 — stage bundle Kaggle `sim-ho26-bundle` (hardlink, khong copy) + 7 dataset pred seed + dataset ticker 2026h1.
Bundle = du lieu cua sim-x1-2021-bundle (stage ~/simbundle_x1_t170) voi market/pred(s42)/funding MOI (doan DEV nguyen
byte) + 2 bins 2026; manifest.txt dinh dang WfoDataset (md5 3 file) + MANIFEST_HO1.json md5 MOI file.
Khong co sim.jar / prof_* (lay tu jar dataset sim-jar-nsel). Usage: python3 ho1_stage_bundle.py <code_sha>"""
import glob
import hashlib
import json
import os
import shutil
import struct
import sys
import time

H = "/home/ubuntu/claude_master/1003/ho1"
SRC = "/home/ubuntu/simbundle_x1_t170"
DEV_DS = "/home/ubuntu/wfo_ds_x1_2021"
DEV_BINS = "/home/ubuntu/predwf_map_s1a2_x1_2021"
OUT = H + "/kaggle/sim-ho26-bundle"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
USER = "chuyendinh"


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sha_concat(files):
    h = hashlib.sha256()
    for p in sorted(files, key=os.path.basename):
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 22), b""):
                h.update(b)
    return h.hexdigest()


def link(src, dst):
    if os.path.lexists(dst):
        os.remove(dst)
    os.link(src, dst)


def count_hdr(p):
    with open(p, "rb") as f:
        return struct.unpack(">i", f.read(4))[0]


def market_range(p):
    n = count_hdr(p)
    with open(p, "rb") as f:
        f.seek(4)
        a = struct.unpack(">q", f.read(8))[0]
        f.seek(4 + 20 * (n - 1))
        b = struct.unpack(">q", f.read(8))[0]
    return a, b


def bins_meta(p):
    import numpy as np
    a = np.fromfile(p, dtype=np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4", 4)]))
    lo, hi = int(a["ts"].min()), int(a["ts"].max())
    return "md5:%s;ts:%d..%d;span:%dd;rec:%d" % (md5f(p), lo, hi, (hi - lo) // 86400000, len(a))


def bundle(code_sha):
    os.makedirs(OUT, exist_ok=True)
    for nm in ("config.properties", "exchange_info_pin.json", "regime_cont_allcoin.csv"):
        link(SRC + "/" + nm, OUT + "/" + nm)
    dev16 = sorted(glob.glob(SRC + "/predict_wf_*.bin"))
    assert len(dev16) == 16
    new2 = sorted(glob.glob(H + "/bins2026x/predict_wf_2026*.bin"))
    assert len(new2) == 2
    for p in dev16 + new2:
        link(p, OUT + "/" + os.path.basename(p))
    link(H + "/ds/market.bin", OUT + "/market.bin")
    link(H + "/gate/pred_s42/pred.bin", OUT + "/pred.bin")
    link(H + "/ds/funding.bin", OUT + "/funding.bin")
    dev18 = sorted(glob.glob(DEV_BINS + "/predict_wf_*.bin"))
    assert sha_concat(dev18) == "407e2abab3053a39a51dcb9f331d063b3e67196bf608ae061aee444cd2841ca5"
    fj = json.load(open(H + "/ds/funding.bin.json"))
    m = {}
    for ln in open(DEV_DS + "/manifest.txt"):
        k, v = ln.rstrip("\n").split("=", 1)
        m[k] = v
    for p in new2:
        m["predictWf." + os.path.basename(p)] = bins_meta(p)
    mr = market_range(OUT + "/market.bin")
    m.update({"exportedAt": time.strftime("%a %b %d %H:%M:%S GMT+07:00 %Y"), "codeGitSha": code_sha,
              "fundingPredDir": DEV_BINS + "+" + H + "/bins2026x", "binsSha256": sha_concat(dev18 + new2),
              "foldCount": "20", "marketCount": str(count_hdr(OUT + "/market.bin")), "predCount": str(count_hdr(OUT + "/pred.bin")),
              "fundingCount": str(count_hdr(OUT + "/funding.bin")), "fundingRaw15mCount": str(fj["raw15m"]),
              "marketRange": "%d..%d" % mr, "md5_market": md5f(OUT + "/market.bin"), "md5_pred": md5f(OUT + "/pred.bin"),
              "md5_funding": fj["md5"], "holdoutBuild": "HO1 prereg 35d03784+ADD1; doan <2026-01-01+07 = DEV byte; seal dong khi dung"})
    assert m["md5_funding"] == md5f(OUT + "/funding.bin")
    keys = [k for k in m if not k.startswith("predictWf.") and not k.startswith(("marketCount", "predCount", "fundingCount",
            "fundingRaw15m", "marketRange", "md5_"))]
    pw = sorted(k for k in m if k.startswith("predictWf."))
    tail = ["marketCount", "predCount", "fundingCount", "fundingRaw15mCount", "marketRange", "md5_market", "md5_pred", "md5_funding"]
    with open(OUT + "/manifest.txt", "w") as f:
        for k in keys + pw + tail:
            f.write("%s=%s\n" % (k, m[k]))
    with open(OUT + "/BINS_SHA256", "w") as f:
        for p in sorted(glob.glob(OUT + "/predict_wf_*.bin")):
            f.write("%s  %s\n" % (hashlib.sha256(open(p, "rb").read()).hexdigest(), os.path.basename(p)))
    allm = {os.path.basename(p): dict(md5=md5f(p), bytes=os.path.getsize(p)) for p in sorted(glob.glob(OUT + "/*"))
            if not p.endswith("dataset-metadata.json")}
    json.dump(allm, open(OUT + "/MANIFEST_HO1.json", "w"), indent=1)
    json.dump({"title": "sim-ho26-bundle", "id": USER + "/sim-ho26-bundle", "licenses": [{"name": "CC0-1.0"}]},
              open(OUT + "/dataset-metadata.json", "w"))
    return allm


def preds():
    out = {}
    for s in SEEDS:
        d = H + "/kaggle/ho26-pred-s%d" % s
        os.makedirs(d, exist_ok=True)
        link(H + "/gate/pred_s%d/pred.bin" % s, d + "/pred.bin")
        md5 = md5f(d + "/pred.bin")
        json.dump({"seed": s, "md5": md5, "prereg": "35d03784+ADD1"}, open(d + "/meta.json", "w"))
        json.dump({"title": "ho26-pred-s%d" % s, "id": USER + "/ho26-pred-s%d" % s, "licenses": [{"name": "CC0-1.0"}]},
                  open(d + "/dataset-metadata.json", "w"))
        out[s] = md5
    return out


def ticker():
    d = H + "/kaggle/wfo-ticker-2026h1"
    os.makedirs(d, exist_ok=True)
    fs = sorted(f for f in glob.glob("/home/ubuntu/java/simulator/kaggle_data_hpo/ticker_2026*.bin.gz")
                if "20260101" <= os.path.basename(f)[7:15] <= "20260630")
    assert len(fs) == 181
    man = {}
    for f in fs:
        link(f, d + "/" + os.path.basename(f))
        man[os.path.basename(f)] = md5f(f)
    json.dump(man, open(d + "/MANIFEST_MD5.json", "w"), indent=1)
    json.dump({"title": "wfo-ticker-2026h1", "id": USER + "/wfo-ticker-2026h1", "licenses": [{"name": "CC0-1.0"}]},
              open(d + "/dataset-metadata.json", "w"))
    return dict(n=len(fs), bytes=sum(os.path.getsize(f) for f in fs))


if __name__ == "__main__":
    res = dict(bundle=bundle(sys.argv[1]), preds=preds(), ticker=ticker())
    json.dump(res, open(H + "/kaggle/stage_manifest.json", "w"), indent=1)
    print(json.dumps({"preds": res["preds"], "ticker": res["ticker"],
                      "bundle_md5": {k: v["md5"] for k, v in res["bundle"].items() if not k.startswith("predict_wf_20")}}))
