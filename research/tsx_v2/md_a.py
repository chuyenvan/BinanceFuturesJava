import json
J = json.load(open("/home/ubuntu/claude_master/tsx_v2/out/phaseA.json"))
print("EPISODES", len(J["episodes"]))
a = J["A2a"]["by_ep"]
print("| Đợt | cụm hoãn/seed | X14 direct | oracle − X14 | H504 − X14 |")
for k in sorted(a):
    v = a[k]
    print("| %s | %.1f | %+.0f | %+.0f | %+.0f |" % (k, v["n"], v["x14_direct"], v["oracle_vs_x14"], v["h504_vs_x14"]))
b = J["A2b"]["by_ep"]
print("| Đợt | cụm OFF/seed | H504 − cut | oracle − cut |")
for k in sorted(b):
    v = b[k]
    print("| %s | %.1f | %+.0f | %+.0f |" % (k, v["n"], v["h504_vs_cut"], v["oracle_vs_cut"]))
print(json.dumps(J["A2b"]["by_year"]))
