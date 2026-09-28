# ADDENDUM cho OpenClaw — sau review kết quả Track B + rào (MASTER, 2026-09-28 tối)

Bối cảnh: Oracle HEAD `21b4556` CHƯA có `PLAN_OPENCLAW_BASELINE_RESET_20260928.md` (commit `af282c9` chỉ ở origin) và
KHÔNG có output Kaggle mới nào sau `xs-a2s6` ⇒ plan reset CHƯA được chạy. Việc OpenClaw đã làm 19:29→20:24: TRACKB_STEP1,
BOOK_COST, BOOK_COST2, RULERS_UNIT, BAR_A_CALIBRATION. Bước đầu: `git pull --ff-only` trên Oracle.

## A. Phát hiện quan trọng nhất: CHI PHÍ SIM ĐANG BỊ THỔI PHỒNG ~0,6%/vòng (đi ngược mọi biến thể "nhiều lệnh")
- `RESULT_LIVE_FILLS_AUDIT` §? + `RESULT_BOOK_COST` §99-102: trên 991 chân THẬT, slip CÓ DẤU vs close phút = −0,02% (≈0);
  0,33%/chân là |slip| VÔ HƯỚNG (nhiễu). Fee thật 0,098%/vòng. Spread+impact đo (bookTicker+aggTrades) ~0,014%/vòng.
- Sim/nghiên cứu dùng 0,8%/vòng (sau 26/09: 0,6%) ⇒ mỗi lệnh bị trừ oan ~0,5–0,7pp.
- Hệ quả: lệnh BIÊN (khi tăng K, nới gate, tăng tần suất) EV đang bị đẩy xuống ≤0 một cách hệ thống ⇒ các verdict
  "nhiều lệnh = rác" (GATESCALE_KEEPLEG0/SWEEP, GATE_RECAL, SIZE_COUNT, K_DENSITY) PHẢI chấm lại ở chi phí thật.
- ⚠️ Phải kiểm trước khi dùng: (i) giá vào/ra của SIM so với "close phút" dùng làm mốc slip (nếu sim vào ở close phút
  thì chi phí sim đúng = fee + spread); (ii) slip có dấu tách theo loại leg: vào PREDICT / BIG_DOWN (lúc sập) / DCA / thoát
  STOP_MARKET (trailing) / STOP_LOSS — nếu leg lúc sập có slip có dấu dương đáng kể thì dùng số của leg đó.

## B. Track B — dương ở chi phí thật nhưng CÓ 3 CỜ ĐỎ phải gỡ trước khi tin
1. Đối chứng coin NGẪU NHIÊN có gross **+0,064%/ngày** (`RESULT_TRACKB_STEP1` §3). Book market-neutral ngẫu nhiên phải ~0.
   ⇒ nghi bias harness: universe TĨNH top-200 theo dv_med của CẢ 2021–2025 (look-ahead/survivorship), stop −10% bất đối
   xứng, hay trọng số long/short lệch. PHẢI giải thích bằng số trước.
2. Control không cùng turnover (0,872 vs 0,351/ngày) ⇒ control phải dùng CÙNG hysteresis/band để tách tín hiệu khỏi turnover.
3. `vol` (short vol cao / long vol thấp) = net SHORT BETA alt; 2022–2025 alt yếu kéo dài ⇒ có thể là beta/regime, không alpha.
   ⇒ hồi quy PnL ngày trên BTC + chỉ số alt EW; báo alpha + t (block).
Chưa được lên bước 2 cho tới khi 1–3 xong.

## C. Rào (a)/(b′): chứng minh toán học là KHÔNG THỂ ĐẠT với chiến lược thật — đề nghị owner bỏ
Với PnL đơn vị ~ chuẩn (μ, σ):
- (b′) bỏ top-25% còn >0 ⇔ 0,75μ − 0,318σ > 0 ⇔ μ/σ > 0,424 ⇒ ở đơn vị NGÀY cần Sharpe năm ≈ 0,424·√365 ≈ **8,1**.
- (a) top-1% ≤ 15% tổng ⇔ 0,01(1 + 2,665σ/μ) ≤ 0,15 ⇔ μ/σ ≥ 0,19 ⇒ đơn vị NGÀY cần Sharpe năm ≈ **3,6**.
Khớp số đo: 3/452 arm qua (a)@15%, 0 bền; book U1 share top-1% 210–382% (`RESULT_BAR_A_CALIBRATION`, `RESULT_RULERS_UNIT`).
⇒ Thay bằng luật 4 tầng ở `PLAN_OPENCLAW_BASELINE_RESET_20260928.md` §3. Với BOOK dùng đơn vị NGÀY + Sharpe/DD/
bỏ-top-episode, không dùng share top-1% lệnh.

## D. Thứ tự việc (thay cho Phase 1–2 của plan reset)
- D0 `git pull`; commit vệ sinh `_claude_tmp/` (Phase 0 plan reset).
- D1 CHI PHÍ THẬT (0 sim): slip có dấu theo loại leg trên 991 chân + đối chiếu giá khớp sim; chốt 3 mức chuẩn:
  `base` (đo), `stress` (p90), `legacy 0,8%` (chỉ để đối chiếu). Pre-reg `PREREG_COST_TRUTH.md`.
- D2 Chấm lại hậu kiểm (0 sim) ở `base`/`stress`: FG_KEEPLEG0, cd-sel15, sc-b1..b4, gatescale KEEPLEG0/T170, cc-t100,
  kg0-q99x, rc-a-q99x — theo luật 4 tầng. Công thức hậu kiểm: net_leg = pnl_sim + (0,008 − c)·notional_leg (khai rõ là
  xấp xỉ, bỏ qua compounding).
- D3 Sim Kaggle (Phase 2 plan reset, k=5) với phí `base` VÀ `stress` (thêm key phí nếu đã có; nếu phải sửa Java ⇒ key gated,
  parity 2 md5).
- D4 Track B: gỡ 3 cờ đỏ mục B (0 sim), rồi mới quyết bước 2.
- D5 Phase 3–4 như plan reset (độ bền, holdout 2026 một lần).
