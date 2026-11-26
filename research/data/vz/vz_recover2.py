"""Buoc 2 khoi phuc: verify metrics5m (cho ready + thu lai), roi upload+verify funding moi nam."""
import logging
import os
import sys
import time

sys.path.insert(0, "/home/ubuntu/claude_master/vz_wt/research/data/vz")
import vz_phase1 as P  # noqa: E402

log = logging.getLogger("recover2")


def verify_retry(full, upload, tries=8):
    for i in range(tries):
        P.wait_ready(full)
        if P.verify_all(full, upload):
            return True
        log.info("verify %s chua OK (lan %d) -> cho 120s", full, i + 1)
        time.sleep(120)
    return False


for ds in ["metrics5m", "funding"]:
    full = "chuyendinh/vz-" + ds
    upload = os.path.join(P.VZ, "upload", "vz-" + ds)
    if ds == "funding":
        P.combine_all_years(ds)
        P.write_readme_year(upload, "vz-" + ds, "all years", {"gov": "DEV + HOLDOUT 2026 (da dung) theo nam", "rows": {}})
        P.upload_auto("vz-" + ds, upload)
    have = sorted(f for f in os.listdir(upload) if f.endswith(".parquet"))
    log.info("%s staging %s", ds, have)
    if not verify_retry(full, upload):
        raise SystemExit("VERIFY FAIL %s" % full)
    log.info("UPLOAD+VERIFY OK %s files=%s", full, have)
    P.clear_staging(upload)
log.info("RECOVER2 DONE")
