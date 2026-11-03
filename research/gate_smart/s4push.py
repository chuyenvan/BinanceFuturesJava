#!/usr/bin/env python3
"""Day kernel S4 (gsm-s4-fwd) CHI khi: account < 2 kernel dang chay, KHONG co kaggle_priority, seed (gst_orch) da xong/dung va
NUP4 khong chay. Usage: s4push.py check | push | fetch"""
import json, os, shutil, subprocess, sys, time
sys.path.insert(0, "/home/ubuntu/claude_master/ho_tradfi_wk")
import notf_orch as N
G = "/home/ubuntu/claude_master/gsmart"
USER = "chuyendinh"
PRIO = "/home/ubuntu/claude_master/locks/kaggle_priority"


def alive(pidf):
    try:
        os.kill(int(open(pidf).read().strip()), 0); return True
    except Exception:
        return False


def ok_to_push():
    busy = N.running()
    why = dict(busy=busy, prio=os.path.exists(PRIO), seed_orch=alive("/home/ubuntu/claude_master/gst1030/orch/orch.pid"),
               nup4_orch=alive("/home/ubuntu/claude_master/nup4_fix/orch/orch.pid"))
    st = json.load(open("/home/ubuntu/claude_master/gst1030/orch/state.json"))
    why["seed_done"] = st.get("gs-x14-s42", {}).get("state") in ("done", "failed")
    why["ok"] = len(busy) < 2 and not why["prio"] and not why["seed_orch"] and not why["nup4_orch"] and why["seed_done"]
    return why


def push():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi(); a.authenticate()
    d = G + "/ds_cells"
    if not os.path.exists(G + "/cells_created"):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        shutil.copyfile(G + "/s4_cells.parquet", d + "/s4_cells.parquet")
        json.dump({"title": "gsm-s4-cells", "id": USER + "/gsm-s4-cells", "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
        a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
        open(G + "/cells_created", "w").write(time.strftime("%F %T"))
        for _ in range(40):
            if "ready" in str(a.dataset_status(USER + "/gsm-s4-cells")).lower(): break
            time.sleep(30)
    k = G + "/kernel"; os.makedirs(k, exist_ok=True)
    shutil.copyfile(G + "/s4k.py", k + "/run.py")
    md = {"id": USER + "/gsm-s4-fwd", "title": "gsm-s4-fwd", "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False,
          "dataset_sources": [USER + "/gsm-s4-cells"] + [USER + "/vz-kline1m-%d" % y for y in (2022, 2023, 2024, 2025, 2026)],
          "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(k + "/kernel-metadata.json", "w"), indent=1)
    r = a.kernels_push(k)
    assert getattr(r, "url", None), r
    print("PUSHED", r.url)


if __name__ == "__main__":
    c = sys.argv[1]
    w = ok_to_push(); print(w)
    if c == "push":
        if not w["ok"]:
            print("KHONG du dieu kien -> khong push"); sys.exit(2)
        push()
    if c == "fetch":
        N.E.WD = G; N.E.fetch("gsm-s4-fwd", r"s4_(fwd\.parquet|meta\.json)$")
