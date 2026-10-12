# PREREG_EXEC — khớp lệnh vào chân (entry) trên DEV bằng aggTrades Binance Vision

Ngày: **2026-10-12**. Agent EXEC. File này commit **TRƯỚC** khi tải dữ liệu E1 và **TRƯỚC** mọi phép đo E2; sau commit
**không đổi thiết kế, ngưỡng, k, chính sách**. Mọi lệch khỏi file này (nếu buộc phải có, vd lỗi dữ liệu) ghi rõ trong
`EXEC_RESULT.md` mục "Lệch pre-reg", không dùng để chọn chính sách.

Ràng buộc: 0 sim, 0 Java, 0 Kaggle, 0 Binance REST (chỉ `data.binance.vision`), 0 chạm 242/shadow, 0 đọc `ho4-*`/`ho26-*`,
0 đụng kho backcast 2020–2021H1. DEV = chân có `start` trong `[2022-01-01, 2026-01-01)` +07; đường giá proxy cắt tại
2026-01-01 00:00 +07 (không tải kline/aggTrades 2026).

## 1. Tập chân (đã xác định, md5 printDone)

Run DEV K24+skipFull stress 1,675 % in-sim, 8 seed (`docs/audit/COVERAGE_M2_BASE_20261009.md` "Baseline"):
`~/kaggle_sim/out/nsel-nen-s{42,7,13,21,99,123,777,2024}` — jar `b7c89f09…`, override `SELECTOR_RANK_TOPK=24`,
`GATE_QUOTA_SKIP_WHEN_FULL=true`, `SIM_CRASH_ENTRY_PENALTY=0.01675`.

| seed | md5 printDone | dòng | chân DEV 2022–25 |
|---|---|---|---|
| 42 | 3d79927b0b0e9f2a9ac592e2819425fe | 3517 | 2936 |
| 7 | 50463d96f6357f86b23df7da828a2ad4 | 3508 | 2930 |
| 13 | e74bb15867b50878e069d3e42e5cf10e | 3529 | 2938 |
| 21 | a218908cb34dfa4e05517843073fdbac | 3529 | 2966 |
| 99 | 344014de49808d80823f97206f5db788 | 3628 | 3031 |
| 123 | 13643b2528df25c02970071bcd233848 | 3515 | 2950 |
| 777 | 8044621b36b766e741350d8fd881f56e | 3452 | 2914 |
| 2024 | 752f6e75e500a7dcc39fb0a993a85e87 | 3548 | 2989 |

Tổng **23 654 chân** (PRED 21 454 · BIG_DOWN 1 728 · DCA_LEVEL1 472), **5 284 sự kiện duy nhất** `(sym, s_ms)`,
528 symbol; cần aggTrades cho **3 071** (sym, ngày UTC), kline 1m cho **2 241** (sym, tháng). Bảng: `exec_legs.py`.

## 2. Mốc thời gian, nến quyết định, quy mô lệnh

- Nến quyết định **M** = nến 1m mở tại `start` của printDone (`s_ms`, giờ +07 → UTC) — đúng quy ước proxy `qsleeve_q0`
  (E = close nến tại `s_ms`, đường thoát từ nến kế). `close_M`, `open_M` lấy từ kline 1m Vision.
- **t_dec = s_ms + 66 s** (live đọc nến M ở giây 6 của phút M+1; khớp `RESULT_LATENCY_FILL`: latency median ~7 s).
- Nến "sập": `br = close_M/open_M − 1 ≤ −1 %`. Nhóm sập: `(−2 %, −1 %]`, `(−4 %, −2 %]`, `≤ −4 %`; nhóm "không sập" `> −1 %`.
- Notional chân `N = size_ratio × E_live`, `size_ratio = margin / (35 000 + Σ pnl đã chốt trước start, cùng seed)`
  (p50 1,14 %, p5–p95 0,36–2,16 %). **E_live = 35 000 (paper, CHÍNH)** và **10 000 (pilot, báo kèm)**. `Q = N / close_M`.
- aggTrades: `price, quantity, transact_time (ms), is_buyer_maker`. `is_buyer_maker=false` = taker MUA (ăn ask);
  `true` = taker BÁN (ăn bid).

## 3. Chính sách (k = 5, chốt; không thêm/bớt sau commit)

Mô phỏng chỉ từ aggTrades trong cửa sổ `[t_dec − 2′, t_dec + 30′]` (+ kline 1m cho P4 và cho đường thoát).

- **P0 — market tại t_dec.** Walk-the-book xấp xỉ bằng các lệnh taker MUA (`is_buyer_maker=false`) theo thời gian từ
  t_dec: cộng dồn qty tới đủ Q trong `[t_dec, t_dec+3 s]`; giá khớp = VWAP phần đã tiêu. Nếu 3 s không đủ qty: nới tới
  30 s (cờ `thin`). Nếu không có taker MUA nào trong 30 s: giá = trade đầu tiên (mọi phía) sau t_dec (cờ `noask`);
  không có trade nào trong 30 s ⇒ sự kiện **thiếu dữ liệu** (loại khỏi mọi chính sách, báo phủ).
  **Giả định:** người mua chủ động vài giây sau t_dec gặp cùng sổ ask mà lệnh ta sẽ gặp; không mô hình cạn sổ chồng lên
  và sổ hồi. Biến thể kiểm **P0max** (mô tả, không dùng GO) = giá taker MUA **cao nhất** trong `[t_dec, t_dec+3 s]` (cận trên).
  Nếu Vision có `bookTicker` cho ngày đó: so ask tốt nhất (bản ghi cuối ≤ t_dec) với P0 trên mẫu ≤ 150 (sym, ngày) ngẫu
  nhiên (seed 20261012) — **chỉ kiểm định**, không thay P0.
- **P1 — limit tại close_M, giữ 60 s** (từ t_dec).
- **P2 — limit close_M × (1 − 0,3 %), giữ 5′.**
- **P3 — ladder 3 nấc** (close_M, ×0,995, ×0,99), mỗi nấc Q/3, giữ 5′; mỗi nấc mô phỏng độc lập.
- **P4 — market trễ tới 1 phút xanh:** xét lần lượt nến M+1, M+2, … (kline Vision); nến j đầu tiên có `close > open` ⇒
  market tại giây 6 của phút sau nến j (cùng mô hình P0). Nến j phải mở ≤ s_ms + 28′ (fill trong cửa sổ 30′);
  không có ⇒ không vào (PnL 0).

**Khớp limit (P1–P3), mỗi nấc giá L:**
1. *Marketable lúc đặt:* tiêu các taker MUA trong `[t_dec, t_dec+3 s]` theo thời gian khi giá ≤ L (dừng ở print đầu tiên
   > L); phần này khớp taker tại giá print. Phần còn lại nằm chờ ở L.
2. *Nằm chờ:* khớp từ taker BÁN có **price < L (xuyên giá)** trong `(t_dec, t_dec + giữ]`; tỉ lệ khớp = min(1, Σqty xuyên / Q còn lại);
   giá = L. **Giả định queue bảo thủ:** print **= L KHÔNG tính khớp** (ta xếp sau toàn bộ sổ có sẵn ở L, không biết độ sâu);
   chỉ print xuyên dưới L mới chứng minh mức L đã bị ăn hết. Biến thể "= L tính khớp" (lạc quan) báo **mô tả**, không GO.
3. Hết giờ giữ: huỷ phần chưa khớp (PnL 0 cho phần đó). Không đuổi giá, không market phần thừa.

## 4. Proxy thoát + PnL

- Luật thoát = `qsleeve_q0` Q4 (đọc `SimulatorMarketLevelTicker1MStopLoss`): arm khi high/E−1 > 7 %, SL trail
  `E·(1+round((peak−min(peak,3 %))/0,5 %)·0,5 %)`, time-stop 168 h, KHÔNG DCA, KHÔNG funding, KHÔNG SL cứng; nến kline 1m Vision.
- **E = giá khớp bình quân** (phần đã khớp) của chính sách; đường thoát bắt đầu từ nến 1m **chứa thời điểm khớp cuối**
  (P0: nến M+1 — trùng quy ước qsleeve); `t0` time-stop = open(nến đó) − 60 s. Cắt tại 2026-01-01 +07 (MTM close cuối, cờ `cut`).
- Phí: `COST = 0,1116 %` notional/vòng **như nhau mọi chính sách** (CHÍNH — không cộng lợi phí maker vì không biết tier live).
  Độ nhạy mô tả: trừ 3 bps cho phần khớp maker.
- **PnL_leg = N × frac_khớp × (px_thoát/E − 1 − COST)** (USD); chân không khớp = 0. DCA/BIG_DOWN tính như chân độc lập
  (proxy kém chính xác cho cụm DCA — chỉ 472/23 654 chân; báo riêng tập không-DCA).

## 5. Thước & thống kê

- **Chi phí vào** (bps) = `(E/close_M − 1)·1e4` trên phần khớp; **tỉ lệ khớp** = Σ frac / số chân.
- **ΔPnL_leg = PnL(Pk) − PnL(P0)** ghép cặp theo chân (cùng seed, cùng N).
- **Đợt** = cụm ngày +07 có ≥1 chân vào (hợp 8 seed), tách khi ≥ 3 ngày liền không có chân (định nghĩa COVERAGE_M2).
  `Δ_e = mean_seed Σ_{chân của seed trong đợt e} ΔPnL`. Thống kê `S = Σ_e Δ_e` (= ΔPnL trung bình/seed, USD paper).
- **CI:** bootstrap theo đợt, B = 4 000, seed 20261012; half-width 95 % = 1,96·sd_boot, **inflate √(2 ln 5) = 1,794**
  ⇒ `CI_infl = S ± 1,794·1,96·sd_boot`.
- **Đợt có lãi:** `n_pos(Pk)` = số đợt có `mean_seed Σ PnL(Pk) > 0`.
- Theo ngày MTM proxy: ΔPnL ghi theo ngày thoát (+07); báo % ngày Δ>0 và maxDD đường vốn chốt (35 000 + Σ PnL proxy theo
  ngày thoát, cận dưới DD) — **mô tả**.
- Lát cắt báo cáo: năm vào 2022/2023/2024/2025 × nhóm sập (§2) — mô tả (không inflate thêm, không GO theo lát).

## 6. Luật quyết định (chốt)

- **GO cho Pk (k=1..4)** ⇔ trên sizing paper 35 000: `CI_infl(S) > 0` hoàn toàn **VÀ** `n_pos(Pk) ≥ 0,9 × n_pos(P0)`.
  Nhiều Pk GO ⇒ báo tất cả, ưu tiên S lớn nhất (không chọn thêm tham số). Pilot 10 000 báo kèm; nếu dấu S ngược ⇒ ghi cảnh báo.
- **Hiệu chuẩn penalty** (chân sập `br ≤ −1 %`, P0, sizing paper): `c̄` = chi phí vào TB (bps) với CI bootstrap theo đợt
  (inflate 1, chỉ 1 phép đo). **ĐÚNG** nếu 167,5 bps ∈ CI; **THỪA** nếu CI_trên < 167,5; **THIẾU** nếu CI_dưới > 167,5.
  Báo thêm chân không sập (sim giả định ~0,67 bps slip).

## 7. Dữ liệu (E1) + kiểm hợp lệ (validate TRƯỚC khi báo)

- Tải `data.binance.vision/data/futures/um/daily/aggTrades/<SYM>USDT/…-<ngày>.zip` CHỈ cho 3 071 (sym, ngày) ở §1, theo lô
  (≤ 4 song song), kiểm sha256 với `.CHECKSUM`, giữ hàng trong cửa sổ các sự kiện, **xoá zip gốc ngay**. Kline 1m:
  `monthly/klines/<SYM>USDT/1m/…-<tháng>.zip` (2 241 sym-tháng), giữ khoảng `[s_ms−2′, min(s_ms+169,5 h, 2026-01-01 +07))`.
  Cache tự tạo ≤ 15 G, ghi md5 trước khi xoá.
- **V1 (aggTrades vs kline 1m):** phút trong cửa sổ có trade: open/high/low/close của aggTrades == kline (đúng tuyệt đối)
  và |Σqty − volume| ≤ 1e-6·volume (+1e-9). **Ngưỡng ≥ 99,9 % phút trùng**; không đạt ⇒ báo, điều tra, không GO.
- **V2 (nến quyết định):** `entry_printDone == close_M·(1 + 0,01675·[br ≤ −1 %])` (rel 1e-6) ≥ 99 % chân có kline.
  Dưới ngưỡng ⇒ báo (lệch nguồn ticker sim vs Vision), dùng close_M Vision làm mốc.
- **V3 (proxy):** proxy với E = entry printDone (đã gồm phạt nếu sập), path từ M+1, trên leg0 không-DCA vs `profit`/100 printDone: pearson ≥ 0,95.
- **V4 (phủ):** % sự kiện / chân có ≥ 1 trade trong `[t_dec, t_dec+30 s]`; sự kiện thiếu loại khỏi mọi chính sách.
- **V5 (vệ sinh):** E ≤ L với mọi khớp nằm chờ; tỉ lệ khớp bảo thủ ≤ lạc quan; P0 thin/noask đếm và báo.

## 8. Hạn chế khai trước

1. aggTrades không có sổ lệnh ⇒ P0 là ước lượng (VWAP người mua chủ động), không phải walk-the-book thật; P0max là cận trên.
2. Khớp limit bỏ qua vị trí queue thật (bảo thủ) và ảnh hưởng của chính lệnh ta lên giá (nhỏ: N p50 ≈ 400 USDT paper).
3. Proxy thoát không DCA/funding; chân không khớp = 0 ⇒ bỏ lỡ cơ hội tính đúng là "không lãi/không lỗ", không tính
   chân thay thế mà sim có thể vào bằng vốn rảnh (bậc 2).
4. Kết quả DEV 2022–2025; xác nhận trên kho backcast 2020–2021H1 là việc sau (không đụng kho vòng này).
5. 8 seed chia sẻ phần lớn sự kiện ⇒ không độc lập; đơn vị bootstrap = đợt lịch (hợp 8 seed).

## 9. Sản phẩm

`research/analysis/exec_legs.py` (bảng chân), `exec_fetch.py` (E1), `exec_measure.py` (E2), `docs/result/EXEC_RESULT.md`
+ `docs/result/exec_result.json`.
