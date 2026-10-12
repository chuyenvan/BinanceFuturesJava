#!/usr/bin/env python3
"""BCAST B3 (PREREG_BACKCAST_RESERVOIR 596c1ef8): dataset Kaggle PRIVATE niem phong `bcast-2020-2021h1-p1` (phang) tu output kernel
bcast-x20-a (exporter) + bcast-ch20-a (chuoi). md5 moi file staged == MANIFEST kernel. Khong doc gia tri du lieu.
Usage: bcast_ds.py stage | upload | status"""
import glob, hashlib, json, logging, os, shutil, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bcast_ds")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
W = "/home/ubuntu/claude_master/1012/bcast"
DSN = "bcast-2020-2021h1-p1"
SD = W + "/stage/" + DSN
XO, CO = W + "/kaggle/out/bcast-x20-a/", W + "/kaggle/out/bcast-ch20-a/"


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def plan():
    P = []
    for p in sorted(glob.glob(XO + "out/ticker/ticker_*.bin.gz")):
        P.append((os.path.basename(p), p, "bcast-x20-a:out/ticker/" + os.path.basename(p)))
    for rel in ["gate/gate.csv.gz", "CLOSES_1H_vision1m.bin", "funding_vision.pkl", "lifecycle.pkl", "market_rebuilt.bin",
                "universe_excl.json", "universe_by_month.json", "ticker_raw_md5.json"]:
        P.append((os.path.basename(rel), XO + "out/" + rel, "bcast-x20-a:out/" + rel))
    for p in [q for q in sorted(glob.glob(XO + "out/t1/*")) + sorted(glob.glob(XO + "out/lab/*")) if not q.endswith(".meta.json")]:
        rel = os.path.relpath(p, XO + "out")
        P.append((rel.replace("/", "_"), p, "bcast-x20-a:out/" + rel))
    for p in sorted(glob.glob(CO + "out/**/*", recursive=True)):
        if os.path.isfile(p) and not p.endswith("MANIFEST.json"):
            rel = os.path.relpath(p, CO + "out")
            nm = rel.replace("/pred.bin", ".bin").replace("/", "_")
            P.append((nm, p, "bcast-ch20-a:out/" + rel))
    return P


def stage():
    from bcast_exp_kernel import fetch
    if len(glob.glob(XO + "out/ticker/ticker_*.bin.gz")) != 369:
        fetch("bcast-x20-a", r"^out/")
    xm = json.load(open(XO + "out/MANIFEST.json")); cm = json.load(open(CO + "out/MANIFEST.json"))
    shutil.rmtree(SD, ignore_errors=True); os.makedirs(SD)
    M = {}
    for nm, p, src in plan():
        k, rel = src.split(":out/")
        want = (xm if k == "bcast-x20-a" else cm)[rel]["md5"]
        got = md5f(p)
        assert got == want, (src, got, want)
        assert nm not in M, nm
        os.link(p, SD + "/" + nm)
        M[nm] = dict(md5=got, bytes=os.path.getsize(p), src=src)
    for k, src in (("x", XO), ("ch", CO)):
        shutil.copyfile(src + "result.json", SD + "/%s_result.json" % k)
        shutil.copyfile(src + "out/MANIFEST.json", SD + "/%s_MANIFEST.json" % k)
    json.dump(M, open(SD + "/MANIFEST_bcast.json", "w"), indent=0, sort_keys=True)
    json.dump(M, open(W + "/MANIFEST_bcast.json", "w"), indent=0, sort_keys=True)
    json.dump({"title": DSN, "id": "chuyendinh/" + DSN, "licenses": [{"name": "CC0-1.0"}]}, open(SD + "/dataset-metadata.json", "w"))
    log.info("STAGE %d file, %.1f MB, md5 khop MANIFEST kernel 100%%", len(M), sum(v["bytes"] for v in M.values()) / 1e6)


def upload():
    from bcast_exp_kernel import api
    r = api().dataset_create_new(SD, public=False, quiet=True, dir_mode="skip")
    log.info("UPLOAD %s", getattr(r, "url", r) if not getattr(r, "error", None) else r.error)


def status():
    from bcast_exp_kernel import api
    a = api()
    log.info("STATUS %s", a.dataset_status("chuyendinh/" + DSN))
    names, tok = [], None
    while True:
        r = a.dataset_list_files("chuyendinh/" + DSN, page_token=tok, page_size=200)
        names += [f.name for f in (r.files or [])]
        tok = getattr(r, "next_page_token", None) or getattr(r, "nextPageToken", None)
        if not tok:
            break
    M = json.load(open(SD + "/MANIFEST_bcast.json"))
    miss = sorted(set(M) - set(n.replace(".gz", "") if n.replace(".gz", "") in M else n for n in names) - set(names))
    log.info("DS files=%d manifest=%d thieu=%s", len(names), len(M), miss[:10])


if __name__ == "__main__":
    {"stage": stage, "upload": upload, "status": status}[sys.argv[1]]()
