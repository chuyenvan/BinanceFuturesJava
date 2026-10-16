"""Khoi phuc vz-metrics5m + vz-funding: upload 1 version chua MOI nam tu file thang trong ~/vz/out, verify sha256."""
import logging
import os
import sys

sys.path.insert(0, "/home/ubuntu/claude_master/vz_wt/research/data/vz")
import vz_phase1 as P  # noqa: E402

log = logging.getLogger("recover")
for ds in ["metrics5m", "funding"]:
    outs = P.combine_all_years(ds)
    upload = os.path.join(P.VZ, "upload", "vz-" + ds)
    have = sorted(f for f in os.listdir(upload) if f.endswith(".parquet"))
    log.info("%s staging %s", ds, have)
    P.write_readme_year(upload, "vz-" + ds, "all years", {"gov": "DEV + HOLDOUT 2026 (da dung) theo nam; xem VZ_RESEARCH_SPLIT", "rows": {}})
    full = P.upload_auto("vz-" + ds, upload)
    if not P.verify_all(full, upload):
        raise SystemExit("VERIFY FAIL %s" % full)
    log.info("UPLOAD+VERIFY OK %s files=%s", full, have)
    P.clear_staging(upload)
log.info("RECOVER DONE")
