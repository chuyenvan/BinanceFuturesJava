# PREREG_HOLDOUT_2026_DRAFT — phán xử HOLDOUT 2026 (arm chính R4, arm phụ G2)

> **TRẠNG THÁI: DRAFT — CHƯA CHỐT.** File này là bản nháp chuẩn bị, KHÔNG phải pre-reg final.
> Chưa được owner duyệt. KHÔNG chạy bất kỳ sim nào qua 2025-12-31 cho tới khi bản này được chốt
> thành `PREREG_HOLDOUT_2026.md` (commit final) VÀ owner duyệt mở seal trong chat.
> Nhiệm vụ E3 chỉ là CHUẨN BỊ: kiểm niêm phong, kiểm kê đầu vào, soạn nháp — KHÔNG chạy sim 2026,
> KHÔNG tính bất kỳ PnL/metric 2026 nào.

---

## 0. RỦI RO — đọc TRƯỚC khi quyết định mở seal (kế thừa `PREREG_H1.md` §0 + `H1_HOLDOUT_PREP.md` §0)

1. 🔴 **2026 KHÔNG còn là holdout nguyên trinh ở tầng gate.** Model gate sinh `p15`
   (`wfo_models/fold_*/Model_Regressor_Return15M.onnx`) được GHI **2026-08-06**, và `WFOGateRunner`
   chạy kế hoạch fold với `end=20260701` ngày **2026-08-19** — tức feature (33 V3FULL), nhãn
   (`label_oldbasket`), siêu tham số và kế hoạch fold đều CHỐT trong lúc kết quả 2026 đang được
   nhìn thấy và backtest. Seal chỉ đặt **2026-09-01**. Phần "researcher degrees of freedom" này
   **không gỡ lại được** ⇒ kết quả 2026 là forward test **có nhiễm**, không phải holdout sạch.
2. 🔴 **Fold cuối TỰ FIT vào holdout.** `fold_20` train tới 2026-04-01 rồi dự báo 2026Q2 — model Q2
   đã thấy Q1 của chính holdout. Đúng chuẩn WFO/live nhưng sau Q1 holdout không còn "model-naive".
3. 🔴 **Cửa sổ chỉ 6 THÁNG (2026-01-01..2026-07-01), không phải 8.** Chặn cứng là feature store gate
   (`gate_dataset_full.csv.gz`) + Tool1 + OI đều hết 2026-07-01 (xem §6). `SIM_END_DATE=20260701`,
   không được kéo xa hơn.
4. 🔴 **~40–45 block 72h ⇒ CI rộng ~2× so với cửa sổ 48 tháng.** Kết luận phải dựa vào RÀO CỨNG và
   DẤU, không dựa vào "có ngoài CI không". Kỳ vọng 0–1 rate ngoài CI.
5. 🔴 **Bins selector 2026 CHƯA có, và nguồn `predwf_G015x26` KHÔNG tái lập được** (§6). Đây là
   blocker đứng — xem §6 và §7. Không có bins ⇒ không có `funding.bin` 2026 ⇒ không chạy được sim 2026.
6. 🔴 **Arm phụ `G2` = code `GateRollingRatio` (jar GDV2 `7368be46…`) CHƯA merge vào `module`.** Nằm
   ở worktree `/home/ubuntu/claude_master/wt_gdv2`. Nếu dùng G2 trên 2026 phải build lại jar từ worktree
   đó (hoặc merge có chủ đích) và **re-verify parity G0 = R4 (md5 `06fd6e9a`)** TRƯỚC khi mở seal.
7. ⚠️ Đĩa Oracle ~11G trống trong / 194G (~95%). Dataset WFO ~4.5G ⇒ xóa ngay sau khi chạy.

---

## 1. CỬA SỔ — chốt 2026-01-01 → 2026-07-01 (GMT+7), 6 tháng, 2 fold

| mốc | giá trị |
|---|---|
| bắt đầu | `1767225600000` = 2026-01-01 00:00 UTC = `HoldoutSeal.SEAL_MS` |
| kết thúc | `1782838800000` = 2026-07-01 00:00 GMT+7 = 2026-06-30 17:00 UTC |
| fold bins | `20260101` (OOS Q1), `20260401` (OOS Q2) — 2 fold, span 90d/91d |
| `SIM_END_DATE` | `20260701` |

---

## 2. HAI ARM — dùng 2, KHÔNG biến thể

### 2.1 Arm CHÍNH duy nhất = `R4` (baseline nghiên cứu, owner chốt 2026-09-29)

- Profile: **`profiles/r4_kg0_k16_f015_g155.properties`** (`docs/decisions/DECISION_BASELINE_R4.md`).
- Khác KEEPLEG0 đúng 5 key: `SELECTOR_RANK_TOPK 8→16`, `SIM_GATE_DYN_SCALE 1.70→1.55`,
  `SIM_F_BASE=0.015`, `SIM_ENTRY_SAMPLE_MIN=1` (nhịp 1′), `SIM_RATE_FEE`+`SIM_SLIPPAGE_RATE` (phí base 0,1116%/vòng).
- **md5 profile (parity):** `printDone.csv` = **`06fd6e9aa9c916945b2cf12310b337ff`** @base (n 2027, eq 104 489);
  @stress = `84402b57`.
- DEV 48 tháng (2021-07-01..2025-12-31): **n 2027 · eq 104 489 · CAGR 27,53 % · ddPhut −16,42 % ·
  UW 164,7 ngày · q* 21,7 % · conc 5,30 % · Calmar_MTM 1,676** (`RESULT_RESET_RULE_P2`, `47a9d90`).

### 2.2 Arm PHỤ = `G2` (mô tả / so sánh, KHÔNG phải đối tượng PASS/FAIL)

- `GateRollingRatio` W90 trên nền R4: `SIM_GATE_ROLLING_MODE=ratio`, `SIM_GATE_ROLLING_PCT=1−ρ`,
  `SIM_GATE_ROLLING_DAYS=90` (`PREREG_GDV2_EVEN`, `2b4dcbd3`). ρ = 4,917e-5 (pct = 0,99995083).
- DEV 48 tháng: **n 2509 · eq 131 374 · CAGR 34,18 % · ddPhut −17,99 % · UW 128,9 ngày · Calmar_MTM 1,900**
  (`RESULT_GDV2_EVEN`, `39944dbb`). GDV2_P3 (`b7f0358f`): G2 PASS 4 tầng @stress nhưng **KHÔNG thay R4**
  (jackknife top-1 FAIL + dCalmar CI chứa 0).
- **Vai trò:** mô tả xem lợi thế "đều lệnh" của G2 (CV n quý 0,505 < 0,693 của R4) có tồn tại trên 2026
  hay chỉ là quá khớp DEV (~26 lần thử). KHÔNG dùng G2 để đổi incumbent; chỉ báo cáo song song.

---

## 3. CỔNG ĐẦU VÀO — phải PASS hết trước khi mở seal (kế thừa `PREREG_H1.md` §2)

| cổng | đo gì | tiêu chí |
|---|---|---|
| **P1** `p15` | tái tạo `predReturn15M` một fold DEV từ feature store + ONNX, đối chiếu `claudedata/wfo_gate_pred.csv` | **spearman ≥ 0,999** (byte-identity báo riêng, do `%.8f` float32) |
| **P2** `CLOSES_1H` | dựng lại đoạn 2025-12 bằng đúng generator gốc, đối chiếu file hiện có | byte-identical |
| **P3** ledger/featv2 | `feat_v2_h1` cắt tới 2024-07-01 == `feat_v2.parquet`; `cand_dev_h1` cắt tới T1 == `cand_dev.parquet` | bằng tuyệt đối (`equal_nan`) |
| **P4** bins | sha256 **16 fold cũ** của bins H1 == `BINS_MANIFEST.md` (`b87762312620f317…`) | 16/16 trùng |
| **P5** parity dataset | build dataset `SIM_END_DATE=20251231` rồi chạy R4 ⇒ đúng `p2-r4-base` | **md5 printDone `06fd6e9a` / n 2027 / eq 104 489** |

**P5 FAIL ⇒ DỪNG** (dataset builder đã vỡ với bins mới; mọi số 2026 sau đó vô nghĩa).
**P1 ✅ đã PASS** (xem §6: `wfo_gate_pred_2026_H1.csv`). **P2/P3/P4 ⛔ bị chặn bởi blocker §6.**

---

## 4. TIÊU CHÍ PASS/FAIL cho `R4` (đối tượng phán xử)

### 4.1 T1 — RÀO RỦI RO (giữ NGUYÊN ngưỡng của luật 4 tầng §9, không hạ)

Ngưỡng giữ nguyên từ `RISK_APPETITE.md` §9 / `RESULT_RESET_RULE_P2` §4 TẦNG 1:

| rào | ngưỡng | ghi chú cho cửa sổ 6 tháng |
|---|---|---|
| maxDD MTM phút | **≤ 40 %/năm** | cửa sổ 6 tháng ⇒ đo trên chuỗi equity MTM phút của 2 quý; "năm xấu nhất" suy biến thành "quý xấu nhất" |
| UW | **≤ 250 ngày** | 6 tháng không đo được UW có ý nghĩa ⇒ **CHỈ BÁO CÁO, không phải rào** (kế thừa X1 muc 7) |
| quý xấu nhất | **≥ −20 %** | đánh trên 2 quý 2026Q1/Q2 |
| 0 năm âm | **CỨNG** | suy biến: không quý nào âm nặng quá −20 % (trùng rào trên) |
| conc 1 coin | **≤ 15 %** (CỨNG) | |

### 4.2 KỲ VỌNG — số lệnh / win% / TSloss% / Calmar so DEV, khoảng dự báo TÍNH TRƯỚC

DEV R4 (48 tháng) làm mốc; 6 tháng = 1/8 thời lượng ⇒ `n_eff` ~40–45 block 72h ⇒ CI rộng ~2×.
Khoảng dưới là **dự đoán ghi trước**, KHÔNG phải ngưỡng PASS/FAIL (kế thừa tinh thần `PREREG_H1` §6).

| chỉ số | DEV R4 | kỳ vọng 2026H1 | cơ sở |
|---|---|---|---|
| `n` (lệnh) | 2027 / 48 tháng | **~200–330** (≈ 1/8 DEV, khoảng 95%) | 2025 = ~784 lệnh/năm; universe còn nở |
| `win%` | ~84 % | **82–86 %** (không xấu đi) | X1 muc 10.2: ổn định xuyên 4 năm |
| `TSloss%` | ~15 % | **14–18 %** | X1 muc 10.2 |
| `mean(profit\|SL)` | −21,85 → (R4 ~−21) | **−24…−34** (xấu hơn DEV) | X1 muc 10.3: độ sâu lệnh thua đang tăng |
| `Calmar_MTM` | 1,676 | **báo riêng, KHÔNG phải tiêu chí** | `sd(dCAGR)` 6 tháng chưa có số đo; equity không phải tiêu chí |
| `conc 1 coin` | 5,30 % | ≤ 15 % (rào) | |

⚠️ **Ghi trước:** "0 rate ngoài CI" là kết quả **null có thông tin**, không phải thất bại của phép đo.
Equity/CAGR báo RIÊNG, dán nhãn "không phải tiêu chí".

### 4.3 VERDICT R4 (luật kết luận — chốt TRƯỚC)

- **PASS** ⇔ R4 **không vi phạm bất kỳ rào cứng nào** ở §4.1 (maxDD, quý ≥ −20 %, conc ≤ 15 %).
- **FAIL** ⇔ vi phạm ít nhất một rào cứng.
- Chỉ báo cáo, KHÔNG tự kết luận "R4 hơn/bằng DEV" — phán xử cuối thuộc owner (luật 4 tầng + rào cứng).

---

## 5. LUẬT CHẠY — một lần duy nhất, không tune sau

1. **Chạy ĐÚNG 2 arm (R4 + G2), TUẦN TỰ, `SIM_END_DATE=20260701`**, `TICKER_SOURCE=file`, neo Kaggle
   (bundle `sim-x1-2021-bundle` + overlay jar/profile) — theo `KAGGLE_SIM_48M.md`. G2 cần jar GDV2 `7368be46`.
2. **MỘT LẦN.** Không grid, không sweep, không "thử thêm một mức", không re-seed. Chạy xong seal lại ngay.
3. **Không tune sau khi thấy số.** Mọi đổi thiết kế (vd: đổi nguồn bins, đổi ngưỡng trailing 0.29) = **AMENDMENT**
   có lý do, commit TRƯỚC khi xem số bị ảnh hưởng.
4. **FAIL thì làm gì** (chốt trước):
   - Nếu **P1–P5 chưa PASS** ⇒ KHÔNG mở seal; sửa blocker trước (xem §7).
   - Nếu R4 **vi phạm rào cứng 2026** ⇒ **giữ incumbent production `B*`**, KHÔNG đổi sang R4; ghi ledger holdout
     đã tiêu một lần; chờ owner quyết hướng tiếp (không tự mở biến thể quanh R4).
   - Nếu R4 **qua rào cứng** ⇒ báo cáo như forward test **có nhiễm** (§0), kèm cảnh báo `fold_20` tự fit; KHÔNG tự
     nâng cấp production.
5. **Ghi ledger holdout** sau khi chạy (đã tiêu `HOLDOUT_UNSEAL` một lần duy nhất).

---

## 6. HIỆN TRẠNG ĐẦU VÀO 2026 (kiểm kê 2026-09-29)

| đầu vào | phục vụ | mep hiện có | trạng thái |
|---|---|---|---|
| ticker 1m (`kaggle_data_hpo/ticker_*.bin.gz`, 2008 file) | giá vào/ra | **2026-07-01** | ✅ đủ (có tới 2026-07-01) |
| OI/derivs (`oi_percoin_20210101_to_20260701.bin.gz`) | feature selector | **2026-07-01** | ✅ đủ |
| `p15` gate (`claudedata/wfo_gate_pred_2026_H1.csv`, sha256 `4cc62c14…`, 260 183 dòng) | gate entry | **2026-07-01** | ✅ đã sinh (P1 PASS; CHƯA nạp Aerospike) |
| **bins selector S1+net015 (`predict_wf_20260101/20260401.bin`)** | `funding.bin` (thứ tự S1 + P(win) net015) | **CHỈ tới 20251001** | 🔴 **THIẾU — BLOCKER** |

### 6.1 Blocker đứng — bins selector 2026 (kế thừa `H1_HOLDOUT_PREP.md` §3/§5)

1. 🔴 **`CLOSES_1H.bin` không có generator.** Toàn bộ file trên đĩa/git đều là READER; không file nào GHI ra nó.
   Không dựng lại được ⇒ `feat_v2`/`cand_dev` không mở rộng sang 2026 ⇒ không train S1 cho 2026 ⇒ không có bins.
   Hai đường đi (user chọn, KHÔNG phải agent chọn): (a) viết generator từ Vision kline 1h; (b) gộp `kline_1m_opt` lên 1h.
2. 🔴 **Bins fold 2026 lấy P(win) từ đâu?** `build_map.py` giữ nguyên multiset P(win) của `predwf_G015x26`;
   fold `20260101`/`20260401` đã bị XÓA và `predwf_G015x26` **không tái lập được**. Train mới = họ `G015_v2`, hiệu
   chuẩn KHÁC ⇒ bản lề trailing `symbolPred <= 0.29` (ngưỡng TUYỆT ĐỐI) đổi nghĩa ⇒ `%STRONG` 2026 đổi vì lý do
   không liên quan 2026. Phải làm phép đo hiệu chuẩn (chỉ DEV, hợp lệ) trước khi chạy (xem `PREREG_H1` §7).

### 6.2 Kế hoạch build còn thiếu (chỉ DEV-train < mốc dự báo, không leak)

Chỉ chạy sau khi owner chốt 2 blocker trên. Trình tự (theo `run_x1.sh`, `x1_ledger.py`, `g72_train.py`,
`x1_s1_rank.py`, `c4_build_map.py` — bản tham số hoá copy vào `research/pipeline/h1/`, không sửa bản gốc):

1. Dựng `CLOSES_1H` 2026 (đường (a) hoặc (b), chờ owner) + kiểm P2 byte-identical đoạn 2025-12.
2. `x1_ledger.py build` với `X1_CUTS` thêm `20260101 20260401`, `X1_LBGLOB='202[1-6]'` (bẫy glob — không là thiếu 2026 im lặng).
3. `g72_train.py` (net015, họ G015_v2) train cutoff `< 20260101`/`< 20260401`, predict OOS — đo hiệu chuẩn vs `G015x26/20251001` TRƯỚC.
4. `x1_s1_rank.py` (S1) train cutoff `< mốc dự báo, predict OOS.
5. `c4_build_map.py` ghép S1 + net015 → `predict_wf_20260101.bin` / `predict_wf_20260401.bin`.
6. Kiểm leak từng fold: **ngày train max < ngày dự báo min**; OI `create_time` phải < mốc dự báo (xem `docs/ops/OI_FIX_LOG.md` / ghi chú data leak OI 09-03).
7. Chạy P3/P4/P5 (§3). P5 FAIL ⇒ DỪNG.

**KHÔNG chạy simulator trên 2026. KHÔNG tính bất kỳ PnL/metric 2026 nào trong bước build này.**

---

## 7. LỆNH MỞ SEAL (CHƯA CHẠY — chỉ ghi để owner chạy một lần khi duyệt)

`HoldoutSeal.java`: `SEAL_MS = 1767225600000`, `UNSEAL_PHRASE = "I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026"`.
Điểm chốt: `WfoDataset.export` (`trimMap`) và `SimulatorMarketLevelTicker1MStopLoss.main` (`clampEnd`).

```bash
export HOLDOUT_UNSEAL=I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026
```

Log PHẢI có dòng `!!!!!!!! HOLDOUT_UNSEAL DUNG ... LAN NAY TINH VAO LEDGER HOLDOUT. !!!!!!!!` ở cả export dataset
lẫn sim. Không thấy dòng đó ⇒ seal chưa mở ⇒ số ra là 2025, vứt đi. Sau khi chạy: `unset HOLDOUT_UNSEAL`,
ghi kết quả vào `docs/result/RESULT_HOLDOUT_2026.md` + ledger holdout.
Lệnh build dataset + 2 arm đầy đủ: mượn `H1_HOLDOUT_PREP.md` §7 (thay profile `h1_c3*` → `r4_kg0_k16_f015_g155`
và arm G2 bằng jar `7368be46`).

---

## 8. CHỖ OWNER DUYỆT (để trống — owner điền)

- [ ] Duyệt cửa sổ 2026-01-01 → 2026-07-01 (GMT+7), 6 tháng, 2 fold.
- [ ] Duyệt arm chính `R4` (md5 `06fd6e9a`) + arm phụ `G2` (mô tả).
- [ ] Chốt blocker `CLOSES_1H` (đường (a) Vision 1h hay (b) gộp kline 1m) — §6.1.1.
- [ ] Chốt nguồn bins net015 (train `G015_v2` mới vs giữ `G015x26`) sau phép đo hiệu chuẩn — §6.1.2.
- [ ] Chốt mở seal (`HOLDOUT_UNSEAL`) — một lần duy nhất.
- [ ] Ký tên / ngày duyệt: ______________

---

## 9. TÁI LẬP / NGUỒN

- Pre-reg H1 cũ: `docs/prereg/PREREG_H1.md` · kế hoạch: `docs/plan/H1_HOLDOUT_PREP.md`.
- Luật 4 tầng: `docs/analysis/RULERS_CURRENT.md` §13 · `docs/runbooks/RISK_APPETITE.md` §9.
- Baseline R4: `docs/decisions/DECISION_BASELINE_R4.md` · `profiles/r4_kg0_k16_f015_g155.properties`.
- R4 DEV: `docs/result/RESULT_RESET_RULE_P2.md` (`47a9d90`) + P3 (`911ad42`).
- G2: `docs/prereg/PREREG_GDV2_EVEN.md` (`2b4dcbd3`) · `docs/result/RESULT_GDV2_EVEN.md` (`39944dbb`).
- Sim Kaggle: `docs/runbooks/KAGGLE_SIM_48M.md`.
