#!/usr/bin/env python3
"""Cho r3g0m-a1 COMPLETE -> fetch -> so byte printDone/equity_summary voi n4f-b0-a1 + kiem log AS_FILE. Ghi g0m_verdict.json."""
import hashlib, json, re, sys, time
sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r3_gate/orch")
import r3_orch_m as M
T, REF = "r3g0n-a1", "/home/ubuntu/claude_master/nup4_fix/results/n4f-b0-a1/storage/"
OUT = "/home/ubuntu/claude_master/res1109/r3_gate/orch/g0n_verdict.json"
while True:
    st = M.load_state()
    if T in st:
        s = M.KS._status(M.KS.kernel_ref(T))
        if s in M.KS.TERMINAL:
            break
    time.sleep(120)
v = {"tag": T, "kstatus": s}
if s == "COMPLETE":
    time.sleep(60)
    o = M.fetch_small(T)
    rj = json.load(open(o + "/result.json"))
    md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
    v.update(ok=rj.get("ok"), jar=rj.get("jar_sha256") == M.JAR_SHA,
             pd=md5(o + "/storage/printDone.csv"), pd_ref=md5(REF + "printDone.csv"),
             es_same=open(o + "/storage/equity_summary.json", "rb").read() == open(REF + "equity_summary.json", "rb").read())
    a = M.KS._api()
    r = a.process_response(a.kernel_output_with_http_info(user_name="chuyendinh", kernel_slug=M.kslug(T)))
    lg = r.get("log") or ""
    v["as_file_ok"] = "AS_FILE OK" in lg
    m = re.search(r"AS_FILE_CHECK OK ([^\"\\\\]*)", lg)
    v["as_check"] = m.group(1) if m else None
    v["preflight_tcp"] = "PREFLIGHT mapper host" in lg
    v["PASS"] = bool(v["ok"] and v["jar"] and v["pd"] == v["pd_ref"] and v["es_same"] and v["as_check"] and not v["preflight_tcp"])
json.dump(v, open(OUT, "w"), indent=1)
M.log.info("G0M VERDICT %s", v)
