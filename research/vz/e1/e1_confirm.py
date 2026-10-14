"""VZ E1 - T7 confirmation runner (build only; NOT run on confirmation years).

    python3 e1_confirm.py --prereg docs/prereg/PREREG_VZ_<NAME>.md --years 2022,2023,2025

Reads the YAML block of the pre-registration (family, variant, thresholds fixed
from 2024, measure, GO rule, k tests for the CI widening sqrt(2 ln k)), then
REFUSES unless that pre-reg file is committed and clean in git. Writes the
result together with the output md5 and the pre-reg commit hash.

Only families whose evaluator is implemented here can run (H-B in v1). This
runner is intentionally allowed to run on 2024 (smoke) only; the confirmation
years' datasets are not part of the readable lake yet (docs/plan/VZ_RESEARCH_SPLIT.md),
so requesting them raises rather than silently reading them.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import yaml

import e1_t3
from e1_common import REPORT, setup_logging, write_json

log = setup_logging("e1_confirm", "e1_confirm.log")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIRM_YEARS = {"2021", "2022", "2023", "2025"}
SMOKE_YEARS = {"2024"}
REQUIRED = ("name", "family", "variant", "thresholds", "measure", "go_rule", "k_tests")


def yaml_block(path):
    text = open(path).read()
    if "```yaml" not in text:
        raise SystemExit("no ```yaml block in %s" % path)
    body = text.split("```yaml", 1)[1].split("```", 1)[0]
    return yaml.safe_load(body)


def git_state(path):
    rel = os.path.relpath(os.path.abspath(path), REPO)
    log_out = subprocess.run(["git", "log", "--oneline", "--", rel], cwd=REPO,
                             capture_output=True, text=True).stdout.strip()
    diff = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    return {"committed": bool(log_out), "dirty": bool(diff), "commit": commit,
            "rel": rel, "log": log_out}


def build_cfg(prereg):
    th = prereg["thresholds"]
    cfg = {"date": "prereg", "features": {}}
    for k, v in th.items():
        if isinstance(v, dict):
            cfg["features"][k] = v
    return cfg


def run(prereg_path, years):
    gs = git_state(prereg_path)
    if not gs["committed"]:
        raise SystemExit("REFUSE: pre-reg %s is not committed (git log empty)" % prereg_path)
    if gs["dirty"]:
        raise SystemExit("REFUSE: pre-reg %s has uncommitted changes" % prereg_path)
    pre = yaml_block(prereg_path)
    missing = [k for k in REQUIRED if k not in pre]
    if missing:
        raise SystemExit("REFUSE: pre-reg missing keys %s" % missing)
    yrs = [y.strip() for y in years.split(",") if y.strip()]
    unsupported = [y for y in yrs if y not in SMOKE_YEARS and y not in CONFIRM_YEARS]
    if unsupported:
        raise SystemExit("REFUSE: unknown years %s" % unsupported)
    if set(yrs) & CONFIRM_YEARS:
        raise SystemExit("REFUSE: confirmation years %s are not readable in this lake "
                         "(only 2024); run this runner only once their datasets exist"
                         % sorted(set(yrs) & CONFIRM_YEARS))
    fam = pre["family"]
    variant = pre["variant"]
    if fam.lower().startswith("h-b"):
        cfg = build_cfg(pre)
        ev = e1_t3.load_events()
        out = e1_t3.evaluate_variant(variant, cfg, ev)
    else:
        raise SystemExit("REFUSE: family %s evaluator not implemented in this runner (v1: H-B)" % fam)
    k = int(pre["k_tests"])
    widen = float(np.sqrt(2 * np.log(max(k, 2))))
    res = {"prereg": pre, "prereg_commit": gs["commit"], "years": yrs,
           "ci_widen_factor_sqrt2lnk": widen, "result": out}
    blob = json.dumps(res, sort_keys=True, default=str).encode()
    res["output_md5"] = hashlib.md5(blob).hexdigest()
    name = str(pre["name"]).replace(" ", "_")
    outpath = os.path.join(REPORT, "e1_confirm_%s.json" % name)
    write_json(outpath, res)
    log.info("confirm %s -> %s md5=%s", name, outpath, res["output_md5"])
    return res


def smoke_check(prereg_path):
    """Assert the runner reproduces the frozen T3 numbers bit-exactly."""
    res = run(prereg_path, "2024")
    rep = json.load(open(os.path.join(REPORT, "e1_t3.json")))
    variant = res["prereg"]["variant"]
    ref = [v for v in rep["variants"] if v["variant"] == variant]
    if not ref:
        return {"pass": False, "reason": "T3 report has no variant %s" % variant}
    ref = ref[0]
    for col in ("net_60", "net_240"):
        for lv, d in res["result"][col].items():
            for stat in ("mean", "median", "hit_rate", "n"):
                a, b = d[stat], ref[col][lv][stat]
                if isinstance(a, float):
                    if not (np.isnan(a) and np.isnan(b)) and a != b:
                        return {"pass": False, "why": (col, lv, stat, a, b)}
                elif a != b:
                    return {"pass": False, "why": (col, lv, stat, a, b)}
    return {"pass": True, "variant": variant}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--years", default="2022,2023,2025")
    ap.add_argument("--smoke-check", action="store_true")
    a = ap.parse_args()
    if a.smoke_check:
        print(json.dumps(smoke_check(a.prereg), default=str))
    else:
        print(json.dumps(run(a.prereg, a.years), default=str))
