# BUG HUNT WFO — 2026-07-13 (lỗi tiềm ẩn làm kết quả không tin được)

Bối cảnh: mọi WFO gần đây ra số khó hiểu (WFE=0.010 trùng khít 2 model, nhiều window 0 lệnh, so sánh maxfav3/ret2 vô nghĩa). Đã truy tận gốc trên data thật (Oracle). Kết luận: **có 2 bug metric/hygiene làm SỐ BÁO CÁO sai lệch**, nhưng verdict FAIL vẫn đúng vì lý do khác (posRatio).

## ✅ ĐÃ LOẠI (không phải bug)
- **market.bin khác md5 giữa 2 dataset**: chỉ **10/2.774.140 record** lệch li ti (jitter recompute basket). Vô hại. Export deterministic (ghi theo TreeMap sort).
- **pred.bin trùng md5 tuyệt đối**: ĐÚNG THIẾT KẾ — `pred.bin` = gate (`ai_pred_market_gate_wfo`, dùng chung). Selector nằm ở **`funding.bin`** (`WFO_FUNDING_PRED_DIR` khác nhau) và md5 funding KHÁC nhau → 2 model thực sự khác selector. Run freqfix cũng cho số lệnh per-window khác nhau (w8 275 vs 201) → selector CÓ tác dụng.

## 🐞 BUG 1 — WFE median bị nhiễm (StrategyWfoTask.java:281)
`aggregate()` nhét WFE của **mọi** window vào median, KHÔNG lọc note. Trong khi `%OOS dương` (dòng 280) lọc đúng (chỉ `oosNote==SUCCESS`).
- Window ZERO_TRADES → wfe=0; TOO_FEW → wfe≈0.01; CAPITAL_LOCK/BURN → wfe rác (1.79, −173).
- ~10/19 window rơi cụm near-zero → **median = 0.010** bất kể window SUCCESS tốt đến đâu.
- Bằng chứng: WFE median ALL=0.010 (cả 2) nhưng **SUCCESS-only = 0.711 (maxfav3) / 0.933 (ret2)** → nếu lọc đúng thì cả 2 QUA ngưỡng WFE≥0.5.
- **Fix**: `wfes` chỉ add khi `oosNote==SUCCESS` (đồng bộ semantics với posCount). Sentinel/disqualify không được vào median.

## 🐞 BUG 2 — job cũ sót lại khi reset (WfoCoordinator reset)
`reset` ghi đè 17 job mới nhưng KHÔNG xóa job ngoài set. Còn w17/w18 từ lần chạy 19-window cũ → report tính **n=19** (đúng phải 17), có window TRÙNG ngày (w17=w15, w18=w16), và w17 stale (1503 lệnh, +3934) lẫn vào cả 2 model y hệt.
- **Fix**: reset xóa mọi job-id không thuộc `buildJobs` hiện tại (purge orphan trong index + record).

## ⚠️ GIỚI HẠN 3 — selector chỉ tới 2025-12
`funding.bin` (selector) range 2021-01..**2025-12**. Mọi OOS window 2026 (w16 = 2026Q1) **rỗng selector** → ~0 lệnh cấu trúc, không phải chiến lược. Gate (pred.bin) tới 2026-05.
- **Fix**: loại window OOS vượt max(funding ts) khỏi buildJobs, HOẶC gen selector tới hiện tại trước khi WFO.

## 🎯 KẾT QUẢ THẬT (sau khi hiểu đúng metric)
- **Verdict FAIL vẫn ĐÚNG** — nhưng vì **posRatio**, không phải WFE: maxfav3 35%, ret2 24% (cần ≥70%). Quá nhiều regime cho 0/ít lệnh hoặc burn.
- freqfix (budget=100, breaker 0.70) đổi kiểu hỏng: window nhiều lệnh chuyển sang **TOO_MUCH_CAPITAL_LOCK / BURN_ACCOUNT** (ret2 w6/w8/w9, maxfav3 w9). Nới tần suất → khóa vốn/cháy chỗ khác. Không có 1 MIN_MOMENTUM dùng chung mọi regime.
- ret2 nhỉnh hơn maxfav3 ở window SUCCESS (WFE 0.933 vs 0.711) nhưng ít window SUCCESS hơn (4 vs 6) → chưa cái nào đạt chuẩn.

## 🐞🔥 BUG 4 (GỐC RỄ THẬT) — funding.bin MẤT forward-fill 15p→phút → selector chỉ có 15m
Engine tra selector bằng `time2SymbolPred.get(time)` (khớp CHÍNH XÁC phút). funding.bin đúng thiết kế phải là **per-minute** (forward-fill mốc 15m ra mọi phút cho tới mốc kế), nhưng bản hiện tại **chỉ có mốc 15m**. Mọi phút không phải bội số 15 → `.get(time)=null` → không vào lệnh. Ảnh hưởng CẢ selector-trade (PREDICT_SYMBOL) LẪN BIG_DOWN (vì BIG_DOWN chọn symbol qua cùng map, SimulatorMarketLevelTicker1MStopLoss.java:201-205).

**Bằng chứng số:**
- funding.bin hiện tại = **175.226 mốc** (cadence đo được = 15.0 phút). File gốc `predict_wf_*.bin` (Kaggle) cũng 15m.
- Thiết kế đã-verify (docs `wfo_architecture.html:266`, `system_architecture_all.html:649`): funding.bin phải **forward-fill 15p→phút = 2.758.365 entry, "align 100% với market timestamps"**, do Python `gen_funding_wf_predictions.py` sinh.
- BIG_DOWN phát hiện **162 mốc** (khớp code cũ 159), nhưng chỉ **9 (5.6%)** trùng mốc 15m có selector → sập 159→9. Code cũ vào 159/162≈98% vì funding hồi đó ĐÃ per-minute (forward-fill).

**Nguyên nhân regression:** 2026-07-08 "bỏ Aerospike, đọc thẳng file Kaggle" → chuyển sang path Java `WfoDataset.buildFundingFromWfFiles()` (dòng 122-163). Hàm này **gom theo ts gốc 15m, KHÔNG forward-fill** (dòng 147-158 `byTs.computeIfAbsent(ts,...)` → out chỉ các mốc 15m). Bước forward-fill mà Python từng làm bị rớt. → "trước cũng gặp vđ này" là vì nó từng được vá ở Python rồi tái phát khi viết lại Java.

**Vì sao bóp méo tất cả:** thiếu 93% số phút giao dịch → tần suất sập (đúng câu hỏi "tại sao ít lệnh hơn cũ" từ đầu campaign), edge BIG_DOWN độc-lập-selector bị thắt cổ chai, và MỌI WFO/so sánh maxfav3-vs-ret2 đều chạy trên nền thiếu 15× dữ liệu → verdict FAIL không đáng tin về NGUYÊN NHÂN.

**Fix (chọn 1):**
- **(A) Khôi phục forward-fill trong export** — `buildFundingFromWfFiles` nhận thêm mốc market (hoặc lưới 1m), với mỗi phút gán `floorEntry(15m-map)` cho tới mốc kế; out ≈ 2.758.365 (khớp market). Trung thành thiết kế đã-verify. Cần re-export 2 dataset + WFO lại.
- **(B) Sửa tra cứu ở engine** — đổi `time2SymbolPred.get(time)` → `floorEntry(time)` có chặn staleness ≤15m (carry-forward lúc đọc, không nhân data). Nhẹ hơn, không cần re-export, nhưng đụng engine (phải đảm bảo LIVE cũng carry-forward y hệt để sim≡live).

## TRẠNG THÁI FIX (2026-07-13)
- ✅ **BUG 4 (gốc rễ) — ĐÃ FIX**: thêm `WfoDataset.forwardFillToGrid()` + wire vào `export()`; funding 15m→per-minute carry-forward, staleness cap 15m (env `WFO_FUNDING_FILL`/`WFO_FUNDING_FILL_STALE_MS`), chia sẻ tham chiếu mảng. Unit test `WfoDatasetForwardFillTest` **4/4 PASS** (fill đều, reference-share, beforeFirst, stale-cap). Jar build OK, deploy Oracle.
- 🔄 Đang re-export 2 dataset (`_ff`) → verify fundingCount ~2.758M + BIG_DOWN coverage ~100% → sim xác nhận BIG_DOWN ~159 → rồi WFO lại.
- ⏳ BUG 1 (WFE median lọc SUCCESS), BUG 2 (purge orphan reset), GIỚI HẠN 3 (loại OOS>max-funding): chưa fix — làm sau khi xác nhận BUG 4 phục hồi tần suất.

## HÀNH ĐỘNG (thứ tự)
1. Fix BUG 1 + BUG 2 + GIỚI HẠN 3 (code) → rebuild → report lại từ job DONE hiện có (BUG1/2 là ở aggregate/report, KHÔNG cần WFO lại; chỉ cần purge orphan rồi chạy `report`).
2. Chỉ SAU khi metric sạch mới bàn tiếp: strategy fail posRatio là thật → cần sửa strategy/selector chứ không phải tinh chỉnh config.
3. ⛔ KHÔNG WFO thêm vòng nào tới khi BUG 1&2 được fix — nếu không mọi số vẫn nhiễm.
