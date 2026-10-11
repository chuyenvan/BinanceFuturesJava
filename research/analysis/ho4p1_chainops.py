#!/usr/bin/env python3
"""HO4-P1 (ADDENDUM-6 af6d6c94): dataset code `ho4p1-code` + kernel chuoi ha nguon (ho4p1_chain.py chay trong Kaggle).
Usage: ho4p1_chainops.py code [new|version] | push <tag> <mode> <cfg-extra-json> | status <tag> | fetch <tag> [regex]"""
import json, logging, os, re, shutil, subprocess, sys
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4p1c")
R = "/home/ubuntu/src/BinanceFuturesJava"
A = R + "/research/analysis"
sys.path.insert(0, A)
W = "/home/ubuntu/claude_master/1011/ho4p1"
USER = "chuyendinh"
FILES = {A + "/ho4p1_chain.py": None, A + "/ho4p1_devcmp.py": None, R + "/research/pipeline/g015_net_train.py": None, A + "/ho1_net015_predict.py": None,
         A + "/ho2_net015_onnx.py": None, A + "/ho1_featv2_window.py": None, A + "/ho1_s1_2026.py": None,
         R + "/research/pipeline/x1/x1_build_map.py": None, "/home/ubuntu/sel1m_code/tool1_col.py": None,
         "/home/ubuntu/sel1m_code/funding_label_pb.py": None, "/home/ubuntu/sel1m_code/funding_label_pb2.py": None,
         "/home/ubuntu/deploy_242_l3/models/g015x26_f15_cut20251001.onnx": None,
         "/home/ubuntu/s1_model/s1a2x1_cut20251001.json": None, "/home/ubuntu/s1_model/s1a2x1_cut20251231.json": None,
         "/home/ubuntu/claudedata/oi/symbol_map.csv": "symbol_map_863.csv",
         "/home/ubuntu/selector_pred_out/symbol_map.csv": "symbol_map_781.csv"}
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
for s in SEEDS:
    FILES["/home/ubuntu/claude_master/1003/ho1/gate/gate_s%d_cut20260101p15.json" % s] = None
MODEL_SHA = {"g015x26_f15_cut20251001.onnx": "7921ceaf2405049ddf2c23187264c34d6c95a38125f33c9ef3506f02f4e6dd8b",
             "s1a2x1_cut20251001.json": "cc0924f1e26f9fcc199e33ef161916e293f48f4b4a0b3f8ca14ade0127997308",
             "s1a2x1_cut20251231.json": "af706dc654c96f075caddc5f4153c768eec0732a28340cf9adbd6a6f791d8bf1",
             "gate_s42_cut20260101p15.json": "6a50ebb6f3714f5b5223979df22a36ea85348fd03ef8488e5c805c5884c87a7a",
             "gate_s7_cut20260101p15.json": "b630646e35d2000e2ceaeec15f27f9e005bc3451b92e8b97d20ea09ddea917eb",
             "gate_s13_cut20260101p15.json": "1b4024bfdf241f57a9e5cd3c4f0ff60b8ccf5f589f470e153670ca9876249379",
             "gate_s21_cut20260101p15.json": "2dc9fcccab90ac0767573e2a0fb9459e446063fb823e12668d2e98f2acdb5cc3",
             "gate_s99_cut20260101p15.json": "de894da8d73d741066e3cf52cc804be06631d7664c9f802b29b38fd3a58cf931",
             "gate_s123_cut20260101p15.json": "953f7f628ab294aaea6079f470096c09e89fe29f9810bf24208c0acd41ecfbc7",
             "gate_s777_cut20260101p15.json": "b53f828cbf26d135cbf9e1df0aa58ae6542f927c1bf6c6756f4e2a404cf37d17",
             "gate_s2024_cut20260101p15.json": "187488a50fc8387cfd239f00ec70da5358527a2fff13dbae1ba1b7c7570d0b07"}
PIN_SHA = "e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec"
CDT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])


def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi(); a.authenticate()
    return a


def code(how):
    import gate_ablation_driver as GA
    d = W + "/stage/ho4p1-code"
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for src, nm in FILES.items():
        dst = d + "/" + (nm or os.path.basename(src))
        shutil.copyfile(src, dst)
    json.dump(list(GA.V3FULL), open(d + "/v3full.json", "w"))
    c = np.fromfile("/home/ubuntu/java/fsrun/CLOSES_1H.bin", dtype=CDT)
    json.dump(sorted(int(x) for x in np.unique(c["sym"])), open(d + "/dev_uni.json", "w"))
    t = c["ts"].astype(np.int64)
    c[t >= int(pd.Timestamp("2025-11-01", tz="UTC").value // 10**6)].tofile(d + "/closes_dev_tail.bin")
    json.dump({"title": "ho4p1-code", "id": USER + "/ho4p1-code", "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
    man = {f: subprocess.run(["md5sum", d + "/" + f], capture_output=True, text=True).stdout.split()[0] for f in sorted(os.listdir(d))}
    json.dump(man, open(W + "/code_manifest.json", "w"), indent=1)
    a = api()
    if how == "new":
        a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
    else:
        a.dataset_create_version(d, "ho4p1 update", quiet=True, dir_mode="skip")
    log.info("CODE DS %s %d file", how, len(man))


RUN = r'''"""HO4-P1 chain kernel launcher (sinh boi ho4p1_chainops.py; ADDENDUM-6 af6d6c94)"""
import glob, json, logging, os, shutil, subprocess, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
CFG = json.loads(__CFG__)
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "xgboost==3.2.0", "onnxruntime==1.23.2", "pandas==2.3.3",
                       "numpy==2.2.6", "pyarrow==25.0.1"])
c = [p for p in glob.glob("/kaggle/input/**/ho4p1_chain.py", recursive=True) if "/ho4p1-code/" in p]
assert c, "thieu ho4p1-code"
shutil.copytree(os.path.dirname(c[0]), "/tmp/code")
CFG["code_dir"] = "/tmp/code"
json.dump(CFG, open("/tmp/cfg.json", "w"))
logging.info("INPUT %s", sorted(set(p.split("/")[3] for p in glob.glob("/kaggle/input/*/*"))))
rc = subprocess.call([sys.executable, "-u", "/tmp/code/" + CFG.get("script", "ho4p1_chain.py"), "/tmp/cfg.json"])
logging.info("CHAIN_RC %s", rc)
sys.exit(rc)
'''


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def push(tag, mode, extra):
    import ho4p1_exp_kernel as E
    act = E.active()
    if len(act) >= 2:
        log.error("DA CO %d kernel dang chay %s", len(act), act); sys.exit(3)
    ex = json.loads(extra)
    cfg = dict(mode=mode, tag=tag, model_sha=MODEL_SHA, pin_sha=PIN_SHA, seeds=SEEDS, **ex)
    if mode == "devcmp":
        cfg["script"] = "ho4p1_devcmp.py"
    fol = os.path.join(W, "kaggle", slug(tag))
    os.makedirs(fol, exist_ok=True)
    code = RUN.replace("__CFG__", repr(json.dumps(cfg)))
    compile(code, "k", "exec")
    open(fol + "/run.py", "w").write(code)
    if mode == "devcmp":
        dss = ["ho4p1-code", "bdchain-gate-store", "funding-tool1-15m", "funding-label-15m", "s1-featv2-x1-20260919",
               "predwf-g015x26-gate", "sim-ho26a-bundle", "ho26-pred-s42"]
        ks = [ex["det_src"], ex["chain_src"]]
    else:
        dss = ["ho4p1-code", "funding-oi-percoin", "sim-ho26a-bundle"] + ["ho26-pred-s%d" % s for s in (SEEDS if mode == "y26" else [42])]
        ks = [ex["oi_src"]] + ([ex["det_src"]] if mode == "det" else sorted(ex["q_src"].values()))
    md = {"id": USER + "/" + slug(tag), "title": slug(tag), "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True, "dataset_sources": [USER + "/" + d for d in dss],
          "competition_sources": [], "kernel_sources": [USER + "/" + k for k in ks]}
    json.dump(md, open(fol + "/kernel-metadata.json", "w"), indent=1)
    r = api().kernels_push(fol)
    log.info("PUSHED %s %s cfg=%s", tag, getattr(r, "url", r), json.dumps(ex))


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "code":
        code(sys.argv[2])
    elif a == "push":
        push(sys.argv[2], sys.argv[3], sys.argv[4])
    elif a in ("status", "fetch"):
        import ho4p1_exp_kernel as E
        if a == "status":
            E.status(sys.argv[2])
        else:
            E.fetch(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else r".")
