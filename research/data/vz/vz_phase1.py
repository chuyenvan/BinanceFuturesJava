"""VZ Phase 1b driver - run year by year: 2024 -> 2025 -> 2023 -> 2022 -> 2021 -> 2026 -> 2020.

Per month: fetch -> build -> validate (V1-V6, 2020 sealed = no V4) -> drop zips.
Per year : pack + upload each dataset (private), round-trip verify ALL files,
           update docs/data/VZ_REGISTRY.md, delete local year, notify owner.

Idempotent: state files and per-month reports make reruns skip finished work.
Long job: launch with `setsid nohup ... &` (see section 5 of VZ_DATA_LAKE.md).
"""
import gzip
import hashlib
import json
import logging
import os
import subprocess
import sys
import time

VZ = os.path.expanduser("~/vz")
CODE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.expanduser("~/claude_master/vz_wt")
REG = os.path.join(WT, "docs/data/VZ_REGISTRY.md")
NOTIFY = os.path.join(VZ, "notify.sh")
UPLOAD = os.path.join(CODE, "vz_upload.sh")
PY = sys.executable

YEARS = [
    ("2024", [f"2024-{m:02d}" for m in range(1, 13)]),
    ("2025", [f"2025-{m:02d}" for m in range(1, 13)]),
    ("2023", [f"2023-{m:02d}" for m in range(1, 13)]),
    ("2022", [f"2022-{m:02d}" for m in range(1, 13)]),
    ("2021", [f"2021-{m:02d}" for m in range(1, 13)]),
    ("2026", [f"2026-{m:02d}" for m in range(1, 10)]),
    ("2020", [f"2020-{m:02d}" for m in range(1, 13)]),
]
SEALED = {"2020"}
NEEDED = {
    "kline1m": ["kline1m"],
    "basis1m": ["premiumIndex1m", "markPrice1m", "indexPrice1m"],
    "metrics5m": ["metrics"],
    "funding": ["fundingRate"],
}
DS_ORDER = ["kline1m", "basis1m", "metrics5m", "funding"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("phase1")


def env():
    e = dict(os.environ)
    e["VZ_KEEP_ZIP"] = "1"  # V6 rebuild needs zips; we delete them per month
    return e


def run(args, check=True):
    log.info("RUN %s", " ".join(args))
    r = subprocess.run(args, cwd=CODE, env=env())
    if check and r.returncode != 0:
        raise RuntimeError("command failed rc=%d: %s" % (r.returncode, " ".join(args)))
    return r.returncode


def notify(msg):
    try:
        subprocess.run([NOTIFY, msg], check=False)
    except Exception as e:  # noqa: BLE001
        log.warning("notify failed: %s", e)


def fetch_done(typ, ym):
    p = os.path.join(VZ, "state", typ, ym + ".json")
    if not os.path.exists(p):
        return False
    try:
        return bool(json.load(open(p)).get("fetch_done"))
    except Exception:  # noqa: BLE001
        return False


def build_done(ds, ym):
    """True only when the build state exists AND the output parquet is present,
    non-empty and its size matches the recorded one (guards pilot/empty builds)."""
    sp = os.path.join(VZ, "state", "build", ds, ym + ".json")
    op = os.path.join(VZ, "out", ds, ym[:4], ym + ".parquet")
    if not (os.path.exists(sp) and os.path.exists(op)):
        return False
    try:
        d = json.load(open(sp))
    except Exception:  # noqa: BLE001
        return False
    sz = os.path.getsize(op)
    if d.get("rows", 0) <= 0 or sz < 2000:
        return False
    return d.get("parquet_bytes", sz) == sz


def zips_present(typ, ym):
    d = os.path.join(VZ, "tmp", typ, ym)
    if not os.path.isdir(d):
        return 0
    return sum(1 for f in os.listdir(d) if f.endswith(".zip"))


def ensure_fetch(typ, ym):
    """Fetch if needed. Also refetch when the fetch state says done but the zips
    are gone (e.g. the pilot month, whose zips were deleted after parsing)."""
    p = os.path.join(VZ, "state", typ, ym + ".json")
    done, n_ok = False, 0
    if os.path.exists(p):
        try:
            d = json.load(open(p))
            done, n_ok = bool(d.get("fetch_done")), int(d.get("n_ok", 0))
        except Exception:  # noqa: BLE001
            done = False
    present = zips_present(typ, ym)
    if done and present > 0 and present >= n_ok:
        return
    if os.path.exists(p):
        os.remove(p)
        log.warning("zips missing for %s %s (state done n_ok=%d present=%d) -> refetch",
                    typ, ym, n_ok, present)
    run([PY, "vz_fetch.py", typ, ym])


def report_ok(ds, ym):
    p = os.path.join(VZ, "reports", "%s-%s.validate.json" % (ds, ym))
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    st = [d[k]["status"] for k in ["V1", "V2", "V3", "V4", "V5", "V6"] if k in d]
    ok = all(s in ("PASS", "SKIP") for s in st)
    return {"ok": ok, "status": st}


def do_month(year, ym):
    for ds in DS_ORDER:
        bd = build_done(ds, ym)
        r = report_ok(ds, ym)
        if bd and r and r["ok"]:
            continue
        for typ in NEEDED[ds]:
            ensure_fetch(typ, ym)
        if not bd:
            run([PY, "vz_build.py", ds, ym])
        run([PY, "vz_validate.py", ds, ym])  # build or stale/failed report -> validate
        r = report_ok(ds, ym)
        if not r["ok"]:
            raise RuntimeError("VALIDATE FAIL %s %s -> %s" % (ds, ym, r["status"]))
    # drop zips for the month
    for ds in DS_ORDER:
        for typ in NEEDED[ds]:
            d = os.path.join(VZ, "tmp", typ, ym)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    os.remove(os.path.join(d, f))


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def combine_year(ds, year):
    """metrics5m/funding: concat monthly parquet of a year into one yearly file."""
    import pandas as pd
    ydir = os.path.join(VZ, "out", ds, year)
    outs = glob_parquet(ydir)
    if not outs:
        return None
    parts = [pd.read_parquet(p) for p in outs]
    df = pd.concat(parts, ignore_index=True)
    df = df.sort_values(["sym", "ts"], kind="mergesort")
    upload = os.path.join(VZ, "upload", "vz-" + ds)
    os.makedirs(upload, exist_ok=True)
    dst = os.path.join(upload, "%s-%s.parquet" % (ds, year))
    df.to_parquet(dst, index=False, compression="zstd", compression_level=9)
    log.info("combine %s %s -> %s rows=%d", ds, year, dst, len(df))
    return dst


def glob_parquet(d):
    import glob
    return sorted(glob.glob(os.path.join(d, "*.parquet")))


def write_readme_year(upload, slug, rg, meta):
    lines = [
        "# " + slug, "",
        "Binance USDⓈ-M (futures/um) Vision lake - dataset **%s**." % rg,
        "Source: data.binance.vision. Pipeline: docs/plan/VZ_DATA_LAKE.md + VZ_PHASE1.md",
        "Encoding: ts=DELTA_BINARY_PACKED, sym=dictionary, floats plain, zstd-9.",
        "Governance: %s" % meta["gov"], "",
        "## Files", "| file | rows | bytes | sha256 |", "|---|---|---|---|",
    ]
    for f in sorted(os.listdir(upload)):
        if not f.endswith(".parquet"):
            continue
        p = os.path.join(upload, f)
        lines.append("| %s | %s | %d | %s |" % (
            f, meta["rows"].get(f, ""), os.path.getsize(p), sha256(p)))
    lines += ["", "validate: V1-V6 per month (see registry / Kaggle files).", ""]
    open(os.path.join(upload, "README.md"), "w").write("\n".join(lines))


def upload_auto(slug, upload):
    """version the dataset if it exists, otherwise create it. Returns the mode used."""
    rc = run(["bash", UPLOAD, slug, upload, "version"], check=False)
    if rc != 0:
        log.warning("version failed for %s -> create", slug)
        rc = run(["bash", UPLOAD, slug, upload, "create"], check=False)
        if rc != 0:
            raise RuntimeError("upload create failed for %s" % slug)
        return "create"
    return "version"


def remote_files(full_id):
    r = subprocess.run(["kaggle", "datasets", "files", full_id],
                       capture_output=True, text=True, env=os.environ)
    rows = []
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(".parquet"):
            rows.append((parts[0], parts[1]))
    return rows


def verify_all(full_id, upload):
    """download the dataset back and compare sha256 of every parquet."""
    import tempfile
    import shutil
    # per-file download (CLI 1.6.17 full-dataset download returns 404 for these)
    w = tempfile.mkdtemp(dir=os.path.join(VZ, "tmp"))
    ok = True
    for f in sorted(os.listdir(upload)):
        if not f.endswith(".parquet"):
            continue
        r = subprocess.run(["kaggle", "datasets", "download", "-d", full_id,
                            "-f", f, "-p", w, "--unzip"],
                           capture_output=True, text=True, env=os.environ)
        got = os.path.join(w, f)
        if r.returncode != 0 or not os.path.exists(got):
            log.error("verify %s download failed rc=%d %s", f, r.returncode, r.stderr[-200:])
            ok = False
            continue
        if sha256(os.path.join(upload, f)) != sha256(got):
            log.error("verify %s sha256 MISMATCH", f)
            ok = False
        os.remove(got)
    shutil.rmtree(w, ignore_errors=True)
    return ok


def registry_append(text):
    with open(REG, "a") as fh:
        fh.write(text)


def git_commit(msg):
    subprocess.run(["git", "add", "-A"], cwd=WT, check=False)
    subprocess.run(["git", "commit", "-m", msg], cwd=WT, check=False)
    subprocess.run(["git", "push", "origin", "data/vz-lake"], cwd=WT, check=False)


def year_stats(year, months):
    import glob
    stats = {}
    for ds in DS_ORDER:
        if ds in ("metrics5m", "funding"):
            continue
        tot = 0
        rows = 0
        syms = 0
        for ym in months:
            p = os.path.join(VZ, "out", ds, year, ym + ".parquet")
            if os.path.exists(p):
                tot += os.path.getsize(p)
            sd = os.path.join(VZ, "state", "build", ds, ym + ".json")
            if os.path.exists(sd):
                d = json.load(open(sd))
                rows += d.get("rows", 0)
                syms = max(syms, d.get("n_sym", 0))
        stats[ds] = {"bytes": tot, "rows": rows, "syms": syms}
    return stats


def main():
    only = sys.argv[1:] or None
    t_start = time.time()
    summary = {}
    for year, months in YEARS:
        if only and year not in only:
            continue
        log.info("############ YEAR %s ############", year)
        y0 = time.time()
        for ym in months:
            log.info("---- %s ----", ym)
            do_month(year, ym)
        # upload per ds
        stats = year_stats(year, months)
        slug_year = "2020s" if year in SEALED else year
        gov = ("SEALED - chi dung theo docs/plan/BACKCAST_RESERVOIR.md" if year in SEALED
               else ("HOLDOUT DA DUNG (HO4) - khong dung de chon/tune" if year == "2026"
                     else "DEV"))
        for ds in ["kline1m", "basis1m"]:
            upload = os.path.join(VZ, "upload", "vz-%s-%s" % (ds, year))
            os.makedirs(upload, exist_ok=True)
            for ym in months:
                src = os.path.join(VZ, "out", ds, year, ym + ".parquet")
                dst = os.path.join(upload, "%s-%s.parquet" % (ds, ym))
                if os.path.exists(src) and not os.path.exists(dst):
                    os.link(src, dst)
            meta = {"gov": gov, "rows": {}}
            write_readme_year(upload, "vz-%s-%s" % (ds, year), gov, meta)
            slug = "vz-%s-%s" % (ds, slug_year)
            full = "chuyendinh/" + slug
            upload_auto(slug, upload)
            ok = verify_all(full, upload)
            if not ok:
                raise RuntimeError("VERIFY FAIL %s" % full)
            log.info("UPLOAD+VERIFY OK %s", full)
            registry_append(
                "\n## P1b %s (%s)\n- slug `%s`; files %d; bytes %d; rows %d; syms~%d; gov %s\n" % (
                    ds, year, full, len(months), stats[ds]["bytes"], stats[ds]["rows"],
                    stats[ds]["syms"], gov))
            # delete local year (only kline/basis)
            import glob as _g
            for p in _g.glob(os.path.join(VZ, "out", ds, year, "*")):
                os.remove(p)
        # metrics5m / funding shared datasets
        for ds in ["metrics5m", "funding"]:
            p = combine_year(ds, year)
            if p is None:
                continue
            upload = os.path.join(VZ, "upload", "vz-" + ds)
            meta = {"gov": gov, "rows": {}}
            write_readme_year(upload, "vz-" + ds, "all years", meta)
            upload_auto("vz-" + ds, upload)
        git_commit("data(vz): Phase1b year %s - build+validate+upload vz-kline1m/basis1m-%s; metrics/funding updated" % (year, slug_year))
        ymsg = ("[VZ P1] nam %s xong: kline %s MB / basis %s MB; V1-V6 PASS; upload + verify sha256 OK; %.1f h" % (
            year, round(stats["kline1m"]["bytes"] / 1e6), round(stats["basis1m"]["bytes"] / 1e6),
            (time.time() - y0) / 3600.0))
        notify(ymsg)
        summary[year] = stats
        with open(os.path.join(VZ, "reports", "phase1b_summary.json"), "w") as fh:
            json.dump(summary, fh, indent=1)
    notify("[VZ P1] 1b HOAN TAT tat ca cac nam trong %.1f h" % ((time.time() - t_start) / 3600.0))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        log.exception("PHASE1b FATAL")
        try:
            notify("[VZ P1] 1b DUNG do loi: %s (xem ~/vz/logs/phase1b.log)" % str(e)[:300])
        except Exception:  # noqa: BLE001
            pass
        sys.exit(1)
