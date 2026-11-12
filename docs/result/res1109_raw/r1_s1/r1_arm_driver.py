#!/usr/bin/env python3
"""R1 arm A1 (NET: net015 raw, dataset predwf-g015x26-gate) va A2 (RND: hoan vi A0, dataset r1-a2-bins).
Cung khung kernel voi A3 (r1_a3_driver: A3_BLOCK doi bins -> s3_funding -> WFO_DATA_DIR moi), cau hinh = tsx-x14-<seed>.
Usage: upload_a2 | check <arm> <seed> | push <arm> <seed>"""
import hashlib
import json
import logging
import os
import sys

sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r1_s1")
import r1_a3_driver as R  # noqa: E402

log = logging.getLogger("r1arm")
ARMS = {"A1": dict(ds="predwf-g015x26-gate", bins=R.D + "/g015x26", prefix="r1-a1-"),
        "A2": dict(ds="r1-a2-bins", bins=R.D + "/a2_bins", prefix="r1-a2-")}


def bins_sha(arm):
    d = ARMS[arm]["bins"]
    fs = sorted(f for f in os.listdir(d) if f.startswith("predict_wf_") and f.endswith(".bin"))
    assert len(fs) == 16, (arm, len(fs))
    if arm == "A2":
        assert json.load(open(d + "/a2_report.json"))["G_SAN"] is True
    h = hashlib.sha256()
    for fn in fs:
        with open(os.path.join(d, fn), "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
    if arm == "A2":
        assert h.hexdigest() == json.load(open(d + "/a2_report.json"))["a2_bins_sha256_concat"]
    return h.hexdigest()


def tag_of(arm, seed):
    return ARMS[arm]["prefix"] + seed.lower()


def upload_a2():
    ks = R.GA.ks_mod()
    d = ARMS["A2"]["bins"]
    bins_sha("A2")
    meta = {"title": "r1-a2-bins", "id": ks.USER + "/r1-a2-bins", "licenses": [{"name": "CC0-1.0"}]}
    json.dump(meta, open(d + "/dataset-metadata.json", "w"))
    r = ks._api().dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
    log.info("dataset create -> %s", getattr(r, "url", r))


def build(arm, seed):
    ks = R.GA.ks_mod()
    tag = tag_of(arm, seed)
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    ds = ARMS[arm]["ds"]
    cfg = {"tag": tag, "profile": R.GA.PROFILE, "overrides": dict(R.OV), "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": R.CODE_SHA, "bins_ds": "", "jar_ds": R.JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "a3_ds": ds, "moc21_ds": R.MOC21_DS, "want_a3_sha": bins_sha(arm)}
    dss = [ks.USER + "/" + R.GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + R.JAR_DS, ks.USER + "/" + R.MOC21_DS,
                                                          ks.USER + "/" + ds]
    dsn, md5 = R.G.pred_of(seed)
    if dsn is not None:
        cfg.update(pred_ds=dsn, want_pred_md5=md5, want_pred_base=R.GA.PRED0_MD5)
        dss.append(ks.USER + "/" + dsn)
    code = R.template(seed).replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": dss, "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(md, f, indent=1)
    return ks, folder, ref, cfg


def check(arm, seed):
    ks, folder, ref, cfg = build(arm, seed)
    rj = json.load(open("/home/ubuntu/kaggle_sim/out/tsx-x14-%s/result.json" % seed.lower()))
    same_ov = {str(k): str(v) for k, v in rj["overrides"].items()} == {str(k): str(v) for k, v in cfg["overrides"].items()}
    log.info("check %s %s: ref=%s overrides_same_as_tsx=%s profile_same=%s want=%s", arm, seed, ref, same_ov,
             rj.get("profile") == cfg["profile"], cfg["want_a3_sha"][:12])
    return same_ov


def push(arm, seed):
    assert check(arm, seed), "overrides khac run tham chieu -> DUNG"
    ks, folder, ref, cfg = build(arm, seed)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s -> %s", ref, getattr(r, "url", r))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "upload_a2":
        upload_a2()
    elif c == "check":
        check(sys.argv[2], sys.argv[3])
    elif c == "push":
        push(sys.argv[2], sys.argv[3])
