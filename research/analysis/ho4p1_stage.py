#!/usr/bin/env python3
"""HO4-P1 (ADDENDUM-6 §6.5): kernel copy ticker 2026 `ho4p1-tk26` (273 ngay UTC, moi ngay lay tu kernel quy so huu) + arts.json
(md5 pred 8 seed / bins 3 / ticker raw 273 tu MANIFEST, chi tai json nho). Usage: ho4p1_stage.py tk26 | arts <chain_slug>"""
import datetime, json, logging, os, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4p1s")
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis"
sys.path.insert(0, A)
W = "/home/ubuntu/claude_master/1011/ho4p1"
USER = "chuyendinh"
QK = {"q1": "ho4p1-x26-q1", "q2": "ho4p1-x26-q2", "q3": "ho4p1-x26-q3"}


def days():
    d, out = datetime.date(2026, 1, 1), []
    while d <= datetime.date(2026, 9, 30):
        q = "q1" if d.month <= 3 else ("q2" if d.month <= 6 else "q3")
        out.append((d.strftime("%Y%m%d"), q))
        d += datetime.timedelta(days=1)
    assert len(out) == 273
    return out


TK = r'''"""HO4-P1: copy ticker 2026 ngay UTC 0101..0930 tu output kernel quy so huu (sinh boi ho4p1_stage.py)."""
import glob, gzip, hashlib, json, logging, os, shutil, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
DAYS = json.loads(__DAYS__)
QK = json.loads(__QK__)
os.makedirs("/kaggle/working/tk", exist_ok=True)
man, miss = {}, []
for d, q in DAYS:
    c = [p for p in glob.glob("/kaggle/input/**/ticker_%s.bin*" % d, recursive=True) if ("/" + QK[q] + "/") in p]
    if not c:
        miss.append(d); continue
    p = c[0]
    dst = "/kaggle/working/tk/ticker_%s.bin.gz" % d
    if p.endswith(".gz"):
        shutil.copyfile(p, dst)
        raw = gzip.open(p).read()
    else:
        raw = open(p, "rb").read()
        with open(dst, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, compresslevel=6, mtime=0) as g:
            g.write(raw)
    man["ticker_%s.bin" % d] = hashlib.md5(raw).hexdigest()
json.dump(man, open("/kaggle/working/tk_raw_md5.json", "w"), indent=0, sort_keys=True)
logging.info("TK26 copied=%d miss=%s", len(man), miss)
sys.exit(0 if not miss else 1)
'''


def tk26():
    import ho4p1_exp_kernel as E
    act = E.active()
    assert len(act) < 2, act
    fol = W + "/kaggle/ho4p1-tk26"
    os.makedirs(fol, exist_ok=True)
    open(fol + "/run.py", "w").write(TK.replace("__DAYS__", repr(json.dumps(days()))).replace("__QK__", repr(json.dumps(QK))))
    md = {"id": USER + "/ho4p1-tk26", "title": "ho4p1-tk26", "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False, "dataset_sources": [], "competition_sources": [],
          "kernel_sources": [USER + "/" + k for k in sorted(QK.values())]}
    json.dump(md, open(fol + "/kernel-metadata.json", "w"), indent=1)
    r = E.api().kernels_push(fol)
    log.info("PUSHED tk26 %s", getattr(r, "url", r))


def arts(chain):
    import ho4p1_exp_kernel as E
    od = W + "/kaggle/out/"
    E.fetch(chain, r"(^|/)(MANIFEST\.json|result\.json)$")
    man = json.load(open(od + chain + "/out/MANIFEST.json"))
    E.fetch("ho4p1-tk26", r"tk_raw_md5\.json$")
    tkm = json.load(open(od + "ho4p1-tk26/tk_raw_md5.json"))
    want = {}
    for q, k in QK.items():
        E.fetch(k, r"(^|/)ticker_raw_md5\.json$")
        want[q] = json.load(open(od + k + "/out/ticker_raw_md5.json"))
    for d, q in days():
        nm = "ticker_%s.bin" % d
        assert tkm[nm] == want[q][nm], ("tk26 md5 != exporter", nm)
    a = dict(chain_slug=chain, tk_slug="ho4p1-tk26", tk_md5=tkm,
             preds={str(s): man["pred_s%d/pred.bin" % s]["md5"] for s in (42, 7, 13, 21, 99, 123, 777, 2024)},
             bins_md5={"predict_wf_%s.bin" % c: man["bins/predict_wf_%s.bin" % c]["md5"] for c in ("20260101", "20260401", "20260701")},
             market_md5=man["market.bin"]["md5"])
    json.dump(a, open(W + "/arts.json", "w"), indent=1)
    log.info("ARTS %s", json.dumps({k: v for k, v in a.items() if k != "tk_md5"}))


if __name__ == "__main__":
    {"tk26": lambda: tk26(), "arts": lambda: arts(sys.argv[2])}[sys.argv[1]]()
