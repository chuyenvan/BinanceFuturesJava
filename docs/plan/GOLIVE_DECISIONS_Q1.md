# GOLIVE — Quyết định owner Q1 + tài khoản con (chốt 2026-10-25)

Nguồn: brief chung v1.2 (MASTER, 10-25) — chép **nguyên ý** quyết định owner đã chốt; project memory `golive_1009.md`.
Phạm vi: đường `c3_live` (v1.2, sau cờ `LIVE_PROFILE=c3_live` + `LIVE_ADAPTER=dry|live`). Đường `c3_shadow` đang chạy và sim **không đổi**.
Owner đã DUYỆT bắt đầu code ngay (10-25). Mọi code v1.2 phải làm **đúng y như dưới đây**; thay đổi = quyết định mới của owner.

## Q1a — Thoát lệnh (trailing sau arm)
- Arm = **+7 %** (như sổ giấy).
- Sau arm: đặt **STOP_MARKET reduce-only TRÊN SÀN**.
- Dời stop lên khi mức mới cao hơn **≥ 1 tick VÀ ≥ 0,1 %**.
- **KHÔNG** SL cứng trước arm.
- Time-stop **168 h** + **TS_MKT_EXT X14** + đóng chủ động = **market reduce-only, idempotent**.

## Q1b — Equity lai
- Vốn tính size = **min(PILOT_CAPITAL config (10 000), totalMarginBalance tài khoản con)** — không tự phình theo lãi trong pilot.
- Drawdown kill-switch (A40, C6) tính trên **totalMarginBalance thật** (gồm BFUSD, Multi-Assets) so với **đỉnh**.
- Đối chiếu **hằng giờ**: |equity sổ − totalMarginBalance| / totalMarginBalance **> 1 %** ⇒ Telegram + **chặn mở mới** tới khi khớp.

## Q1c — C2 trượt giá có dấu
- Chỉ tính trượt **bất lợi**, có dấu (mua: `fill/ref − 1 > 0`; `ref` = close nến 1m quyết định).
- **> 1,7 %** ⇒ cảnh báo.
- **> 2,5 %** xảy ra **3 lần trong 24 h** ⇒ latch **NO_NEW_ENTRY** (vẫn quản lý vị thế); **CHỈ owner mở lại bằng script**.
- Ngưỡng là **tham số config** (sẽ chốt lại sau exec-probe ~100 leg).

## TradFi
- **Loại TradFi perps** (cổ phiếu / ETF / FX / commodity …) khỏi **universe mua** VÀ khỏi tính **market level / ALT_EW / feature thị trường** của `c3_live`.
- Sim làm sau (P1). **Không sửa đường `c3_shadow` đang chạy.**

## Tài khoản con (pilot c3_live)
- **Multi-Assets Mode BẬT** (đã kiểm 10-25), **one-way**, **CROSS 1x**, ký quỹ **10k BFUSD** (USDT = 0).
- Key ở `/root/.config/c3live/keys.env` trên 242 (`C3_LIVE_API_KEY` / `C3_LIVE_API_SECRET`, chmod 600).
- Code đọc từ file theo đường dẫn config **`LIVE_C3_KEYS_FILE`** (mặc định đường trên); **KHÔNG hardcode, KHÔNG log key**;
  file thiếu / quyền ≠ 600 ⇒ **từ chối bật push**.

## Ánh xạ sang code v1.2 (branch `v1.2/lib`)
| quyết định | nơi thực thi | trạng thái |
|---|---|---|
| Key file 600 + owner, không log | `c3live.client.C3LiveKeys` / `C3LiveClient.create` (C2) | xong ở lib |
| Multi-Assets bật, one-way, CROSS 1x | `c3live.guard.AccountModeGuard` (C5) — multiAssets KHÔNG tự đổi | xong ở lib |
| totalMarginBalance cho Q1b | `ExchangeGateway.account()` → `AccountSnapshot.getTotalMarginBalance()` | API sẵn; logic sizing/kill-switch/đối chiếu: vòng 2 (C1, C8, C9) |
| STOP_MARKET reduce-only trên sàn, dời ≥1 tick ∧ ≥0,1 % | `ExchangeGateway.newStopMarket` (Algo API) + `SymbolRules.roundStopPriceForLong` | API sẵn; logic ratchet: vòng 2 (C6) |
| Đóng market reduce-only idempotent | `newMarketOrder(..., reduceOnly=true)` + `queryOrder` theo clientOrderId | API sẵn; idempotency: vòng 2 (C3) |
| C2 trượt có dấu, latch | — | vòng 2 (C8) |
| Loại TradFi khỏi universe mua + market level | `c3live.universe.SymbolUniverseLive` (`isBuyable`, `marketIndexMembers`) | xong ở lib; trường phân loại thật CHƯA XÁC MINH (cần dump exchangeInfo) |
