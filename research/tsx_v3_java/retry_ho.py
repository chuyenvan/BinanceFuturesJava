#!/usr/bin/env python3
"""TSX_V3_JAVA - day lai DUNG 1 lan (prereg §2) 2 run HO cua TSX_V2_SIM bi loi ha tang, cfg y het, tag moi (khong dung state TSX_V2_SIM):
  tsx2-ho-vt25-s123: ERROR 2 lan (Kaggle, result.json thieu)  -> tsx3j-ho-vt25-s123
  tsx2-ho-v420-s7:   push 12:21 khong tao kernel (URL rong, status 404 lien tuc 8h+) -> tsx3j-ho-v420-s7
Parity = research/tsx_v2_sim/run.py post_ho (q.check, printDone truoc 2025-12-24 = ho4-k24-b, dong [TSX]).
Push khong tao kernel (404 lien tuc ~24 phut) khong tinh la 1 lan chay -> day lai push (toi da 8), cho slot CPU < 5.
Out: ~/claude_master/tsx_v3_java/res_<tag>.json, retry_state.json. Usage: python3 retry_ho.py
"""
import importlib.util
import json
import logging
import os
import sys
import time

WJ = "/home/ubuntu/claude_master/tsx_v3_java"
spec = importlib.util.spec_from_file_location("tsx2run", "/home/ubuntu/claude_master/vz_e1_wt/research/tsx_v2_sim/run.py")
R2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R2)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx3j_retry")
RETRY = {"tsx3j-ho-vt25-s123": "tsx2-ho-vt25-s123", "tsx3j-ho-v420-s7": "tsx2-ho-v420-s7"}


def main():
    q = R2.Q()
    ks = R2.GA.ks_mod()
    sp = R2.specs(q)
    stp = WJ + "/retry_state.json"
    st = json.load(open(stp)) if os.path.exists(stp) else {}
    for t, src in RETRY.items():
        st.setdefault(t, dict(src=src, state="TODO", pushes=0, n404=0))
        assert sp[src]["scope"] == "HO"
    while True:
        for t, src in RETRY.items():
            s = st[t]
            if s["state"] == "TODO":
                try:
                    acct = list(q.running(ks))
                except Exception as e:  # noqa: BLE001
                    log.warning("running %s", str(e)[:100])
                    continue
                if len(acct) >= 5:
                    log.info("cho slot CPU (acct dang chay %d) truoc khi day %s", len(acct), t)
                    continue
                try:
                    r = q.push(ks, t, sp[src]["ov"], sp[src]["seed"], "20261001", True)
                    s.update(state="PUSHED", pushes=s["pushes"] + 1, at=time.strftime("%F %T"), n404=0)
                    log.info("PUSHED %s (= %s cfg y het, seed %d) -> %s", t, src, sp[src]["seed"], r)
                except Exception as e:  # noqa: BLE001
                    log.error("push %s loi %s", t, str(e)[:300])
                time.sleep(40)
            elif s["state"] == "PUSHED":
                try:
                    k = ks._status(ks.kernel_ref(t))
                except Exception as e:  # noqa: BLE001
                    msg = str(e)[:100]
                    log.warning("status %s %s", t, msg)
                    if "404" in msg:
                        s["n404"] += 1
                        if s["n404"] >= 6 and s["pushes"] < 8:
                            log.error("%s 404 %d lan -> push KHONG tao kernel (khong tinh la 1 lan chay) -> day lai push", t, s["n404"])
                            s["state"] = "TODO"
                    continue
                s["n404"] = 0
                if k not in ks.TERMINAL:
                    continue
                log.info("%s -> %s", t, k)
                try:
                    ks.fetch(t)
                except Exception as e:  # noqa: BLE001
                    log.error("fetch %s %s", t, str(e)[:200])
                r = R2.post_ho(q, t, sp[src])
                r["kstatus"], r["src"] = str(k), src
                json.dump(r, open(WJ + "/res_%s.json" % t, "w"), indent=1)
                s.update(state="DONE", kstatus=str(k), passed=r["passed"])
                log.info("POST %s passed=%s md5=%s n=%s tsx=%s chk=%s", t, r["passed"], r.get("md5"), r.get("n"), r.get("tsx"), r.get("chk"))
        json.dump(st, open(stp, "w"), indent=1)
        if all(st[t]["state"] == "DONE" for t in RETRY):
            log.info("RETRY XONG %s", {t: st[t].get("passed") for t in RETRY})
            return
        time.sleep(240)


if __name__ == "__main__":
    main()
