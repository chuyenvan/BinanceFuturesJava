# PREREG_EVENT_SOURCE_2 — Nguồn sự kiện thứ 2: cổng DỪNG 0-sim cho (H1) micro-structure mới và (H4) path market-signal

**Ngày:** 2026-09-30 · **Nhánh:** `module` · **Trạng thái:** CHỐT **TRƯỚC** khi đo · **Chi phí: 0 sim / 0 train**.
**Kế thừa:** `docs/plan/REVIEW_FLOW_OPT.md` (§0/§3) · `RESULT_OFI_V3_EVENT2` (`d6f2bbba`) · `RESULT_K_DENSITY` (`1579f5a`) ·
`RESULT_CAPACITY_DIAG` (`aedf535`) · `SUGGEST_DOUBLE_ENTRIES` · `DECISION 0013`.
**Ràng buộc:** không chạm 242/ONNX/LIVE · DEV ≤ 2025-12-31 · KHÔNG push file dữ liệu · luật `RISK_APPETITE.md` §9.

---

## 0. CÂU HỎI DUY NHẤT

> Có nguồn/lệnh nào sinh **SỰ KIỆN THẬT NGOÀI pool S1**, rơi vào **tuần GATE ĐÓNG**, và có `net > 0` **ngoài CI** không?
> (`K_DENSITY`: 132/234 tuần gate đóng; khe dài 70–129 ngày **giống nhau ở mọi K** ⇒ không K nào lấp được.)

---

## 1. H4 — path market-signal (BIG_DOWN / DCA-level) · **0-sim, chạy được NGAY, 0 tiền**

**Cơ chế đã có trong code (không sửa `.java`):** leg BIG_DOWN **bypass** cổng AI
(`SimulatorMarketLevelTicker1MStopLoss.java:1326` `if (!levelChange.equals(MarketLevelChange.BIG_DOWN))`),
nguồn `MarketBigChangeDetector.getMarketStatus1M(...)` (`Simulator…:332`); DCA-level `:390`
`MarketBigChangeDetector.isDcaAlt(...)`. ⇒ hai path này **đã có thể** nổ ở tuần gate đóng.

**Đo (đọc artifact có sẵn: `printDone.csv` của B0 + nhãn tuần open/close theo `GateRatioBuffer`):**
- A1: đếm `n_event` BIG_DOWN và DCA_LEVEL1 **rơi trong 132 tuần gate ĐÓNG** (tỉ lệ trên tổng leg mỗi loại).
- A2: phân phối `net/leg` (`gross − 0,006`) của riêng hai loại đó trong tuần đóng — **bootstrap block-72h, 2000 rep, seed 20260905, `inflate(k)`**.
- A3: ổn định — dịch gốc bin ±1..6 ngày; và `random`-control cùng tick (như `OFI_V3_EVENT2`).

**Cổng DỪNG (đọc TRƯỚC, không nới sau khi thấy số):** **CHỈ** đi tiếp sim nếu **A1 ≥ 100 event/4 năm** **VÀ** A2 `net > 0` ngoài CI **VÀ** A3 nhất quán dấu.
Ngược lại ⇒ **ĐÓNG H4** (giữ nguyên G2+FLAT3). Kỳ vọng ghi trước: **nghi ngờ FAIL** (`BD_THRESHOLD_FRAGILITY`: PnL BIG_DOWN dao 2× giữa 4 điểm ngưỡng).
**Cần data mới:** KHÔNG.

---

## 2. H1 — micro-structure mới (L2 depth / liquidation) · **0-sim, NHƯNG cần dữ liệu mới**

**Tiền đề:** OFI V3 (aggTrades free) = **S1 + 2 cột** (spearman 0,87–0,93; top-8 ngoài pool **0,054 %**; 293 entry thật/4 năm) ⇒ NO-GO.
Nguồn thật sự độc lập **chưa có dữ liệu** (bulk Vision chỉ có `bookDepth` %, KHÔNG phải L2 — `PROPOSAL_MICROSTRUCTURE_DATA`).

**Khi có dữ liệu (subset nhỏ, có trần ngân sách), đo ĐÚNG phương pháp `OFI_V3_EVENT2`:**
- B1: % tick nguồn mới **nằm NGOÀI** pool S1 cùng tick (cổng: phải **≥ 20 %** mới coi là độc lập; OFI chỉ 0,054 %).
- B2: số cặp `(ts,sym)` ngoài pool S1, và trong tuần gate đóng (cổng: **≥ 200/4 năm**).
- B3: `net_coin` của tập mới vs `random-K` + `noise` (**cùng NaN-mask**), CI block-72h, 2000 rep, seed 20260919, `inflate(k)`.
- B4: ổn định gốc bin ±0..6 ngày (delta phải cùng dấu ở ≥ 6/7 pha, như OFI).

**Cổng DỪNG:** đi tiếp **CHỈ** khi B1 ≥ 20 % **VÀ** B2 ≥ 200 **VÀ** B3 `net > 0` **ngoài CI** vs **CẢ HAI** đối chứng.
**Cần data mới:** **CÓ** — L2 order-book depth (mua; licences/survivorship rủi ro) hoặc liquidation (thu forward, không có bulk lịch sử).
Ghi chú licences/survivorship: `docs/plan/PROPOSAL_MICROSTRUCTURE_DATA.md` §0.

---

## 3. LUẬT KHÔNG ĐỔI SAU KHI THẤY SỐ

- Không thêm biến thể, không nới cổng DỪNG, không chọn ngưỡng sau khi thấy số.
- Mọi phán quyết dùng luật §9: T1 MTM-phút · T2 (`q* ≥ 15`, top-1 ≤ 25) · T3 (win% ≥ −2,0 pp, TSloss% ≤ +2,5 pp) · T4 (`n` mục tiêu, `Calmar_MTM ≥ 0,90×1,877`, `conc ≤ 4,09 %`).
- Kết quả ghi vào `docs/result/RESULT_EVENT_SOURCE_2.md`; thô vào JSON **không push file dữ liệu lớn**.
