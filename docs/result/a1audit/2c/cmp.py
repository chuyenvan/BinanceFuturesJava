#!/usr/bin/env python3
# [A1 delta] so md5 out/fund jar 2c voi md5 ref dcae2e2b DA GHI o lan audit 1 (a1_compare.json) + CTL + strace
import gzip, hashlib, json, os
P = os.path.expanduser("~/claude_master/v12/a1d_parity")
ref = json.load(open(os.path.expanduser("~/claude_master/v12/a1/docs/result/a1audit/a1_compare.json")))
out = {}
for d in ["22", "23"]:
    base = P + "/%s_a1d" % d
    r = {}
    for f in ["out_BT", "out_NEW2", "fund_BT", "fund_NEW2"]:
        m = hashlib.md5(); n = 0
        with gzip.open(base + "/" + f + ".csv.gz", "rb") as fh:
            for line in fh:
                m.update(line); n += 1
        rf = ref[d][f]["ref"]
        r[f] = {"a1d": [m.hexdigest(), n], "ref_dcae2e2b": rf, "match": [m.hexdigest(), n] == rf}
    for c in ["cmp_ctl_gate.json", "cmp_ctl_fund.json"]:
        j = json.load(open(base + "/" + c))
        r[c] = {"rows": [j.get("rows_ref"), j.get("rows_new")], "only": [j.get("only_ref"), j.get("only_new")],
                "cols_not_bit1": {k: v.get("bit") for k, v in j.get("cols", {}).items() if v.get("bit") != 1.0},
                "same_as_ref_run": ({k: v.get("bit") for k, v in j.get("cols", {}).items() if v.get("bit") != 1.0}
                                    == ref[d]["ref_" + c]["cols_not_bit1"])}
    hj = [x for x in os.listdir(base) if x.startswith("harness_")][0]
    j = json.load(open(base + "/" + hj))
    segs = [j["BT"]] + j.get("NEW2", [])
    r["strace_af_inet_nonlo"] = [s["strace"]["af_inet_non_loopback"] for s in segs]
    r["to242"] = [s["strace"]["to_242"] for s in segs]
    r["rc"] = [s["rc"] for s in segs]
    out[d] = r
json.dump(out, open(P + "/a1d_compare.json", "w"), indent=1)
for d, r in out.items():
    print(d, {f: r[f]["match"] for f in ["out_BT", "out_NEW2", "fund_BT", "fund_NEW2"]},
          "gate", r["cmp_ctl_gate.json"], "fund", r["cmp_ctl_fund.json"], "strace", r["strace_af_inet_nonlo"], r["to242"], r["rc"])
