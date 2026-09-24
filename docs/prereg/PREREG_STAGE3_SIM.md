# PREREG_STAGE3_SIM — chốt TRƯỚC: SIM 3 biến thể (V0/V5/V1) vs MỐC 45-feature (KEEPLEG0)

**Ngày chốt:** 2026-09-25 · **Chi nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC — chưa chạy kernel nào
**Tiền đề (đã đóng băng):** `docs/result/RESULT_STAGE2_TRAIN.md` (commit `2101540`) — Stage 2 **NULL toàn bộ**
(`ΔIC(V5−V0) = −0,004332 [−0,006828, −0,001786]` ⇒ đối chứng NHIỄU cùng mask cũng "thắng" mốc;
V1/V3 hơn V0 nhưng **không tách được khỏi V5**); pre-reg Stage 2 = `PREREG_STAGE2_FEATVAR.md` (`dd27c6c`).
**Runbook:** `AGENT_RUNBOOK.md` §0 (DEV only · pre-reg trước · equity KHÔNG phải tiêu chí · so sánh CÙNG
NGUỒN HẠ TẦNG · không push git · không sim trên Oracle), `RISK_APPETITE.md` §6–§7, `KAGGLE_SIM.md`.

> Luật của vòng này: **chốt TRƯỚC rồi mới chạy.** Mọi thứ dưới đây (kênh · cách dựng bins/dataset ·
> cổng parity · chỉ số · CI · k · luật quyết định · dự đoán khoá trước) **không được sửa sau khi xem số**.
> Pre-reg này phải **COMMIT trước** khi push kernel sim đầu tiên lên Kaggle.

---

## 0. CÂU HỎI

**Cắt 45 → 21 feature thì HỆ THỐNG có tệ đi không?** (thước chính = **SIM**, không phải rank-IC/lift@8 —
thước selector chỉ là thước phụ, đã NULL ở Stage 2). Hai câu phụ:
(2) SIM có phân biệt được **feature thật** với **cột nhiễu** không (V1/V5 vs V0)? *(không ⇒ cả chuỗi
bất khả phân biệt ⇒ NULL)*; (3) có nên đổi selector sang 21 feature không.

## 1. BỐN KÊNH (chốt, không thêm không bớt)

Nền = **FLATGRID KEEPLEG0** (`profiles/t170_flat_keepleg0.properties` ≡ `x1_gs_t170` +
`DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0`; `CONC_CAP_PERCOIN` 15% đã có sẵn, là **no-op** đo
được trên nền này). **CÙNG một cấu hình, CHỈ khác `WFO_FUNDING_PRED_DIR` (thư mục bins).**

| kênh | model cấp **multiset `P(win)`** cho bins | vector | file version |
|---|---|---|---|
| **MOC** | `predwf_map_s1a2_x1_2021` = 18 fold bins đang là nền `kg0-g170` (45 feature, net015) | 45 | — |
| **V0** | Stage 2 arm `V0` (21 keeper) | 21 | `fs_v4_21.json` |
| **V1** | Stage 2 arm `V1` (21 + cả 5 feature mới) | 26 | `fs_v5_26.json` |
| **V5** | Stage 2 arm `V5` (21 + 5 + 5 **cột nhiễu** cùng mask) | 31 | `fs_v9_31.json` |

**V2/V3/V4 KHÔNG chạy** (Stage 2 đã NULL, vô ích). Đây là **3 ứng viên** so với MỐC ⇒ **`k = 3`**.

### 1.1 Cách dựng bins của kênh (cố định)

Đường đang chạy: `predwf_map_s1a2_x1*` = **thứ tự coin theo ranker S1** (`pred_s1a2x1.parquet`) ×
**multiset `P(win)` giữ nguyên của model net015** (`c4_build_map.py`, xem `BINS_MANIFEST.md` §X1).
Vòng này **chỉ thay cái model cấp multiset** — giữ nguyên ranker S1:

1. `s3_build_map.py s1a2x1 <out_dir>` (= bản sao `c4_build_map.py`, **chỉ thêm** env `S1_SC` cho đường
   dẫn ledger, mặc định = hành vi cũ) với `G015_BINS_DIR = <bins Stage 2 của arm>`,
   `S1_SC = pred_s1a2x1.parquet`, `X1_CUTS = 16 cutoff 20220101..20251001`.
2. **2 fold 2021** (`predict_wf_20210701.bin`, `predict_wf_20211001.bin`) **lấy nguyên bản của MỐC**
   (Stage 2 chỉ có 16 fold từ 2022 ⇒ không có bins 2021). **Mọi kênh** (kể cả MỐC) đều có **đủ 18
   fold** ⇒ thư mục bins của 4 kênh **giống nhau về độ phủ**, chỉ khác nội dung 16 fold 2022+.

### 1.2 Cách dựng dataset WFO của kênh (cố định, và LÝ DO)

`market.bin` / `pred.bin` **copy NGUYÊN BYTE từ bundle** (`sim-x1-2021-bundle`, md5 `4ab691c908fc545c26243e8328d7a0a6`
/ `5dd6bb4c3f98d89d58770005c0001526`) ⇒ 4 kênh dùng **cùng một** market/pred ⇒ **0 confound dữ liệu**.
`funding.bin` **dựng lại** từ thư mục bins của kênh bằng một bản dịch Python **byte-faithful** của
`WfoDataset.buildFundingFromWfFiles` + `forwardFillToGrid` (h=4h, `WFO_SEL_HORIZON_IDX=0`, stale 15m):
`score = 1−p0`, mã hoá `(symId<<32) | floatBits(score)`, gom theo mốc 15m theo **đúng thứ tự file/record**,
forward-fill lên lưới phút của `market.bin`. `manifest.txt` = bản của bundle, **chỉ sửa** dòng phải sửa
(`md5_funding`, `predictWf.*`, `foldCount`, `binsSha256`, `fundingPredDir`, `exportedAt`, `fundingCount`,
`fundingRaw15mCount`) — **không** sửa `md5_market`/`md5_pred`/`schemaVersion`.

**Vì sao không `ExportWfoDataset` trên Kaggle:** đường export quét Aerospike **hôm nay**; bundle là
snapshot 2026-09-12. Lệch dữ liệu market/pred giữa các kênh ⇒ confound. Cách trên **ép mọi kênh dùng
đúng một bộ market/pred**.

## 2. CỔNG (phải PASS trước khi đọc bất kỳ số nào)

| # | cổng | PASS khi |
|---|---|---|
| **P0** | mapper | log `Loaded Symbol Mapper: N` với **N ≥ 800** (thực đo các vòng trước: 863) |
| **P1** | **MOC = mốc Kaggle** | md5 `printDone.csv` = **`99e42b75cf1a2142f9cd14dc72e371ba`**, **n = 1.085**, equity = **103.083** |
| **P2** | **bộ dựng funding là byte-faithful** | dựng lại `funding.bin` của **MOC** (18 bins của bundle) ⇒ md5 = **`8e57d900d5c54c744bfcaf5c9b27fc93`** (= md5_funding trong manifest bundle) |
| **P3** | đồng nhất dữ liệu | `md5_market`/`md5_pred` của 4 dataset = của bundle (byte-identical, vì copy) |

**P1 hoặc P2 FAIL ⇒ DỪNG, báo RỎ, không đọc số kinh tế.** (P1 FAIL nhưng P2 PASS ⇒ ghi rõ "cấu hình
sim lệch", vẫn được đọc số **so sánh giữa 4 kênh** — vì cùng lệch — nhưng **không** được gọi là tái lập mốc.)

## 3. CHỈ SỐ (chốt trước)

### (a) 5 rate + CI
`win%`, `TSloss%`, `mP|SM`, `mP|SL`, `meanP` (đúng định nghĩa `c3_rates`/`gd92xexit_score`). **`n` và
`mMargin` KHÔNG phải quality rate** (kênh thang đo của sizing compound). CI = block-bootstrap **ghép cặp
theo khối 72h, 2000 rep, seed 20260905**, báo **CẢ HAI** độ rộng: `1.21` (legacy, phụ) và
**`c3_rates.inflate(k=3) = 1.482316`** (độ rộng QUYẾT ĐỊNH). "Ngoài CI" = ngoài **cả hai**.
So sánh chính: **{V0,V1,V5} vs MOC**. So sánh phụ (câu hỏi 2): **V1 vs V0** và **V5 vs V0**, cùng luật CI.

### (b) Rào cứng `RISK_APPETITE.md` §7 — **theo năm** VÀ **toàn kỳ**
`maxDD ≤ 40%/năm` · `UW ≤ 250 ngày` · quý xấu nhất `≥ −20%` · **không** năm âm · tập trung 1 coin `≤ 15%`.
`maxDD`/`UW` **đo trên chuỗi equity MTM MỐC PHÚT** (`intraday_dd.py` §2; cache dùng lại nếu có);
biến thể P=**bar.low** báo kèm như kiểm độ bền. `qmin`/`conc`/`ret` theo chuỗi NGÀY (như các vòng trước).

### (c) Bảng PnL chi tiết theo năm (n + PnL USDT) cho **4 kênh** + **TOTAL PnL** + equity cuối.

### (d) Cơ chế: `n` · `meanP` · `hold` · `turnover` · `Σfunding/ΣPnL`.

## 4. LUẬT QUYẾT ĐỊNH (chốt trước)

Một kênh `X ∈ {V0,V1,V5}` chỉ **GIỮ/ĐỔI** khi **đồng thời**:
1. **≥ 2 rate ngoài CI** (độ rộng `inflate(3)`) **cùng hướng TỐT** so với MỐC; **VÀ**
2. **hết rào cứng** (mọi năm + toàn kỳ); **VÀ**
3. **0 rate XẤU ngoài CI**.

Không thoả ⇒ **NULL** (giữ nguyên 21 keeper/45-feature như đang chạy). Nhiều kênh cùng thoả ⇒ so theo
**trục** (V0 = cắt 45→21; V1 = thêm feature thật; V5 = thêm nhiễu cùng mask) và **không** chọn ô max
theo equity. **`V0 ≈ MOC`** ⇒ kết luận: **cắt 45→21 KHÔNG làm hệ thống tệ đi** (cũng không tốt hơn) —
có thể đề xuất giữ 21 keeper cho gọn, **kèm cảnh báo**: đổi ONNX dim = **đụng đường LIVE**, cần owner
duyệt riêng — **vòng này KHÔNG tự làm**.

**Đổi selector/ONNX/LIVE = NGOÀI PHẠM VI:** không chạm `NUM_FEATURES`, `extractFeatures45`,
`Funding_Classifier_Final.onnx`, `shadow_c3/`.

## 5. DỰ ĐOÁN KHOÁ TRƯỚC

| # | Dự đoán | Cách kiểm |
|---|---|---|
| P1 | Cổng parity P1 PASS (md5 `99e42b75…`, 1.085 leg / 103.083) | §2 |
| P2 | Cổng P2 PASS (funding dựng lại = `8e57d900…`) | §2 |
| P3 | **V0 ≈ MOC** ở 5 rate (0 rate ngoài CI, hoặc 1 rate ngoài CI ở kênh `mMargin`) | §3a |
| P4 | **V1 ≈ V0** và **V5 ≈ V0** ⇒ SIM **không** phân biệt được feature thật với nhiễu | §3a (phụ) |
| P5 | Cả 4 kênh **PASS** rào cứng §7 (mọi năm + toàn kỳ) | §3b |
| P6 | `n` của 4 kênh chênh < 20%; `Σfunding/ΣPnL` 4 kênh chênh < 5 pp | §3d |

**Nếu P4 SAI** (V5 khác V0 ngoài CI) ⇒ cảnh báo: chênh lệch đến từ *thêm cột + mask*, không phải feature.

## 6. HẠ TẦNG / CHI PHÍ / PHẠM VI

- **Toàn bộ sim trên Kaggle** (CPU kernel, bundle `sim-x1-2021-bundle`, 7 dataset `wfo-ticker-2021..2025h2`,
  `TICKER_SOURCE=file`, `SIM_END_DATE=20251231`, jar của bundle sha256 `2c2f8aef…`, `-Xmx22g`).
  **KHÔNG** Java/sim trên Oracle; **KHÔNG** claude-run/Claude Code. So sánh **Kaggle ↔ Kaggle**
  (MỐC lấy bản Kaggle `kg0-g170`). Chạy tối đa 4 kernel song song (≤ 5 slot).
- **DEV only:** cửa sổ `2021-07-01 .. 2025-12-31`. **KHÔNG** chạm 2026 / `HoldoutSeal` (kernel chỉ dùng
  bins ≤ `20251001`; mốc 18 fold cũng vậy). **KHÔNG** chạy `juice`. **KHÔNG** push git.
- Chấm điểm + CI: **offline trên Oracle** (thuần Python, không Java/sim) sau khi kéo `printDone.csv` +
  `sim.out` của 4 kênh về; MTM phút tính **trong kernel** (cần dữ liệu 1m, Oracle không còn dữ liệu 1m).
- Chi phí Kaggle = **0** (CPU kernel không tính quota).
- Output tool giữ **nhỏ**: kernel chỉ in dòng tổng kết + JSON; file lớn (`funding.bin` 4,4 GB, bins, dataset)
  **xoá** trước khi kernel kết thúc.

## 7. VIỆC KHÔNG LÀM

1. Không sim 6 arm (V2/V3/V4 NULL ở Stage 2). 2. Không đổi tiêu chí/ngưỡng/k sau khi xem số.
3. Không chạm 2026/HoldoutSeal/shadow/242. 4. Không đổi ONNX/`NUM_FEATURES`/đường LIVE.
5. Không tự tích hợp; không push.
