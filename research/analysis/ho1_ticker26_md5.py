#!/usr/bin/env python3
"""HO1 B6 bo sung — md5 ticker 2026h1 Kaggle <-> Oracle (quyet dinh MASTER 4). Seal DONG: chi md5/kich thuoc, khong doc noi dung.
Kaggle tu giai nen .bin.gz -> .bin, nen so md5(gunzip(Oracle .gz)) voi md5(Kaggle .bin).
Usage: python3 ho1_ticker26_md5.py oracle | submit | status | fetch | compare"""
import glob, gzip, hashlib, json, logging, os, sys
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R)
sys.path.insert(0, R + "/research/analysis")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("t26md5")
H = "/home/ubuntu/claude_master/1003/ho1"
SRC = H + "/kaggle/wfo-ticker-2026h1"
TAG = "ho1-t26md5"
KCODE = '''import glob, hashlib, json, os
out = {}
for p in sorted(glob.glob("/kaggle/input/**/ticker_2026*", recursive=True)):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    out[os.path.basename(p)] = [h.hexdigest(), os.path.getsize(p), p]
json.dump(out, open("/kaggle/working/ticker26_md5.json", "w"), indent=0)
print("N", len(out))
'''


def md5_stream(fh):
    h = hashlib.md5()
    for b in iter(lambda: fh.read(1 << 22), b""):
        h.update(b)
    return h.hexdigest()


def oracle():
    out = {}
    for p in sorted(glob.glob(SRC + "/ticker_2026*.bin.gz")):
        with gzip.open(p, "rb") as f:
            out[os.path.basename(p)[:-3]] = md5_stream(f)
    json.dump(out, open(H + "/ticker26_oracle_gunzip_md5.json", "w"), indent=0)
    log.info("oracle n=%d", len(out))


def ks():
    import gate_ablation_driver as GA
    return GA.ks_mod()


def submit():
    k = ks()
    ref = k.kernel_ref(TAG)
    folder = os.path.join(k.WORKDIR, k.slug(TAG))
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, "run.py"), "w").write(KCODE)
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False,
          "dataset_sources": [k.USER + "/wfo-ticker-2026h1"], "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(os.path.join(folder, "kernel-metadata.json"), "w"), indent=1)
    r = k._api().kernels_push(folder)
    log.info("PUSHED %s %s", ref, getattr(r, "url", r))


def status():
    k = ks()
    log.info("%s %s", TAG, k._status(k.kernel_ref(TAG)))


def fetch():
    k = ks()
    d = H + "/t26md5_out"
    os.makedirs(d, exist_ok=True)
    k._api().kernels_output(k.kernel_ref(TAG), path=d, force=True, quiet=True)
    log.info("fetched %s", os.listdir(d))


def compare():
    o = json.load(open(H + "/ticker26_oracle_gunzip_md5.json"))
    kg = {n: v[0] for n, v in json.load(open(H + "/t26md5_out/ticker26_md5.json")).items()}
    ok = sorted(n for n in o if kg.get(n) == o[n])
    bad = sorted(n for n in o if n in kg and kg[n] != o[n])
    miss = sorted(set(o) - set(kg))
    extra = sorted(set(kg) - set(o))
    res = dict(n_oracle=len(o), n_kaggle=len(kg), ok=len(ok), bad=bad, miss=miss, extra=extra,
               pass_=len(ok) == len(o) == len(kg) == 181)
    json.dump(res, open(R + "/docs/result/ho1/ticker26_md5_check.json", "w"), indent=1)
    log.info("TICKER26 %s", json.dumps(res))


def version():
    """HO1b: dataset wfo-ticker-2026h1 v1 thieu 60 file (20260101..20260301: staging la symlink tuong doi hong) -> version moi du 181."""
    import time
    k = ks()
    t0 = time.time()
    r = k._api().dataset_create_version(SRC, version_notes="HO1b: du 181 file 20260101..20260630 (v1 thieu 60 do symlink hong)",
                                        quiet=True, dir_mode="skip")
    log.info("VERSION %s (%.0fs)", getattr(r, "url", r), time.time() - t0)
    for _ in range(240):
        st = str(k._api().dataset_status(k.USER + "/wfo-ticker-2026h1")).lower()
        if st == "ready":
            break
        time.sleep(30)
    log.info("DATASET wfo-ticker-2026h1 status %s", st)


if __name__ == "__main__":
    dict(oracle=oracle, version=version, submit=submit, status=status, fetch=fetch, compare=compare)[sys.argv[1]]()
