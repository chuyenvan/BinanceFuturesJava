#!/usr/bin/env python3
"""Tai CHI cac file ticker_YYYYMMDD.bin can (01-23..02-06) tu output kernel ho4p1-tk26 (API Kaggle da cau hinh; chi doc, khong push).
Khong doc / in credential. In ten + bytes + md5 (so voi tk_raw_md5.json neu co)."""
import os, sys, hashlib, json, requests
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
want = set(sys.argv[2].split(',')); out = sys.argv[1]; os.makedirs(out, exist_ok=True)
api = KaggleApi(); api.authenticate()
ref = json.load(open('/home/ubuntu/claude_master/1011/ho4p1/kaggle/out/ho4p1-tk26/tk_raw_md5.json'))
tok = None; got = 0; seen = 0
with api.build_kaggle_client() as kg:
    while True:
        rq = ApiListKernelSessionOutputRequest(); rq.user_name = 'chuyendinh'; rq.kernel_slug = 'ho4p1-tk26'
        if tok: rq.page_token = tok
        rs = kg.kernels.kernels_api_client.list_kernel_session_output(rq)
        for it in rs.files:
            seen += 1
            nm = os.path.basename(it.file_name).replace('.gz', '')
            if nm in want:
                b = requests.get(it.url, timeout=300).content
                open(os.path.join(out, nm + '.gz'), 'wb').write(b)
                import gzip as _g; m = hashlib.md5(_g.decompress(b)).hexdigest(); got += 1
                print(nm, len(b), m, 'ref_ok' if ref.get(nm) == m else 'REF_DIFF/NA', flush=True)
        tok = rs.next_page_token
        if not tok: break
print('files_listed', seen, 'downloaded', got)
