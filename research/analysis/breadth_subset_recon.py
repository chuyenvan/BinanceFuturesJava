"""[BREADTH SUBSET B8] RECON 0-sim: gate-profile per-year cho 5 universe
{all, top50, top30, major, alt} + book-composition T170 (majors/alts) + cong GO/NO-GO (§1.3).
Nguon: trend_rank_ic.load_closes (CLOSES_1H.bin, ts<2026-01-01 = HOLDOUT rule), map_kaggle.csv,
printDone.csv T170 (level=PREDICT_SYMBOL_TRADE). Tai dung breadth_regime.up_matrix/
breadth_from_up_matrix va breadth_robust.continuous_gate (gate_up=1.0/down=1.7/thr=0.5, KHOA).
0-sim: KHONG chay Java, KHONG build, KHONG sua .java. Logging module, cam print().
Chay: cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/breadth_subset_recon.py
Ghi: research/analysis/out/breadth_subset_recon.json
"""
import csv
import json
import logging
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trend_rank_ic as T  # noqa: E402  (load_closes)
import breadth_regime as BR  # noqa: E402  (up_matrix, breadth_from_up_matrix, ...)
import breadth_robust as RB  # noqa: E402  (continuous_gate, GATE_UP/DOWN/THR)

logging.basicConfig(level=logging.INFO, format="%(message)s")
L = logging.getLogger("brsubset")

OUT_JSON = os.path.join(HERE, "out", "breadth_subset_recon.json")
MAP_KAGGLE = "/home/ubuntu/map_kaggle.csv"
PRINTDONE = "/home/ubuntu/java/devrun/X1_GS_T170_2021_REPRO/storage/printDone.csv"

# Majors KHOA TRUOC (market-cap-top on dinh 2021-2025), KHONG doi sau khi thay ket qua.
MAJOR_NAMES = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT",
               "LINK", "TRX", "MATIC", "POL", "LTC", "BCH"]


def load_symmap():
    sym2id = {}
    with open(MAP_KAGGLE) as f:
        r = csv.DictReader(f)
        for d in r:
            sym2id[d["symbol"]] = int(d["symId"])
    return sym2id


def base_name(sym):
    for q in ("USDT", "USDC", "BUSD"):
        if sym.endswith(q):
            return sym[:-len(q)]
    return sym


def major_symids(sym2id):
    ids = set()
    for s, sid in sym2id.items():
        if base_name(s) in MAJOR_NAMES:
            ids.add(sid)
    return ids


def gate_per_year(score_arr, dates):
    out = {}
    for y in (2021, 2022, 2023, 2024, 2025):
        m = (dates.year == y)
        v = score_arr[m]
        v = v[np.isfinite(v)]
        if len(v) == 0:
            out[str(y)] = None
            continue
        g = np.array([RB.continuous_gate(x) for x in v])
        out[str(y)] = dict(n=int(len(v)), score_mean=float(v.mean()),
                           gate_mean=float(g.mean()), gate_median=float(np.median(g)))
    return out


def book_composition():
    rows = []
    with open(PRINTDONE) as f:
        r = csv.DictReader(f)
        for d in r:
            if d.get("level") != "PREDICT_SYMBOL_TRADE":
                continue
            sym = (d.get("sym") or "").strip()
            start = (d.get("start") or "").strip()
            yr = start[:4] if len(start) >= 4 and start[:4].isdigit() else "NA"
            rows.append((yr, sym, base_name(sym) in MAJOR_NAMES))
    total = len(rows)
    maj = sum(1 for _, _, m in rows if m)
    comp = {"total": total, "n_major": maj, "n_alt": total - maj,
            "pct_major": (100.0 * maj / total if total else None),
            "pct_alt": (100.0 * (total - maj) / total if total else None), "per_year": {}}
    for y in sorted(set(r[0] for r in rows)):
        yr = [r for r in rows if r[0] == y]
        m = sum(1 for _, _, mm in yr if mm)
        comp["per_year"][y] = dict(total=len(yr), n_major=m, n_alt=len(yr) - m,
                                   pct_major=(100.0 * m / len(yr) if yr else None))
    comp["major_positions"] = sorted(Counter(s for _, s, mm in rows if mm).items())
    comp["top20_symbols"] = Counter(s for _, s, _ in rows).most_common(20)
    return comp


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    sym2id = load_symmap()
    majors = major_symids(sym2id)
    L.info("majors symIds (%d): %s", len(majors), sorted(majors))

    df = T.load_closes()
    present = sorted(int(s) for s in df["sym"].unique())
    daily = BR.build_daily_close_by_sym(df, present)
    day0, day1 = BR.day_id(BR.SIM0), BR.day_id(BR.SIM1)
    day_range = np.arange(day0, day1 + 1)
    dates = pd.to_datetime(day_range.astype(np.int64) * BR.DAY_MS, unit="ms")

    majors_present = sorted(s for s in present if s in majors)
    universes = {
        "all": present,
        "top50": [s for s in present if s <= 50],
        "top30": [s for s in present if s <= 30],
        "major": majors_present,
        "alt": [s for s in present if s not in majors],
    }
    for lbl, syms in universes.items():
        L.info("universe %s: %d symId", lbl, len(syms))

    result = {"meta": dict(sim0=BR.SIM0, sim1=BR.SIM1, ma=200, thr_pct=50.0,
                           gate_up=RB.GATE_UP, gate_down=RB.GATE_DOWN, gate_thr=RB.GATE_THR_SCORE,
                           major_names=MAJOR_NAMES, major_symids=sorted(majors),
                           major_symids_present=majors_present, n_present=len(present),
                           note="top30/50 = symId<=N (PROXY thu tu niem yet, giong B5/6/7). "
                                "major/alt theo map_kaggle.csv + MAJOR_NAMES khoa truoc. "
                                "gate=continuous_gate(1.0/1.7/0.5) causal MA200/thr50.")}

    gate_profile = {}
    for lbl, syms in universes.items():
        up_mat, _ = BR.up_matrix(daily, syms, day_range, 200)
        breadth, _ = BR.breadth_from_up_matrix(up_mat)
        gp = gate_per_year(breadth / 100.0, dates)
        gate_profile[lbl] = gp
        L.info("gate_mean/nam [%-5s]: %s", lbl,
               {y: (None if gp[y] is None else round(gp[y]["gate_mean"], 4)) for y in sorted(gp)})
    result["gate_profile_per_year"] = gate_profile

    comp = book_composition()
    result["book_composition_t170"] = comp
    L.info("BOOK-COMP T170: total=%d major=%.2f%% alt=%.2f%% (major_positions=%s)",
           comp["total"], comp["pct_major"], comp["pct_alt"], comp["major_positions"])
    for y in sorted(comp["per_year"]):
        pc = comp["per_year"][y]
        L.info("  %s: total=%d major=%d (%.2f%%)", y, pc["total"], pc["n_major"], pc["pct_major"])

    pm = comp["pct_major"]
    if pm is not None and pm < 40:
        rel, how = "alt", "book alt-heavy (major<40%)"
    elif pm is not None and pm > 60:
        rel, how = "major", "book major-heavy (major>60%)"
    else:
        rel, how = "composite", "book mix ~50/50 -> book-weighted composite"
    result["relevant_breadth_choice"] = dict(pct_major=pm, rel_universe=rel, how=how)
    L.info("RELEVANT-BREADTH: %s (%s)", rel, how)

    def gm(prof, y):
        v = prof.get(str(y))
        return None if v is None else round(v["gate_mean"], 4)

    comp_gate = {}
    for y in (2021, 2022, 2023, 2024, 2025):
        gmaj, galt = gate_profile["major"].get(str(y)), gate_profile["alt"].get(str(y))
        pcy = comp["per_year"].get(str(y))
        if gmaj and galt and pcy and pcy["total"] > 0:
            wm = pcy["n_major"] / pcy["total"]
            comp_gate[str(y)] = round(wm * gmaj["gate_mean"] + (1 - wm) * galt["gate_mean"], 4)
        else:
            comp_gate[str(y)] = None
    result["composite_gate_per_year"] = comp_gate
    L.info("composite book-weighted gate/nam: %s", comp_gate)

    allgate = {str(y): gm(gate_profile["all"], y) for y in (2021, 2022, 2023, 2024, 2025)}
    if rel == "composite":
        relgate = dict(comp_gate)
    else:
        relgate = {str(y): gm(gate_profile[rel], y) for y in (2021, 2022, 2023, 2024, 2025)}
    result["allgate_per_year"] = allgate
    result["relgate_per_year"] = relgate

    diffs = {}
    for y in (2021, 2022, 2023, 2024, 2025):
        rv, av = relgate.get(str(y)), allgate.get(str(y))
        diffs[str(y)] = None if (rv is None or av is None) else round(rv - av, 4)
    result["rel_minus_all"] = diffs
    any_big = any(v is not None and abs(v) >= 0.10 for v in diffs.values())
    all_small = all(v is not None and abs(v) < 0.10 for v in diffs.values())

    g22, g23, g24, g25 = (relgate.get("2022"), relgate.get("2023"),
                          relgate.get("2024"), relgate.get("2025"))
    go_cond = (g25 is not None and g25 >= 1.60 and g23 is not None and g23 <= 1.20
               and g24 is not None and g24 <= 1.20 and g22 is not None and g22 >= 1.55 and any_big)
    nogo = []
    if all_small:
        nogo.append("rel~all (chenh moi nam <0.10)")
    if (g23 is not None and g23 > 1.30) and (g24 is not None and g24 > 1.30):
        nogo.append("siet ca 2023&2024 (gate>1.30)")
    if rel == "major" and (g25 is not None and g25 < 1.4):
        nogo.append("major-heavy & major-breadth 2025 khoe (gate2025<1.4)")

    verdict = "GO" if go_cond else ("NO-GO" if nogo else "BORDERLINE")
    result["gate_decision"] = dict(rel_universe=rel, g2022=g22, g2023=g23, g2024=g24, g2025=g25,
                                   any_big_diff_vs_all=any_big, go_cond=go_cond,
                                   nogo_trigger=nogo, verdict=verdict)
    L.info("=== GO/NO-GO verdict=%s | rel=%s g22=%s g23=%s g24=%s g25=%s | diffs=%s | nogo=%s ===",
           verdict, rel, g22, g23, g24, g25, diffs, nogo)

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    L.info("DONE -> %s", OUT_JSON)


if __name__ == "__main__":
    main()
