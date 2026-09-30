# RESULT_SHORT_FEASIBILITY — SHORT có cửa không? (đảo hướng + đảo gate, PROXY 0-sim)

Ngày: **2026-09-30**, branch `module`, repo `/home/ubuntu/src/BinanceFuturesJava`.
Pre-reg: **`docs/prereg/PREREG_SHORT_FEASIBILITY.md`** (commit **`9c570e6f`**, chốt **TRƯỚC** mọi phép đo
mới; sau đó **không sửa thiết kế**). Script: `research/analysis/short_feas_reverse.py` (P1),
`research/analysis/short_feas_proxy.py` (P2/P3). Output: `docs/result/RESULT_SHORT_FEASIBILITY.json`.
**CHỈ ĐỌC + 0-sim** · **KHÔNG sửa `.java`** · **KHÔNG chạm production/242/ONNX/LIVE** · **không push
file dữ liệu** · **DEV ≤ 2025-12-31** (không chạm 2026).

---

## 0. KẾT LUẬN (một dòng)

> **NO-GO.** Cả hai cổng GO đều **FAIL**: **G1** — đảo chiều tại đúng điểm vào của `G2` cho
> `net_short = −102 173 USDT` (so sổ long **+96 909 USDT**), **win% short 14,1 %**;
> **G2** — không decile nào của S1 đạt ngưỡng (decile âm nhất **−0,0898 %/24h** ≫ ngưỡng
> **−0,2098 %**), và dấu còn **lật theo năm** (2022 −0,43 % vs 2023 +0,27 %). Không có cửa nào ở
> carry / down-signal / rank-short / reverse-gate. **Đóng hướng short** cho tới khi có **DATA MỚI**
> (liquidation / L2 / fill thật).

---

## 1. INVENTORY — mọi thứ đã thử trên chiều SHORT / tín hiệu "giảm"

| # | Hướng | Cái gì đã thử | Kết quả (số + commit) | Đã kết luận |
|---|---|---|---|---|
| (i) | **Carry / funding** | Short top-decile funding (V1 pure / V2 filter chống squeeze / V3 dollar-neutral), 8h, 627 sym, 2021–2025 | `RESULT_SHORT_CARRY.md` (`edd1e70`): thu funding thật **+0,0251 %/chu kỳ** (85,0 % kỳ dương) nhưng cost **0,1599 %/chu kỳ** ⇒ **cost/gross = 810 %**; net V1 **−0,1402 %**, V3 −0,1127 %, V2 −0,3751 %; CI72h×1,21 **ngoài 0 phía ÂM** | **NO-GO** (âm có ý nghĩa; "đổi phía không lật được kết quả") |
| (i′) | Carry (probe code) | `CarryEdgeProbe.java` (probe read-only cross-sectional dollar-neutral, 2026-07-10) | `docs/archive/.../STRATEGY_CONSOLIDATED.md` §B.7: "**carry đã loại**, tham khảo pattern" | **LOẠI** |
| (ii) | **Hedge overlay** | Overlay short BTC (counterfactual, beta rolling causal) trên sổ long T170 | `RESULT_HEDGE_OVERLAY_A.md` (`03c037e`): **NULL** — hedge triệt được beta (`r²` 0,0312→0,0015) nhưng **ICC tăng 4,3×**, maxDD −11,84 %→−17,32 %, UW 92→266, hard-year 5/5→3/5; kể cả beta hằng in-sample vẫn không đạt c1/c4 | **NULL**; khuyến nghị **KHÔNG làm Phương án B** |
| (iii) | **Tín hiệu DOWN** | `BIG_UP` / `MEDIUM_UP` / `MEDIUM_DOWN` (code cũ `157cf4d`) + `BIG_DOWN_OLD` tham chiếu | `RESULT_BIGUP_MEDIUPDOWN.md` (`5102899`): cả 3 level **NO-GO** — 52–81 % fire **trùng MOM15**, phần độc lập edge ≈ 0 (p 0,52–0,81); DEV CI chứa 0; sign-flip 2022 âm | **NO-GO cả 3** |
| (iii′) | DOWN (bounce) | Reversal-bounce long (tổng quát `isBtcTrendReverse`), ngưỡng cố định | `RESULT_REVERSAL_BOUNCE.md` (`a68dc88`): DEV net **−0,080 %** (CI chứa 0, p=0,35); %coin+ 38,3 %; sign-flip 2025 âm | **NO-GO** |
| (iii″) | DOWN (detector) | 4 detector "pump xong chuẩn bị dump" (6 feature) trên 1089 lệnh | `RESULT_PUMPDUMP_DETECT.md` (`f22bae0`): cả 6 feature **NULL**; lọc "extension cao" **cắt đúng nguồn lời** (PnL ròng âm phần lớn nguồn) | **NULL** |
| (iii‴) | DOWN (alt waves) | "pump rồi dump" / alt đi xuống dài hạn | `RESULT_ALT_REGIME_WAVES.md` (`b0e91fa`): A1/A2 ✅ (alt âm h365; excess kurt **+370/+1964/+878**) nhưng **A3 ❌** — "7 ngày +30 % rồi 30 ngày âm" 61,60 % ≈ nền 60,42 %, CI chứa 0 | **ĐÚNG MỘT PHẦN** (hình dạng, không phải tín hiệu) |
| (iv) | **Khả năng engine** | Đường SELL trong sim | `SimulatorMarketLevelTicker1MStopLoss.java:375` — `{ // co ENABLE_SHORT da go 2026-09-03 (long-only) }`; entry `OrderSide.BUY` (`DetectEntrySignal2TradeNormal.java:795,1101`); 7 call `createOrderBUY`; 20 file Java tham chiếu `OrderSide.BUY`; `OrderTargetInfoTest.computeFundingOnClose` dấu funding cho `SELL` còn **DRAFT + REVIEW-POINT** (2026-07-18) | **LONG-ONLY** ⇒ đổi short = **sửa CODE**, không phải config |

**Kết luận inventory:** mọi hướng short/funding/down đã thử đều **NO-GO/NULL**; engine **không có đường SELL**.

---

## 2. P1 — ĐẢO CHIỀU TỪ THẾ (proxy; nói rõ là XẤP XỈ)

Nguồn: `G2ART = /home/ubuntu/kaggle_sim/out/de-p1` (`result.json`: n **2517**, equity 35 000 → **131 908**,
jar sha256 `7368be46…`, profile `r4_kg0_k16_f015_g155` + GDV2 gate). Tập lệnh long đã đóng: `storage/printDone.csv`.

- `Σ pnl_long = +96 908,9 USDT` (`Σ funding = −1 420,5` ⇒ sổ long **thu ròng** funding, khớp `RESULT_FUNDING_SIGN`).
- Mirror: `ret_short_price = −ret_long_price`; `ret_long_price = tp/entry−1`, mean **+4,477 %**/lệnh,
  win long **85,9 %**.
- Chi phí (khóa): `fee_rt = 2×0,000982×Σnotional = 4 927,9`; `slip_rt = 336,2` (`Σnotional = 2 509 118`).
- **`net_short = −Σpnl_long − fee_rt − slip_rt = −102 173 USDT`**; **win% short = 14,1 %**
  (chỉ 14,1 % lệnh có giá giảm).

| Năm | n | `pnl_long` | `net_short` (ước) |
|---|---|---|---|
| 2021 | 434 | +6 486 | −6 959 |
| 2022 | 423 | +4 609 | −5 087 |
| 2023 | 527 | +24 918 | −25 933 |
| 2024 | 599 | +30 842 | −32 393 |
| 2025 | 534 | +30 054 | −31 801 |

⇒ **Đảo hướng được/âm ở CẢ 5 năm**. Cơ chế: `G2` **mua-đáy** (vào khi 15m momentum giảm), giá
sau đó **bật lên** (mean +4,48 %) ⇒ bán khống vào đúng các điểm đó là **âm đối xứng + trả thêm phí**.

> ⚠️ **XẤP XỈ (ghi rõ theo pre-reg §3 P1):** mirror tại **cùng giá thoát** KHÔNG tái tạo được
> trailing/stop-loss path-dependent của short; đây là **đối chứng đảo dấu**, không phải short live.
> Nhưng nó đủ mạnh để bác G1 vì biên quá lớn (−102 k vs ngưỡng > 0).

**Cổng G1: FAIL** (`net_short = −102 173 < 0`).

---

## 3. P2 — ĐẢO GATE (S1 score: short ở decile cực trị)

Nguồn: `S1PANEL` (`pred_s1a2x1.parquet`, 6 573 909 dòng) × `CLOSES_1H.bin` (snapshot 1h, `min_n=10`,
decision ≤ 2025-12-31). `s1 = −score`; decile **0** = s1 thấp nhất (bị S1 xếp "tệ nhất"),
decile **9** = s1 cao nhất (= long pick của selector). n = **10 307 664** dòng, s1 non-null 9 267 327.

**IC tự tính lại** (giải mâu thuẫn dấu trong `RESULT_S1_RANK_QUALITY`): `Spearman(s1, ret)` mean
**−0,02465 / −0,04065 / −0,06932** ở 1h/4h/24h — **khớp** doc cũ (cùng dấu, cùng bậc).

**Mean forward return theo decile (%/horizon):**

| h | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1h | −0,0043 | −0,0038 | −0,0011 | −0,0019 | −0,0004 | −0,0025 | −0,0007 | −0,0036 | −0,0021 | **+0,0081** |
| 4h | −0,0074 | −0,0071 | −0,0042 | −0,0059 | −0,0025 | −0,0082 | −0,0048 | −0,0115 | −0,0128 | **+0,0080** |
| 24h | −0,0330 | −0,0385 | −0,0253 | −0,0328 | −0,0226 | −0,0450 | −0,0298 | −0,0774 | **−0,0898** | **+0,0245** |

- **Decile âm mạnh nhất = d8 (−0,0898 %/24h)** — vẫn **nhỏ hơn 2,3 lần** ngưỡng chi phí
  `−(fee_rt+slip_rt) = −0,2098 %`.
- **Dấu lật theo năm** (d8, 24h): 2022 **−0,431 %**, 2023 **+0,268 %**, 2024 **+0,077 %**, 2025 **−0,278 %**
  ⇒ âm chỉ **2/4 năm** (yêu cầu ≥3/4). (2021 chỉ ~24 snapshot S1 ⇒ bỏ, ghi rõ.)
- d9 (long pick) **dương** ở 3/4 năm (trừ 2022) — quán tính "momentum/tail pump" của nhóm điểm cao.
- **Mâu thuẫn nội tại giữ lại làm hạn chế:** decile **mean** (d9 dương cao nhất) ngược dấu `rank_ic`
  (âm) — vì `rank_ic` là **rank-based** (bền đuôi) còn mean decile bị **đuôi phải** chi phối
  (cùng hiện tượng đã ghi ở `RESULT_S1_RANK_QUALITY` và `RESULT_PUMPDUMP_DETECT`). **Không đổi kết luận:**
  mọi decile đều **|mean ret24| ≤ 0,09 % ≪ cost 0,21 %** ⇒ dù đọc theo dấu nào cũng **không có cửa short**.

**Cổng G2: FAIL** (không decile nào đạt ngưỡng; thêm nữa không bền theo năm).

---

## 4. P3 — ĐỐI CHIẾU CHI PHÍ (nhắc lại, không đo lại)

| Mốc | Số | Nguồn |
|---|---|---|
| `fee_rt` (G2) | **0,1964 %**/vòng | `SIM_RATE_FEE=0,000982`×2 (config) |
| `slip_rt` | 0,0134 %/vòng | `SIM_SLIPPAGE_RATE=0,000067`×2 |
| Carry short gross (funding thu) | +0,0251 %/chu kỳ 8h | `RESULT_SHORT_CARRY` §3.1 |
| Carry cost | 0,1599 %/chu kỳ ⇒ **cost/gross 810 %** | idem |
| Long top-K funding nhỏ nhất (K=5/10/20) | −0,2223 / −0,1709 / −0,1460 %/chu kỳ | `RESULT_FUNDING_TOPK_ROTATE` §0 |

⇒ Chi phí (fee+slip+funding) **luôn lớn hơn mọi gross short đo được 1–2 bậc độ lớn**.

---

## 5. TRẢ LỜI (4 câu, bắt buộc)

### (1) Short có cửa KHÔNG (theo proxy)? — **KHÔNG.**
- **Carry**: đã đo, NO-GO (thu +0,0251 % vs cost 0,1599 %/chu kỳ; cost/gross 810 %).
- **Down-signal** (BIG_UP/MEDIUM_DOWN/BIG_DOWN_OLD/reversal-bounce/pump-dump): tất cả NO-GO/NULL.
- **Rank-short** (P2): cửa hẹp nhất là decile 8 với −0,0898 %/24h — **không đủ** so cost 0,2098 %; và lật dấu theo năm.
- **Reverse-gate** (P1): đảo chiều tại điểm vào `G2` = **−102 173 USDT** (âm cả 5 năm).
- **Hedge** (short BTC overlay): NULL (ICC tăng 4,3×).

### (2) Chi phí BUILD nếu muốn thử nghiệm tử tế — **cao, không có cơ sở hoàn vốn.**
- **Code**: dựng lại **đường SELL** đã gỡ 2026-09-03 (`SimulatorMarketLevelTicker1MStopLoss.java:375`),
  đổi/ bổ sung entry `OrderSide.BUY` → SELL (`DetectEntrySignal2TradeNormal.java:795,1101`),
  **7 call site `createOrderBUY`** trong sim, **20 file Java** tham chiếu `OrderSide.BUY`.
- **Kế toán margin/liquidation/borrow** cho chân short (chưa có; `OrderTargetInfoTest.computeFundingOnClose`
  dấu funding cho `SELL` còn **DRAFT + REVIEW-POINT** — phải chốt dấu trước khi tin bất kỳ số nào).
- **Pred/gate riêng cho short**: cần dataset + train + gate mới (0-sim proxy đã cho thấy **không có tín hiệu**;
  build pred trước rồi mới thấy không có edge = đốt thời gian).
- Ước lượng tối thiểu (từ `RESULT_HEDGE_OVERLAY_A` §7.1 khi bàn Phương án B): **647–890 dòng Java** thay đổi
  chạm `equityNow()`/`marginRunning` — rủi ro **phá parity `md5`** ngay cả khi short OFF. ⇒ **float cost ≫ 0 expected payoff.**

### (3) Rủi ro CẤU TRÚC của short — **lệch xấu (squeeze) + funding + borrow.**
- **Squeeze / đuôi phải (đo được, `RESULT_SHORT_CARRY` §5)**: MAE p99 **+20,38 %**, max **+602,21 %**
  (`ALPACAUSDT` 2025-04-30); ~**1,04 %** vị thế bị **+20 % ngược chiều trong 1 chu kỳ 8h** — so gross kỳ vọng
  cả chu kỳ chỉ **+0,02 %** ⇒ rủi ro ≈ **10⁴ × lợi nhuận kỳ vọng**.
- **Đuôi dày alt (`RESULT_ALT_REGIME_WAVES`)**: excess kurtosis **+370,9 / +1964,0 / +878,3** (1d/7d/30d),
  skew dương lớn ⇒ cực trị "pump" thường trực.
- **Funding (quy ước đã kiểm 2 tầng, `RESULT_FUNDING_SIGN`)**: `rate>0` ⇒ **long trả / short thu** — nhưng
  **80,6 %** kỳ (DEV) chỉ **+0,5 bp** median; "thu ròng" của sổ long là **sự kiện episode** (FTX = 51,6 % mean),
  **2024 đổi dấu**. Short đối xứng ⇒ **cùng bất định**, không phải nguồn ổn định.
- **Borrow/liquidation**: dữ liệu hiện tại (close 1h/1m + funding) **không** mô hình được ⇒ **không đo được**
  rủi ro chính của short. Đây là lý do cần DATA MỚI.

### (4) KẾT LUẬN DỨT KHOÁT: **`NO-GO`**
- **G1 FAIL**: `net_short = −102 173 USDT` (sổ long +96 909), win% short **14,1 %**, âm **cả 5 năm**.
- **G2 FAIL**: decile âm nhất **−0,0898 %/24h** ≫ ngưỡng **−0,2098 %**; dấu lật năm (2/4).
- Không có biến thể nào dương ⇒ **không có "unconfirmed"/post-hoc** cần xử lý.
- ⇒ **ĐÓNG HƯỚNG SHORT** cho tới khi có **DATA MỚI** (liquidation feed / orderbook L2 / fill thật).
  Dữ liệu hiện có (close + funding) **đủ để kết luận NO-GO**, nhưng **không đủ** để *chứng minh* short
  có thể sống trong điều kiện khác — nên ghi là **NO-GO trên dữ liệu hiện có**, không phải "short bất khả".

---

## 6. Giới hạn (nói rõ)

1. **P1 là đối chứng đảo dấu**, mirror tại **cùng giá thoát**; trailing/SL path-dependent của short
   **không** tái tạo được. Biên (−102 k vs +97 k) quá lớn để đảo verdict, nhưng đây **không** phải short live.
2. **P2 dùng snapshot 1h** (không phải nhịp ra quyết định thật của sim), và **S1 ≠ selector chạy live** —
   chỉ là proxy xếp hạng.
3. **Mâu thuẫn dấu `rank_ic` vs decile mean** giữ nguyên (rank-based bền đuôi vs mean bị đuôi phải chi phối);
   đã nêu, và **không** ảnh hưởng kết luận (mọi |mean| ≪ cost).
4. **2021 trong P2** chỉ ~24 snapshot S1 ⇒ loại khỏi kiểm bền (ghi rõ, không chọn theo kết quả).
5. **Không** mô hình margin/liquidation/borrow ⇒ mọi kết luận về short là **cận trên lạc quan**;
   thực tế sẽ **xấu hơn**.

---

## 7. Sản phẩm + tuân thủ

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_FEASIBILITY.md` | chốt trước (commit **`9c570e6f`**) |
| `docs/result/RESULT_SHORT_FEASIBILITY.md` | file này |
| `docs/result/RESULT_SHORT_FEASIBILITY.json` | số tổng hợp (nhỏ) |
| `research/analysis/short_feas_reverse.py` | P1 (`33cea407`) |
| `research/analysis/short_feas_proxy.py` | P2/P3 (`33cea407`) |
| `research/analysis/out/short_feas_reverse.json`, `out/short_feas_proxy.json` | output script |

- 0-sim, thuần Python, **không chạy Java trên Oracle**, **không sửa `.java`**, không `claude-run`.
- **DEV ≤ 2025-12-31**; không chạm 2026.
- Không push file dữ liệu (chỉ `.md`/`.py`/`.json` tổng hợp).
