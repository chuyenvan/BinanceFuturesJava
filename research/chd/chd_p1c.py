import sys, io, time, os, json
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
import requests
from concurrent.futures import ThreadPoolExecutor
k = os.environ["CRYPTOHFTDATA_API_KEY"]
base = "https://api.cryptohftdata.com/v1"
r = requests.get(base + "/symbols", params={"exchange": "binance_futures", "data_type": "liquidations"}, timeout=30)
j = r.json(); print("symbols keys", list(j.keys()) if isinstance(j, dict) else type(j), {kk: (vv if not isinstance(vv, list) else vv[:3]) for kk, vv in j.items()} if isinstance(j, dict) else "")
r = requests.get(base + "/status", timeout=30); print("status", r.status_code, r.text[:1500])
objs = L.list_hour("2025-09-02", 12)
un = [o["key"] for o in objs if o["data_type"] is None]
print("unparsed", len(un), un[:5])
# root listing with delimiter
p = L.prov(); s3 = p.client()
rr = s3.list_objects_v2(Bucket=p.bucket, Prefix="binance_futures/", Delimiter="/")
cps = rr.get("CommonPrefixes") or []
print("bf date prefixes n", len(cps), cps[:3], cps[-3:], "trunc", rr.get("IsTruncated"))
# throughput test: 400 small liquidation files, 8 threads
liq = [o for o in objs if o["data_type"] == "liquidations"][:400]
t = time.time()
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(lambda o: L.get_bytes(o["key"])[1], liq))
dt = time.time() - t
print(f"8 threads {len(liq)} files {sum(res)/1e6:.2f}MB in {dt:.1f}s -> {len(liq)/dt:.1f} files/s")
t = time.time()
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(lambda h: len(L.list_hour("2025-09-03", h)), range(8)))
print("list 8 hours 8 threads", res, round(time.time() - t, 1), "s")
