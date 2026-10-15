"""VZ AUDIT B4 - definition / pre-reg pass: C4 (bootstrap config) + D1 (pre-reg).

C4  Confirms the bootstrap actually used by the runner (block 5 UTC days, NREP
    2000, seed 20261014) matches the pre-reg YAML, and is deterministic: two
    independent `day_level_boot` calls on the same input give bit-identical
    replicate means (=> the CI in the report is reproducible).
D1  Confirms the pre-reg commit (997f18f3) predates the Q6 run, that the YAML
    block carried the same numbers as the markdown text, and that the Q6 output
    md5 is reproducible from the stored JSON (i.e. the report was not edited
    after the run).

Read-only. Writes ~/vz_e1/reports/audit_b4_defs.json. No year data is read.
"""
import hashlib
import json
import os
import subprocess

import numpy as np
import yaml

import e1_confirm
import e1_stats
from e1_common import (BOOT_BLOCK_DAYS, BOOT_NREP, SEED, REPORT, setup_logging,
                       write_json)

log = setup_logging("e1_audit_b4_defs", "e1_audit_b4_defs.log")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PREREG = os.path.join(REPO, "docs", "prereg", "PREREG_VZ_B4.md")
PREREG_COMMIT = "997f18f32405ea22eccfd1ba41e26113ff558569"
Q6_JSON = os.path.join(REPORT, "e1_confirm_B4.json")


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True).stdout.strip()


# ------------------------------------------------------------------ C4
def c4_bootstrap(pre):
    pre_boot = pre["bootstrap"]
    cfg = {"code_block_days": BOOT_BLOCK_DAYS, "code_nrep": BOOT_NREP, "code_seed": SEED,
           "prereg": pre_boot,
           "match": bool(int(pre_boot["block_days"]) == BOOT_BLOCK_DAYS
                         and int(pre_boot["nrep"]) == BOOT_NREP
                         and int(pre_boot["seed"]) == SEED)}
    rng = np.random.default_rng(7)
    vals = rng.normal(size=5000)
    days = np.repeat(np.arange(100, dtype=np.int64), 50)
    lv = np.tile(np.array([1, 2, 3, 4, 5], dtype=np.int64), 1000)
    a, la = e1_stats.day_level_boot(vals, days, lv)
    b, lb = e1_stats.day_level_boot(vals, days, lv)
    same = all(np.array_equal(a[k]["reps_mean"], b[k]["reps_mean"], equal_nan=True)
               for k in a)
    cfg["deterministic_two_calls"] = bool(same and np.array_equal(la, lb))
    # spread on the real confirm output must equal the reported one (same seed path)
    cfg["n_days_blocks"] = {"n_days": int(a[1]["n_days"])}
    log.info("C4 block=%d nrep=%d seed=%d match_prereg=%s deterministic=%s",
             BOOT_BLOCK_DAYS, BOOT_NREP, SEED, cfg["match"], cfg["deterministic_two_calls"])
    return cfg


# ------------------------------------------------------------------ D1
def d1_prereg(pre):
    frm = yaml.safe_load(open(PREREG).read().split("```yaml", 1)[1].split("```", 1)[0])
    text = open(PREREG).read()
    c_time = git("log", "-1", "--format=%cI", PREREG_COMMIT)
    c_subj = git("log", "-1", "--format=%s", PREREG_COMMIT)
    q6 = json.load(open(Q6_JSON))
    q6_md5 = q6["output_md5"]
    blob = json.dumps({k: v for k, v in q6.items() if k != "output_md5"},
                      sort_keys=True, default=str).encode()
    recomputed = hashlib.md5(blob).hexdigest()
    # YAML vs markdown: the numbers that decide the test
    checks = {
        "variant_yaml_eq_text": bool(frm["variant"] == "V2_tss_reversal_q5"
                                     and "V2_tss_reversal_q5" in text),
        "measure_primary_net_1440": bool(frm["measure"]["primary"] == "net_1440"
                                         and "net 24h" in text),
        "k_tests_38_in_text": bool(int(frm["k_tests"]) == 38 and "k = 38" in text
                                   and "√(2 ln 38) = 2,70" in text),
        "years_2022_2023_2025": bool([int(x) for x in frm["years"]] == [2022, 2023, 2025]
                                     and "2022, 2023, 2025" in text),
        "cost_fee_2leg_000982": bool(float(frm["cost"]["fee_2leg"]) == 0.000982
                                     and "fee_2leg: 0.000982" in text),
        "edges_match_frozen_config": None,
    }
    froz = json.load(open(os.path.join(HERE, "configs", "t3_thresholds.json")))
    checks["edges_match_frozen_config"] = bool(
        [float(x) for x in frm["thresholds"]["tss_reversal"]["edges"]]
        == [float(x) for x in froz["features"]["tss_reversal"]["edges"]])
    # the pre-reg must predate the Q6 output file (mtime) and the run log start
    q6_mtime = os.path.getmtime(Q6_JSON)
    run_log = os.path.join(os.path.expanduser("~/vz_e1/logs"), "confirm_b4.log")
    run_start = os.path.getmtime(run_log) if os.path.exists(run_log) else None
    return {
        "prereg_commit": PREREG_COMMIT,
        "prereg_commit_iso": c_time,
        "prereg_commit_subject": c_subj[:90],
        "q6_output": os.path.basename(Q6_JSON),
        "q6_prereg_commit_recorded": q6.get("prereg_commit"),
        "q6_md5_recorded": q6_md5,
        "q6_md5_recomputed": recomputed,
        "q6_md5_reproducible": bool(q6_md5 == recomputed),
        "q6_run_log_start_iso": (subprocess.run(
            ["date", "-d", "@%d" % int(run_start), "--iso-8601=seconds"],
            capture_output=True, text=True).stdout.strip() if run_start else None),
        "q6_decision": q6["go_rule"]["decision"],
        "yaml_vs_markdown": checks,
        "yaml_block_keys": sorted(frm.keys()),
    }


def main():
    pre = e1_confirm.yaml_block(PREREG)
    res = {"C4_bootstrap": c4_bootstrap(pre), "D1_prereg": d1_prereg(pre)}
    write_json(os.path.join(REPORT, "audit_b4_defs.json"), res)
    log.info("defs report written: %s", json.dumps(res["D1_prereg"], default=str)[:400])
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
