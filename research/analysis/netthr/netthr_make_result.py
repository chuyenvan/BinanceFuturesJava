#!/usr/bin/env python3
"""Sinh docs/result/RESULT_LABEL_NETTHR.md + label_netthr.json tu rep_ALL.json (chi trinh bay so da do)."""
import json
import logging
import shutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mkres")
SRC = "/home/ubuntu/claude_master/0930_netthr/rep_ALL.json"
R = "/home/ubuntu/src/BinanceFuturesJava"
d = json.load(open(SRC))
cuts = list(d["folds"].keys())
F = d["folds"]
B = d["boot"]
OM = d["overall_means"]


def f5(x):
    return "%+.5f" % x


def ci(o):
    return "[%+.5f, %+.5f]" % (o["lo_infl"], o["hi_infl"])


L = []
w = L.append
w("# RESULT — LABEL_NETTHR (sweep NET_THR cho selector G015, TANG MODEL)")
w("")
w("Pre-reg: `docs/prereg/PREREG_LABEL_NETTHR.md` (md5 `277caa6bcd0ae44425894cf72b285302`, commit `1cdacdc2`, chot TRUOC so). "
  "DEV <= 2025-12-31, 16 fold (20220101..20251001), seed 42, KHONG fold 2026, KHONG 242/shadow. Tho: `docs/result/label_netthr.json`. "
  "Sim: KHONG chay (khong arm nao qua cong, xem §0).")
w("")
w("## 0. Ket luan (rui ro truoc)")
w("")
m10, m20 = B["M_010"]["overall"], B["M_020"]["overall"]
w("1. **Khong arm nao qua cong => DUNG, khong sim.** Cong = ΔrankIC duong ngoai 0 (pre-reg) VA lift@8 khong kem (MASTER 09-30). "
  "M_010: ΔrankIC %s (CI infl %s, 16/16 fold duong) nhung **lift@8 %s (CI %s), AUC %s => kem co y nghia**. "
  "M_020: ΔrankIC %s (CI %s, 0/16 fold duong) => khong qua." % (
      f5(m10["ic"]["delta"]), ci(m10["ic"]), f5(m10["lift8"]["delta"]), ci(m10["lift8"]), f5(m10["auc"]["delta"]),
      f5(m20["ic"]["delta"]), ci(m20["ic"])))
w("2. **Theo chu cua pre-reg rieng ΔrankIC thi M_010 'qua'** (CI > 0, gap ~12x san nhieu 0.0007). Toi khong sim vi dieu kien lift@8 khong kem (MASTER) khong dat va rank-IC vs retEnd_4h AM o moi fold "
  "(M_015 %s) nen 'IC tang' = bot am, khong phai 'chon coin loi hon'. Neu MASTER muon sim M_010 theo chu pre-reg thi bins da co (`out_M_010`), can quyet dinh — toi khong tu y." % f5(OM["M_015"]["rank_ic"]))
w("3. **Cau hoi 'doi NET_THR doi THU HANG hay chi calibration?'**: doi ca hai, nhung theo MOT TRUC. Nhan lo hon (0.010) hoac chat hon (0.020) doi thu hang coin co the do duoc: "
  "xs-rank-corr per-tick vs M_015 = M_010 %.3f, M_020 %.3f (san nhieu retrain, ORIG vs M_015 = %.3f). M_010 thap hon san ro (16/16 fold ΔIC cung dau) => thu hang doi that; "
  "M_020 xs-corr ~ san nhieu (khong tach duoc khoi nhieu bang tuong quan) nhung ΔIC am o 16/16 fold (xem §3), tuc thu hang do duoc theo IC. Huong doi la **danh doi**: NET_THR thap => IC len (bot nghieng ve coin vol cao) nhung lift@8/AUC xuong; NET_THR cao => nguoc lai. "
  "Khong arm nao troi hon o CA HAI thuoc do => label-threshold la nut **tradeoff vol-tilt**, khong phai lever ranking mien phi." % (
      d["overall_xs_rank_corr"]["M_010"], d["overall_xs_rank_corr"]["M_020"], d["overall_xs_rank_corr"]["ORIG"]))
w("4. **'Gate G2 tu bu' CHUA KIEM** (khong sim). Cau nay khong duoc rut ra tu ket qua nay. Chi biet: p_mean gan nhu khong doi (%.3f/%.3f/%.3f, do scale_pos_weight) nhung **p_std doi manh** (%.3f/%.3f/%.3f cho M_010/M_015/M_020) => phan phoi p va gate rolling ratio co the bi anh huong; can sim de biet."
  % (OM["M_010"]["p_mean"], OM["M_015"]["p_mean"], OM["M_020"]["p_mean"], OM["M_010"]["p_std"], OM["M_015"]["p_std"], OM["M_020"]["p_std"]))
w("")
w("## 1. Tai lap M_015 (kiem hop le nen)")
w("")
w("- Trainer `research/pipeline/g015_net_train.py` md5 `a32bb0f759a884b2cb3cdff7aa1e9297` (nhung nguyen vao kernel, assert md5), xgboost 3.2.0, GPU, seed 42, 16 fold; kernel `chuyendinh/netthr-m015-gpu|m010-gpu|m020-gpu` (dataset `funding-oi-percoin`, `funding-unf15-data`, `sel1m-code`; chi link file feature/label start < 20260101).")
w("- Fold 20240101: n_train 14,834,006 · pos 0.1864 · spw 4.365823 **khop tuyet doi** deploy (G4_RECIPE_C4). Fold dau n_train 3,730,472 khop kernel ablation cu.")
w("- **KHONG the spearman 1.0/fold**: retrain GPU khong byte-identical (runbook §0 rui ro 2; chi predict-tu-model-goc moi 1.0). Thay bang: xs-rank-corr per-tick M_015 vs predwf_G015x26 (deploy) = **%.3f** (theo fold %s). Day la **san nhieu retrain** de doc moi so sanh ben duoi." % (
    d["overall_xs_rank_corr"]["ORIG"], ", ".join("%.2f" % F[c]["orig_vs_M_015_spearman_xs"] for c in cuts)))
o = B["ORIG"]["overall"]
w("- San nhieu bang so: ORIG − M_015 (CUNG nhan, chi khac retrain): ΔrankIC %s (CI infl %s — 'ngoai 0' du la nhieu thuan, vi CI block-72h khong bao seed/device noise), Δlift@8 %s, ΔAUC %s. **|Δ| <= ~0.0007 (IC) la nhieu.**" % (
    f5(o["ic"]["delta"]), ci(o["ic"]), f5(o["lift8"]["delta"]), f5(o["auc"]["delta"])))
w("")
w("## 2. Tang model — tong 16 fold (mean per-fold; per-timestamp cross-section, MIN_N 30 coin/tick)")
w("")
w("Target do co dinh = `retEnd_4h`; win_ref = `retEnd_4h > 0.015` cho lift/AUC. lift@8 = win-rate top-8 theo p / win-rate toan tick. AUC_cs = AUC per-tick (win_ref). spread = mean(retEnd top-8) − mean(retEnd toan tick).")
w("")
w("| arm | rank-IC | lift@8 | AUC_cs | spread top8 (4h) | p_mean | p_std | xs-corr vs M_015 |")
w("|---|---:|---:|---:|---:|---:|---:|---:|")
for k in ["M_015", "M_010", "M_020", "ORIG"]:
    x = OM[k]
    xc = "—" if k == "M_015" else "%.3f" % d["overall_xs_rank_corr"][k]
    w("| %s | %s | %.4f | %.4f | %+.5f | %.4f | %.4f | %s |" % (k, f5(x["rank_ic"]), x["lift8"], x["auc_cs"], x["t8ret_spread"], x["p_mean"], x["p_std"], xc))
w("")
w("(ORIG = predwf_G015x26 deploy, chi tham chieu san nhieu.)")
w("")
w("### Delta paired vs M_015 (CI block-72h 2000 rep seed 20260905, inflate k=2 = %.4f)" % d["infl"])
w("")
w("| arm | metric | Δ | CI95 raw | CI95 inflate | folds Δ>0 |")
w("|---|---|---:|---|---|---:|")
for a in ["M_010", "M_020"]:
    for mname, key in [("rank-IC", "ic"), ("lift@8", "lift8"), ("AUC_cs", "auc"), ("win-rate top8", "t8win"), ("spread top8", "t8ret")]:
        oo = B[a]["overall"][key]
        if key in ("ic", "auc", "t8win", "t8ret"):
            npos = sum(1 for c in cuts if B[a]["per_fold"][key][c]["delta"] > 0)
            ns = "%d/16" % npos
        else:
            npos = sum(1 for c in cuts if F[c][a]["lift8"] > F[c]["M_015"]["lift8"])
            ns = "%d/16" % npos
        w("| %s | %s | %s | [%+.5f, %+.5f] | %s | %s |" % (a, mname, f5(oo["delta"]), oo["lo"], oo["hi"], ci(oo), ns))
w("")
w("## 3. Theo fold")
w("")
w("| fold | IC M_015 | ΔIC M_010 | ΔIC M_020 | lift M_015 | Δlift M_010 | Δlift M_020 | xc M_010 | xc M_020 | xc ORIG |")
w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for c in cuts:
    f = F[c]
    w("| %s | %s | %s | %s | %.3f | %+.3f | %+.3f | %.3f | %.3f | %.3f |" % (
        c, f5(f["M_015"]["rank_ic"]), f5(B["M_010"]["per_fold"]["ic"][c]["delta"]), f5(B["M_020"]["per_fold"]["ic"][c]["delta"]),
        f["M_015"]["lift8"], f["M_010"]["lift8"] - f["M_015"]["lift8"], f["M_020"]["lift8"] - f["M_015"]["lift8"],
        f["M_010"]["xs_rank_corr_vs_M_015"], f["M_020"]["xs_rank_corr_vs_M_015"], f["ORIG"]["xs_rank_corr_vs_M_015"]))
w("")
w("## 4. Cong (pre-reg + dieu kien MASTER)")
w("")
w("| arm | ΔrankIC CI infl > 0 (pre-reg) | > san nhieu 0.0007 | lift@8 khong kem | QUA CONG SIM |")
w("|---|---|---|---|---|")
w("| M_010 | CO (%s) | CO | **KHONG** (Δ %s, CI %s) | **KHONG** |" % (ci(m10["ic"]), f5(m10["lift8"]["delta"]), ci(m10["lift8"])))
w("| M_020 | KHONG (%s) | — | co (Δ %s) | **KHONG** |" % (ci(m20["ic"]), f5(m20["lift8"]["delta"])))
w("")
w("## 5. Rui ro / gioi han")
w("")
w("1. **Mot seed, mot may (GPU)**. CI block-72h chi bao bien dong thoi gian, KHONG bao bien dong retrain. San nhieu do duoc (ORIG vs M_015) ΔIC 0.0007, xs-corr 0.94. ΔIC cua M_010 (0.0080) gap ~12x san; nhung Δlift/AUC cua M_010 va M_020 nen doc voi cung san (ΔAUC ORIG −0.0018 vs M_010 −0.0144: gap ~8x).")
w("2. **rank-IC vs retEnd_4h AM moi fold** (ca deploy). Model chon coin de vuot +1.5% (vol cao) — lift@8 ~1.69 nhung spread return top-8 chi ~+2bp/4h. rank-IC theo retEnd la proxy yeu cho viec selector lam; ΔIC>0 o M_010 co the chi la bot nghieng vol. Dinh nghia lift@8/AUC/spread do toi (script `netthr_metrics.py`) chot theo pre-reg 'lift@8 (top-8 admit), AUC' voi win_ref co dinh 0.015 — pre-reg khong ghi cong thuc chi tiet, day la dien giai.")
w("3. spread top-8 return tang o M_010 (+%.5f, CI infl %s) nhung la ~2.4bp/4h, cung bac voi nhieu economics — khong dung de chung minh loi ich." % (B["M_010"]["overall"]["t8ret"]["delta"], ci(B["M_010"]["overall"]["t8ret"])))
w("4. **Khong sim** => khong biet ΔIC/Δlift co chuyen thanh §9 khong, va gate rolling G2 co tu hieu chinh khong. Ket luan 'label-thr khong phai lever' chi o TANG MODEL, mot seed.")
w("5. Base rate nhan toan DEV tren Kaggle = 0.1885 (pre-reg ghi 0.1849, kha nang gom 2026); khong anh huong (n_train fold 20240101 khop tuyet doi).")
w("6. Provenance: chain kernel (`~/claude_master/0930_netthr`) da dung san truoc khi toi vao (khong ro nguoi tao); toi da review (md5 trainer, fold list, symlink chi <20260101, THR/ARM tung kernel) truoc khi dung. Dataset `funding-unf15-data` khong doc truc tiep, nhung khop n_train/pos/spw voi deploy nen chap nhan.")
w("")
w("## 6. Viec treo")
w("")
w("- MASTER quyet: (a) chap nhan verdict 'khong sim'; hoac (b) sim M_010 theo chu pre-reg (bins `out_M_010` neu con; da xoa se phai tai lai kernel `chuyendinh/netthr-m010-gpu`); hoac (c) them seed (M_015 s43 + M_010 s43) de dong san nhieu — can amendment pre-reg truoc.")
w("- Neu muon do 'thu hang vs vol-tilt' ro hon: doi target do (vd. quantile-return rank, hoac IC vs |ret|/vol) — ngoai pham vi pre-reg.")
w("")
w("## 7. File / job")
w("")
w("- Kaggle kernels COMPLETE, khong con job chay: `chuyendinh/netthr-m015-gpu`, `netthr-m010-gpu`, `netthr-m020-gpu`.")
w("- Ma: `research/analysis/netthr/` (`netthr_metrics.py`, `netthr_build_kernel.py`, `netthr_kernel_template.py`, `netthr_chain.sh`, `netthr_show.py`, `netthr_make_result.py`). Tho: `docs/result/label_netthr.json`.")
w("- Bins goc (16 fold x 3 arm) o `~/claude_master/0930_netthr/out_M_0xx` — da don sau commit (xem tin nhan).")
open(R + "/docs/result/RESULT_LABEL_NETTHR.md", "w").write("\n".join(L) + "\n")
shutil.copy(SRC, R + "/docs/result/label_netthr.json")
log.info("written %d lines", len(L))
