# ADD4 — v1.2 go-live chạy trên TÀI KHOẢN CON (thay ADD1 MAIN_ACCOUNT)

**Lý do:** ADD1 chọn tk chính vì giả định "tk con không hưởng lãi BFUSD". Owner 11-09 đã test 5 USD trên tk con: vẫn có lãi BFUSD ⇒ giả định sai, ưu tiên cách ly rủi ro.

**§1 Phạm vi.** v1.2 (micro 1 000 USDT → pilot 10 000 USDT) chạy trên một tk con riêng, key riêng. LEGACY ở lại tk chính. Không có thao tác chéo tài khoản nào từ code. Nạp hoặc rút vốn giữa tk chính và tk con chỉ do owner làm tay.

**§2 Key tk con (`golive_check_key` phải ĐẠT trước `micro_on`):**
- ipRestrict = true (chỉ IP 242), enableWithdrawals = false, enableFutures = true.
- SHA8 khác key tk chính (3ef771e0).
- Tại thời điểm `micro_on`: 0 vị thế, 0 lệnh mở, 0 algo; dualSidePosition = false.
- Ghi lại multiAssetsMargin và danh sách tài sản margin. Nếu vốn để dưới dạng BFUSD thì BFUSD phải có trong account assets với marginAvailable = true, nếu không thì TRƯỢT.

**§3 Bỏ ràng buộc LEGACY.** Bỏ yêu cầu "owner đóng LEGACY + `legacy_verify` trước pilot" (ADD1). LEGACY độc lập với v1.2. Các guard LEGACY (`LEGACY_QUEUE_LIVE_BLOCK`, đếm LEGACY) không còn là điều kiện go-live, chỉ ghi log.

**§4 Nhận diện phạm vi trên tk con.** Mọi vị thế, lệnh hay algo trên tk con KHÔNG có cid `c3-`/`c3x-`/`c3s-` ⇒ KHẨN + chặn mở lệnh mới, KHÔNG tự đóng. Owner hoặc MASTER xử lý.

**§5 Kill-switch.** A40, C1–C6 (C6 −40 %) tính trên equity của tk con, equity = totalMarginBalance quy USDT, bao gồm giá trị margin của BFUSD. Ngưỡng giữ nguyên.

**§6 Rate.** Weight theo IP vẫn dùng chung với LEGACY trên 242 ⇒ giữ nguyên cơ chế IP cap. Bộ đếm lệnh (order count) và 429 lệnh tính theo tk con.

**§7 Gate giữ nguyên.** G-MICRO (ADD11/ADD15), G-PILOT (ADD2), G-EXIT (ADD3) không đổi tiêu chí. Số ngày G-MICRO đã đếm vẫn giữ, vì parity dry không phụ thuộc tài khoản. G-EXEC/G-EXIT đo trên fill của tk con.

**§8 Phí.** Đo commission thực từ `userTrades` của tk con, ghi lại commissionAsset và mức phí hiệu dụng. Mức phí không phải gate mới; ảnh hưởng của phí đã nằm trong G-EXIT (net PnL/leg ≥ 80 % sim). Nếu phí hiệu dụng > giả định sim thì báo MASTER.

**§9 Chuyển đổi.** Code và ops sửa theo ADD4 phải qua A1 PASS trước `micro_on`. Không đổi strategy, gate, ngưỡng hay universe.

## ERRATA 11-09

**§5 (sửa):** lớp kill-switch CHÍNH vẫn là kill-switch trong jar r4t, tính trên sổ c3 (`C3MainEquity`). Ngưỡng A40, C1–C6 giữ nguyên, không đổi jar vì G-MICRO (ii) gắn với r4t. Trên tk con chỉ có vị thế c3 nên sổ c3 ≈ equity tk con; chênh lệch chỉ do lãi hoặc giá BFUSD. Lớp PHỤ là `golive_monitor`, đo DD theo totalMarginBalance tk con ≤ −40 %: KHẨN + `run/KILL_SWITCH` (chặn mở mới, không flatten). Monitor phải có lịch chạy tự động trước `micro_on`.

**§3 (sửa):** khi c3_live chạy cùng JVM, LEGACY bị chặn mở lệnh mới (`LiveProfileC3`/`LEGACY_QUEUE_LIVE_BLOCK`, từ thiết kế tk chính). Trong ADD4 hành vi này GIỮ NGUYÊN, vì không đổi jar trong cửa sổ G-MICRO. LEGACY vẫn quản lý vị thế đang có. Việc nới chặn (nếu env cho phép) là quyết định riêng của owner, phải qua A1, không gắn với gate go-live.
