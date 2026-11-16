# PREREG_PARITY_V12_DRY — ADDENDUM 22 (CHỐT 2026-11-16, MASTER; TRƯỚC khi bật cờ trên 242): bật sizing + DCA grid ở dry (audit D-01) và điều kiện G-MICRO bổ sung

**Trạng thái:** CHỐT bởi MASTER 2026-11-16 ~14:10 +07, TRƯỚC khi owner chạy `dry_enable_grid_sizing.sh`. Nguồn: audit go-live 11-16
(`~/claude_master/v12/AUDIT_GOLIVE_1116_{A,B,C,D}.md`), gói script Đợt 1 commit `e4677554` (nhánh `v1.2/wave1`), A1 `~/claude_master/v12/A1_WAVE1.md`
(PASS-WITH-MINOR, 0 FAIL). Mọi con số dưới đây ghi TRƯỚC khi có dữ liệu sau thay đổi; không đổi sau khi thấy số.

## 0. Lý do
- Audit D-01 / A-01 (MASTER tự xác nhận trên 242 ngày 11-16): env v_t_m thiếu `LIVE_APPLY_GRID_RATIO=true` và `LIVE_DCA_GRID_ENABLED=true`
  (code mặc định TẮT). Hệ quả đo được trong log dry: 23/23 `SUBMIT` có `legIdx=0`, `budget` ≈ 33–37,5 USDT ở `C3_CAPITAL=10000`
  (sim arm A3: 225 = 2,25 % vốn mỗi leg), `HOURLY entry{DCA_OFF=148}`. Tức đường lệnh c3 (dry và sẽ là live) đang chạy leg = 1/6 sim
  và KHÔNG có DCA grid; ở micro 1 000 mỗi leg 3,75 < `minBudget` 5 ⇒ 0 lệnh.
- Parity harness KHÔNG so sizing / DCA / exit (điểm mù đã ghi ở ADD6 và handoff) nên lỗi này không làm ngày nào TRƯỢT.
- Sửa: chỉ đổi cấu hình (2 dòng env), KHÔNG đổi jar. Đây là kéo live về đúng cấu hình sim đã pre-register (A3), không phải chỉnh chiến lược.

## 1. Thay đổi (cố định trước)
- 242, v_t_m: thêm `export LIVE_APPLY_GRID_RATIO=true`, `export LIVE_DCA_GRID_ENABLED=true`; restart v_t_m 1 lần (LEGACY cùng JVM).
  Jar giữ nguyên r4u3fin2 md5 `641803565297d4065d90245e04a00f11`; ingestor giữ nguyên `5e78ac0663b4a765551eac1c362bf194`.
  `LIVE_ADAPTER=dry`, `C3_CAPITAL=10000` giữ nguyên.
- A1 đã xác minh trong code: 2 cờ chỉ được đọc ở `LiveGridSizing` / `LiveDcaGridC3`; không đổi lệnh thật, sizing hay DCA của LEGACY
  (leg LEGACY `legIdx=-1` giữ nguyên budget; queue LEGACY bị chặn); adapter dry đi qua DryGateway.
- Công thức sau khi bật (live và sim dùng chung hàm): `leg_i = C3_CAPITAL × F_BASE / Σw × w_i × SCALE × (1 − U/0,6)`; với tham số 242
  = profile sim ⇒ mỗi leg (leg0 + 3 bậc DCA −50 / −75 / −90 %) = 2,25 % vốn khi U = 0 ⇒ 225 USDT ở vốn 10 000.

## 2. Cách tính trong parity / G-MICRO
1. **Ngày restart = XÁM** (đổi cấu hình sizing), như ngày swap jar (ADD6 / ADD10).
2. **Smoke 24 h đo LẠI** từ START_MS thật của JVM mới (script ghi vào `gmicro_target.json`). Tiêu chí smoke = ADD21 §4, THÊM: log JVM mới có
   `[LIVE-SIZING] LIVE_APPLY_GRID_RATIO=true` và `[LIVE-DCA-GRID] LIVE_DCA_GRID_ENABLED=true … applyRatio=true`; 0 dòng `DCA_OFF` trong
   `HOURLY entry{…}` kể từ JVM mới.
3. **(ii) đo LẠI:** cần ≥ 1 ngày SẠCH / SẠCH-T chạy TRỌN trên cặp jar ADD21 **với 2 cờ bật**. Mọi giá trị `ii` harness in ra cho ngày
   trước ngày restart này KHÔNG dùng để mở cổng (kể cả nhãn 11-15).
4. **(i):** các ngày SẠCH đã có (11-07, 08, 09, 11, 12) VẪN tính cho (i) — chúng chứng minh feature / p15 / gate khớp, phần harness thực sự đo,
   và phần đó không phụ thuộc 2 cờ. Ngày sau restart tính bình thường.
5. **Chứng nhận tay tạm thời (audit C-01):** harness chưa cài ADD21 §3–§4 và mục 2 ở trên. Cho tới khi cài xong (Đợt 2, có test tiêm lỗi + A1),
   `ii` và smoke CHỈ được coi là ĐẠT khi có **biên bản MASTER** (`docs/result/GMICRO_MANUAL_<ngày>.md`, commit) ghi số đếm từng trường của
   ADD21 §4 + mục 2 ở trên, kèm lệnh đếm. JSON in "DAT" mà không có biên bản ⇒ KHÔNG đủ.

## 3. Điều kiện G-MICRO BỔ SUNG (bắt buộc trước khi MASTER tạo gate file)
Lý do: audit C-02 / C-03 — 5/5 ngày SẠCH của (i) đều có gate đóng suốt ngày (0 ngày có entry selector được so với sim); selection khi gate mở,
sizing, DCA, exit chưa từng được so với sim.
- **(iii) Replay đường lệnh:** replay ≥ 1 ngày lịch sử có gate MỞ (ngày sập) qua ĐÚNG jar `641803565297d4065d90245e04a00f11` ở chế độ dry
  với 2 cờ bật, so với sim A3 cùng ngày: tập coin được chọn, thứ tự, budget từng leg, các leg DCA, thời điểm + giá thoát. Tiêu chí PASS / FAIL
  và ngày replay được chốt trong prereg RIÊNG (`PREREG_E2E_REPLAY_V12`) TRƯỚC khi chạy. Chưa có prereg + kết quả PASS ⇒ không tạo gate file.
- **(iv) Kiểm sizing trên dry thật:** kể từ JVM mới, MỌI dòng `[C3-LIVE] SUBMIT` phải có `budget` trong ±2 % của
  `0,0225 × C3_CAPITAL × (1 − U_before/0,6)`; mọi leg DCA grid có `legIdx ≥ 1`. 1 dòng lệch ⇒ FAIL, báo MASTER. 0 dòng SUBMIT trong cửa sổ
  (gate không mở) ⇒ (iv) = "KHÔNG ĐO ĐƯỢC" — khi đó (iii) là bằng chứng duy nhất, không vì thế mà nới.
- **(v) Script go-live:** micro_on chạy bản đã qua A1 với các MINOR M1, M5 của `A1_WAVE1.md` đã sửa; md5(monitor+lib) có trong
  `A1_APPROVED_MONITOR.md5`.

## 4. Kỳ vọng ghi trước (kiểm sai)
- Sau restart: `DCA_OFF` biến mất khỏi dòng HOURLY; không có `BUDGET_SMALL` ở vốn 10 000; `[LIVE-SIZING]` / `[LIVE-DCA-GRID]` BAT đúng 1 lần / JVM.
- LEGACY: số vị thế managed không đổi do restart (43; giảm tự nhiên do LEGACY tự đóng lệnh không tính là lỗi của thay đổi này); 0 lệnh mới,
  0 thay đổi cỡ lệnh / DCA thật của LEGACY trên tk chính. Thấy khác ⇒ rollback env ngay (script có sẵn), báo MASTER.
- Sổ dry c3 trước restart: 0 vị thế ⇒ không có vị thế c3 nào mang cấu hình cũ sang.
- Vốn micro: ở 1 000, leg = 22,5 × (1 − U/0,6): BTC (min notional 50) luôn bị loại; 5 symbol min 20 bị loại khi U > 0,067; mọi symbol
  `BUDGET_SMALL` khi U > 0,467. Owner 11-16: chấp nhận nâng micro tới 4 000 nếu cần; hướng ưu tiên là nâng riêng leg dưới mức tối thiểu lên
  mức tối thiểu (đổi jar ⇒ Đợt 3, prereg riêng). Quyết định vốn micro chốt sau kết quả (iii).

## 5. Rollback
- Script tự rollback khi hậu kiểm trượt: env.sh về backup gốc + restart + kiểm `adapter=dry`, `C3_CAPITAL` cũ. Sau rollback: trạng thái
  parity như trước ADD22 (ngày đó vẫn XÁM vì có restart).
