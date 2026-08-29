# TRACE — Backtest drift (vì sao kết quả không tái lập so với lần chạy 2026-06-02 10:57)

> Truy vết git, **read-only**. Kết luận ngắn ở cuối (Bước 5).

## TL;DR (đọc trước)
Hai kết quả **KHÔNG MÂU THUẪN trên cùng một hệ** — chúng là **hai thứ khác nhau hoàn toàn**:
- **"Chuẩn 10:57"** = `TraceData2Test` **ĐỌC LẠI FILE ĐÃ LƯU** `../simulator/storage/OrderTestDone.data` (kết quả của một lần sim CŨ, **2021→2026 full**, sinh ở deploy SIBLING `../simulator/`, ngoài repo, thời điểm/code KHÔNG biết).
- **"Mới"** = `RunFilterAblation` chạy backtest **TƯƠI in-memory, chỉ 2025-10→2026-04 (7 tháng)**.
→ Khác **nguồn dữ liệu** (file lưu vs chạy tươi), khác **giai đoạn** (5 năm vs 7 tháng), khác **harness**. Bot long-only/martingale chạy full lịch sử (gồm bear 2022) thì LỖ; chạy cửa sổ 7 tháng thuận thì LÃI — **đúng như bản chất, KHÔNG phải bug**.
→ Ngoài ra có **trôi tham số/code thật** (slippage, look-ahead guard) khiến **không lần nào tái lập 100% từ git** được.

---

## Bước 1 — Mốc commit

| | commit | thời gian | ghi chú |
|---|---|---|---|
| **BASE** (≤ 10:57 02/06) | `cb50841` | 2026-06-01 06:24 | "update HPO mơi nhất" — commit cuối TRƯỚC lần chạy chuẩn |
| **NOW** (HEAD) | `7c7563f` | 2026-06-02 22:47 | + working tree còn edit Task0/Task1 chưa commit |
| (giữa) | `7f70e30` | 2026-06-02 22:16 | "Bước 0 + 1" — commit SAU lần chạy chuẩn cùng ngày |

⚠️ **Lần chạy chuẩn 10:57 KHÔNG ứng với một commit sạch.** Lúc đó HEAD = `cb50841` (từ 06-01) NHƯNG working tree đang **bẩn** (nhiều file sửa chưa commit — sau này gom vào `7f70e30`). **Hơn nữa** `TraceData2Test` không chạy sim mà đọc artifact `../simulator/storage/OrderTestDone.data` — file này do một lần sim ở **deploy khác** sinh ra, **không nằm trong git**. ⇒ **Không thể tái lập 100% lần 10:57 từ git.**

---

## Bước 2 — Harness của 2 lần chạy (điểm mấu chốt, không chỉ là diff file)

### "Chuẩn 10:57" — `bigchange/test/TraceData2Test`
- KHÔNG phải simulator. `main()` gọi `traceLog` + `showFileAll("OrderTestDone.data")`.
- Đọc `../simulator/storage/OrderTestDone.data` (TreeMap order đã đóng) + `../simulator/storage/BalanceIndex.data` + log `../simulator/logs/nohup.out` (đường dẫn **sibling `../simulator/`**, là deploy chạy sim dài hạn — KHÔNG phải thư mục repo này).
- Tính thống kê **theo năm 2021…2026** từ dữ liệu file đó (UnProfitMin, PnL/năm, margin, balance-ratio).
- ⇒ Con số "LỖ nặng 2025-2026, UnProfitMin -39%" là của **lần sim đã lưu trước đó** (full lịch sử), KHÔNG phải chạy mới. Code sinh ra file đó: **không truy được từ git** (artifact nhị phân ngoài repo).

### "Mới" — `ai_ml/validation/RunFilterAblation` (+ `SimulatorMarketLevelTicker1MStopLoss`)
- Chạy backtest TƯƠI in-memory: nạp Aerospike (`getAllMarketDataFromAerospike` / `getAllMarketAiPredictionsFromAerospike` / `getAllFundingPredictionsPrimitiveFromAerospike`), period **`START_DATE=20251001` → `END_DATE=20260430`** (7 tháng), tính metric ngay từ `allOrderDone`.

### Diff code các file luồng (cb50841 → working tree)
- `Configs.java`: **+Bước 0** (SLIPPAGE_RATE, APPLY_SLIPPAGE, BLOCK_INTRABAR_LOOKAHEAD) + FILTER_MODE/FILTER_USE_MOM24 + TimeZoneGuard. **Params HPO (MIN_MOMENTUM_*, AI_DYNAMIC_*, …) là context line → cb50841 ĐÃ có sẵn bộ HPO, KHÔNG trôi.**
- `OrderTargetInfoTest.java`: `updateStatusNew` thêm **bịt look-ahead** (`if BLOCK_INTRABAR_LOOKAHEAD return`); `calTp` thêm **slippage 2 chân**. (calMargin/calFundingFee KHÔNG đổi; `updateFundingFee` vẫn comment ở cả 2 mốc.)
- `SimulatorMarketLevelTicker1MStopLoss.java`: +14/- (cắm `BacktestIntegrityGuard`, nuôi ring history mỗi phút, tắt log per-tick). Không đổi công thức vào/đóng lệnh.
- `AIRejectFilter.java`: +12 (FILTER_MODE bọc RISK/MOM24).
- `BudgetManagerSimple.java` / `BalanceIndex.java`: **không đổi** giữa cb50841 ↔ now.
- `TraceOrderDone.java`: -317 dòng (gọt mạnh) — nhưng đây là **tool report**, không ảnh hưởng file `OrderTestDone.data` đã lưu.

---

## Bước 3 — Phân loại thay đổi theo mức ảnh hưởng

🔴 **ĐỔI KẾT QUẢ MẠNH**
- `[Configs] SLIPPAGE_RATE` | (cb50841: **không có slippage**) → now: **0.003** | thêm 0.6% trượt giá khứ hồi mỗi cụm → ảnh hưởng PnL rất lớn. ⚠️ Giá trị này còn **flip-flop 0.0005↔0.003** trong các edit working-tree (xem Bước 4.2).
- `[OrderTargetInfoTest.calTp] + slippage 2 chân` | thêm `-qty*entry*SLIPPAGE_RATE*2` | giảm PnL mọi lệnh.
- `[OrderTargetInfoTest.updateStatusNew] bịt look-ahead` | cũ khớp SL nội-nến (lạc quan ảo) → now đặt SL nến này, khớp nến sau | **đổi cả số lệnh lẫn PnL**.
- `[harness/giai đoạn]` | file lưu 2021→2026 vs RunFilterAblation 2025-10→2026-04 | **nguyên nhân chi phối** (xem Bước 4.5).

🟡 **CÓ THỂ ẢNH HƯỞNG**
- `[AIRejectFilter] FILTER_MODE/FILTER_USE_MOM24` | now mặc định bỏ MOM24 (mode C) | ablation cho thấy A=C → ~vô hại, nhưng vẫn là khác logic.
- `[Simulator] nuôi ring history mỗi phút + guard` | đổi cách tính indicator/chặn chạy | có thể đổi nhẹ entry.

⚪ **VÔ HẠI**
- TimeZoneGuard (chuẩn hoá tz, không đổi số nếu máy đã GMT+7), tắt log per-tick, comment, rename, gọt `TraceOrderDone` (tool report).

---

## Bước 4 — Nghi phạm hàng đầu (kiểm riêng)

1. **Configs bị HPO ghi đè?** → **KHÔNG phải thủ phạm giữa BASE↔now.** `cb50841` ĐÃ dùng bộ HPO (các dòng `MIN_MOMENTUM_15M=0.01720 // Cũ: 0.02284` là context, không có +/-). Cả 2 mốc đều HPO. (Trong phiên có revert→HPO→revert nhưng **net = HPO** ở cả hai đầu.)
2. **SLIPPAGE_RATE 0.003 vs 0.0005** → **CÓ trôi, nghiêm trọng.** `cb50841`: **không có biến này** (chưa làm Bước 0). `7f70e30` và working tree hiện tại: **0.003**. Trong phiên từng đặt 0.0005 rồi đổi 0.003 (working-tree, không commit riêng) → **6× chênh, đổi mạnh PnL**. Lần chạy chuẩn (đọc file cũ) **gần như chắc KHÔNG có slippage** (file sinh trước Bước 0).
3. **calFundingFee** → **không đổi**: `updateFundingFee` comment ở **cả** cb50841 lẫn now (funding fee ≈ 0 ở cả hai). Không giải thích chênh lệch. (Lưu ý chung: PnL tuyệt đối của cả hai đều hơi lạc quan vì thiếu funding fee.)
4. **Nguồn data** → KHÁC LOẠI: "chuẩn" đọc **file `OrderTestDone.data`** (artifact sim cũ, ngoài git); "mới" đọc **Aerospike** (`ai_pred_market_full_basket_v2`, `funding_pred_1m_v5`, market_data) chạy tươi. Không so trực tiếp được.
5. **Giai đoạn test** → **KHÁC: 2021→2026 (file lưu) vs 2025-10→2026-04 (RunFilterAblation).** Đây là khác biệt **đương nhiên**, không phải bug. Martingale long-only full-lịch-sử (gồm bear) → LỖ; cửa sổ 7 tháng thuận → LÃI. Khớp cảnh báo ROADMAP: "chạy 1 cửa sổ sẽ kết luận sai".

`RATE_FEE = 0.002` (2 chân) — không đổi giữa 2 mốc.

---

## Bước 5 — Kết luận

**(a) Do CODE/THAM SỐ hay do GIAI ĐOẠN?**
→ **Chủ yếu do KHÁC HARNESS + KHÁC GIAI ĐOẠN (bình thường), KHÔNG phải bug logic backtest.** Lần "chuẩn" chỉ là **đọc lại artifact 2021→2026 của một sim cũ** (ngoài git); lần "mới" là **chạy tươi 7 tháng gần đây**. So sánh hai cái này về bản chất là so táo với cam.
→ **Đồng thời** có **trôi tham số/code thật** (thêm slippage 0.003 + bịt look-ahead sau `cb50841`; SLIPPAGE_RATE còn flip-flop 0.0005↔0.003) khiến **không bản nào tái lập 100% từ git**.

**(b) Cách khôi phục khả năng tái lập:**
1. **Lần "chuẩn 10:57" KHÔNG tái lập được từ git** — input của nó là file nhị phân `../simulator/storage/OrderTestDone.data` do một sim ở deploy khác sinh ra, thời điểm/code không track. Muốn có lại con số đó phải biết chính xác lần sim nào tạo ra file đó (không có trong repo này).
2. **Để so sánh đúng (apples-to-apples)** với hệ hiện tại: chạy `RunFilterAblation` (hoặc engine sim hiện tại) trên **CÙNG giai đoạn 2021→2026** như file cũ, trên **CÙNG 1 commit**, với slippage/guard **cố định** → rồi mới so. Đừng so chạy-tươi-7-tháng với file-lưu-5-năm.
3. **Quy trình chống trôi từ nay:** trước mỗi lần chạy "chính thức" phải (i) **commit** (không chạy trên working-tree bẩn), (ii) **ghi rõ commit + giai đoạn (TIME_RUN→END) + bộ Configs** (đặc biệt `SLIPPAGE_RATE`, `APPLY_SLIPPAGE`, `BLOCK_INTRABAR_LOOKAHEAD`, `RATE_FEE`, `FILTER_MODE`/`FILTER_USE_MOM24`), (iii) **chốt nguồn data + version set Aerospike**. Cùng commit + cùng giai đoạn + cùng Configs ⇒ ra cùng số (sim không có random; nếu vẫn lệch mới là bug).

### Hành động đề xuất (ngoài phạm vi truy vết, chờ duyệt)
- **Chốt `SLIPPAGE_RATE`** một giá trị (0.003 hay 0.0005?) và **commit** — nó đang là biến working-tree trôi, làm mọi backtest không nhất quán.
- Nếu muốn đối chứng "hệ thật lỗ hay lãi": chạy engine hiện tại **2021→2026** (đúng giai đoạn file cũ) để xem có tái hiện cảnh lỗ full-lịch-sử không — đó mới là phép so có nghĩa.

---
*Lưu ý: báo cáo này chỉ truy vết, không sửa code. Working tree hiện có edit Task0/Task1 (MOM24 off, RunTailLossDiagnostic) chưa commit.*
