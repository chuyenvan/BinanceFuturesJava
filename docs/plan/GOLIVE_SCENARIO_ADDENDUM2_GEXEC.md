# GOLIVE_SCENARIO — ADDENDUM 2: G-EXEC chuyển từ G-MICRO sang G-PILOT (2026-11-05)

Gốc: `docs/plan/GOLIVE_SCENARIO.md` (613ff5ca) + ADDENDUM 1 (`GOLIVE_SCENARIO_ADDENDUM1_MAIN_ACCOUNT.md`, 90cd2e77).
Addendum này CHỈ đổi vị trí cổng G-EXEC và nguồn leg được đếm. Mọi mục khác của bản gốc và ADD1 giữ nguyên.

## 0. Khai báo thứ tự (bắt buộc đọc)
Addendum này được viết **SAU** khi đã xem số **mô tả** của exec-probe (chưa đủ |E| ≥ 100, nên **không phải verdict**):
- số leg: **49 / 100**;
- entry: trung vị trượt **−15,7 bps**;
- thoát trailing: trung vị **26,8 bps**, p90 **209 bps**, so với sim **0,67 bps**.

Vì vậy addendum **không đổi** bất kỳ ngưỡng, cột, quy tắc verdict (GREEN/AMBER/RED_SIZE, W1–W6, V1–V5) nào của PREREG_EXEC_PROBE.
Nó chỉ đổi (a) G-EXEC chặn ở cổng nào và (b) leg nào được đếm vào E. Các con số trên không được dùng để chọn ngưỡng.

## 1. Lý do
1. Exec-probe mới có 49/100 leg; hạn cứng 11-22 09:37 nhiều khả năng hết trước khi đủ 100 (lệnh dồn theo đợt sập, bản gốc §G-EXEC
   đã ghi rủi ro này). Giữ G-EXEC trong G-MICRO thì micro-live bị chặn bởi một phép đo có thể không bao giờ hoàn tất.
2. Micro-live với `C3_CAPITAL=1000` chính là phép đo trượt THẬT trên sàn, cùng đường lệnh, cùng tài khoản sẽ chạy pilot. Trượt thật
   là thứ G-EXEC cần trả lời trước khi chốt size pilot (Q4). Rủi ro vốn của micro bị giới hạn bởi 1 000 USDT.

## 2. Thay đổi
### 2.1 G-MICRO (ADD1 §3)
- **Bỏ mục 4 (G-EXEC)** khỏi G-MICRO. G-MICRO còn mục 1, 2, 3, 5, 6, 7 (giữ nguyên chữ).
- File `GOLIVE_GATE_MICRO.ok` không cần dẫn chứng G-EXEC.

### 2.2 G-PILOT (ADD1 §4) — thêm mục 6
6. **G-EXEC:** có verdict theo PREREG_EXEC_PROBE (nguyên chữ, |E| ≥ 100) trên tập E mở rộng ở §2.3, HOẶC owner đã quyết Q4
   bằng văn bản (ghi commit). Không verdict và không có quyết định Q4 ⇒ **không chạy pilot**.
- File `GOLIVE_GATE_PILOT.ok` phải có dòng `g_exec=<GREEN|AMBER|RED_SIZE|Q4_OWNER> <commit/đường dẫn dẫn chứng>`.

### 2.3 Fill micro-live thật được đếm vào G-EXEC
- **Được đếm:** leg ENTRY/DCA của c3 (cid `c3-`) trên tài khoản chính trong kỳ micro, trạng thái CONFIRMED trong sổ c3 (mỗi cid
  đúng 1 lần). Dòng log tham chiếu [sửa R4q]: xác nhận REST `[C3-LIVE-EXEC] FILL <sym> <cid> …`
  (`C3LiveOrderExecutor.java:426`) HOẶC xác nhận stream `[C3-LIVE-FILL] xac nhan qua stream <sym> <cid> …` (`FillAccounting`);
  cùng cid chỉ một trong hai xuất hiện (sổ xác nhận 1 lần). Trượt = fill/ref − 1, ref = close nến 1m quyết định (cùng định nghĩa C2 và exec-probe).
- **Gộp:** E = leg exec-probe (đến khi probe dừng) ∪ leg micro thật. Mỗi leg gắn nguồn (`probe` | `micro`). Verdict chấm 1 lần khi
  |E| ≥ 100, quy tắc PREREG_EXEC_PROBE giữ nguyên. Báo thêm verdict riêng từng nguồn (chỉ mô tả).
- **V1–V5:** áp cho leg micro khi đo được. Mục chỉ có nghĩa với probe (vd lat_snap) ghi `N/A (micro)` kèm lý do, không tính là trượt.
- **Giới hạn phải ghi trong báo cáo:** leg micro rất nhỏ (≈ 2,25 % × 1 000 ≈ 22 USDT), nên đo phần spread/độ trễ, **không** đo tác
  động khối lượng ở size pilot (≈ 225 USDT/leg). Cột `slip_x025` theo prereg vẫn là cột chính.
- **Thoát (trailing c3s-/c3x-):** báo trung vị/p90 trượt thoát của micro **chỉ mô tả**, đặt cạnh số probe ở §0. Không đặt ngưỡng
  mới (đã thấy số).

## 3. Script
- Thứ tự: addendum này được commit TRƯỚC mọi thay đổi cổng trong script `ops/c3live/golive_*`.
- Hiện không script nào kiểm G-EXEC (file gate do MASTER ký). Thay đổi duy nhất trong script: `golive_pilot_on.sh` từ chối khi
  `GOLIVE_GATE_PILOT.ok` thiếu dòng `g_exec=` (cùng cách kiểm `jar_md5=` / `size=`).

## 4. Sửa R4q (2026-11-05)
- §2.3: đơn vị đếm là cid CONFIRMED trong sổ. A1 4o MIN-5 nói tag `[C3-LIVE-EXEC] FILL` không tồn tại; thực tế có (dòng 426), nhưng
  chỉ xuất hiện khi REST xác nhận trước stream. Đường stream dùng `[C3-LIVE-FILL] xac nhan qua stream`. Không đổi ngưỡng hay quy tắc.
- Tiêu chí trượt THOÁT: xem ADDENDUM 3 (`GOLIVE_SCENARIO_ADDENDUM3_GEXIT.md`).
