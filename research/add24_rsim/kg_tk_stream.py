#!/usr/bin/env python3
"""Tai TUAN TU ticker_YYYYMMDD.bin.gz (ho4p1-tk26 output, API Kaggle da cau hinh, chi doc) theo thu tu ngay; ghi marker .done; dung lai
khi trong thu muc > MAXP file chua tieu thu (consumer Java xoa sau khi doc). In md5 (sau giai nen) so voi tk_raw_md5.json."""
import os, sys, time, hashlib, json, gzip, requests
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
out = sys.argv[1]; want = sys.argv[2].split(','); MAXP = 6
ref = json.load(open('/home/ubuntu/claude_master/1011/ho4p1/kaggle/out/ho4p1-tk26/tk_raw_md5.json'))
api = KaggleApi(); api.authenticate(); urls = {}; tok = None
with api.build_kaggle_client() as kg:
    while True:
        rq = ApiListKernelSessionOutputRequest(); rq.user_name = 'chuyendinh'; rq.kernel_slug = 'ho4p1-tk26'
        if tok: rq.page_token = tok
        rs = kg.kernels.kernels_api_client.list_kernel_session_output(rq)
        for it in rs.files: urls[os.path.basename(it.file_name)] = it.url
        tok = rs.next_page_token
        if not tok: break
bad = 0
for d in want:
    nm = 'ticker_%s.bin.gz' % d
    while len([x for x in os.listdir(out) if x.endswith('.bin.gz')]) >= MAXP: time.sleep(2)
    b = requests.get(urls[nm], timeout=600).content
    m = hashlib.md5(gzip.decompress(b)).hexdigest(); ok = ref.get(nm[:-3]) == m; bad += (not ok)
    open(os.path.join(out, nm), 'wb').write(b); open(os.path.join(out, 'ticker_%s.done' % d), 'w').write(m)
    print(nm, len(b), m, 'ref_ok' if ok else 'REF_DIFF', flush=True)
print('DONE bad', bad)
