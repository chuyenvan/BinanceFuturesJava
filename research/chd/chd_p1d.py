import sys, time, os
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
c = L.client()
p = L.prov()
print("s3 host", urlparse(p.client()._scheme + "://" + p.client()._host).netloc.split(".")[-3:])
objs = [o for o in L.list_hour("2025-09-04", 7) if o["data_type"] == "liquidations"]
# sequential latency S3
t = time.time()
for o in objs[:20]:
    L.get_bytes(o["key"])
print("S3 seq per GET", round((time.time() - t) / 20, 3))
# worker API with JWT
tok = c._jwt_manager.get_jwt_token() if c._jwt_manager else None
sess = requests.Session()
from requests.adapters import HTTPAdapter
sess.mount("https://", HTTPAdapter(pool_connections=16, pool_maxsize=16))
H = {"Authorization": f"Bearer {tok}"}
def api_get(o):
    r = sess.get("https://api.cryptohftdata.com/v1/download", params={"file": o["key"]}, headers=H, timeout=60)
    return r.status_code, len(r.content)
t = time.time()
rs = [api_get(o) for o in objs[20:40]]
print("API seq per GET", round((time.time() - t) / 20, 3), set(x[0] for x in rs))
for nt in (8, 16):
    sub = objs[40 + (nt - 8) * 20: 40 + (nt - 8) * 20 + 160]
    t = time.time()
    with ThreadPoolExecutor(nt) as ex:
        rs = list(ex.map(api_get, sub))
    dt = time.time() - t
    print(f"API {nt} thr {len(sub)} -> {len(sub)/dt:.1f}/s codes {set(x[0] for x in rs)}")
sub = objs[200:360]
t = time.time()
with ThreadPoolExecutor(8) as ex:
    rs = list(ex.map(lambda o: L.get_bytes(o["key"])[1], sub))
dt = time.time() - t
print(f"S3 8 thr {len(sub)} -> {len(sub)/dt:.1f}/s")
