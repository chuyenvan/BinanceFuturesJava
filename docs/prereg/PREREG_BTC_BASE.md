# PREREG_BTC_BASE — lớp BTC "lấp thời gian chờ" dưới crash-buy K24+skipFull

Ngày 2026-10-20. Câu hỏi owner: thêm sleeve BTC làm nền giữa các đợt crash-buy (crash-buy chạy chồng lên). Owner chấp nhận
maxDD tổng ≤ 40 %, riêng BTC chấp nhận DD 80 %. Cần trả lời (1) có tăng CAGR trong giới hạn DD không, (2) cơ chế "lấp chỗ trống"
có hơn chia tĩnh không (nếu không ⇒ chỉ là beta allocation), (3) vào/ra khi nào.
Chỉ đo hậu kiểm trên chân lệnh sẵn có: 0 sim Java mới, 0 đụng 242/shadow/live, 0 Binance REST. HO 2026 W9 chỉ để xác nhận; 2020 niêm phong.
Commit file này TRƯỚC khi chạy bất kỳ biến thể overlay nào (chỉ Bước 0 — khảo sát dữ liệu/phơi nhiễm B0 — đã chạy).

## 0. Kết quả Bước 0 (khảo sát, không đo hiệu quả overlay)

Script `docs/result/btc_base/{px_build.py, bb_core.py, bb_step0.py}`, JSON `docs/result/btc_base/step0.json`.

- **Sizing sim** (đọc code `SimulatorMarketLevelTicker1MStopLoss.createOrder` + `TradeUtils.managerBudget`, profile r4_kg0_k16_f015_g155):
  `budget = equityNow × F_BASE(0,015) × throttle / ladder`, `throttle = clamp(1 − U/U_MAX)`, U = margin đang mở / equity, U_MAX 0,60,
  `SIM_FIX_B3=true` ⇒ equityNow = balance + unrealized (equity **MTM**), leverage 1 ⇒ margin = notional. ⇒ size tỉ lệ equity MTM.
- **V1 tái lập B0** (chân ECMEAS bucket `edge_attr/legs.parquet` win D, lọc như KILLSW; MTM phút, close kline1m Vision qua `gvz_mtm.kp`,
  ffill ≤ 60′): CAGR22, maxDD22 phút, ΣPnL trùng ECMEAS tới 1e-9 cả 8/8 seed (TB CAGR22 36,1 %, maxDD22 −22,6 %, tệ nhất −24,7 %).
  HO: B0 = `ho4-k24-b-s*` (printDone + giá cache Vision `1013/ecm/ecm_px`), ROI W9 / maxDD W9 / eq0 trùng `tsx/ho/ho_mtm.json` 8/8
  (TB ROI 10,19 %).
- **V2 phủ giá**: DEV 0 chân không có giá, 0 phút thiếu sau ffill 60′ (≈ 9,1M chân-phút/seed); HO 0/0.
- **Phân phối n_t = Σ notional MTM mở / equity MTM (B0, theo phút)** — median qua 8 seed [min; max]:

| | mean | p50 | p90 | p99 | max | % t n=0 | % t n<5 % | % t n<10 % |
|---|---|---|---|---|---|---|---|---|
| DEV 2021-07→2025-12 | 4,4 % [4,3; 4,6] | 0 | 16,0 % | 37,9 % | 51,8 % [50,9; 52,4] | 62,7 % | 76,2 % | 83,6 % |
| HO 2026 W9 | 3,1 % [2,5; 3,5] | 0 | 11,6 % | 30,0 % | 40,0 % | 66,8 % | 79,7 % | 88,3 % |

  Gross max 0,52×E < 1 ⇒ sim không bao giờ cho gross > 1×E; định nghĩa "chỗ trống" = max(0, G − n_t), G = 1,0 giữ nguyên.
- **Dữ liệu BTC/ETH**: close 1m BTCUSDT/ETHUSDT USDT-M (Binance Vision kline1m; 2021-01..2025-12 file có sẵn trên Oracle,
  2026-01..09 từ Kaggle `chuyendinh/vz-kline1m-2026`) — **0 phút thiếu** 2021-01-01 → 2026-10-01. Funding Vision `~/vz/out/funding`
  BTCUSDT/ETHUSDT 6 297 mốc 8h mỗi symbol (2021-01-01 → 2026-09-30 16:00 UTC). BTC: DEV 34 153 → 87 626 (+157 %, maxDD phút −77,6 %);
  HO W9 87 595 → 84 318 (−3,7 %, maxDD −40,9 %).
- Tương quan ngày (+07) BTC vs crash-buy B0: toàn kỳ ≈ 0,20; trong ngày có lệnh mới ≈ 0,31 (≈ 165 ngày/seed).

## 1. Khung (cố định)

- DEV: mô phỏng 2021-07-01 00:00 → 2026-01-01 00:00 (+07), vốn 35 000, 8 seed 42 7 13 21 99 123 777 2024.
  **CAGR = CAGR22** (cửa sổ chuẩn ECMEAS/KILLSW/ISO_RISK: 2022-01-01 → 2026-01-01 +07). **maxDD cho luật = toàn kỳ DEV**, equity MTM lấy
  mẫu theo ngày (close +07) VÀ theo giờ, lấy cái tệ hơn ("DD luật"); DD phút báo cáo kèm. Calmar = CAGR22 / |DD luật| (+ Calmar22 phút như ECMEAS).
- HO = 2026 W9 (2026-01-01 → 2026-10-01 +07), xác nhận một lần cho O(w*). Overlay bắt đầu ở đầu W9 với vốn = equity B0 tại đó; chân mở
  trước W9 giữ size gốc.
- Giá BTC/ETH: close 1m USDT-M Vision làm **proxy giá spot** (spot kline không có trên Oracle; bỏ qua basis spot–perp — ghi giới hạn).

## 2. Mô hình (cố định)

- BTC sleeve = BTC SPOT ở tài khoản tách (không cross-margin với crash-buy), không đòn bẩy. Phí 0,04 %/chiều + trượt 0,05 %/chiều
  (0,09 % notional mỗi lần mua/bán). Tiền bán BTC nằm tiền mặt (lãi 0).
- Crash-buy: giữ nguyên chân (thời điểm, giá vào/ra, PnL/notional) của B0; mỗi chân i mở ở phút m0 được scale ρ_i = V_cb(m0)/E_B0(m0),
  V_cb = vốn tính size của crash-buy trong biến thể (equity trước khi tính chân mở cùng phút). Bậc 1: không mô phỏng lại throttle/trần.
- **B0**: crash-buy như hiện tại, 100 % vốn.
- **S(w)**: chia tĩnh; w vốn BTC, (1−w) crash-buy (V_cb = E − giá trị BTC), rebalance về tỉ lệ đầu mỗi tháng (00:00 UTC ngày 1,
  khớp close phút 23:59 trước đó).
- **O(w)** overlay "lấp chỗ trống": crash-buy giữ nguyên size tính trên TỔNG equity E (V_cb = E). BTC target b* = min(w, max(0, G − n_t)) × E,
  G = 1,0. **RA**: tại phút crash-buy vào lệnh làm n_t + b_t > G (n_t gồm chân vừa mở, MTM close phút đó), bán BTC đủ phần thiếu ngay phút
  đó ở close 1m phút vào lệnh. **VÀO**: chỉ ở mốc 00:00 UTC hằng ngày (quyết định và khớp bằng close phút 23:59 UTC — thông tin trước
  00:00), mua BTC lên b*; không mua ngay khi lệnh crash-buy đóng. Nếu b_t > b* (vd. BTC tăng giá) thì bán bớt về b* ở mốc ngày
  (rebalance đúng về b* cả hai chiều, không có dải). Lưới **w ∈ {0,2; 0,3; 0,4; 0,5}**.
- Báo cáo thêm (KHÔNG dùng để chọn; tính cho mọi w của lưới, nêu bật w*):
  - O(w)+T: cắt lỗ cố định — sleeve về 0 khi BTC close ngày (UTC) ≤ 70 % đỉnh close 180 ngày (gồm hôm nay); vào lại khi close ngày
    > max close 30 ngày trước đó. Đánh giá ở mốc ngày. Lịch sử giá từ 2021-01-01 (đủ 180 ngày trước DEV).
  - O(w)-ETH: sleeve = rổ BTC/ETH 50/50 (về 50/50 ở mỗi mốc ngày; RA bán theo tỉ lệ giá trị).
  - O(w)-perp: như O(w) nhưng trừ funding BTCUSDT thực tế (long trả rate × notional ở mỗi mốc funding).
  - O(w, G=1,5).
  - S'_bh(w̄): như S'(w̄) nhưng mua một lần không rebalance.
- **S'(w*)** = S(w̄) (cơ chế S, rebalance tháng) với w̄ = trung bình theo thời gian (phút) của b_t/E trong O(w*), tính riêng từng seed.

## 3. Luật (chốt trước)

- **Chọn w***: w LỚN NHẤT trong lưới mà trên DEV: DD luật của O(w) ≥ −40 % ở SEED TỆ NHẤT VÀ ΔCAGR22(O(w) − B0) > 0 ở 8/8 seed.
  Không w nào đạt ⇒ **NO-GO**.
- **GO DEV** nếu w* tồn tại.
- **Câu hỏi (2)**: so O(w*) với S(w*) VÀ S'(w*). "Lấp chỗ trống có giá trị" chỉ khi O(w*) hơn S'(w*) về CAGR22 ở ≥ 7/8 seed VÀ
  DD luật seed tệ nhất của O(w*) không tệ hơn của S'(w*) quá 2pp. Nếu không ⇒ kết luận: chỉ là beta allocation.
- **HO 2026 W9 xác nhận O(w*)**: ΔROI W9 (O − B0) > 0 ở ≥ 6/8 seed VÀ DD luật W9 (tệ hơn của ngày/giờ) ≥ −40 % mọi seed.
  HO phụ thuộc đường đi BTC 2026 (beta) ⇒ báo kèm BTC buy&hold W9 (−3,7 %, DD −40,9 %).
- Không thêm biến thể / không đổi lưới, G, phí, ngưỡng sau khi thấy kết quả.

## 4. Chỉ số bắt buộc (mỗi biến thể × seed)

CAGR22 (+ CAGR toàn kỳ), maxDD (ngày, giờ, phút; toàn kỳ và cửa sổ 22), Calmar, tháng tệ nhất, giai đoạn DD sâu nhất (đỉnh–đáy),
mức sử dụng vốn trung bình (n_t + b_t)/E, tương quan ngày BTC vs crash-buy (toàn kỳ, ngày có lệnh mới), số lần bán ở chân RA, PnL các lần
bán đó so với giá mua bình quân, đóng góp PnL BTC vs crash-buy, riêng năm 2022 (PnL theo sleeve, DD 2022), maxDD riêng sleeve BTC (chỉ số
TWR của sleeve, mẫu giờ). Bảng: median và min/max qua 8 seed.

## 5. Kiểm vệ sinh (FAIL ⇒ dừng, báo, không đọc kết quả)

- V1: B0 tái lập số tham chiếu (DEV CAGR22/maxDD22 vs ECMEAS; HO ROI/maxDD W9 vs ho_mtm.json) sai ≤ 0,3pp mỗi seed. (Bước 0: PASS.)
- V2: MTM missing = 0 (chân không giá, phút thiếu sau ffill). (Bước 0: PASS.)
- V3: O(w=0) ≡ B0 (|ΔE| ≤ 1e-6 USD mọi phút).
- V4: ngay sau mỗi lần bán RA: n_t + b_t ≤ G + 1e-3 (dung sai phí).
- V5: không look-ahead — thay giá BTC sau một mốc cắt bằng giá xáo trộn ⇒ mọi giao dịch BTC trước mốc cắt không đổi; RA chỉ dùng
  close phút vào lệnh; mốc ngày dùng close 23:59 UTC.
- Kiểm nội bộ: equity dựng vector hoá khớp equity tính trong vòng sự kiện tại các mốc sự kiện.

## 6. Giới hạn đã biết (ghi trước)

Beta BTC: DEV BTC +157 % (2021-07 → 2025-12) nên chia tĩnh có lợi thế beta; tương quan crash-buy–BTC tăng đúng lúc sập (ngày có lệnh mới
0,31 vs 0,20) — RA bán BTC ngay đáy; giả định tài khoản tách nên không mô phỏng liquidation/cross-margin; size crash-buy scale bậc 1 (không
chạy lại sim Java); proxy spot bằng giá perp; HO W9 là một đường BTC duy nhất.

## 7. Sản phẩm

`docs/result/BTC_BASE.md` + `docs/result/btc_base/` (script, JSON nhỏ). Làm việc trong `~/claude_master/btc_base/`.
