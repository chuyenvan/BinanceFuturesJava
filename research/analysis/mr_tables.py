#!/usr/bin/env python3
"""mr_tables.py — in BANG markdown cho RESULT_MONEY_RANKER tu JSON cua money_ranker_score.py."""
import json
import sys

COLS = ["ic", "pacc", "dec_mono", "dec_rho", "glift8", "netm8", "auc8", "lift8", "base"]


def tab(summary, arms, ruler, setname):
    hdr = "| arm | " + " | ".join("`%s`" % c for c in COLS) + " | n_tick |"
    print(hdr)
    print("|" + "---|" * (len(COLS) + 2))
    for a in arms:
        s = summary.get("%s|%s|%s" % (a, ruler, setname))
        if not s:
            print("| **%s** | NA |" % a)
            continue
        cells = []
        for c in COLS:
            v = s["metrics"].get(c)
            if not v:
                cells.append("-")
                continue
            star = "*" if v["strict"] else ("+" if v["honest"] else "")
            cells.append("%+.5f%s" % (v["mean"], star))
        print("| **%s** | %s | %d |" % (a, " | ".join(cells), s["n_tick"]))


def dtab(delta, newarms, controls, ruler, setname, metrics=("ic", "pacc", "dec_mono")):
    print("| Δ | " + " | ".join("`%s`" % m for m in metrics) + " |")
    print("|" + "---|" * (len(metrics) + 1))
    for a in newarms:
        for ctl in controls:
            d = delta.get("%s|%s|%s|%s" % (a, ctl, ruler, setname))
            if not d:
                continue
            cells = []
            for m in metrics:
                v = d["metrics"].get(m)
                if not v:
                    cells.append("-")
                    continue
                star = "*" if v["strict"] else ("+" if v["honest"] else "")
                cells.append("%+.5f%s" % (v["mean"], star))
            print("| %s−%s (n=%d) | %s |" % (a, ctl, d["n_tick_common"], " | ".join(cells)))


if __name__ == "__main__":
    J = json.load(open(sys.argv[1]))
    arms = sys.argv[2].split(",") if len(sys.argv) > 2 else J["arms"]
    ctls = J["controls"]
    for ruler in ("money4", "money72", "lab4", "lab72"):
        if not any(k.startswith(a + "|" + ruler) for a in arms for a in [a]):
            pass
        print("\n#### ruler `%s` — set `all16`\n" % ruler)
        tab(J["summary"], arms, ruler, "all16")
        print()
        dtab(J["delta"], arms, ctls, ruler, "all16")
