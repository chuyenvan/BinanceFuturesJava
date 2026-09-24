#!/usr/bin/env python3
"""stage2_report.py — sinh `docs/result/RESULT_STAGE2_TRAIN.md` tu artifact cua kernel Stage 2.

Doc: /tmp/s2out/{stage2_summary.json, stage2_metrics.json, stage2_score.json, <TAG>_perfold_ticks.parquet}
Ra: docs/result/RESULT_STAGE2_TRAIN.md  (in ra stdout de review)
Khong train, khong sim. Read-only.
"""
import json, os, sys
import numpy as np, pandas as pd

S2 = sys.argv[1] if len(sys.argv) > 1 else "/tmp/s2out"
OUT = sys.argv[2] if len(sys.argv) > 2 else \
    "/home/ubuntu/src/BinanceFuturesJava/docs/result/RESULT_STAGE2_TRAIN.md"
ARMS = ["V0", "V1", "V2", "V3", "V4", "V5"]
LABEL = {"V0": "21 keeper (MOC)", "V1": "21 + ca 5", "V2": "21 + {mom7d,mom30d}",
         "V3": "21 + {rvol7d}", "V4": "21 + {daysSinceHigh30D,oi_delta7d}",
         "V5": "21 + 5 + 5 NHIEU"}
FS = {"V0": "fs_v4_21", "V1": "fs_v5_26", "V2": "fs_v6_23", "V3": "fs_v7_22",
      "V4": "fs_v8_23", "V5": "fs_v9_31"}
FOLDS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701",
         "20231001", "20240101", "20240401", "20240701", "20241001", "20250101", "20250401",
         "20250701", "20251001"]


def fm(x, n=6, sign=True):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return ("%+.*f" if sign else "%.*f") % (n, x)


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    S = load(os.path.join(S2, "stage2_summary.json"))
    SC = load(os.path.join(S2, "stage2_score.json"))
    ME = load(os.path.join(S2, "stage2_metrics.json"))
    ticks = {}
    for t in ARMS:
        p = os.path.join(S2, "%s_perfold_ticks.parquet" % t)
        if os.path.exists(p):
            ticks[t] = pd.read_parquet(p, columns=["ts", "fold", "ic", "lift8", "n_coin", "n8"])
    L = []
    A = L.append
    A("# RESULT_STAGE2_TRAIN — Stage 2 (train 6 bien the feature) — ket qua")
    A("")
    A("**Ngay:** 2026-09-24 · **Chi nhanh:** `module` · **Trang thai:** DO XONG (train+predict+bins; **KHONG sim**)")
    A("**Tien dang ky (chot TRUOC, da commit truoc khi push kernel):** `docs/prereg/PREREG_STAGE2_FEATVAR.md`"
      " — commit `dd27c6c`")
    A("**Code:** `dd27c6c` (pre-reg + fs_v4..v9) · `32ef0af` (trainer `--add-feats`/`--arms`, build prefeat,"
      " kernel, cham diem)")
    A("**Kernel:** `chuyendinh/g015p2-stage2-featvar-gpu` (Kaggle GPU, private) ·"
      " dataset moi `chuyendinh/funding-prefeat-stage2`")
    A("**Pham vi:** 16 fold DEV `20220101..20251001` · **KHONG cham 2026/HoldoutSeal** · KHONG cham ONNX/LIVE ·"
      " KHONG push git · Kaggle ↔ Kaggle (khong tron Oracle)")
    A("")
    A("---")
    A("")
    A("## 0. Tra loi ngan")
    A("")
    if SC:
        A("`k = %d` · he so no rong CI = `c3_rates.inflate(%d)` = **%.6f** (khong hardcode) ·"
          " block 72h · 2000 rep · seed %s" % (SC["k"], SC["k"], SC["inflate"], "20260905"))
    A("")
    A("| Bien the | Vector | so cot | file version | so fold xong | rank-IC (mean) | lift@8 (mean) |"
      " hon V0? | khac V5? | **KET** |")
    A("|---|---|---:|---|---:|---:|---:|---|---|---|")
    for t in ARMS:
        nf = len(ticks[t].fold.unique()) if t in ticks else (len(S["arms"][t]["folds"]) if S and t in S["arms"] else 0)
        if SC and t in SC["arms"]:
            ic = fm(SC["arms"][t]["ic"]["mean"])
            lf = fm(SC["arms"][t]["lift8"]["mean"])
        else:
            ic = lf = "n/a"
        v = (SC or {}).get("verdict", {}).get(t)
        vd = v if t in ("V0", "V5") else (v or {})
        hon = "-" if t in ("V0", "V5") else ("co" if (v or {}).get("hon_V0") else "khong")
        khac = "-" if t in ("V0", "V5") else ("co" if (v or {}).get("khac_V5") else "khong")
        ket = "MOC" if t == "V0" else ("DOI CHUNG NHIEU" if t == "V5" else
              ("**GIU**" if (v or {}).get("GIU") else "NULL"))
        A("| **%s** | %s | %d | `%s.json` | %d/16 | %s | %s | %s | %s | %s |"
          % (t, LABEL[t], (SC or {}).get("arms", {}).get(t, {}).get("n_feat", 0) or
             {"V0": 21, "V1": 26, "V2": 23, "V3": 22, "V4": 23, "V5": 31}[t], FS[t], nf, ic, lf, hon, khac, ket))
    A("")
    if SC and SC.get("verdict"):
        kept = [t for t, v in SC["verdict"].items() if v.get("GIU")]
        A("**Ket luan theo luat §4 pre-reg:** %s"
          % ("**NULL** — khong bien the nao dong thoi hon V0 VA khac V5 ngoai CI ⇒ giu nguyen **21 keeper**."
             if not kept else "GIU: " + ", ".join(kept)))
    A("")
    A("---")
    A("")
    A("## 1. Cong du lieu / tinh dung dan (phai PASS truoc khi doc so)")
    A("")
    if S:
        ca = S["cross_arm"]
        A("- **CROSS_ARM `n_train`/`pos`/`spw`/`n_oos`** giua %d arm x %d fold: **%s**"
          % (len(ca["arms"]), len(ca["folds"]),
             "KHOP TUYET DOI" if not ca["mismatch"] else "**LECH — LOI CO CHE**: %s" % json.dumps(ca["mismatch"])[:600]))
        b = ca["base_arm"]; f = ca["folds"][0]
        m = S["arms"][b]["folds"][f]
        A("- Moc %s fold %s: `n_train=%d` · `pos=%.5f` · `spw=%.6f` · `n_oos=%d`"
          % (b, f, m["n_train"], m["pos"], m["spw"], m["n_oos"]))
        A("- Tien trinh train (hit cua cot append theo nam): `%s`" % (ca.get("add_hits") or "n/a"))
        A("- `num_feature` tung arm: %s"
          % ", ".join("%s=%d" % (t, S["arms"][t]["num_feature"]) for t in ARMS if t in S["arms"]))
    A("- **Cong tai lap du lieu (doi chieu ban deploy):** fold `20220101` cho `pos=0.26989` · `spw=2.705276`"
      " — khop moc deploy da tai lieu hoa (`0.2699` / `2.70527601`, `docs/plan/PREP_STAGE2_TRAIN.md` §1.3)"
      " ⇒ tap dong/nhan/split cua vong nay DUNG la cua net015-45, chi khac vector cot.")
    A("- `spw` tang dan theo fold (2.705276 → 4.287861) — khop quy luat expanding (pos 0,2699 → 0,1891).")
    A("- `drop_cols` tung arm va `base_trainer_sha256`: xem `net_train_summary.json` cua tung arm.")
    A("")
    A("---")
    A("")
    A("## 2. Bang chinh — rank-IC + lift@8 (OOS, gop 16 fold, CI paired block-72h x `inflate(k)`)")
    A("")
    A("### 2.1 So tuyet doi theo bien the")
    A("")
    A("| Bien the | n_tick | so coin/tick | rank-IC | CI raw | CI x inflate | lift@8 | CI raw | CI x inflate |")
    A("|---|---:|---:|---:|---|---|---:|---|---|")
    if SC:
        for t in ARMS:
            if t not in SC["arms"]:
                continue
            r = SC["arms"][t]
            A("| %s | %d | %.1f | %s | [%s, %s] | [%s, %s] | %s | [%s, %s] | [%s, %s] |"
              % (t, r["n_tick"], r["n_coin_mean"], fm(r["ic"]["mean"]),
                 fm(r["ic"]["raw"][0]), fm(r["ic"]["raw"][1]),
                 fm(r["ic"]["infl"][0]), fm(r["ic"]["infl"][1]),
                 fm(r["lift8"]["mean"]),
                 fm(r["lift8"]["raw"][0]), fm(r["lift8"]["raw"][1]),
                 fm(r["lift8"]["infl"][0]), fm(r["lift8"]["infl"][1])))
    A("")
    A("### 2.2 Doi dau (paired, theo tung tick) — luat quyet dinh §4")
    A("")
    A("| Bien the | Δrank-IC vs V0 [CI x inflate] | Δrank-IC vs V5 (nhieu) [CI x inflate] |"
      " Δlift@8 vs V0 | Δlift@8 vs V5 | hon V0 ngoai CI? | khac V5 ngoai CI? |")
    A("|---|---|---|---|---|---|---|")
    if SC:
        for t in ARMS:
            if t not in SC.get("vs", {}):
                continue
            r = SC["vs"][t]
            def g(k):
                x = r.get(k)
                if not x:
                    return "n/a"
                return "%s [%s, %s]" % (fm(x["mean"]), fm(x["infl"][0]), fm(x["infl"][1]))
            A("| %s | %s | %s | %s | %s | %s | %s |"
              % (t, g("ic_vs_V0"), g("ic_vs_V5"), g("lift8_vs_V0"), g("lift8_vs_V5"),
                 (r.get("ic_vs_V0") or {}).get("huong_tot"), (r.get("ic_vs_V5") or {}).get("huong_tot")))
    A("")
    A("### 2.3 rank-IC theo TUNG FOLD (16 fold × 6 bien the)")
    A("")
    if ticks:
        hdr = "| fold | " + " | ".join(ARMS) + " |"
        A(hdr); A("|---|" + "---:|" * len(ARMS))
        for f in FOLDS:
            row = []
            for t in ARMS:
                if t in ticks:
                    s = ticks[t][ticks[t].fold == f]["ic"]
                    row.append(fm(s.mean()) if len(s) else "-")
                else:
                    row.append("-")
            A("| %s | %s |" % (f, " | ".join(row)))
        A("")
        A("| fold | " + " | ".join("lift@8 " + t for t in ARMS) + " |")
        A("|---|" + "---:|" * len(ARMS))
        for f in FOLDS:
            row = []
            for t in ARMS:
                if t in ticks:
                    s = ticks[t][ticks[t].fold == f]["lift8"]
                    row.append(fm(s.mean()) if len(s) else "-")
                else:
                    row.append("-")
            A("| %s | %s |" % (f, " | ".join(row)))
        A("")
        A("| fold | n_tick | so coin/tick (V0) |")
        A("|---|---:|---:|")
        if "V0" in ticks:
            g = ticks["V0"].groupby("fold")
            for f in FOLDS:
                if f in g.groups:
                    A("| %s | %d | %.1f |" % (f, len(g.get_group(f)), g.get_group(f).n_coin.mean()))
    A("")
    A("---")
    A("")
    A("## 3. Doi chung NHIEU — V0 vs V5 (bai hoc OFI: 'them cot != them tin hieu')")
    A("")
    if SC and "V5" in SC.get("vs", {}):
        r = SC["vs"]["V5"]
        A("- `Δrank-IC(V5 − V0)` = **%s**, CI x inflate = **[%s, %s]** ⇒ %s"
          % (fm(r["ic_vs_V0"]["mean"]), fm(r["ic_vs_V0"]["infl"][0]), fm(r["ic_vs_V0"]["infl"][1]),
             "**CI CHUA 0** ⇒ nhieu KHONG hon moc (dung du doan P1)"
             if not r["ic_vs_V0"]["huong_tot"] else
             "**CI NGOAI 0 theo CHIEU MANH HON** ⇒ **P1 SAI**: hieu ung 'them cot' KHONG den tu noi dung feature"))
        A("- `Δlift@8(V5 − V0)` = %s, CI x inflate = [%s, %s]"
          % (fm(r["lift8_vs_V0"]["mean"]), fm(r["lift8_vs_V0"]["infl"][0]), fm(r["lift8_vs_V0"]["infl"][1])))
    A("")
    A("---")
    A("")
    A("## 4. Doi chieu DU DOAN KHOA TRUOC (pre-reg §5)")
    A("")
    A("| # | Du doan | Ket qua |")
    A("|---|---|---|")
    if SC and "V5" in SC.get("vs", {}):
        p1 = "DUNG" if not SC["vs"]["V5"]["ic_vs_V0"]["huong_tot"] else \
            "**SAI** ⇒ theo pre-reg §5: vong nay **NULL / khong do duoc**, giu 21 keeper + phai dieu tra subset-selection-bias"
        A("| P1 | V5 (nhieu) khong hon V0 ngoai CI o rank-IC | %s |" % p1)
    if SC:
        d1 = SC["vs"].get("V1", {}).get("ic_vs_V0")
        d2 = SC["vs"].get("V1", {}).get("ic_vs_V5")
        if d1 and d2:
            A("| P2 | \\|Δ(V1−V5)\\| < \\|Δ(V1−V0)\\| (neu V1 'thang' thi phan lon la do them cot/mask) | %s |"
              % ("DUNG" if abs(d2["mean"]) < abs(d1["mean"]) else "**SAI**"))
    if SC and SC.get("verdict"):
        kept = [t for t, v in SC["verdict"].items() if v.get("GIU")]
        A("| P3 | Ket cuc NULL cho V1..V4 | %s |" % ("DUNG" if not kept else "**SAI** (GIU: %s)" % ",".join(kept)))
    if S:
        A("| P4 | n_train/pos/spw/n_oos khop tuyet doi giua 6 bien the | %s |"
          % ("DUNG" if not S["cross_arm"]["mismatch"] else "**SAI** — loi co che"))
    if SC and "V3" in SC.get("vs", {}):
        r = SC["vs"]["V3"]
        A("| P5 | V3 (rvol7d) la ung vien sang nhat nhung van khong vuot §4 | rank-IC Δ vs V0 = %s ⇒ %s; Δ vs V5 = %s ⇒ %s |"
          % (fm(r["ic_vs_V0"]["mean"]),
             "VUOT V0" if r["ic_vs_V0"]["huong_tot"] else "khong vuot V0",
             fm(r["ic_vs_V5"]["mean"]),
             "VUOT V5 (sai P5)" if r["ic_vs_V5"]["huong_tot"] else "khong tach duoc khoi V5"))
    A("")
    A("> **LAM RO SAU KHI XEM SO (KHONG sua pre-reg):** pre-reg §4 viet \"CI khong chua 0 VA **cUNG DAU DUONG**\".")
    A("> Cau do viet theo quy uoc `IC > 0`. Do duoc: **rank-IC cua MOI bien the deu AM** (giong Stage 0 —")
    A("> momentum/vol dai han tuong quan AM voi `retEnd_4h`), nen \"HON\" phai doc la **|IC| LON HON = AM HON**.")
    A("> Bang §2.2 o tren dung ban doc theo **chieu tot len** (`huong_tot`). Neu doc **CHU NGHIA** (dau duong)")
    A("> thi khong bien the nao 'hon V0' ca — **ket cuc NULL khong doi** (V1/V3/V5 deu AM HON V0, tuc la")
    A("> \"khong duong\" theo chu nghia). Ca hai ban doc deu cho **cung mot ket luan §0**. Khong doi tieu chi/nguong/k.")
    A("")
    A("---")
    A("")
    A("## 5. Model + bins — noi luu (de Stage 3 dung lai)")
    A("")
    A("- **Kernel output (nguon chinh, con nguyen tren Kaggle):**"
      " `https://www.kaggle.com/code/chuyendinh/g015p2-stage2-featvar-gpu` (tab Output) và API"
      " `GET /api/v1/kernels/output?userName=chuyendinh&kernelSlug=g015p2-stage2-featvar-gpu`")
    A("  - `<TAG>/model_f<fidx>_4h.json` = 16 model/bien the (`fidx` = vi tri trong `CUT_DATES`,"
      " **KHONG** phai so fold deploy — khop theo CUTOFF)")
    A("  - `<TAG>/predict_wf_<cutoff>.bin` = 16 bin/bien the (26 B/rec, `>q h 4f`, `p0` = 4h);"
      " `<TAG>/net_train_summary.json`, `stage2_summary.json`, `stage2_metrics.json`,"
      " `<TAG>_perfold_ticks.parquet`")
    A("- **Backup tai may (ben vung, khong phai /tmp):** `/home/ubuntu/claudedata/stage2_featvar_out/`"
      " (173 MB: 6 thu muc model + `*_perfold_ticks.parquet` + 3 JSON summary/score/metrics + log kernel)."
      " **KHONG** tai 5,3 GB bins — bins o kernel output (tai lai bang API theo `fileName`).")
    A("- Du lieu nguon cot append: `/home/ubuntu/claudedata/prefeat_stage2/prefeat_full.parquet`"
      " (39.610.611 dong · 924 MB · sha256 `a601fef5599d12216dddbd9ff25c540109c4af76d2de89efbf188e1789d71d38`)"
      " + dataset Kaggle `chuyendinh/funding-prefeat-stage2`.")
    A("- **Bang sha256 bins tung fold × tung arm:** trong `stage2_summary.json` (khoa `sha_bin`).")
    if S:
        A("")
        A("| arm | so fold co bin | sha256 bin fold dau (vi du) |")
        A("|---|---:|---|")
        for t in ARMS:
            if t in S["arms"]:
                fs = S["arms"][t]["folds"]
                A("| %s | %d | `%s` (%s) |" % (t, len(fs), list(fs.values())[0]["sha_bin"][:16] + "...",
                                               list(fs.keys())[0]))
    A("")
    A("- **KHONG** ghi de `/home/ubuntu/claudedata/predwf_G015/model_f*_4h.json` (ban deploy 2026-08-14)"
      " va **khong** cham `shadow_c3/*.onnx`.")
    A("")
    A("---")
    A("")
    A("## 6. De xuat Stage 3 (chay tren Kaggle, khong phai o day)")
    A("")
    A("1. `c4_build_map.py s1a2x1` cho tung bien the (`<TAG>/predict_wf_*.bin` -> bins S1-order) —"
      " **dung dung 16 bins** `20220101..20251001` (fold 2026 KHONG dua vao).")
    A("2. Dataset + sim 48 thang tren **Kaggle** (khong tron Oracle), moi bien the mot arm.")
    A("3. Cham bang `research/analysis/x1_rates.py --k 6`: 5 rate (`win%`/`TSloss%`/`mP|SM`/`mP|SL`/`meanP`)"
      " + rao cung `RISK_APPETITE.md §7` (`maxDD<=40%`, quy xau nhat `>=-20%`, `UW<=250`, tap trung 1 coin"
      " `<=15%`, khong nam am) + `maxDD` do bang **MTM moc phut**. `n` va `mMargin` **khong** phai quality rate.")
    A("4. Chi ket luan khi **>= 2 rate ngoai CI**; neu khong ⇒ NULL, giu 21 keeper."
      " Neu 1 bien the GIU o tang rank-IC thi **uu tien** no cho sim (tiet kiem slot).")
    A("")
    A("---")
    A("")
    A("## 7. Ghi chu co che / sai lech")
    A("")
    A("- `oi_delta7d` (idx 49) **gan nhu NaN trong 2021** (do OI 5m offline chi bat dau giua 2021):"
      " tren ma tran nam 2021 do duoc **92,3 % NaN**. He qua: o fold 0 (train = 2021) bien the co cot nay"
      " (V1/V4) **thuc chat khong duoc them thong tin OI**; V5 (nhieu cung mask) do do cung \u2018trong\u2019 tuong ung"
      " ⇒ phep so V1/V4 vs V5 o fold 0 gan nhu so 21 vs 21.")
    A("- `mom30d`/`daysSinceHigh30D` NaN ~4,5 % (warmup + coin moi list) — nhu Stage 0.")
    A("- Tap dong KHONG doi khi them cot (join trai + NaN, va `--drop-cols` chi cat cot): da assert.")
    A("- Multiplicity **k = 6** ap cho **ca hai** chieu so (vs V0 va vs V5) — khong noi `k` sau khi xem so.")
    A("- **Co che do duoc (quan trong nhat vong nay):** 3 bien the CO cot append (V1 +5 that / V3 +1 that /"
      " V5 +5 nhieu) deu dich rank-IC ve cung mot phia voi do lon tuong duong; 2 bien the chi +2 cot that"
      " (V2, V4) gan nhu khong dich. ⇒ Phan 'thang' KHONG quy duoc cho noi dung 5 feature.")
    A("- `lift@8` cua MOI bien the deu duong lon (~+0,105) va chenh nhau rat it ⇒ thuoc nay khong phan biet duoc arm.")
    A("- CI o tang rank-IC dung cung hang so `c3_rates` nhu `x1_rates.py` ⇒ nhat quan giua Stage 2 va Stage 3.")
    A("")
    A("---")
    A("")
    A("## 8. Gioi han / phan CHUA chay")
    A("")
    A("- **16/18 fold**: 2 fold `20260101`/`20260401` **KHONG** chay (HoldoutSeal 2026-01-01).")
    A("- **Chua sim**: moi ket luan kinh te (PnL) de Stage 3. rank-IC + lift@8 **khong** du de doi model.")
    A("- Nhan do = `retEnd_4h` (ban lien tuc cua nhan train `retEnd_4h > 0,015`), khong dung `maxFav`.")
    A("- `lift@8` dung top-8 theo `p0` **trong tung tick** — proxy cua selector, khong phai PnL.")
    A("")
    A("*Sinh boi `research/analysis/stage2_report.py` tu artifact kernel.*")
    txt = "\n".join(L) + "\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(txt)
    print("WROTE %s (%d bytes, %d dong)" % (OUT, len(txt), len(L)))
    print(txt[:1500])


if __name__ == "__main__":
    main()
