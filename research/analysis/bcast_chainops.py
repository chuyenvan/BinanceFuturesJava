#!/usr/bin/env python3
"""BCAST (PREREG_BACKCAST_RESERVOIR 596c1ef8): day kernel chuoi ha nguon bc20 (bcast_chain.py nhung vao run.py; module + model tu
dataset ho4p1-code; OI ghim funding-oi-percoin; dau vao = output kernel exporter x_src).
Usage: bcast_chainops.py push <tag> <x_src>"""
import json, logging, os, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bcast_chops")
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis"
sys.path.insert(0, A)
import ho4p1_chainops as HC  # noqa: E402
import bcast_exp_kernel as E  # noqa: E402
W = "/home/ubuntu/claude_master/1012/bcast"
RUN = r'''"""BCAST chain kernel launcher (sinh boi bcast_chainops.py; PREREG_BACKCAST_RESERVOIR 596c1ef8)"""
import glob, json, logging, os, shutil, subprocess, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
CFG = json.loads(__CFG__)
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "xgboost==3.2.0", "onnxruntime==1.23.2", "pandas==2.3.3",
                       "numpy==2.2.6", "pyarrow==25.0.1"])
c = [p for p in glob.glob("/kaggle/input/**/ho4p1_chain.py", recursive=True) if "/ho4p1-code/" in p]
assert c, "thieu ho4p1-code"
shutil.copytree(os.path.dirname(c[0]), "/tmp/code")
open("/tmp/code/bcast_chain.py", "w").write(__SRC__)
CFG["code_dir"] = "/tmp/code"
json.dump(CFG, open("/tmp/cfg.json", "w"))
logging.info("INPUT %s", sorted(set(p.split("/")[3] for p in glob.glob("/kaggle/input/*/*"))))
rc = subprocess.call([sys.executable, "-u", "/tmp/code/bcast_chain.py", "/tmp/cfg.json"])
logging.info("CHAIN_RC %s", rc)
sys.exit(rc)
'''


def push(tag, x_src):
    act = E.active()
    if len(act) >= 2 or any("/bcast-" in x for x in act):
        log.error("KHONG DAY: dang chay %s", act); sys.exit(3)
    cfg = dict(mode="bc20", tag=tag, model_sha=HC.MODEL_SHA, pin_sha=HC.PIN_SHA, seeds=HC.SEEDS, x_src=x_src)
    fol = os.path.join(W, "kaggle", E.slug(tag))
    os.makedirs(fol, exist_ok=True)
    code = RUN.replace("__CFG__", repr(json.dumps(cfg))).replace("__SRC__", repr(open(A + "/bcast_chain.py").read()))
    compile(code, "k", "exec")
    open(fol + "/run.py", "w").write(code)
    md = {"id": HC.USER + "/" + E.slug(tag), "title": E.slug(tag), "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [HC.USER + "/ho4p1-code", HC.USER + "/funding-oi-percoin"],
          "competition_sources": [], "kernel_sources": [HC.USER + "/" + x_src]}
    json.dump(md, open(fol + "/kernel-metadata.json", "w"), indent=1)
    r = HC.api().kernels_push(fol)
    log.info("PUSHED %s %s x_src=%s (active truoc %s)", tag, getattr(r, "url", r), x_src, act)


if __name__ == "__main__":
    assert sys.argv[1] == "push"
    push(sys.argv[2], sys.argv[3])
