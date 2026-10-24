#!/usr/bin/env python3
"""Nhan theo PREREG_PARITY_V11_WINDOW_ADDENDUM2 (4eef2788) [+ ADDENDUM3 (67ce404a) tu 10-24] cho moi (phut, nguon) lech.
  K1'' : (a) M in [W_start-20', W_end+10'] cua 1 cua so [LIVE-KLINE] co reread_overwritten > 0 (W_start = W_end - minutes)
         VA (b) phep thay nen tai lap gia tri live trong dung sai. Ho thay nen thuc thi duoc (khong co nen live tren Oracle):
         1 nen KHA DUNG (s, X), X trong khoang (a) va X <= M, coi nhu KHONG co trong buffer live (co che H2, D1 ADD1 §7.1);
         tinh lai DOC LAP rateDown15MAvg (= momentum15M) float32 theo jar, so live trong 1e-6*(1+|b|) va kiem
         momentumAcceleration = momentum5M_live - momentum15M_moi. Chi ap duoc khi moi lech cua phut chi qua kenh momentum15M
         (gate: momentum15M/momentumAcceleration; MD: rateDown15MAvg; FUND: cot muc-thi-truong = momentum15M/accel live;
         NET/GV-O/P1: he qua). Ngoai ho nay => (b) khong chung minh => K5 (CHUA GIAI THICH).
  K6'  : S1-V, top-24 trung TAP va THU TU; moi dong lech: hoan doi ke (|dhang|=1/n) / tie-split (|dhang|=0,5/n) voi doi tac
         |dv| <= max(1e-6*|v|, 1e-7); score-only: ADD2 dung chu |dscore| <= max(1e-6*|score|, 1e-7) (ngay < 10-24),
         ADD3 khong can (ngay >= 10-24). Luon bao kem so theo cach doc con lai.
  K2, K3' : giu (labels_<tag>.json, kprime_<tag>.json).  K5 : phut co >= 1 nguon khong nhan.
env PV_DAY [PV_WORK]. Ghi WORK/kpp_<tag>.json. Khong doc 242."""
import io
import json
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import day_eval as E  # noqa: E402
from pv_cfg import day_ms  # noqa: E402

C = E.C
WORK, TAG, VIS = C["WORK"], C["tag"], C["VIS"]
MIN, F32 = 60000, np.float32
DAY_D, DAY_PREV = C["day"], C["day_prev"]
ADD3 = DAY_D >= "2026-10-24"
f7, eq = E.f7, E.eq
DIED = {"BTCDOMUSDT", "USDCUSDT"}
R15SET = {"momentum15M", "momentumAcceleration"}
tg_live = {}


def ms(s):
    import datetime as dt
    return int(dt.datetime.strptime("2026-" + s + " +0700", "%Y-%m-%d %H:%M %z").timestamp() * 1000)


def tolv(v):
    return max(1e-6 * abs(v), 1e-7)


def load_vis(day, sym):
    p = "%s/%s/%s.zip" % (VIS, day, sym)
    if not os.path.exists(p):
        return None
    with zipfile.ZipFile(p) as z:
        raw = z.read(z.namelist()[0]).decode()
    d = pd.read_csv(io.StringIO(raw), header=0 if raw.startswith("open_time") else None, usecols=[0, 1, 2, 3, 4, 7], dtype=str)
    d.columns = ["t", "o", "h", "l", "c", "qv"]
    out = {"t": d.t.astype(np.int64).values}
    for k in ("o", "h", "l", "c", "qv"):
        out[k] = np.array([F32(x) for x in d[k].values], dtype=np.float32)
    return out


def rate(a, b):
    return F32(F32(a - b) / b)


def avg_tree(vals):
    keys = np.unique(np.asarray(vals, np.float32))
    n = min(100, len(keys) * 4 // 5)
    tot, cnt = F32(0), 0
    for k in keys:
        cnt += 1
        tot = F32(tot + k)
        if cnt >= n:
            break
    return F32(tot / F32(cnt)) if len(keys) else F32(0)


class R15:
    """Bo dem 15 nen KHA DUNG theo so dem (MarketDataInlineGenerator.update + MarketBigChangeDetector), float32."""

    def __init__(self, uni, t_from, t_to):
        self.t0 = t_from
        n = (t_to - t_from) // MIN + 1
        self.A = {}
        for s in uni:
            if s in DIED:
                continue
            parts = [x for x in (load_vis(DAY_PREV, s), load_vis(DAY_D, s)) if x is not None]
            if not parts:
                continue
            arr = {k: np.concatenate([p[k] for p in parts]) for k in ("t", "o", "h", "l", "c", "qv")}
            g = {k: np.full(n, np.nan, np.float32) for k in ("o", "h", "l", "c", "qv")}
            m = (arr["t"] >= t_from) & (arr["t"] <= t_to)
            ix = (arr["t"][m] - t_from) // MIN
            for k in g:
                g[k][ix] = arr[k][m]
            self.A[s] = g
        self.n = n

    def run(self, windows):
        buf = {s: [] for s in self.A}
        out, srch = {}, {}
        btc = self.A["BTCUSDT"]
        for i in range(self.n):
            M = self.t0 + i * MIN
            rb = rate(btc["c"][i], btc["o"][i]) if not np.isnan(btc["c"][i]) else F32(0)
            per = {}
            for s, g in self.A.items():
                if np.isnan(g["c"][i]):
                    continue
                o, h, l, c, qv = g["o"][i], g["h"][i], g["l"][i], g["c"][i], g["qv"][i]
                avail = (l != h) or (qv != 0)
                if avail:
                    b = buf[s]
                    b.append((M, h))
                    if len(b) > 100:
                        del b[:5]
                rc = rate(c, o)
                if (rb > -0.004 and rc < -0.15) or rc > 0.3:
                    continue
                if avail:
                    per[s] = (rate(c, F32(max(x[1] for x in buf[s][-15:]))), c)
            out[M] = avg_tree([v[0] for v in per.values()])
            if M in windows:
                lv, A_, B_ = tg_live[M], windows[M][0], windows[M][1]
                hits = []
                base = {s: v[0] for s, v in per.items()}
                for s, (r, c) in per.items():
                    b = buf[s]
                    for j in range(1, min(16, len(b)) + 1):
                        X = b[-j][0]
                        if not (A_ <= X <= min(B_, M)):
                            continue
                        alt = dict(base)
                        if j == 1 and X == M:
                            alt.pop(s)
                        else:
                            nb = b[:len(b) - j] + b[len(b) - j + 1:]
                            alt[s] = rate(c, F32(max(x[1] for x in nb[-15:])))
                        v = avg_tree(list(alt.values()))
                        if abs(float(v) - float(lv)) <= 1e-6 * (1 + abs(float(lv))):
                            hits.append({"symbol": s, "candle": f7(X), "r15_new": float(v)})
                srch[M] = hits
        return out, srch


def k6p(g):
    """K6'. Tra dict: K6p_add2 (dung chu ADD2), K6p_add3 (score-only khong can), reason."""
    top_c = list(g.sort_values(["score_calc", "symbol"]).symbol.head(24))
    top_l = list(g.sort_values(["score_live", "symbol"]).symbol.head(24))
    G = g.set_index("symbol")
    bad_feat = {}
    for i in range(7):
        m = ~eq(g["c%d" % i], g["l%d" % i])
        for s in g.symbol[m]:
            bad_feat.setdefault(s, set()).add(i)
    bad_score = set(g.symbol[~eq(g.score_calc, g.score_live)])
    reason, ok_feat, kinds = None, True, set()
    for s, cols in bad_feat.items():
        for c in cols:
            if c not in (2, 5):
                ok_feat, reason = False, "feature_khac"
                break
            v = 1 if c == 2 else 4
            n = int(np.sum(~np.isnan(g["c%d" % v].values)))
            lc, cc = float(G.loc[s, "l%d" % c]), float(G.loc[s, "c%d" % c])
            d = abs(lc - cc)
            tl = 1e-6 * (1 + abs(lc))
            kind = "swap" if abs(d - 1.0 / n) <= tl else ("tie" if abs(d - 0.5 / n) <= tl else None)
            if kind is None:
                ok_feat, reason = False, "feature_khac"
                break
            if kind == "swap":
                part = g[(g.symbol != s) & eq(g["l%d" % c], cc) & eq(g["c%d" % c], lc)]
            else:
                part = g[(g.symbol != s) & (eq(g["c%d" % c], cc) | eq(g["l%d" % c], lc))]
            hit = False
            for s2 in part.symbol:
                for sd in ("l", "c"):
                    a, b = float(G.loc[s, "%s%d" % (sd, v)]), float(G.loc[s2, "%s%d" % (sd, v)])
                    if abs(a - b) <= tolv(max(abs(a), abs(b))):
                        hit = True
            if not hit:
                ok_feat, reason = False, "khong_doi_tac"
                break
            kinds.add(kind)
        if not ok_feat:
            break
    so = sorted(bad_score - set(bad_feat))
    so_abs = [abs(float(G.loc[s, "score_calc"]) - float(G.loc[s, "score_live"])) for s in so]
    so_ok2 = all(a <= tolv(float(G.loc[s, "score_live"])) for s, a in zip(so, so_abs))
    if so:
        kinds.add("score_only")
    top_ok = top_c == top_l
    if not top_ok:
        reason = "top24_khac"
    elif ok_feat and not so_ok2:
        reason = "score_only_vuot_can_ADD2"
    return {"K6p_add2": bool(top_ok and ok_feat and so_ok2), "K6p_add3": bool(top_ok and ok_feat),
            "reason": reason, "kinds": sorted(kinds), "score_only_rows": len(so),
            "score_only_max_abs": max(so_abs) if so_abs else 0.0, "rows_bad": len(set(bad_feat) | bad_score)}


def main():
    lab = json.load(open(WORK + "/labels_%s.json" % TAG))
    kp = json.load(open(WORK + "/kprime_%s.json" % TAG))
    k3p = {r["min"]: (r.get("k3p_check") or {}) for r in kp["rows"]}
    JG = pd.read_csv(WORK + "/join_gate.csv.gz").set_index("min")
    JF = pd.read_csv(WORK + "/join_fund.csv.gz", dtype={"symbol": str})
    SV = pd.read_csv(WORK + "/s1v_rows.csv.gz")
    wins = []
    for ln in E.loglines():
        if "[LIVE-KLINE] reread" in ln:
            t = E.lt(ln)
            m = re.search(r"reread_overwritten=(\d+)", ln)
            mm = re.search(r"win\{minutes=(\d+)", ln)
            if t and m and int(m.group(1)) > 0:
                we = (t // MIN) * MIN
                wins.append((we - int(mm.group(1) if mm else 10) * MIN, we, int(m.group(1))))
    fcols = ["f%d" % i for i in range(40) if "f%d" % i not in E.FUND_T1]
    rows, need = [], {}
    for r in lab["bad_minutes"]:
        t = ms(r["min"])
        info = {"min": r["min"], "sources": r["sources"], "K2": [x for x in r["labels"] if x.startswith("K2")]}
        inw = [w for w in wins if w[0] - 20 * MIN <= t <= w[1] + 10 * MIN]
        info["windows"] = [(f7(a), f7(b), n) for a, b, n in inw]
        dev = {"gate": [], "MD": [], "FUND": []}
        if t in JG.index:
            g = JG.loc[t]
            dev["gate"] = [f for f in E.NONFUND_GATE if not eq([g[f + "_l"]], [g[f + "_b"]])[0]]
            dev["MD"] = [a for a, b in (("rateDownAvg", "r_down"), ("rateUpAvg", "r_up"), ("rateDown15MAvg", "r_down15"))
                         if not eq([g[a]], [g[b]])[0]]
        x = JF[JF["min"] == t]
        fd = sorted(c for c in fcols if len(x) and (~eq(x[c + "_l"], x[c + "_b"])).any())
        dev["FUND"] = fd
        chan = False
        if inw and t in JG.index and set(dev["gate"]) <= R15SET and set(dev["MD"]) <= {"rateDown15MAvg"}:
            g = JG.loc[t]
            ok = True
            for c in fd:
                vals = x[c + "_l"].astype(float)
                if vals.nunique() != 1 or not any(eq([vals.iloc[0]], [g[f + "_l"]])[0] for f in R15SET):
                    ok = False
            chan = ok and any(s in r["sources"] for s in ("P1F", "MD", "FUND"))
        info["dev"] = dev
        info["r15_channel"] = bool(chan)
        if chan:
            need[t] = (min(w[0] for w in inw) - 20 * MIN, max(w[1] for w in inw) + 10 * MIN)
            tg_live[t] = F32(JG.loc[t, "rateDown15MAvg"])
        rows.append((t, r, info))
    val = {"targets": len(need)}
    srch = {}
    if need:
        U = [x.strip() for x in open(C["U"]) if x.strip()]
        eng = R15(U, day_ms(DAY_PREV), C["T1"])
        r15, srch = eng.run(need)
        bt = {int(m): F32(v) for m, v in JG["r_down15"].items()}
        cmpm = [m for m in r15 if m in bt]
        val["reimpl_eq_BT_bit"] = "%d/%d" % (sum(r15[m] == bt[m] for m in cmpm), len(cmpm))
        val["reimpl_ne_BT_minutes"] = [f7(m) for m in cmpm if r15[m] != bt[m]][:20]
        val["valid"] = all(r15[m] == bt[m] for m in cmpm)
    out_rows = []
    for t, r, info in rows:
        k1 = False
        hits = srch.get(t, [])
        if info["r15_channel"] and hits and val.get("valid"):
            g = JG.loc[t]
            k1 = any(eq([float(g["momentum5M_l"]) - h["r15_new"]], [g["momentumAcceleration_l"]])[0] for h in hits)
        info["k1pp_hits"] = hits[:10]
        info["k1pp_n_hits"] = len(hits)
        s1 = k6p(SV[SV.ts == t]) if "S1V" in r["sources"] else None
        for mode in ("add2", "add3"):
            per = {}
            for s in r["sources"]:
                labs = list(info["K2"])
                if k3p.get(r["min"], {}).get(s) is True:
                    labs.append("K3'")
                if k1 and s in ("P1F", "MD", "FUND", "NET", "GV_O", "P1"):
                    labs.append("K1''")
                if s == "S1V" and s1["K6p_" + mode]:
                    labs.append("K6'")
                per[s] = sorted(set(labs))
            info["per_source_" + mode] = per
            info["K5_" + mode] = any(not v for v in per.values())
        info["s1v"] = s1
        out_rows.append(info)

    def summ(mode):
        cnt = {}
        for rr in out_rows:
            for x_ in sorted(set(sum(rr["per_source_" + mode].values(), []))):
                cnt[x_] = cnt.get(x_, 0) + 1
        k5 = [rr["min"] for rr in out_rows if rr["K5_" + mode]]
        return {"minutes_with_label": cnt, "K5": len(k5), "K5_minutes": k5,
                "K5_by_source": {s: sum(1 for rr in out_rows if rr["K5_" + mode] and not rr["per_source_" + mode].get(s, [1]))
                                 for s in ("P1F", "P1", "MD", "FUND", "NET", "GV_O", "S1V")},
                "K5_nonS1V_minutes": [rr["min"] for rr in out_rows if rr["K5_" + mode] and
                                      any(not v for s, v in rr["per_source_" + mode].items() if s != "S1V")]}
    res = {"addendum": "ADDENDUM2 4eef2788" + (" + ADDENDUM3 67ce404a (chinh thuc)" if ADD3 else " dung chu (chinh thuc); ADD3 chi mo ta"),
           "day": DAY_D, "official_mode": "add3" if ADD3 else "add2", "n_bad_minutes": len(out_rows),
           "official": summ("add3" if ADD3 else "add2"), "alternative": summ("add2" if ADD3 else "add3"),
           "live_kline_windows_reread_gt0": [(f7(a), f7(b), n) for a, b, n in wins],
           "k1pp_validation": val,
           "k1pp_minutes": [{"min": rr["min"], "windows": rr["windows"], "dev": rr["dev"], "r15_channel": rr["r15_channel"],
                             "n_hits": rr["k1pp_n_hits"], "hits": rr["k1pp_hits"],
                             "K1pp": "K1''" in sum(rr["per_source_add2"].values(), [])}
                            for rr in out_rows if rr["sources"] != ["S1V"]],
           "S1V": {"minutes": sum(1 for rr in out_rows if rr["s1v"]),
                   "K6p_add2": sum(1 for rr in out_rows if rr["s1v"] and rr["s1v"]["K6p_add2"]),
                   "K6p_add3": sum(1 for rr in out_rows if rr["s1v"] and rr["s1v"]["K6p_add3"]),
                   "not_K6p_add3_reason": {k: sum(1 for rr in out_rows if rr["s1v"] and not rr["s1v"]["K6p_add3"]
                                                  and rr["s1v"]["reason"] == k)
                                           for k in ("top24_khac", "feature_khac", "khong_doi_tac")},
                   "score_only_max_absdiff": max([rr["s1v"]["score_only_max_abs"] for rr in out_rows if rr["s1v"]] + [0])},
           "rows": out_rows}
    json.dump(res, open(WORK + "/kpp_%s.json" % TAG, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("rows",)}, indent=1, default=str)[:7000])


if __name__ == "__main__":
    main()
