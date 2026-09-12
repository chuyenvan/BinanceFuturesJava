# PREREG_DEV2021_READJUDICATE — phan xu lai T170 / T130 (+ GD92 blocked) tren DEV mo rong ve 2021

Commit TRUOC khi chay bat ky sim variant nao. Khong sua sau khi thay ket qua.
Nguon da doc: RESULT_DEV2021, PREREG_DEV2021, PREREG_X1, run_x1.sh, run_x1_sim.sh,
x1_build_map.py, x1_s1_rank.py, x1_s1_save_model.py, WfoDataset.java, ExportWfoDataset,
RESULT_GATESCALE, RESULT_GATEDYN, RESULT_GATEDYN2, AUDIT_GATEDYN_GD92, x1_rates.py.

## 0. Muc tieu
DEV da mo lui ve 2021 (RESULT_DEV2021: x26 2021 3 fold + S1 2021 2 fold, integrity PASS).
Them fold 2021 = them lenh OOS 2021Q3+Q4 => power cao hon. Phan xu LAI cac bien the gate
"chet TRONG CI (khong sai huong)" voi power moi. KHONG cham holdout 2026 (SIM_END_DATE=20251231),
KHONG cham 242, KHONG tune, KHONG push, KHONG doi code / rebuild.

## 1. Chon config (<=3, 1/family) — doc RESULT cu, KHONG bia config moi
- **T170** (tighter dyn-gate): `profiles/x1_gs_t170.properties`, SIM_GATE_DYN_SCALE=1.70.
  RESULT_GATESCALE: T170 co 2 rate CHAT LUONG ngoai CI (win% +2.87, TSloss% -4.85) DEU TOT,
  nhung d CAGR CI [-18.1,+8.9] OM 0 => "khong phan biet duoc" = chet TRONG CI, dung huong.
- **T130** (gate-scale bien con lai, gan pass nhat): `profiles/x1_gs_t130.properties`, scale=1.30.
  Giua L80/T130: T130 gan pass hon (d CAGR -8.3pp vs L80 -12.9pp; T130 0 rate xau, L80 3 rate
  xau SAI HUONG). L80 = flat-ward da biet xau => KHONG chon. T130 = diem bien GS con lai.
- **GD92** (rolling pct=0.92/90d): **BLOCKED — KHONG chay, bao master, KHONG va.**
  Co che GateRollingThreshold + key SIM_GATE_ROLLING_PCT/DAYS DA BI XOA o commit f1c43a3
  (L7: "gate ve MOT class EntryGate + xoa 4 co che tro"; 149 dong GateRollingThreshold.java xoa;
  profiles/x1_gd92.properties -> profiles/archive/). Jar HEAD 8dd10ae: EntryGate chi con
  GATE_DYN_SCALE. Chay GD92 = khoi phuc code da xoa + rebuild = doi code + build = NGOAI pham vi.

=> Chay **2 variant: T170, T130**. Multiplicity **k = so variant chay = 2**.

## 2. Baseline MOI (DEV mo rong)
X1_C3_FULL tren DEV mo rong = baseline MOI (md5 KHAC 2478e90d cu vi dataset + cua so khac).
`profiles/x1_c3_full.properties` (SIM_GATE_DYN_SCALE khong khai = 1.0). Devrun: X1_C3_FULL_2021.
SIM_END_DATE=20251231, TIME_RUN=20210701 (cua so 2021-07-01..2025-12-31), holdout 2026 nguyen ven.

## 3. Tich hop fold 2021 (bins + dataset) — cong sanity, fail => DUNG + bao
- S1 2021 rank: `x1_s1_rank.py` X1_CUTS="20210701 20211001" (canonical script, seed42 CPU/hist,
  X1_SHUF=999=tat shuffle) => `pred_s1a2x1_y21.parquet` (2 fold OOS 2021Q3/Q4). Ledger
  cand_dev_x1.parquet da co 2021 (ts_min 2021-03-31).
- Mapped bins 2021: `x1_build_map.py` name=s1a2x1_y21, X1_CUTS="20210701 20211001",
  X1_G015_DIR=/home/ubuntu/kg015x26_2021/g015x26-2021-gpu/out =>
  `predwf_map_s1a2_x1_2021/predict_wf_2021{0701,1001}.bin`. Cong: ty le "co score" 2021 > 0 va
  cung bac do lon voi cac fold cu; ~0 (lech key ts/sym) => DUNG.
- Bins dir mo rong: COPY 16 bins cu tu predwf_map_s1a2_x1 (verify sha256 khop BINS_SHA256) + 2 bins
  2021 = 18 bins trong predwf_map_s1a2_x1_2021. KHONG ghi de dir goc.
  Cong: ts-range 18 bin ROI NHAU (WfoDataset disjoint guard) + moi span<=100d; overlap => DUNG.
- Dataset: ExportWfoDataset, profile tro WFO_FUNDING_PRED_DIR=predwf_map_s1a2_x1_2021 =>
  `wfo_ds_x1_2021` (KHONG ghi de wfo_ds_x1). Cong: manifest foldCount=18, leakFreeFrom=2021-07-01.

## 4. Cong sanity 2022+ overlap (fail => DUNG + bao)
So tap (symbol, entry_time, exit_reason) cua X1_C3_FULL_2021 entry>=2022-01-01 vs baseline cu
X1_C3_FULL_PARITY_R (n=2266, 16 fold, cung model cac fold do). Ky vong overlap CAO. Margin/equity
path doi do warmup 2021 nen KHONG so margin. Overlap thap bat thuong => nghi corruption/leak =>
DUNG + bao, KHONG va.

## 5. Cham + quyet dinh
- `research/analysis/x1_rates.py X1_C3_FULL_2021 <variant>` (5 rate + CI khoi-72h x1.21, bang nam,
  rang buoc cung tuyet doi HARD_DD=15 / UW=120 / nam>=0 / quy>=-5).
- Quyet dinh (theo LUAT CU): variant THANG <=> >=2 rate CHAT LUONG ngoai CI CUNG HUONG TOT
  (tren toan cua so mo rong) VA PASS het rang buoc cung tung nam. Else NULL.
  Multiplicity k=2. Ghi ca hai cach doc: (a) x1_rates.py CI x1.21 (block-72h), (b) ghi chu
  nguong nghiem hon sqrt(2 ln 2)=1.177. NULL co tinh thong tin.
- Bao rieng (KHONG phai tieu chi): equity/CAGR/n.

## 6. Du doan ghi truoc (de kiem chinh minh)
- T170: 2 rate (win%/TSloss%) co the van ngoai CI dung huong voi power moi -> co the THANG neu
  rang buoc cung con PASS ca 5 nam (2021-2025). T130: nhieu kha nang NULL (cu 0 rate ngoai CI).
  Xac suat >=1 variant THANG ~35%. Rang buoc cung 2021 (thi truong som, bien dong) la rui ro moi.

## 7. Ngoai pham vi
Holdout 2026, tune sieu tham so / doi seed / doi scale sau khi thay so, box 242, config moi,
khoi phuc + rebuild GD92, git push, ghi de dir/dataset goc.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
