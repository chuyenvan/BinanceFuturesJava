"""FEE0_RESCORE gates G1-G6 + verdict + danh muc mo ta. Doc s_daily/q4_daily/s_res/q4_res/x14_daily."""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f0_common as F  # noqa: E402

N_TESTS = 89 + 7
S = pd.read_parquet(F.WK + "/s_daily.parquet")
Q = pd.read_parquet(F.WK + "/q4_daily.parquet")
sres = json.load(open(F.WK + "/s_res.json")); qres = json.load(open(F.WK + "/q4_res.json"))
X = pd.read_parquet(F.WK + "/x14_daily.parquet")["median_seed"].dropna()
SIGS = ["S1_BTC", "S1_ETH", "S7_BTC", "S7_ETH", "S8_BTC", "S8_ETH", "Q4"]


def ser(sig, mdl):
    return (Q[f"Q4|{mdl}"] if sig == "Q4" else S[f"{sig}|{mdl}"]).dropna()


out = {"N_tests": N_TESTS}
passed = []
for sig in SIGS:
    st = {m: F.split(ser(sig, m)) for m in ("M0", "M1_W5", "M1_W15", "M1_W30", "M2", "gross")}
    fill = sres[sig]["fill_W15"] if sig != "Q4" else {p: qres[p]["fill_W15"] for p in ("E", "C")}
    m1 = ser(sig, "M1_W15")
    j = pd.concat([m1.rename("s"), X.rename("x")], axis=1, join="inner")
    corr = float(j.s.corr(j.x))
    d = F.dsr(m1, N_TESTS); d2 = F.dsr(m1, 89 + 21)
    e1, c1 = st["M1_W15"]["E"]["sharpe"], st["M1_W15"]["C"]["sharpe"]
    sgn = all(np.sign(st[f"M1_W{w}"][p]["sharpe"]) == np.sign(st["M1_W15"][p]["sharpe"]) for w in (5, 30) for p in ("E", "C"))
    G = {"G1": e1 >= 1.0 and c1 >= 1.0,
         "G2": st["M2"]["E"]["sharpe"] >= 0.5 and st["M2"]["C"]["sharpe"] >= 0.5,
         "G3": st["M1_W15"]["E"]["maxdd"] >= -0.25 and st["M1_W15"]["C"]["maxdd"] >= -0.25,
         "G4": corr <= 0.3,
         "G5": fill["E"] >= 0.6 and fill["C"] >= 0.6 and sgn,
         "G6": d["dsr"] >= 0.5}
    rest = all(G[k] for k in ("G2", "G3", "G4", "G5", "G6"))
    if G["G1"] and rest:
        v = "GO"
    elif c1 >= 1.0 and 0.7 <= e1 < 1.0 and rest:
        v = "UNG_VIEN"
    else:
        v = "NO-GO"
    if v != "NO-GO":
        passed.append(sig)
    out[sig] = {"stats": st, "fill_W15": fill, "corr_x14": corr, "n_overlap_x14": int(len(j)), "dsr": d, "dsr_N110": d2,
                "sign_stable_W5_W30": bool(sgn), "gates": {k: bool(x) for k, x in G.items()}, "verdict": v}
    print(f"{sig:7s} M1 E {e1:+.2f} C {c1:+.2f} dd {st['M1_W15']['E']['maxdd']:+.2f}/{st['M1_W15']['C']['maxdd']:+.2f} | M2 E {st['M2']['E']['sharpe']:+.2f} C {st['M2']['C']['sharpe']:+.2f}"
          f" | M0 E {st['M0']['E']['sharpe']:+.2f} C {st['M0']['C']['sharpe']:+.2f} | gross E {st['gross']['E']['sharpe']:+.2f} C {st['gross']['C']['sharpe']:+.2f}"
          f" | fill {fill['E']:.2f}/{fill['C']:.2f} | corrX14 {corr:+.2f} | DSR {d['dsr']:.2f} | {''.join('1' if G[k] else '0' for k in sorted(G))} -> {v}")
if len(passed) >= 2:
    P = pd.concat([ser(s, "M1_W15") for s in passed], axis=1).fillna(0).mean(axis=1)
    out["portfolio"] = {"members": passed, "M1_W15": F.split(P)}
else:
    out["portfolio"] = {"members": passed, "note": "<2 tin hieu dat -> khong ghep"}
json.dump(out, open(F.WK + "/gates.json", "w"), indent=1, default=float)
print("passed", passed)
