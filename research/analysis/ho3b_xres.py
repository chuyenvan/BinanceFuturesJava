import json, sys
d = json.load(open(sys.argv[1]))
print(json.dumps({k: v for k, v in d.items() if k != "tasks"}))
for t in d.get("tasks", []):
    print("TASK", t["name"], "rc", t["rc"], "secs", t["secs"], "outputs", list(t["outputs"].items())[:4])
    print("   tail:", t["tail"][-600:].replace("\n", " / "))
