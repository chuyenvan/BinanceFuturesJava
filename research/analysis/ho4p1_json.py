#!/usr/bin/env python3
"""HO4-P1: gom ket qua (khong so 2026) -> docs/result/ho4/HO4_P1.json + ban sao json thanh phan. Usage: ho4p1_json.py"""
import json, logging, os, shutil, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
W = "/home/ubuntu/claude_master/1011/ho4p1/"
R = "/home/ubuntu/src/BinanceFuturesJava/docs/result/ho4/"
J = lambda p: json.load(open(W + p)) if os.path.exists(W + p) else None
ch = J("kaggle/out/ho4p1-chain-y26/result.json") or {}
ch.pop("manifest", None)
out = dict(prereg=["af6d6c94", "923d7643", "95da70a9", "106dd923", "0b798c10"],
           s1=dict(fix="76c5bc40", merge="0594986e", tests_before=259, tests_after=264,
                   jar_exporter_sha256="99c5f040c9295a610fe815e7c6759ccfccbd1cca370dcfc3bcb935b33ec3a2fb", jar_sim="b7c89f09"),
           p3_det=dict(exp=J("det_exp.json"), oi=J("det_oi.json"), chain=J("det_chain.json")),
           p3_dev=J("kaggle/out/ho4p1-devcmp/out/devcmp.json"),
           s4=dict(chain_y26=ch, arts=J("arts.json"), no_funding_union=J("no_funding_union.json")),
           s5=dict(q1r=J("det_s5q1.json"), chain=J("det_s5chain.json"), parity=J("q/parity_ho4p1.json")),
           kernels32={k: {x: v.get(x) for x in ("state", "md5", "n", "pushes", "kstatus", "chk")}
                      for k, v in (J("q/state.json") or {}).items() if k.startswith("ho4-")},
           p3_dev_sim=J("sim_gate.json"), dupfx=json.load(open(R + "ho4p1_dupfx.json")) if os.path.exists(R + "ho4p1_dupfx.json") else None,
           l5_parity=json.load(open("/home/ubuntu/claude_master/1011/livefix/l5/lf2_parity_result.json"))
           if os.path.exists("/home/ubuntu/claude_master/1011/livefix/l5/lf2_parity_result.json") else None,
           queue_status=open(W + "q/queue_status.tsv").read() if os.path.exists(W + "q/queue_status.tsv") else None)
json.dump(out, open(R + "HO4_P1.json", "w"), indent=1, default=str)
for a, b in (("excl26.json", "ho4p1_excl26.json"), ("arts.json", "ho4p1_arts26.json"), ("det_s5chain.json", "ho4p1_s5_chain.json")):
    if os.path.exists(W + a):
        shutil.copyfile(W + a, R + b)
logging.info("JSON_OK %s", sorted(out))
