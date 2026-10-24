"""chd helper: S3 listing + download via cryptohftdata SDK internals. Key only from env, never printed."""
import os, io, sys, time, logging, json
from pathlib import Path
logging.basicConfig(level=logging.WARNING)
for n in ("urllib3", "requests", "cryptohftdata"):
    logging.getLogger(n).setLevel(logging.WARNING)
from cryptohftdata import CryptoHFTDataClient
from cryptohftdata.bulk import parse_object_key, write_payload, _iter_body
import zstandard as zstd

EX = "binance_futures"
_client = None
_prov = None

def client():
    global _client
    if _client is None:
        k = os.environ.get("CRYPTOHFTDATA_API_KEY")
        if not k:
            sys.exit("NO KEY IN ENV")
        _client = CryptoHFTDataClient(api_key=k)
    return _client

def prov(workers=8):
    global _prov
    if _prov is None:
        _prov = client()._bulk_credential_provider(workers)
        _prov.client()
    return _prov

def list_prefix(prefix):
    p = prov()
    s3 = p.client()
    out = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=p.bucket, Prefix=prefix):
        for e in page.get("Contents", []) or []:
            k = e.get("Key", "")
            parts = parse_object_key(k)
            if parts is None:
                out.append({"key": k, "size": int(e.get("Size", 0)), "data_type": None, "symbol": None})
                continue
            out.append({**parts, "key": k, "size": int(e.get("Size", 0))})
    return out

def list_hour(date, hour):
    return list_prefix(f"{EX}/{date}/{hour:02d}/")

def get_bytes(key, retries=5):
    """returns decompressed parquet bytes (or None if missing)."""
    p = prov()
    last = None
    for a in range(retries):
        try:
            r = p.client().get_object(Bucket=p.bucket, Key=key)
            b = r["Body"]
            try:
                data = b.read() if hasattr(b, "read") else b""
            finally:
                b.close()
            exp = r.get("ContentLength") or 0
            if exp and len(data) != exp:
                raise IOError(f"short read {len(data)}/{exp}")
            if data[:4] == b"\x28\xb5\x2f\xfd":
                data = zstd.ZstdDecompressor().decompressobj().decompress(data)
            return data, int(exp or len(data))
        except Exception as e:
            msg = str(e)
            if "NoSuchKey" in msg or "404" in msg:
                return None, 0
            last = e
            time.sleep(min(2 ** a, 30))
    raise last
