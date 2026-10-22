#!/usr/bin/env python3
"""TSX_V3_JAVA chan doan VA5 (L45 S99/S2024 lech +1 cum hoan vs Java): liet ke cum hoan tai dung khong co trong P0 / X14."""
import json
import logging
import sys

import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/tsx_v3_java")
import score as S  # noqa: E402

log = logging.getLogger("diag")
for arm, s in (("L45", "S99"), ("L45", "S2024"), ("L45", "A1"), ("T25", "S99")):
    d = S.DA.load(S.tag_of(arm, s))
    run = dict(c=S.DA.clusters(d))
    p0 = S.DA.clusters(S.DA.load("gqsf-" + s.lower()))
    x = S.DA.clusters(S.DA.load(S.tag_of("X14", s)))
    df = S.deferred(run, p0, S.days_set(arm), S.cap_min(arm))
    kp = set(zip(p0["sym"], p0["t0"]))
    kx = set(zip(x["sym"], x["t0"]))
    df["in_p0"] = [k in kp for k in zip(df["sym"], df["t0"])]
    df["in_x14"] = [k in kx for k in zip(df["sym"], df["t0"])]
    xm = x.set_index(["sym", "t0"])
    lst = []
    for _, r in df[~df["in_p0"]].iterrows():
        k = (r["sym"], r["t0"])
        xa = xm.loc[k] if k in xm.index else None
        if isinstance(xa, pd.DataFrame):
            xa = xa.iloc[0]
        lst.append(dict(sym=r["sym"], t0=str(r["t0"]), te=str(r["te"]), age_h=round(r["age_min"] / 60, 1), st=r["st"], exit=r["exit"],
                        mark=str(r["mark_day"].date()), x14_age_h=None if xa is None else round(xa["age_min"] / 60, 1),
                        x14_st=None if xa is None else xa["st"]))
    log.warning("%s %s: n_recon=%d, khong-trong-P0=%d (exit %s), trong X14 %d", arm, s, len(df), int((~df["in_p0"]).sum()),
                df.loc[~df["in_p0"], "exit"].value_counts().to_dict(), int(df["in_x14"].sum()))
    for z in lst:
        log.warning("   %s", json.dumps(z))
