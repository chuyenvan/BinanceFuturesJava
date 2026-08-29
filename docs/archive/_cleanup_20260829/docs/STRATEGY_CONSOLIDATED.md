# CHIẾN LƯỢC — HỢP NHẤT (phiên nghiên cứu + chiến dịch 2026-07-10)

# ⚠️ CẢNH BÁO LEAK (2026-08-03) — HƯỚNG DẪN DATA BÊN DƯỚI ĐÃ DEPRECATED

Doc này viết 2026-07-10, TRƯỚC khi phát hiện leak (2026-07-12). Các chỉ dẫn data sau ĐÃ SAI — KHÔNG dùng:
- ❌ `WFO_FUNDING_PRED_DIR=/home/ubuntu/claudedata/wf_pred_ret2` — dir chứa file leak `predict_wf_20260101.bin` (single-cutoff full-history 2021→2026). Đã quarantine.
- ❌ `wfo_dataset_v4` "chuẩn" — CONTAMINATED (build từ wf_pred_ret2 gồm file leak, exportedAt 07-10 13:37 đọc file leak mtime 13:36). Đã quarantine.

✅ **DATASET CHUẨN HIỆN TẠI (leak-free WFO):** `wfo_ds_ret2wf_4h_ff` (build từ `wf_pred_ret2wf/` — 16 file per-fold sạch, horizon 4h). Xem `docs/reports/START_HERE_20260802.md` + `HANDOFF_20260803_giveback03_frozen.md`. Guard chống tái-nhiễm đã thêm ở `WfoDataset.buildFundingFromWfFiles` (throw khi predict_wf overlap range).

---

> Gộp từ `STRATEGY_FINDINGS_20260710.md` (nghiên cứu chi tiết, bằng chứng đo được) +
> `MASTER_STRATEGY_CAMPAIGN.md` (spec chiến dịch điều phối task `tasks/140-144`). Giữ nguyên mọi số liệu +
> kết luận của cả hai, chỉ gộp trùng phần mục tiêu (giống hệt nhau ở cả 2 bản gốc). Không đổi nội dung kỹ
> thuật. Bổ sung cho [STRATEGY_ROADMAP_3PART](STRATEGY_ROADMAP_3PART.md) (phân rã Entry/Success/Fail) và
> [SOLUTION_FRAMEWORK_20260711](SOLUTION_FRAMEWORK_20260711.md) (cây nhánh + điểm dừng, viết sau 1 ngày,
> đã CHƯA đạt 20%/năm — xem đó để biết diễn biến MỚI NHẤT so với chốt lạc quan hơn ở đây).

## 0. Mục tiêu chiến dịch (chốt 2026-07-10, chung cho cả nghiên cứu + campaign)

- **Chấp nhận được:** ≥ **20%/năm**, ổn định lâu dài.
- **Kỳ vọng cao (không bắt buộc):** ≥5%/mỗi quý.
- **Ràng buộc thanh khoản:** không giữ vốn kẹt trong một vị thế quá ~1 năm (thanh khoản là một mục tiêu
  đầu tư, không chỉ PnL).

Điểm mấu chốt: **"≥5% MỌI quý" là bất khả với kiến trúc long-only bắt pump** — nó cấu trúc chỉ ăn được ở
quý có sóng, nằm im ở quý phẳng. Nhưng **"20%/năm + không quý nào lỗ đáng kể"** thì KHỚP với hình dạng
thực tế của hệ (phẳng lúc xấu, ăn đậm lúc sóng) và là mục tiêu hợp lý.

---

# PHẦN A — NGHIÊN CỨU CHI TIẾT (nguồn: STRATEGY_FINDINGS_20260710.md)

> Tài liệu hợp nhất một phiên nghiên cứu chiến lược đầy đủ. Nguồn số: đo thật trên dataset leak-free
> (`wfo_dataset_v3`/`v4`), simulator full-history, WFO 17 cửa sổ, smoke A/B label trên Kaggle/Oracle. Mọi
> con số trong đây là đo được, không suy đoán; chỗ nào là giả thuyết hoặc chưa đo đều ghi rõ.

## A.1 Kết luận chính (đọc trước)

Chiến lược tốt **không phải** "thêm stop-loss" hay "thêm carry sleeve" như trực giác ban đầu. Sau khi loại
trừ có hệ thống bằng số, chiến lược đúng là:

**Giữ nguyên kiến trúc long-only + DCA + Gate-tự-tắt, cộng 3 tinh chỉnh đã đo là dương:**

| # | Tinh chỉnh | Giá trị | Bằng chứng | Đánh đổi |
|---|---|---|---|---|
| 1 | `TS_GIVEBACK_RATIO` (nhả đỉnh trailing) | **0.85–1.0** (thay 0.5 hardcode) | PST All $: 0.3→−307, 0.5→+109, 0.7→+277, 0.85→+658, **1.0→+951** (đơn điệu) | Không — DCA giữ nguyên ~5300, maxDD không xấu đi |
| 2 | Label selector | **`ret2`** (`retEnd_H ≥ 2%`) thay `maxFav ≥ 6%` | %OOS+ 17.6%→**29.4%**; retEnd top-decile thắng label cũ ở cả 2 fold | Nhỏ (nhiệm vụ khó hơn, LIFT thấp hơn nhưng đúng hướng) |
| 3 | Giữ DCA nguyên | — | Mọi thí nghiệm cắt DCA đều làm PnL tệ đi | — |

**Đổi thước đo cho đúng bản chất:** không đo "≥5% mọi quý", mà đo **"không lỗ quý nào + ăn đậm quý sóng +
kiểm soát maxDD lúc ăn đậm"**.

## A.2 Chẩn đoán cốt lõi (tại sao "model tốt mà tiền không về")

Có một nghịch lý được giải bằng số:

| Tầng | Kết quả leak-free | Kết luận |
|---|---|---|
| **Ranking (model)** | Selector WF: LIFT 4h=2.87 / 12h=1.97, rankIC 0.344; Gate IC 0.30–0.50/quý | Edge THẬT, khỏe |
| **Chuyển hóa → tiền** | WFE median = 0.000; lãi dồn ở rất ít quý | Edge ≈ 0 ở tầng vận hành |

**Edge là gì?** Smoke A/B label trả lời chính xác: label cũ (`maxFav ≥ 6%`) ở fold sóng 2025Q4 có
top-decile **chạm +6% tới 68.8%** số kèo (LIFT 1.7) nhưng **retEnd ≈ 0.00%** — tức chọn đúng coin sẽ pump,
nhưng pump xong xìu sạch trong 12h. → **Edge của model là "dò biến động", KHÔNG phải "dò lợi nhuận".**
Đây là gốc của mọi vấn đề: LIFT/IC đẹp đang đo nhầm thứ.

`ret2` sửa đúng điểm này: label thưởng cho kèo **giữ được lãi tới cuối horizon**, không phải kèo chỉ chạm
đỉnh rồi rơi.

**Hệ KHÔNG lỗ ở quý xấu — nó chỉ không trade.** WFO v4: cửa sổ trade thực chất (≥10 lệnh) đều dương; các
cửa sổ "không dương" đều là ZERO_TRADES (Gate reject 30/30 = tự tắt) hoặc TOO_FEW_TRADES âm không đáng kể
(win 11 = −4.9, win 16 = −24.2, đều <10 lệnh). Cơ chế "Gate reject sạch → tự tắt ở regime xấu" **hệ đã có
sẵn** — không cần xây regime filter riêng.

## A.3 Bằng chứng: các hướng đã LOẠI (bằng số, không phải cảm tính)

| Hướng | Cách test | Kết quả | Vì sao loại |
|---|---|---|---|
| SL cứng theo độ sâu (mọi lệnh) | sweep 5/10/15% | Net **âm** cả 3 mức | Cắt đúng đuôi lỗ PST nhưng chặt luôn chân DCA đang lãi |
| SL cứng chỉ PREDICT_SYMBOL_TRADE | sweep 5/10/15% | Net âm | Cùng lý do, nhẹ hơn |
| Time-stop (thesis-expiry) | 24/48/72h | Net âm trên PnL | Lệnh "ì" phần lớn sẽ hồi; cắt sớm trúng phần hồi |
| Label triple-barrier nhỏ (6%/2-3%/12h) | smoke 2 fold | FAIL | retEnd không cải thiện; P(sập trước) chỉ giảm ~4% |
| Label triple-barrier lớn (15%/5-7%/72h) | smoke 2 fold | FAIL | retEnd tệ hơn label cũ ở fold sóng |
| **Carry sleeve** (short coin funding cao) | backtest funding+price | Net dao động −329%..+349% | **Price PnL nuốt carry**: short coin funding cao = short coin đang pump → bị nghiền. Chỉ khả thi nếu delta-neutral thật (cần spot leg — hệ perp-only không có) |

**Ba thí nghiệm exit độc lập đều âm** → bệnh KHÔNG ở tầng exit-cắt, mà ở tầng chọn kèo. Đây là lý do đổi
trọng tâm sang label (`ret2`) và nuôi-lãi (`giveback`).

## A.4 Sửa lỗi dữ liệu trong quá trình (provenance)

Nghiên cứu này chỉ tin được vì đã vá các lỗ hổng dữ liệu, ghi lại để không tái phát:

- **funding.bin trỏ nhầm set leaky:** dataset đêm trước dùng `funding_selector_pred_1m` (Aerospike, leaky,
  **dừng cứng 31/12/2025** → win 16 zero-trade). Đã chuyển sang `predict_wf_*.bin` per-fold leak-free
  (`WFO_FUNDING_PRED_DIR`). **Bài học: env var phải verify trước mỗi export** (lỗi im lặng).
- **pred.bin thiếu 2021–2022:** gate pred chỉ có từ cuối 2022 → win 0–4 (2022) ZERO_TRADES vì thiếu data
  gốc, KHÔNG phải chiến lược dở. Chưa vá (chấp nhận, ngoài phạm vi).
- **ghost USDC:** 38 cặp `*USDCUSDT` lọt basket 2 tháng cuối (2026-01→02) do bug normalize
  `DataManagerAerospikeFloatSim:940`. Méo nhẹ, gói gọn 2 tháng. Chưa vá tại nguồn.
- **symId sạch:** GATE-0 (task 133) đo `N_symId_mismatch = 0` — nỗi lo lớn nhất (regen market xáo symId
  → join lệch câm) KHÔNG xảy ra. Survivorship phủ 60/62 coin DEAD.
- **dataset chuẩn hiện tại:** `wfo_dataset_v4` (funding = ret2 leak-free, phủ 2021→2026Q1).

## A.5 Con số annual — trung thực về khoảng trống

**Chưa có** số annual của cấu hình khuyến nghị chạy full-history fixed-config. Cái đã đo:

- Baseline full-history (config cũ, giveback ~0.5): balance 35000 → ~39641 (2021→2026-06),
  ≈ **+13% / 5.4 năm ≈ 2.4%/năm** — DƯỚI mục tiêu 20%/năm.
- Các tinh chỉnh (giveback 1.0, ret2) đo được là dương **theo từng thành phần**, nhưng **số tích hợp
  full-history với cả 3 mảnh cùng lúc thì CHƯA chạy**.
- WFO v4 per-window (+9045 tổng) là **tối ưu riêng từng cửa sổ** → lạc quan/dễ overfit, không dùng làm số
  annual thật được.

→ **Phép đo quyết định còn thiếu (ưu tiên #1):** chạy simulator full-history với `wfo_dataset_v4` +
`TS_GIVEBACK_RATIO=1.0` + bộ gene cố định tốt nhất, đọc CAGR thật + maxDD + phân bố theo năm. Đây là con
số trả lời trực tiếp "có đạt 20%/năm không". (Cập nhật: task 141 đã chạy phần này — xem
[SOLUTION_FRAMEWORK_20260711](SOLUTION_FRAMEWORK_20260711.md) §0, kết quả THỰC TẾ ~5%/năm, DƯỚI kỳ vọng ở
đây.)

## A.6 Rủi ro còn mở (phải giữ trong đầu)

1. **Đuôi bear-market chưa test.** "Không lỗ quý nào" một phần nhờ DCA gồng tới khi hồi — trong 2021–2026
   (chủ yếu hồi phục) thì hồi được. **Bear kéo dài + coin delist (LUNA/FTT/DYM kẹt 160 ngày) là rủi ro
   đuôi thật chưa đo.** Đây cũng là nơi ràng buộc thanh khoản ≤1 năm cắn: DCA không giới hạn thời gian
   **mâu thuẫn** với "không giữ vốn quá 1 năm".
2. **Nghịch lý time-stop vs thanh khoản.** Time-stop bị loại vì âm PnL — nhưng đó là đánh giá *chỉ theo
   PnL*. Giờ coi thanh khoản là mục tiêu, time-stop **không còn là "xấu"** mà là một đánh đổi có chủ đích:
   mất chút PnL để bảo đảm không vị thế nào kẹt >1 năm. **Cần đo lại time-stop dài (ví dụ 270 ngày) dưới
   thước "thanh khoản", không phải thước "PnL tối đa".**
3. **maxDD 34%** ở đúng cửa sổ ăn đậm (w15). Ăn 6152 nhưng sụt 34% vốn giữa chừng → chỗ cần tinh chỉnh
   sizing/giveback, là rủi ro thật duy nhất còn lộ rõ.
4. **Mẫu nhỏ:** chỉ ~6 cửa sổ trade thực chất trong 4 năm.

## A.7 Cấu hình khuyến nghị (để Uni chốt — verdict thuộc về Uni)

```properties
# Dataset: wfo_dataset_v4 (funding = ret2 leak-free)
WFO_FUNDING_PRED_DIR=/home/ubuntu/claudedata/wf_pred_ret2   # bắt buộc set, không để rỗng
TS_GIVEBACK_RATIO=1.0        # nuôi lãi — mảnh dương rõ nhất
# RATE_PROFIT_STOP_MARKET: khi giveback=1.0 thì tham số này không còn tác dụng (đã đo)
# DCA: giữ nguyên
# Cân nhắc thêm (chưa đo, mục A.6.2): TIME_STOP_HOURS dài ~ để chặn kẹt vốn >1 năm
```

Các mảnh này đã có sẵn trong code (biến env/config, mặc định tắt → không đổi hành vi cũ nếu không set).
Không mảnh nào cần kiến trúc mới.

## A.8 Việc kế tiếp (đề xuất, theo thứ tự — trạng thái gốc lúc viết 2026-07-10)

1. **[Quyết định số annual]** Chạy sim full-history cấu hình khuyến nghị → CAGR + maxDD + phân bố năm.
   Trả lời trực tiếp "20%/năm?". Rẻ, hạ tầng có sẵn.
2. **[Rủi ro thanh khoản]** Đo lại time-stop dài (270 ngày) dưới thước thanh khoản — chấp nhận mất bao
   nhiêu PnL để không kẹt vốn >1 năm.
3. **[Rủi ro đuôi]** Test riêng giai đoạn bear (2022) với DCA + xem tier-based DCA stop (chỉ gồng sâu
   Tier-1 bluechip, Tier-2/3 có điểm dừng) — cần tier mapping (chưa có).
4. **[maxDD]** Sizing động ở cửa sổ ăn đậm để giảm maxDD 34% mà giữ PnL.

## A.9 Phụ lục — artifact phiên này (trên Oracle `161.118.212.3`)

| File | Nội dung |
|---|---|
| `/home/ubuntu/claudedata/wfo_dataset_v4/` | Dataset chuẩn hiện tại (funding ret2 leak-free) |
| `/home/ubuntu/claudedata/wf_pred_ret2/` | 17 file `predict_wf_*.bin` label ret2 |
| `docs/reports/wfo_strategy_window.md` | Bảng WFO v4 17 cửa sổ (mới nhất) |
| `/home/ubuntu/claudedata/giveback_oracle_master.md` + `giveback2_master.md` | Sweep giveback 0.3–1.0 |
| `/home/ubuntu/claudedata/stoploss_ab*_master.md`, `timestop_ab_master.md` | Các thí nghiệm exit (đã loại) |
| `/home/ubuntu/carry_probe/carry_v3_k5.log` | Backtest carry (đã loại — price nuốt) |
| Kaggle `smoke-tb-label-ab`, `selector-wf-pred-ret2` | Smoke label + gen pred ret2 |
| `CarryEdgeProbe.java`, `SimulatorMarketLevelTicker1MStopLoss` (env `WFO_DATA_DIR`/`SIM_END_DATE`/`TS_GIVEBACK_RATIO`/`HARD_STOP_LOSS_RATE`/`TIME_STOP_HOURS`) | Code mới thêm phiên này |

**Nguyên tắc vận hành đã học (đắt giá):** không ghi đè jar khi có job WFO đang chạy (classloading lười →
NoClassDefFoundError, mất 1.5h); `--once` của supervisor không harvest; `setsid nohup` cho mọi job dài;
verify env var trước export; 226 không chạy được sim cần ticker sống (chỉ Oracle có firewall tới 242).

---

# PHẦN B — SPEC CHIẾN DỊCH (nguồn: MASTER_STRATEGY_CAMPAIGN.md)

> **Vai trò:** Đây là spec chủ (master define) do Desktop (điều phối) viết. Worker CCD Opus headless nhận
> từng task trong `tasks/` chạy song song. Desktop **không tự chạy tay** — chỉ theo dõi task + phân tích
> kết quả. Verdict cuối luôn thuộc Uni.

## B.1 Chẩn đoán nền (đã đo phiên 2026-07-10 — worker COI LÀ SỰ THẬT, không đo lại)

- Ranking-edge THẬT (Selector WF LIFT 12h≈1.97, rankIC 0.34; Gate IC 0.30–0.50) **nhưng** strategy-edge ≈ 0
  (WFE median 0.000). Model hiện tại là **"máy dò biến động", không phải "dò lợi nhuận"** — bằng chứng:
  top-decile label cũ ở 2025Q4 chạm +6% tới 68.8% nhưng retEnd ≈ 0. (Chi tiết đầy đủ: §A.2.)
- **Đã LOẠI (đừng đề xuất lại):** mọi exit-rule (hard-SL / level-SL / time-stop) net âm; triple-barrier
  tĩnh (6% và 15%) fail; carry-short-funding bị price PnL nuốt (không hợp perp-only). (Chi tiết: §A.3.)
- **Đã GIỮ (dương):** `TS_GIVEBACK_RATIO` cao (0.85–1.0, PST +109→+951, không đánh đổi); label `ret2`
  (retEnd_H≥2%, %OOS+ 3→5); giữ DCA nguyên. (Chi tiết: §A.1.)
- Hệ **không lỗ quý xấu, chỉ không trade** (Gate reject 30/30 tự tắt). Cửa sổ trade thực chất (≥10 lệnh)
  đều dương; cửa sổ âm đều là <10 lệnh, âm không đáng kể.

## B.2 Nguyên tắc đánh giá (BẤT BIẾN — mọi task tuân theo)

1. **Fitness = PnL thật (backtest-lite), KHÔNG phải LIFT/IC/AUC.** LIFT/IC cao đã chứng minh không đồng
   nghĩa kiếm tiền. Xếp hạng ứng viên bằng CAGR-lite / maxDD / %quý-dương.
2. **Walk-forward bắt buộc.** Train quá khứ → predict OOS. Purge = độ dài horizon. Không in-sample.
3. **Backtest-lite chỉ để LỌC/xếp hạng, KHÔNG để chốt.** Nó lạc quan (bỏ DCA/slippage/price-interaction).
   Top candidate BẮT BUỘC qua engine Java (`SimulatorMarketLevelTicker1MStopLoss`) mới được coi là thật.
4. **Pre-register ngưỡng TRƯỚC khi nhìn số.** Ghi vào report trước khi chạy.
5. **Validate-small trước full.** Smoke 1 combo/2 fold ra kết quả sạch → mới scale.
6. **Đo, không đoán.** Mọi số phải verify nguồn.

## B.3 Kiến trúc chiến dịch — các track song song

Mỗi track là 1 task file trong `tasks/`. Chạy song song, độc lập. Roll-up ở §B.4.

| Task | Tên | Resource | Phụ thuộc | Output |
|---|---|---|---|---|
| 140 | Sweep backtest-lite mò model (45 combo, 5 kernel Kaggle) | kaggle_distributed | — | ranked combos `sweep_part*.json` |
| 141 | Xác nhận Java cấu hình khuyến nghị (ret2 + giveback 1.0) full-history | oracle | — | CAGR/maxDD/năm |
| 142 | Time-stop dưới lăng kính THANH KHOẢN (270/360 ngày) | oracle | — | PnL-vs-holding tradeoff |
| 143 | Test đuôi bear 2022 + tier-DCA (chỉ gồng sâu Tier-1) | oracle | — | maxDD bear, survival |
| 144 | Feature mới "pump-giữ-thanh-khoản" (re-export Java ff nếu cần) | oracle | 140 (chờ tín hiệu pump-featset thắng) | ff mới + so LIFT-PnL |

**Phân bổ tài nguyên (Uni chốt 2026-07-10):** `local` = máy điều phối, CHỈ dispatch, KHÔNG job nặng (cap
1). Mọi compute Java/export → `oracle` (cap 3, VPS chính). `heavy_226` = benchmark only. `kaggle` = 5 slot
CPU. **Worker model: Opus/Sonnet/Haiku — TUYỆT ĐỐI KHÔNG Fable** (đổi qua env `WORKER_MODEL`, mặc định
`claude-sonnet-4-6`).

**Task 140 là trục chính** (mò model). 141–143 chạy song song để bồi rủi ro/thanh khoản. 144 chờ 140.

## B.4 Roll-up → quyết định (Desktop làm, KHÔNG delegate)

Khi các task báo done, Desktop tổng hợp bảng:
- Top-5 combo theo `composite` từ 140, kèm 3 số raw (cagr_lite, maxdd_lite, %q+).
- Đối chiếu combo thắng với xác nhận Java (141 + chạy Java cho top combo).
- Bảng thanh khoản (142) + đuôi bear (143) để chọn tham số an toàn.
- Trình Uni: 1 cấu hình khuyến nghị + rủi ro còn lại. **Không menu.**

## B.5 HÀNG RÀO cho worker (bài học đắt — vi phạm là hỏng chạy)

1. **KHÔNG ghi đè jar khi có job Java đang chạy.** `pgrep -af 'WfoWorker|SimulatorMarketLevel'` phải rỗng
   trước khi scp jar. Classloading lười → NoClassDefFoundError giết job (đã mất 1.5h vì lỗi này).
2. **`setsid nohup ... </dev/null >log 2>&1 &` cho MỌI job dài.** Không job nào được chết theo SSH.
3. **Verify env var TRƯỚC export.** `WFO_FUNDING_PRED_DIR`, `WFO_SET_PRED` rỗng → fallback set leaky câm.
4. **242 chỉ đọc, KHÔNG ghi/restart.** `touches_live_process=false`, `writes_242_data=false` cho mọi task này.
5. **226 KHÔNG chạy được sim cần ticker sống** (firewall tới 242 chỉ mở cho Oracle). 226 chỉ compute thuần.
6. **python stdout block-buffered** → dùng `python -u`; SIGKILL/OOM để lại log 0 byte — luôn kiểm exit + OOM.
7. **File to (label 42M dòng, OI 3.15GB gz)** → filter theo `feat_ts` + đọc chunk TRƯỚC merge, tránh OOM câm.
8. **Log/output → `/d/claudedata` hoặc Oracle `/home/ubuntu/claudedata`** (C: đã crash 3 lần vì đầy).
9. SLF4J/Log4j, không `System.out`. Java là nguồn sự thật; Python chỉ train/validate.
10. **KHÔNG tự quyết PnL/verdict/threshold** — pre-register rồi để Uni chốt. NEEDS_HUMAN khi phân vân.

## B.6 Data chuẩn (dùng đúng, không tự chế nguồn)

- Kaggle dataset: `chuyendinh/funding-selector-wfo-data` (features_*.bin.gz, oi_percoin_*.bin.gz,
  funding_label.csv.gz 42M dòng, symbol_map.csv). Kaggle **tự giải nén .gz khi mount** → path bỏ .gz hoặc
  glob `*.bin*`.
- WFO dataset chuẩn: Oracle `/home/ubuntu/claudedata/wfo_dataset_v4` (funding = ret2 leak-free).
- Pred ret2: `/home/ubuntu/claudedata/wf_pred_ret2` (17 file predict_wf).
- Engine Java jar: build local `mvn -q -DskipTests package` (Corretto-17) → scp Oracle
  `/home/ubuntu/java/simulator/binance-futures-backfill.jar`.
- Simulator env: `WFO_DATA_DIR`, `SIM_END_DATE=20260601` (ticker lag), `TS_GIVEBACK_RATIO`,
  `HARD_STOP_LOSS_RATE`, `TIME_STOP_HOURS`, `WRITE_SIM_STORAGE=true` (rồi TraceData2Test đọc logs/nohup.out).

## B.7 Harness sẵn có (đừng viết lại từ đầu)

- `python/tool/sweep_harness.py` — backtest-lite sweep (đã có, đang vướng OI-load, task 140 sửa nốt).
- `CarryEdgeProbe.java` — probe read-only (carry đã loại, tham khảo pattern).
- Kaggle kernel pattern: dynamic path resolver `glob /kaggle/input/**/features_*.bin*` (xem
  `kaggle_pred_ret2/kernel_main.py`).
