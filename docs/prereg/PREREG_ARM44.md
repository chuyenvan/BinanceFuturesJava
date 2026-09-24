# PREREG_ARM44 — chốt TRƯỚC: BỎ ĐÚNG **1** CỘT `rvol15m` (45 → 44), train + SIM + chấm

**Ngày chốt:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC — chưa push kernel nào
**Tiền đề (đã đóng băng):**
- `docs/result/RESULT_STAGE3_SIM.md` (`d94b61d`) — vòng SIM 4 kênh trên nền KEEPLEG0: **NULL toàn bộ**;
  kênh `V0` (cắt 45 → **21 keeper**, bỏ **24** cột) XẤU hơn MỐC ngoài CI ở **2/5** rate (`mP|SM` −0,739;
  `meanP` −1,159) nhưng PASS hết rào cứng §7. ⇒ Vòng đó **KHÔNG** test "bỏ **đúng 1** cột" — nó test
  "cắt về 21 keeper". **Chưa** kết luận được gì về việc bỏ **đúng** `rvol15m`.
- `docs/diag/DIAG_RVOL15M.md` (`6628988`) — `rvol15m` đo **ĐỘ LỚN / fat-tail**, không đo **DẦU**
  (IC vs `|retEnd|` +0,2449; AUC vs đuôi thua 0,7264 > AUC vs nhân 0,6523). Offline **không đủ** kết luận
  cắt/giữ (rank-IC nói cắt, `lift@8` nói giữ) ⇒ **SIM là thước quyết định**.
- `docs/analysis/EVAL_SELECTOR_FEATURES.md` (`025767f`) — `#36 rvol15m` gain share **34,09 %**.
- **Quyết định của owner: "bỏ `rvol15m`"** ⇒ vòng này là **kiểm chứng đúng yêu cầu đó** (1 cột).
- Tiền lệ vòng Stage 2: **đối chứng nhiễu V5 "thắng" y như feature thật** (`RESULT_STAGE2_TRAIN` §4) ⇒
  luôn cảnh giác multiplicity / luôn cần mốc so cùng nguồn.

**Runbook:** `AGENT_RUNBOOK.md` §0 (DEV only · pre-reg trước · equity **KHÔNG** phải tiêu chí · so sánh
**CÙNG NGUỒN HẠ TẦNG** · không push git · không sim trên Oracle), `RISK_APPETITE.md` §6–§7, `KAGGLE_SIM.md`.

> Luật của vòng này: **chốt TRƯỚC rồi mới chạy.** Mọi thứ dưới đây (kênh · cách dựng bins/dataset ·
> cổng parity · chỉ số · CI · `k` · luật quyết định · dự đoán khoá trước) **không được sửa sau khi xem số**.
> Pre-reg này phải **COMMIT trước** khi push kernel train đầu tiên lên Kaggle.

---

## 0. CÂU HỎI

**Bỏ ĐÚNG cột `#36 rvol15m` (45 → 44) có làm HỆ THỐNG tệ đi không?** Thước chính = **SIM** (bins của
arm 44 chạy qua đúng nền KEEPLEG0). Thước phụ = **thước CỦA CHÍNH SELECTOR** (rank-IC cross-section OOS
+ top-8 lift) — chỉ để đọc cơ chế, **không** dùng để đổi model.
⇒ **GIỮ 44 hay GIỮ 45?**

---

## 1. BAO NHIÊU KÊNH — 3 (chốt, không thêm không bớt)

Nền = **FLATGRID KEEPLEG0** (`profiles/t170_flat_keepleg0.properties`). **CÙNG một cấu hình, CHỈ khác
`WFO_FUNDING_PRED_DIR` (thư mục bins).**

| kênh | model cấp multiset `P(win)` cho bins | vector | nguồn bins | vai trò |
|---|---|---|---|---|
| **MOC** | `predwf_map_s1a2_x1_2021` = 18 fold bins đang là nền `kg0-g170` (**45** cột, net015, bản deploy) | 45 | **nguyên bản của bundle** | **MỐC** |
| **A45** | **retrain 45 cột** trong **cùng kernel** với A44 (cùng ma trận/seed/fold) | 45 | kernel train của vòng này | **đối chứng chẩn đoán** (nền nhiễu retrain — KHÔNG phải ứng viên) |
| **A44** | **retrain 44 cột** = 45 − `#36 rvol15m` | 44 | kernel train của vòng này | **ỨNG VIÊN DUY NHẤT** |

- **Ứng viên so với MỐC = đúng 1 (A44)** ⇒ **`k = 1`**. `A45` là **đối chứng chẩn đoán** (không phải
  ứng viên, không bao giờ được "GIỮ/ĐỔI"): nó tách *"hiệu ứng bỏ 1 cột"* khỏi *"hiệu ứng retrain/máy"*.
- Vì sao **không** dùng luôn A45 làm MỐC: mô hình deploy là **bản 2026-08-14**; retrain 45 hôm nay chỉ
  tái lập ở mức **spearman 0,986** (`PREP_STAGE2_TRAIN` §1.6 — *không phân biệt được* với nền nhiễu
  between-seed 0,984931). MỐC kinh tế **bắt buộc** là bản deploy (md5 `99e42b75…`), y như vòng Stage 3.

### 1.1 Cách dựng bins của kênh (cố định — y vòng Stage 3)

1. Đường đang chạy: `predwf_map_s1a2_x1*` = **thứ tự coin theo ranker S1** (`pred_s1a2x1.parquet`) ×
   **multiset `P(win)` giữ nguyên của model** (`s3_build_map.py s1a2x1`, bản sao `c4_build_map.py`).
   Vòng này **chỉ thay cái model cấp multiset** — **giữ nguyên ranker S1** ở **mọi** kênh.
2. **A44/A45:** `s3_build_map.py s1a2x1` trên **16 fold bins** của arm (`G015_BINS_DIR=<kernel train>/stage2/<TAG>`,
   `S1_SC=pred_s1a2x1.parquet`, `X1_CUTS`=16 cutoff `20220101..20251001`) + **2 fold 2021**
   (`predict_wf_20210701/20211001.bin`) **lấy nguyên bản của MỐC** ⇒ **cả 3 kênh đủ 18 fold**, chỉ khác
   nội dung 16 fold 2022+ (đúng như Stage 3; hệ quả: mọi so sánh chỉ nói về **16 fold 2022+**, phần 2021H2
   giống nhau tuyệt đối).

### 1.2 Cách dựng dataset WFO của kênh (cố định) + LÝ DO

`market.bin`/`pred.bin` **copy NGUYÊN BYTE từ bundle** (`sim-x1-2021-bundle`, md5
`4ab691c908fc545c26243e8328d7a0a6` / `5dd6bb4c3f98d89d58770005c0001526`) ⇒ 3 kênh dùng **cùng một**
market/pred ⇒ **0 confound dữ liệu**. `funding.bin` **dựng lại** từ thư mục bins của kênh bằng
`s3_funding.py` (bản dịch Python **byte-faithful** của `WfoDataset.buildFundingFromWfFiles` +
`forwardFillToGrid`, h=4h, `WFO_SEL_HORIZON_IDX=0`, stale 15m) — đã qua cổng tái lập ở vòng trước.
`manifest.txt` = bản của bundle, **chỉ sửa** dòng phải sửa (`md5_funding`, `predictWf.*`, `foldCount`,
`binsSha256`, `fundingPredDir`, `exportedAt`, `fundingCount`, `fundingRaw15mCount`).

### 1.3 Cấu hình chạy (cố định)

`prof_x1_gs_t170.properties` (trong bundle) + override `DCA_GRID_WEIGHTS=1,1,1,1`,
`DCA_GRID_SCALE=6.0`, `CONC_CAP_PERCOIN_ENABLED=true`, `CONC_CAP_PERCOIN_PCT=0.15`
⇒ **đúng `profiles/t170_flat_keepleg0.properties`** (KEEPLEG0). `SIM_END_DATE=20251231`,
`TICKER_SOURCE=file`, jar của bundle sha256 `2c2f8aef…`, `-Xmx22g`.

- `CONC_CAP_PERCOIN` là **no-op đo được** trên nền này (`RESULT_GATESCALE_KEEPLEG0` §4: kênh `kg0-cap`
  md5 `99e42b75…` **y hệt** OFF, `blocked=0`) — và vẫn giữ làm "bảo hiểm miễn phí".
- **Nếu vì bật cap mà cổng parity P1 FAIL** ⇒ chạy lại **đúng cấu hình Stage 3** (không cap) và **ghi RÕ**
  sai lệch đó. (Cấu hình đó đã cho parity `99e42b75…` ở `d94b61d`.)

---

## 2. TRAIN ARM 44 (bắt buộc `CROSS_ARM_OK`)

Đường train **đã xác minh** (`docs/plan/PREP_STAGE2_TRAIN.md`), **giữ nguyên** mọi thứ trừ vector cột:

| mục | giá trị |
|---|---|
| script | `research/pipeline/g015_net_train_add.py` (**KHÔNG** `--add-feats` ⇒ `NF=45`, hành vi gốc) |
| arms | `A45:` (không bỏ cột) · `A44:36` (bỏ **đúng** cột 36 = `rvol15m`) — **cùng một lần dựng ma trận** |
| folds | **16 fold DEV**: `20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001` |
| nhãn | `y = (retEnd_4h > 0.015)`, lọc `nBars_4h >= 16` & notna (`LABEL_MODE=net`) |
| split | expanding WFO, `OOS_MONTHS=3`, `PURGE_STEPS=288` (72h), `TZ=+7h`, assert `ts.max() < cutoff` mỗi fold |
| hyperparam | `n_estimators=400, max_depth=5, lr=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=20`, `spw=(1−pos)/pos` **theo từng fold**, `eval_metric=auc`, `tree_method=hist`, `random_state=42`, `device=cuda` (Kaggle GPU), xgboost 3.2.0 |
| lưu | `stage2/A45/` + `stage2/A44/`: 16 `model_f<fidx>_4h.json` (**fidx = vị trí trong `CUT_DATES`**, khớp theo **cutoff**, không theo số trong tên) + 16 `predict_wf_<cutoff>.bin` (26 B/rec) + `net_train_summary.json`; gốc: `stage2_summary.json` |

**CỔNG CƠ CHẾ `CROSS_ARM_OK` (BẮT BUỘC):** `n_train` / `pos` / `spw` / `n_oos` của **A44** phải **KHỚP
TUYỆT ĐỐI** với **A45** ở **cả 16 fold** (trainer tự assert). Lệch ⇒ **LỖI CƠ CHẾ** (không phải kết quả):
**DỪNG, báo RÕ**, không đọc số kinh tế. `--drop-cols` không được đổi tập dòng/nhãn/split.

**Đối chiếu độc lập (cùng nguồn hạ tầng Kaggle):** `n_train/pos/spw/n_oos` của fold `20220101` phải khớp
`3.730.472 / 0,26989 / 2.705276 / 1.123.854` (giá trị đã ghi trong `RESULT_STAGE2_TRAIN` §1 cho **cùng**
fold, **cùng** trainer, **cùng** môi trường Kaggle GPU).

---

## 3. CỔNG (phải PASS trước khi đọc bất kỳ số nào)

| # | cổng | PASS khi |
|---|---|---|
| **P0** | mapper | log `Loaded Symbol Mapper: N` với **N ≥ 800** (thực đo các vòng trước: **863**) |
| **P1** | **MOC = mốc Kaggle** | md5 `printDone.csv` = **`99e42b75cf1a2142f9cd14dc72e371ba`**, **n = 1.085**, equity = **103.083** |
| **P2** | dựng funding byte-faithful | `md5_funding` của MOC = **`8e57d900d5c54c744bfcaf5c9b27fc93`**; `binsSha256` MOC = **`407e2aba…`** |
| **P3** | đồng nhất dữ liệu | `md5_market`/`md5_pred` của **3** dataset = của bundle (copy nguyên byte) |
| **P4** | MTM mốc phút tái lập | kênh MOC tái lập **số đã công bố** của KEEPLEG0: minute maxDD **−19,96 %**, UW **147,2 ngày** (`RESULT_INTRADAY_DD` §3.1); + 4 cổng nghiệm thu `s3_intraday` (V1 ≤ 1 USDT · V2-rel ≤ 0,05 % · V3 ≤ 1 % · V5 ≤ 0,1 pp) |
| **P5** | jar | sha256 `2c2f8aef78c98470fdc3b0d464edd7ec2c604a7589985b1f4211c1da05fcdca0` |

**P1 hoặc P2 FAIL ⇒ DỪNG, báo RỎ, không đọc số kinh tế.** (P1 FAIL nhưng P2 PASS ⇒ ghi rõ "cấu hình sim
lệch", vẫn được đọc **so sánh giữa 3 kênh** — vì cùng lệch — nhưng **không** được gọi là tái lập mốc.)

---

## 4. CHỈ SỐ (chốt trước)

### (a) 5 rate + CI — và cách xử lý `k = 1` (GHI RÕ, KHÔNG bịa hệ số)
`win%`, `TSloss%`, `mP|SM`, `mP|SL`, `meanP` (đúng định nghĩa `c3_rates`/`gd92xexit_score`).
`n` và `mMargin` **KHÔNG** phải quality rate. CI = block-bootstrap **ghép cặp theo khối 72h, 2000 rep,
seed 20260905**, báo **CẢ HAI** độ rộng:

- `c3_rates.inflate(k=1) = 1.0` ⇒ **CI gốc, KHÔNG nở rộng** (đúng nghĩa "k=1 thì công thức inflate vô
  nghĩa"). Con số này **bắt buộc** phải in ra.
- `1.21` = **hằng số LEGACY có sẵn trong repo** (`gd92xexit_score.LEGACY`, dùng ở mọi vòng trước) —
  **không phải** hệ số bịa ra ở vòng này.
- **Độ rộng QUYẾT ĐỊNH = `1.21`** (rộng hơn), "ngoài CI" = ngoài **CẢ HAI** ⇒ thực chất **ngoài `1.21`**.
  Đây là lựa chọn **bảo thủ** (khó "thấy" khác biệt hơn). Ghi chú: `inflate(2) = 1.17741 < 1.21` ⇒ độ
  rộng `1.21` **cũng đã bao** cả gia đình 2 kênh `{A45, A44}` — nên kết luận không phụ thuộc việc coi A45
  là "ứng viên" hay "đối chứng".

**So sánh chính:** **A44 vs MOC**. **So sánh chẩn đoán (không quyết định):** **A45 vs MOC**
(nền nhiễu retrain) và **A44 vs A45** (*hiệu ứng thuần của việc bỏ 1 cột*, cùng kernel/seed/ma trận).

### (b) Thước CỦA SELECTOR (theo đúng định nghĩa Stage 2)
`rank-IC` cross-section **theo từng tick** giữa `p0` và `retEnd_4h` (chỉ tick có ≥ 2 coin) + **top-8 lift@8**
= `mean_y(top-8 theo p0 trong tick) − base_rate(tick)`, `THR = 0.015`; gộp 16 fold OOS.
- **Trong kernel:** ruler của **A45** và **A44** (bins giá trị của chính arm) — cùng kernel, cùng nhãn.
- **Tham chiếu "45"**: ruler của **bản deploy** (`claudedata/predwf_G015x26/predict_wf_*.bin`, 16 fold)
  tính **offline trên Oracle** bằng **đúng đoạn code đó** + **đúng file nhãn đó** (đã kiểm: 20 file `.pb`
  của `chuyendinh/funding-label-15m` **trùng tên + trùng số byte** với `/home/ubuntu/label_15m`).
  **Khai báo rõ provenance** (bins deploy đọc local; A44/A45 đọc từ kernel output) — không trộn vào 1 cột.

### (c) Rào cứng `RISK_APPETITE.md` §7 — **theo năm** VÀ **toàn kỳ**
`maxDD ≤ 40 %/năm` · `UW ≤ 250 ngày` · quý xấu nhất `≥ −20 %` · **không** năm âm · tập trung 1 coin `≤ 15 %`.
`maxDD`/`UW` đo trên **chuỗi equity MTM MỐC PHÚT**; biến thể `P=bar.low` báo kèm (kiểm độ bền).
`qmin`/`conc`/`ret` theo chuỗi NGÀY (như các vòng trước).

### (d) `maxDD`/`UW` trên **MTM MỐC PHÚT** (dựng lại theo `docs/result/RESULT_INTRADAY_DD.md` §2, qua
`s3_intraday.py` chạy **trong kernel**, dùng lại cache nếu có).

### (e) BẢNG PnL CHI TIẾT THEO NĂM (`n` + PnL USDT) + **TOTAL** + **equity cuối** cho **cả 3 kênh**.

### (f) Cơ chế: `n` · `meanP` · `hold` · `turnover` · `Σfunding/ΣPnL` · `mean symbolPred`.

---

## 5. LUẬT QUYẾT ĐỊNH (chốt trước — nguyên văn theo đề bài)

`A44` **THAY ĐƯỢC MỐC** (tức đề xuất "GIỮ 44") khi **đồng thời**:
1. **≥ 2 rate ngoài CI** (độ rộng quyết định **1.21**) **cùng hướng TỐT** so với MỐC; **VÀ**
2. **hết rào cứng §7** (mọi năm + toàn kỳ); **VÀ**
3. **0 rate XẤU ngoài CI**; **VÀ**
4. **không XẤU hơn ở `maxDD`/`UW` MTM mốc phút** so với MỐC.

Không thoả ⇒ **GIỮ 45** (kết luận **NULL**: bỏ 1 cột không chứng minh được là tốt hơn ⇒ không đổi).

- **Bổ sung (không thay luật):** nếu A44 khác MỐC **nhưng A45 (retrain control) cũng khác MỐC tương tự**
  ⇒ gán hiệu ứng cho **retrain/máy**, **không** gán cho việc bỏ cột; ghi rõ.
- Không chọn ô "max theo equity" (`AGENT_RUNBOOK` §0: equity **không** phải tiêu chí).
- **Đổi selector/ONNX/LIVE = NGOÀI PHẠM VI:** không chạm `NUM_FEATURES`, `extractFeatures45`,
  `Funding_Classifier_Final.onnx`, `shadow_c3/`. Kể cả khi A44 "thay được MỐC", vòng này **KHÔNG** tự
  tích hợp — đổi ONNX dim = **đụng đường LIVE**, cần owner duyệt riêng.

---

## 6. DỰ ĐOÁN KHOÁ TRƯỚC

| # | Dự đoán | Cách kiểm |
|---|---|---|
| **Q1** | Cổng P1 PASS (md5 `99e42b75…`, 1.085 leg / 103.083) **kể cả khi bật `CONC_CAP_PERCOIN`** | §3 |
| **Q2** | `CROSS_ARM_OK` PASS: A44 khớp A45 tuyệt đối ở 16 fold; fold `20220101` khớp `RESULT_STAGE2_TRAIN` §1 | §2 |
| **Q3** | **A44 ≈ MOC** ở 5 rate (0 rate ngoài CI, **hoặc** ≤ 1 rate và rate đó **không** phải cặp `mP\|SM`/`meanP`) | §4a |
| **Q4** | Nền nhiễu retrain **A45 ≈ MOC** (0 rate ngoài CI) | §4a |
| **Q5** | Cả 3 kênh **PASS** rào cứng §7 (mọi năm + toàn kỳ) | §4c |
| **Q6** | Ruler: `\|Δrank-IC(A44−A45)\|` nhỏ — **dự đoán cắt `rvol15m` làm top-8 lift@8 GIẢM** (nó đo fat-tail), nên nếu có khác biệt thì khác biệt **bất lợi cho A44** | §4b |
| **Q7** | `n` của 3 kênh chênh < 20 %; `Σfunding/ΣPnL` chênh < 5 pp | §4f |

- **Nếu Q3 SAI theo hướng TỐT** (A44 ≥ 2 rate TỐT ngoài CI, 0 XẤU, hết rào) ⇒ luật §5 buộc kết luận
  **GIỮ 44** — nhưng phải kèm cảnh báo multiplicity (`k=1`, 1 ứng viên, 5 rate, 1 lần đo) và bắt buộc
  đối chiếu A45 (§4a) trước khi tin.
- **Nếu Q4 SAI** (A45 khác MOC ngoài CI) ⇒ mọi chênh lệch A44↔MOC **không đọc được** thành hiệu ứng của
  cột `rvol15m`.

---

## 7. HẠ TẦNG / CHI PHÍ / PHẠM VI

- **TRAIN trên Kaggle GPU** (kernel private, `enable_internet=false`, dataset `funding-tool1-15m`,
  `funding-label-15m`, `funding-oi-percoin`, `sel1m-code`) — **KHÔNG** claude-run/Claude Code,
  **KHÔNG** Java/sim trên Oracle (shadow LIVE).
- **SIM trên Kaggle CPU** (`sim-x1-2021-bundle` 7 dataset `wfo-ticker-2021..2025h2`, `s3-s1-sc`,
  `s3-moc-2021bins`, `TICKER_SOURCE=file`, `SIM_END_DATE=20251231`, jar của bundle, `-Xmx22g`).
  **So sánh Kaggle ↔ Kaggle** (MỐC = bản Kaggle, chạy **lại trong vòng này** bằng **cùng template kernel**
  như A45/A44 ⇒ cùng phiên bản code). Chạy ≤ 5 kernel song song (slot CPU account).
- **MTM mốc phút:** 1 kernel riêng (cần dữ liệu 1m; Oracle **không** còn dữ liệu 1m).
- **DEV only:** cửa sổ `2021-07-01 .. 2025-12-31`. **KHÔNG** chạm 2026 / `HoldoutSeal` (kernel chỉ dùng
  bins ≤ `20251001`). **KHÔNG** `juice`. **KHÔNG** push git.
- **Chấm điểm + CI: offline trên Oracle** (thuần Python, không Java/sim) sau khi kéo artifact về.
- **Chi phí:** sim/MTM = **0** (CPU kernel không tính quota); train = **1 kernel GPU** (~2 arm × 16 fold,
  ước lượng ~60–75 phút GPU theo `RESULT_STAGE2_TRAIN` 149,5 phút cho 6 arm).
- **Output tool giữ NHỎ:** kernel train chỉ tải về JSON/parquet metric (~30 MB/arm) — **KHÔNG** tải bins
  (~0,93 GB/arm); kernel sim chỉ in dòng tổng kết + JSON; xoá file lớn trước khi kernel kết thúc.

---

## 8. VIỆC KHÔNG LÀM

1. Không chạy thêm kênh nào khác (V0/V1/V5 của vòng trước đã NULL — không chạy lại).
2. Không đổi tiêu chí/ngưỡng/`k`/luật §5 sau khi xem số. 3. Không chạm 2026/`HoldoutSeal`/`shadow_c3`.
4. Không đổi ONNX/`NUM_FEATURES`/`extractFeatures45`/đường LIVE. 5. Không tự tích hợp; **không push git**.
6. Không dùng `rvol15m` cho bất kỳ cột mới nào (đây là phép bỏ, không phải phép thay).
