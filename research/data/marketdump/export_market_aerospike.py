#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
READ-ONLY dump Aerospike set `test.market_data_object` -> WfoDataset `market.bin` + parquet.

Nguon: Docker container `aerospike-wfo` (network host, port 3222, localhost).

CƠ SỞ ĐỌC (đã kiểm trong code Java, KHÔNG đoán):
  - `DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike()` (dòng ~2249):
        Long timestamp = record.getLong("time");
        byte[] compressed = (byte[]) record.getValue("data");
        results.put(timestamp, MarketDataObject.decodeMarketDataFromBinary(compressed));
    => khóa map = bin `time` (epoch ms), KHÔNG phải user_key. Kết quả là TreeMap<Long,...>
       nên phút trùng bị GỘP (bản ghi được scan sau cùng thắng).
  - `WfoDataset` (dòng 66) dùng đúng hàm đó rồi `writeMarket(mkt)`.
  - `MarketDataObject.decodeMarketDataFromBinary` đọc ByteBuffer default => BIG-ENDIAN,
    thứ tự (rateDownAvg, rateUpAvg, rateDown15MAvg) = (down, up, down15).

`market.bin` tái lập ĐÚNG `WfoDataset.writeMarket` (dòng ~339):
  writeInt(count) (BIG-ENDIAN)
  rồi mỗi dòng writeLong(ts_ms), writeFloat(down), writeFloat(up), writeFloat(down15)
  (DataOutputStream => BIG-ENDIAN), sắp TĂNG dần theo ts (TreeMap<Long,...>).

Ghi chú dữ liệu thật: một phần nhỏ record (dạng ghi không gửi user_key) có user_key=None
nhưng vẫn đủ bin `time` + `data` => vẫn dựng lại được bằng `time` (đúng như reader Java).

`market.parquet`: cột ts(int64), down(float32), up(float32), down15(float32).

RÀNG BUỘC: CHỈ scan/get Aerospike. KHÔNG write/delete/truncate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import struct
import subprocess
import sys
import time
from array import array
from datetime import datetime, timedelta, timezone

import numpy as np

# ----------------------------- hằng số nguồn -----------------------------
AS_HOST = "127.0.0.1"
AS_PORT = 3222
NAMESPACE = "test"
SET_NAME = "market_data_object"
GMT7 = timezone(timedelta(hours=7))
KEY_FMT = "%Y%m%d-%H%M"
EXPECTED_OBJECTS = 2947861  # asinfo objects (chỉ để đối chiếu)

DATASET_ID = "chuyendinh/vz-marketdata"
DATASET_TITLE = "vz-marketdata"

log = logging.getLogger("mktdump")


# ----------------------------- tiện ích -----------------------------
def setup_logging(out_dir: str) -> None:
    os.makedirs(os.path.join(out_dir, "logs"), exist_ok=True)
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(os.path.join(out_dir, "logs", "export.log"))
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.handlers = []
    log.addHandler(fh)
    log.addHandler(sh)


def parse_ts(uk: str) -> int:
    """user_key `yyyyMMdd-HHmm` (GMT+7) -> epoch ms."""
    dt = datetime.strptime(uk, KEY_FMT).replace(tzinfo=GMT7)
    return int(dt.timestamp() * 1000)


def fmt_ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, GMT7).strftime("%Y-%m-%d %H:%M")


def key_for_ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, GMT7).strftime(KEY_FMT)


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def df_report() -> str:
    try:
        out = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout
        return out.strip().splitlines()[-1].strip()
    except Exception as exc:  # pragma: no cover
        return f"df failed: {exc}"


# ----------------------------- scan (READ-ONLY) -----------------------------
def scan_all(host: str, port: int):
    import aerospike

    cfg = {
        "hosts": [(host, port)],
        "policies": {"timeout": 8000, "use_services_alternate": True},
    }
    client = aerospike.client(cfg)

    ts = array("q")
    down = array("f")
    up = array("f")
    d15 = array("f")
    hasuk = array("b")  # 1 nếu có user_key hợp lệ, 0 nếu không
    stats = {
        "n_seen": 0,
        "n_rows": 0,
        "n_no_time": 0,
        "n_bad_data": 0,
        "n_keyless": 0,
        "n_uk_time_mismatch": 0,
    }
    samples = []  # user_key mẫu (để spot-check)
    t0 = time.time()

    scan = client.scan(NAMESPACE, SET_NAME)

    def cb(rec):
        # scan callback nhận 1 tuple (key, meta, bins)
        key, _meta, bins = rec
        stats["n_seen"] += 1
        uk = key[2]

        data = bins.get("data")
        if data is None or len(data) < 12:
            stats["n_bad_data"] += 1
            return

        tbin = bins.get("time")
        if tbin is None:
            if isinstance(uk, str):
                t = parse_ts(uk)
            else:
                stats["n_no_time"] += 1
                return
        else:
            t = int(tbin)

        d, u, x15 = struct.unpack(">fff", bytes(data[:12]))

        if isinstance(uk, str):
            try:
                if parse_ts(uk) != t:
                    stats["n_uk_time_mismatch"] += 1
            except ValueError:
                stats["n_uk_time_mismatch"] += 1
            if len(samples) < 300:
                samples.append(uk)
            hasuk.append(1)
        else:
            stats["n_keyless"] += 1
            hasuk.append(0)

        ts.append(t)
        down.append(d)
        up.append(u)
        d15.append(x15)
        stats["n_rows"] += 1
        if stats["n_seen"] % 500000 == 0:
            log.info("scan... seen=%d rows=%d (%.1fs)", stats["n_seen"], stats["n_rows"], time.time() - t0)

    scan.foreach(cb)
    log.info("scan DONE seen=%d rows=%d keyless=%d no_time=%d bad_data=%d uk_time_mismatch=%d in %.1fs",
             stats["n_seen"], stats["n_rows"], stats["n_keyless"], stats["n_no_time"],
             stats["n_bad_data"], stats["n_uk_time_mismatch"], time.time() - t0)
    return client, ts, down, up, d15, hasuk, samples, stats


# ----------------------------- dựng mảng + gộp TreeMap -----------------------------
def build_sorted(ts, down, up, d15, hasuk):
    a_ts = np.frombuffer(ts, dtype=np.int64).astype(np.int64, copy=True)
    a_dn = np.frombuffer(down, dtype=np.float32).astype(np.float32, copy=True)
    a_up = np.frombuffer(up, dtype=np.float32).astype(np.float32, copy=True)
    a_15 = np.frombuffer(d15, dtype=np.float32).astype(np.float32, copy=True)
    a_hk = np.frombuffer(hasuk, dtype=np.int8).astype(np.int8, copy=True)
    n_raw = int(a_ts.size)

    # Sắp theo ts; trong cùng ts ưu tiên record CÓ user_key, rồi (down,up,down15) để tất định.
    hasuk_inv = (a_hk == 0).astype(np.int8)
    order = np.lexsort((a_15, a_up, a_dn, hasuk_inv, a_ts))
    ts_s = a_ts[order]
    dn_s = a_dn[order]
    up_s = a_up[order]
    d15_s = a_15[order]

    # TreeMap semantics: mỗi ts giữ 1 bản ghi (bản đầu sau khi lexsort = ưu tiên user_key).
    keep = np.empty(ts_s.size, dtype=bool)
    if ts_s.size:
        keep[0] = True
        keep[1:] = ts_s[1:] != ts_s[:-1]
    starts = np.nonzero(keep)[0]

    # Đếm xung đột: cùng ts nhưng data khác nhau.
    n_dup_collapsed = int(ts_s.size - starts.size)
    n_conflict = 0
    conflict_examples = []
    if n_dup_collapsed:
        gid = np.cumsum(keep) - 1  # group index theo từng dòng
        gstart = starts[gid]
        dup_rows = np.nonzero(~keep)[0]
        for i in dup_rows:
            g = int(gstart[i])
            if (dn_s[i] != dn_s[g]) or (up_s[i] != up_s[g]) or (d15_s[i] != d15_s[g]):
                n_conflict += 1
                if len(conflict_examples) < 10:
                    conflict_examples.append({
                        "ts": int(ts_s[i]), "ts_str": fmt_ts(int(ts_s[i])),
                        "kept": [rep(dn_s[g]), rep(up_s[g]), rep(d15_s[g])],
                        "dropped": [rep(dn_s[i]), rep(up_s[i]), rep(d15_s[i])],
                    })

    return {
        "n_raw": n_raw,
        "n_unique": int(starts.size),
        "n_dup_collapsed": n_dup_collapsed,
        "n_conflict": n_conflict,
        "conflict_examples": conflict_examples,
        "ts": ts_s[starts],
        "down": dn_s[starts],
        "up": up_s[starts],
        "down15": d15_s[starts],
    }


def rep(x) -> str:
    return repr(float(x))


# ----------------------------- ghi artifact -----------------------------
def write_market_bin(path: str, ts_s, dn_s, up_s, d15_s) -> int:
    n = int(ts_s.size)
    dt = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])
    assert dt.itemsize == 20, dt.itemsize
    rec = np.empty(n, dtype=dt)
    rec["ts"] = ts_s
    rec["down"] = dn_s
    rec["up"] = up_s
    rec["down15"] = d15_s
    with open(path, "wb") as f:
        f.write(struct.pack(">i", n))
        f.write(rec.tobytes())
    return n


def write_market_parquet(path: str, ts_s, dn_s, up_s, d15_s) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    tbl = pa.table(
        {
            "ts": pa.array(ts_s, type=pa.int64()),
            "down": pa.array(dn_s, type=pa.float32()),
            "up": pa.array(up_s, type=pa.float32()),
            "down15": pa.array(d15_s, type=pa.float32()),
        }
    )
    pq.write_table(tbl, path, compression="zstd")


# ----------------------------- kiểm tra -----------------------------
def validate(built, stats) -> dict:
    ts_s = built["ts"]
    dn_s = built["down"]
    up_s = built["up"]
    d15_s = built["down15"]
    out = {
        "n_objects_asinfo": EXPECTED_OBJECTS,
        "n_seen": stats["n_seen"],
        "n_rows_raw": built["n_raw"],
        "n_rows_unique_ts": built["n_unique"],
        "n_dup_collapsed": built["n_dup_collapsed"],
        "n_dup_conflict": built["n_conflict"],
        "dup_conflict_examples": built["conflict_examples"],
        "n_keyless": stats["n_keyless"],
        "n_no_time": stats["n_no_time"],
        "n_bad_data": stats["n_bad_data"],
        "n_uk_time_mismatch": stats["n_uk_time_mismatch"],
    }
    ts_min = int(ts_s[0]) if ts_s.size else None
    ts_max = int(ts_s[-1]) if ts_s.size else None
    out["ts_min"] = ts_min
    out["ts_max"] = ts_max
    out["ts_min_str"] = fmt_ts(ts_min) if ts_min is not None else None
    out["ts_max_str"] = fmt_ts(ts_max) if ts_max is not None else None
    diffs = np.diff(ts_s)
    out["n_non_increasing"] = int(np.count_nonzero(diffs <= 0))
    out["strictly_increasing"] = out["n_non_increasing"] == 0
    out["n_nan"] = int(np.count_nonzero(~np.isfinite(dn_s)) + np.count_nonzero(~np.isfinite(up_s)) + np.count_nonzero(~np.isfinite(d15_s)))
    out["zero_nan"] = out["n_nan"] == 0
    out["n_rows_equals_expected"] = out["n_rows_unique_ts"] == EXPECTED_OBJECTS
    return out


def spotcheck(client, parquet_path: str, samples, dup_ts_set) -> dict:
    import pyarrow.parquet as pq

    tbl = pq.read_table(parquet_path)
    ts = tbl.column("ts").to_numpy()
    dn = tbl.column("down").to_numpy()
    up = tbl.column("up").to_numpy()
    d15 = tbl.column("down15").to_numpy()

    # chọn 3 user_key mẫu mà ts KHÔNG bị trùng (tránh nhập nhằng gộp TreeMap)
    chosen = []
    for uk in samples:
        t = parse_ts(uk)
        if t in dup_ts_set:
            continue
        if uk not in [c[0] for c in chosen]:
            chosen.append((uk, t))
        if len(chosen) == 3:
            break
    if len(chosen) < 3:  # fallback: lấy bất kỳ
        for uk in samples:
            if uk not in [c[0] for c in chosen]:
                chosen.append((uk, parse_ts(uk)))
            if len(chosen) == 3:
                break

    res = []
    all_ok = True
    for k, t in chosen:
        _key, _meta, bins = client.get((NAMESPACE, SET_NAME, k))
        live = tuple(struct.unpack(">fff", bytes(bins["data"][:12])))
        j = int(np.searchsorted(ts, t))
        pq_ok = j < len(ts) and int(ts[j]) == t
        pq_vals = (float(dn[j]), float(up[j]), float(d15[j])) if pq_ok else None
        matches = pq_ok and all(np.float32(live[i]) == np.float32(pq_vals[i]) for i in range(3))
        live_time = int(bins.get("time", -1))
        item = {
            "key": k,
            "ts": t,
            "ts_str": fmt_ts(t),
            "time_bin": live_time,
            "time_bin_matches_parquet_ts": live_time == t,
            "live_down_up_down15": [rep(x) for x in live],
            "parquet_down_up_down15": [rep(x) for x in pq_vals] if pq_vals else None,
            "match": bool(matches),
        }
        all_ok = all_ok and matches
        res.append(item)
        log.info("SPOTCHECK %s ts=%s live=%s parquet=%s match=%s", k, fmt_ts(t), item["live_down_up_down15"], item["parquet_down_up_down15"], matches)
    return {"all_match": bool(all_ok), "items": res}


# ----------------------------- Kaggle -----------------------------
def _kaggle_env():
    env = dict(os.environ)
    env["KAGGLE_CONFIG_DIR"] = os.path.expanduser("~/.kaggle")
    return env


def _kaggle(args, label):
    log.info("kaggle %s", " ".join(args))
    r = subprocess.run(["kaggle"] + args, env=_kaggle_env(), capture_output=True, text=True)
    log.info("kaggle[%s] rc=%d out=%s err=%s", label, r.returncode, (r.stdout or "")[-3000:], (r.stderr or "")[-3000:])
    return r


def kaggle_upload(out_dir: str, files, version_note: str) -> dict:
    stage = os.path.join(out_dir, "kaggle_upload")
    os.makedirs(stage, exist_ok=True)
    meta = {"title": DATASET_TITLE, "id": DATASET_ID, "licenses": [{"name": "CC0-1.0"}]}
    with open(os.path.join(stage, "dataset-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    for src in files:
        dst = os.path.join(stage, os.path.basename(src))
        if os.path.exists(dst):
            os.remove(dst)
        try:
            os.link(src, dst)
        except OSError:
            import shutil

            shutil.copy2(src, dst)

    r = _kaggle(["datasets", "create", "-p", stage, "-r", "zip", "-t", "-q"], "create")
    created = r.returncode == 0
    if not created:
        blob = ((r.stdout or "") + (r.stderr or "")).lower()
        if ("already" in blob) or ("409" in blob) or ("exist" in blob):
            r = _kaggle(["datasets", "version", "-p", stage, "-m", version_note, "-r", "zip", "-t", "-q"], "version")
            created = r.returncode == 0
    return {"stage": stage, "create_ok": created, "create_rc": r.returncode,
            "create_out": (r.stdout or "")[-500:], "create_err": (r.stderr or "")[-500:]}


def kaggle_wait_ready(max_tries: int = 60, sleep_s: int = 10) -> dict:
    last = ""
    for i in range(max_tries):
        r = _kaggle(["datasets", "status", DATASET_ID], f"status{i}")
        txt = ((r.stdout or "") + (r.stderr or "")).strip()
        last = txt
        low = txt.lower()
        if ("ready" in low) or ("ok" in low) or ("complete" in low):
            if "error" not in low:
                return {"ready": True, "status": txt, "tries": i + 1}
        time.sleep(sleep_s)
    return {"ready": False, "status": last, "tries": max_tries}


def kaggle_roundtrip(out_dir: str, files, local_sha: dict) -> dict:
    import shutil
    import zipfile

    rt = os.path.join(out_dir, "rt")
    if os.path.isdir(rt):
        shutil.rmtree(rt)
    os.makedirs(rt, exist_ok=True)
    r = _kaggle(["datasets", "download", DATASET_ID, "-p", rt, "--unzip", "-q"], "download")
    if r.returncode != 0:
        for src in files:
            name = os.path.basename(src)
            _kaggle(["datasets", "download", DATASET_ID, "-f", name, "-p", rt, "-q"], f"download-{name}")
            zp = os.path.join(rt, name + ".zip")
            if os.path.exists(zp):
                with zipfile.ZipFile(zp) as z:
                    z.extractall(rt)
    res = {}
    for src in files:
        name = os.path.basename(src)
        dst = os.path.join(rt, name)
        if not os.path.exists(dst):
            res[name] = {"present": False, "local_sha256": local_sha[name]}
            continue
        h = sha256_file(dst)
        res[name] = {"present": True, "rt_sha256": h, "local_sha256": local_sha[name], "match": h == local_sha[name]}
    return res


# ----------------------------- main -----------------------------
def main():
    ap = argparse.ArgumentParser(description="READ-ONLY dump Aerospike market_data_object -> market.bin + parquet")
    ap.add_argument("--out-dir", default="~/marketdump", help="thư mục output")
    ap.add_argument("--host", default=AS_HOST)
    ap.add_argument("--port", type=int, default=AS_PORT)
    ap.add_argument("--skip-upload", action="store_true", help="bỏ bước Kaggle upload + round-trip")
    ap.add_argument("--skip-download-verify", action="store_true", help="bỏ bước tải ngược kiểm sha256")
    args = ap.parse_args()

    out_dir = os.path.expanduser(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    setup_logging(out_dir)

    log.info("==== marketdump START out_dir=%s ====", out_dir)
    df_before = df_report()
    log.info("df_before: %s", df_before)

    client, ts, down, up, d15, hasuk, samples, stats = scan_all(args.host, args.port)
    built = build_sorted(ts, down, up, d15, hasuk)
    log.info("build: raw=%d unique_ts=%d dup_collapsed=%d conflict=%d",
             built["n_raw"], built["n_unique"], built["n_dup_collapsed"], built["n_conflict"])

    bin_path = os.path.join(out_dir, "market.bin")
    pq_path = os.path.join(out_dir, "market.parquet")
    write_market_bin(bin_path, built["ts"], built["down"], built["up"], built["down15"])
    log.info("wrote %s", bin_path)
    write_market_parquet(pq_path, built["ts"], built["down"], built["up"], built["down15"])
    log.info("wrote %s", pq_path)

    val = validate(built, stats)
    log.info("VALIDATE %s", json.dumps(val, ensure_ascii=False))

    # tập ts trùng để tránh chọn nhầm khi spot-check
    dup_ts = set()
    if built["n_dup_collapsed"]:
        # ts trùng = ts xuất hiện >1 lần trong raw
        raw_ts = np.frombuffer(ts, dtype=np.int64)
        u, c = np.unique(raw_ts, return_counts=True)
        dup_ts = set(int(x) for x in u[c > 1])
    spot = spotcheck(client, pq_path, samples, dup_ts)
    try:
        client.close()
    except Exception:
        pass

    bin_sha = sha256_file(bin_path)
    pq_sha = sha256_file(pq_path)
    bin_bytes = os.path.getsize(bin_path)
    pq_bytes = os.path.getsize(pq_path)
    sha = {"market.bin": bin_sha, "market.parquet": pq_sha}
    log.info("sha256 market.bin=%s (%d bytes)", bin_sha, bin_bytes)
    log.info("sha256 market.parquet=%s (%d bytes)", pq_sha, pq_bytes)

    upload = {}
    roundtrip = {}
    if not args.skip_upload:
        files = [bin_path, pq_path]
        note = f"marketdump {datetime.now(GMT7).strftime('%Y-%m-%d')} n={built['n_unique']}"
        upload = kaggle_upload(out_dir, files, note)
        log.info("UPLOAD %s", json.dumps(upload, ensure_ascii=False))
        if upload.get("create_ok"):
            ready = kaggle_wait_ready()
            log.info("READY %s", json.dumps(ready, ensure_ascii=False))
            if ready.get("ready") and not args.skip_download_verify:
                roundtrip = kaggle_roundtrip(out_dir, files, sha)
                log.info("ROUNDTRIP %s", json.dumps(roundtrip, ensure_ascii=False))
                import shutil

                shutil.rmtree(os.path.join(out_dir, "rt"), ignore_errors=True)

    summary = {
        "generated_at": datetime.now(GMT7).isoformat(),
        "source": {
            "container": "aerospike-wfo",
            "host": args.host,
            "port": args.port,
            "namespace": NAMESPACE,
            "set": SET_NAME,
            "ts_source": "bin 'time' (getAllMarketDataFromAerospike: record.getLong(\"time\"))",
            "key_format": KEY_FMT + " (GMT+7) [chỉ để đối chiếu user_key]",
        },
        "n_objects_asinfo": EXPECTED_OBJECTS,
        "n_rows_unique_ts": built["n_unique"],
        "validate": val,
        "spotcheck": spot,
        "files": {
            "market.bin": {"bytes": bin_bytes, "sha256": bin_sha},
            "market.parquet": {"bytes": pq_bytes, "sha256": pq_sha},
        },
        "kaggle": {"dataset_id": DATASET_ID, "upload": upload, "roundtrip": roundtrip},
        "df_before": df_before,
        "df_after": df_report(),
    }
    with open(os.path.join(out_dir, "market_dump_summary.json"), "w") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)

    log.info("df_after: %s", summary["df_after"])
    log.info("==== marketdump END ====")
    log.info("SUMMARY %s", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
