#!/usr/bin/env python3
# [A1] so sanh parity offline: ref (jar dcae2e2b) vs a1 (jar build tu a896595f) — doc lap, chi hashlib/json/gzip
import gzip, hashlib, json, os, sys
P = os.path.expanduser("~/claude_master/v12/a1_parity")
res = {}
for d in ["22", "23"]:
    r = {}
    ref, new = P + "/%s_ref" % d, P + "/%s_a1" % d
    if not (os.path.isdir(ref) and os.path.isdir(new)):
        res[d] = "missing"; continue
    for f in ["out_BT", "out_NEW2", "fund_BT", "fund_NEW2"]:
        h = []
        for base in (ref, new):
            p = base + "/" + f + ".csv.gz"
            if not os.path.exists(p):
                h.append(None); continue
            m = hashlib.md5(); n = 0
            with gzip.open(p, "rb") as fh:
                for line in fh:
                    m.update(line); n += 1
            h.append((m.hexdigest(), n))
        r[f] = {"ref": h[0], "a1": h[1], "match": h[0] is not None and h[0] == h[1]}
    for base, tag in ((ref, "ref"), (new, "a1")):
        for c in ["cmp_ctl_gate.json", "cmp_ctl_fund.json"]:
            try:
                j = json.load(open(base + "/" + c))
                bits = {k: v.get("bit") for k, v in j.get("cols", {}).items() if v.get("bit") != 1.0}
                r[tag + "_" + c] = {"rows_ref": j.get("rows_ref"), "rows_new": j.get("rows_new"), "only_ref": j.get("only_ref"),
                                    "only_new": j.get("only_new"), "cols_not_bit1": bits}
            except Exception as e:
                r[tag + "_" + c] = "ERR " + str(e)
        # strace AF_INET non-loopback
        hj = [x for x in os.listdir(base) if x.startswith("harness_") and x.endswith(".json")]
        if hj:
            j = json.load(open(base + "/" + hj[0]))
            def sc(x):
                return (x or {}).get("strace", {})
            bt = sc(j.get("BT"))
            n2 = [sc(x) for x in j.get("NEW2", [])]
            r[tag + "_strace"] = {"BT_af_inet_nonlo": bt.get("af_inet_non_loopback"), "BT_to242": bt.get("to_242"),
                                  "NEW2_af_inet_nonlo": [x.get("af_inet_non_loopback") for x in n2],
                                  "rc": [ (j.get("BT") or {}).get("rc") ] + [x.get("rc") for x in j.get("NEW2", [])],
                                  "suspicious": [(j.get("BT") or {}).get("suspicious_log_lines")] + [x.get("suspicious_log_lines") for x in j.get("NEW2", [])]}
    res[d] = r
# doi chieu voi ref cua tac gia (safe_parity d22_base, da xoa file? chi con md5 trong json)
json.dump(res, open(P + "/a1_compare.json", "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
