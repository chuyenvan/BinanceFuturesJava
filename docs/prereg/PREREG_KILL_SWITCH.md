# PREREG_KILL_SWITCH — kill-switch theo equity (QUEUE_1015 P5)

- **Ngày:** 2026-10-15. **Trạng thái:** ĐỀ XUẤT — **chuẩn bị, KHÔNG deploy**. Branch `feat/kill-switch` (từ `module`), **không merge**.
- **Phạm vi:** code + spec sau cờ **mặc định TẮT**. Không đổi 242, không đổi shadow, không sửa systemd.
- **Cờ:** `KILL_SWITCH_ENABLED` (bool, **mặc định false**). Tắt ⇒ mọi hàm trả `DISABLED`, `blocksNewEntries()=false`; lớp **không được tham chiếu** từ bất kỳ đường sim nào ⇒ parity sim **byte-identical** (tầm thường).

## 1. Bậc hành vi

| Bậc | Điều kiện | Hành vi |
|---|---|---|
| `WARN` | DD ≥ `KILL_SWITCH_DD_WARN` **hoặc** UW ≥ `KILL_SWITCH_UW_DAYS_WARN` | Chỉ **cảnh báo** (Telegram). Không đổi giao dịch. |
| `PAUSE` | DD ≥ `KILL_SWITCH_DD_PAUSE` **hoặc** UW ≥ `KILL_SWITCH_UW_DAYS_PAUSE` | **Không mở lệnh MỚI**; **vẫn quản lý vị thế đang có** (trailing/SL/time-stop chạy bình thường). |
| `STOP` | DD ≥ `KILL_SWITCH_DD_STOP` | Dừng hẳn (không mở lệnh mới). Việc có tiếp tục quản lý vị thế hay không do owner chốt. |

- **DD** = `(equityĐỉnh − equityHiệnTại) / equityĐỉnh` (đỉnh cập nhật theo thời gian; đỉnh mới ⇒ UW về 0).
- **UW** (under-water) = số ngày kể từ lần lập đỉnh gần nhất.
- Phục hồi: từ `WARN`/`PAUSE` về `NORMAL` khi `DD < KILL_SWITCH_DD_RESUME` (nếu khai) **và** `UW < KILL_SWITCH_UW_DAYS_WARN`.
- Đỉnh mới hoặc phục hồi đủ sâu ⇒ về `NORMAL`; **không tự nhảy bậc ngược nếu chưa khai `DD_RESUME`** (giữ nguyên bậc hiện tại).

## 2. Tham số — **owner chốt, code KHÔNG đặt giá trị**

| Key | Ý nghĩa | Bắt buộc |
|---|---|---|
| `KILL_SWITCH_ENABLED` | bật/tắt (mặc định `false`) | có |
| `KILL_SWITCH_DD_WARN` / `_PAUSE` / `_STOP` | ngưỡng DD theo bậc (phân số: `0.10` = −10%) | owner khai |
| `KILL_SWITCH_UW_DAYS_WARN` / `_PAUSE` | ngưỡng UW (ngày) | owner khai |
| `KILL_SWITCH_DD_RESUME` | ngưỡng phục hồi về `NORMAL` | tùy chọn |
| `KILL_SWITCH_NOTIFY` | gửi Telegram (mặc định `false`) | tùy chọn |

**Key nào vắng ⇒ bậc đó KHÔNG bao giờ kích hoạt (inert).** Vì vậy bật `KILL_SWITCH_ENABLED=true` mà chưa khai ngưỡng ⇒ an toàn (không bao giờ chặn).

## 3. Thông báo

Gửi qua **kênh healthcheck hiện có** (Telegram của shadow: chat `6548680563` — cùng bot/kênh mà `~/shadow_c3/bin/health.sh` và `P2PTelegramNotifier` đang dùng). Cơ chế: `KillSwitch.setNotifier(consumer)`; production nối vào hàm gửi Telegram hiện có. Chỉ gửi khi **đổi bậc** và `KILL_SWITCH_NOTIFY=true` (không spam).

## 4. Điểm nối (chưa wire)

- **Live/paper:** gọi `killSwitch.onEquity(equity, now)` mỗi khi cập nhật equity (cùng chỗ `BudgetManagerSimple.updateBalance` / `ShadowBookC3`), rồi chặn nhánh mở lệnh mới khi `blocksNewEntries()` — **chưa nối** trong PR này (chuẩn bị, không deploy).
- **Sim:** **không nối** (giữ parity).

## 5. Kiểm chứng

- `KillSwitchTest` 8/8 PASS: mặc định TẮT; bật mà không khai ngưỡng ⇒ inert; bậc DD; bậc UW; PAUSE chặn mở lệnh mới nhưng KHÔNG `halted()`; phục hồi về NORMAL; đỉnh mới reset UW; notifier chỉ bắn khi đổi bậc + `NOTIFY=true`; equity ≤ 0 bị bỏ qua.
- `mvn -o test` toàn module: xem commit.
- Parity sim: lớp không được tham chiếu từ đường sim; mọi key mặc định TẮT ⇒ byte-identical.
