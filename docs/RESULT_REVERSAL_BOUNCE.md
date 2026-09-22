# RESULT_REVERSAL_BOUNCE — đo edge "reversal-bounce long" (tổng quát hóa `isBtcTrendReverse`)

Ngày: 2026-09-22. Pre-reg: `docs/PREREG_REVERSAL_BOUNCE.md` (commit `a68dc88`, chốt TRƯỚC khi chạy).
Script: `research/analysis/reversal_bounce.py` (sinh tín hiệu) + `reversal_bounce_stats.py` (đo).
0-sim, thuần Python, không Java, không push. DEV + đối chiếu 2021/2025; **KHÔNG chạm HOLDOUT 2026.**

**KẾT LUẬN: NO-GO.** (edge OOS sau phí ≤ 0, không ổn định, %coin+ < 50%.)

---

## 1. Nguồn dữ liệu + định nghĩa trigger (đã chốt ở pre-reg)

- **Nguồn 1M closes:** Aerospike set `kline_1m_opt` (127.0.0.1:3222), key `YYYYMMDD-HHMM`,
  value = protobuf nén Snappy `{symbol: [O,H,L,C,Usdt]}` per-phút — cùng nguồn BD/MOM15. Đọc thuần
  Python (`aerospike` + `cramjam`), đã extract san thành `raw/<sym>.f32` (627 symbol, 619M dòng,
  2021-01-01..2025-12-31 UTC). **Causal**: chỉ dùng nến đã đóng.
- **Trigger (1 ngưỡng CỐ ĐỊNH, không vòng lặp nới ngưỡng):**
  - Mốc 15m-aligned `j` (`epoch_min % 15 == 14`); `drop(j) = min(close/max15m−1, close/max30m−1)`
    với `max15m=max(high[j−14..j])`, `max30m=max(high[j−29..j])`.
  - `drop(j) <= −0.01` (DROP_THRESH = 1%) ⇒ chân giảm; `priceReverse = open[j−14]`.
  - **Fire** tại nến đầu tiên `t > j` có `close[t] > priceReverse` (vượt mốc đáy-đảo).
  - Universe: 627 USDT perp (gồm coin delist — không lọc survivorship). HOLD cố định 24h.
  - Khác biệt ghi rõ: dùng **max cửa sổ 15/30m** (code gốc dùng high nến đơn — REVIEW gắn cờ mong manh).
- **Chi phí:** taker 0.05%×2 + slip 0.5×range-1m + funding (Aerospike `funding_data`).

---

## 2. Kết quả edge

| Mẫu | N | meanNet | meanRaw | winrate | CI72h | p(mean>0) |
|---|---|---|---|---|---|---|
| ALL 2021-2025 | 3 785 409 | **+0.003%** | +0.31% | 46.1% | [−0.252%, +0.252%] | 0.513 |
| **DEV 2022-01..2024-06** | 1 179 302 | **−0.080%** | +0.22% | 46.8% | [−0.449%, +0.269%] | 0.353 |

- Raw edge thô (+0.31%) **bị chi phí ăn hết** (fee 0.10 + slip ~0.24 + funding) → net ≈ 0.
- **DEV (cửa sổ trọng điểm) net ÂM** (−0.08%). CI block-72h chứa 0; `p(mean>0)=0.35`.
- **Null test** (block sign-flip 72h, seed 20260905): `p(obs)=0.49` — không khác 0.
- CI x1.21 (theo yêu cầu task): ALL = [−0.302%, +0.307%]; DEV = [−0.515%, +0.355%]. (Ghi chú: theo
  `AUDIT_CI_INFLATE_STANDARDIZATION`, 1 ứng viên đơn ⇒ `inflate(1)=1.0`; x1.21 là legacy — báo cả hai.)

### Decay theo năm (sign-flip, KHÔNG ổn định)

| Năm | N | meanNet | p(mean>0) |
|---|---|---|---|
| 2021 | 598 709 | +0.59% | 0.97 |
| 2022 | 438 037 | **−0.43%** | 0.11 |
| 2023 | 368 727 | +0.16% | 0.79 |
| 2024 | 845 383 | +0.21% | 0.78 |
| 2025 | 1 534 553 | **−0.26%** | 0.14 |

Edge đảo dấu theo năm; năm gần nhất (2025) ÂM. → không có edge ổn định.

- **%coin+** = 38.3% (624/624 symbol có ≥1 trade, chỉ 38% dương) → < 50%, đa số coin thua.
- **Delisting** (trung thực, không lọc): short-delist N=3180 net **−0.53%** (raw −0.41%).

---

## 3. Overlap / ICC với MOM15 (điều kiện tiên quyết)

**MOM15** = breadth cross-sectional `rateDown15MAvg` = mean của 100 symbol sụt sâu nhất theo
`close/max15m − 1` (SURVEY §1; `getMarketStatus1M`). "MOM15 fire" = `rateDown15MAvg < −0.028`
(= `SMALL_DOWN_15M`, bản live). Tính từ chính `raw/*.f32` (175 268 mốc 15m, range [−0.581, 0.000]).

| Phép đo | Kết quả |
|---|---|
| % fire lúc MOM15 fire (<−0.028) — tầng phút (breadth) | **0.92%** (34 771 / 3 785 409) |
| % fire lúc MOM15 im | **99.08%** |
| % fire rơi vào ngày MOM15 có giao dịch (printDone C2b DEV) | **7.8%** (quiet **92.2%**) |
| fire trùng (symbol, ngày) với lệnh MOM15 | **0.00%** |
| ICC(net_ret) theo ngày / theo episode 72h | **0.156 / 0.057** |

⇒ Về **thời gian/pha**, reversal-bounce **ĐỘC LẬP MOM15** (fire 99% lúc MOM15 im, 0% trùng
symbol+ngày, ICC episode thấp). Điều này **phủ định** prior "co-clustering" của pre-reg (CAVEAT
của SURVEY) — trên dữ liệu thật, nó không cụm vào các đợt selloff MOM15 giao dịch.

**NHƯNG** — phát hiện quan trọng (descriptive, hậu kiểm, KHÔNG phải kết luận pre-reg):

| Tập con | N | meanNet | winrate | CI72h |
|---|---|---|---|---|
| fire lúc MOM15 **im** (99.1%) | 3 750 638 | **−0.030%** | 46.0% | [−0.29%, +0.22%] |
| fire lúc MOM15 **fire** (0.92%) | 34 771 | **+3.56%** | 58.5% | [+1.94%, +5.58%] |

Toàn bộ edge dương tập trung vào **0.92% fire lúc MOM15 đang fire** (selloff toàn thị trường) —
đúng lúc nó **KHÔNG** còn là cược độc lập (chính là regime dip-buy mà MOM15 đã giao dịch). Phần
99% fire "độc lập" (MOM15 im) có net ≈ 0. ⇒ **độc lập về timing nhưng không có edge ở phần độc lập.**

---

## 4. Gate GO/NO-GO (PREREG §6)

| Điều kiện GO | Kết quả | Đạt? |
|---|---|---|
| `mean(net_ret) > 0` trên DEV, CI loại 0 | DEV −0.08%, CI chứa 0, p=0.35 | **KHÔNG** |
| ICC theo episode đủ thấp | 0.057 (72h) — thấp | có |
| Overlap MOM15 thấp (fire ngày MOM15 im) | 99% im — nhưng phần im có edge ≈ 0 | có về timing, **không** về edge |

**→ NO-GO.** Không đạt điều kiện edge OOS > 0 sau phí (DEV net âm; toàn bộ mẫu ≈ 0; sign-flip theo
năm; %coin+ 38%). Không thêm biến thể, không đổi ngưỡng, không nới cửa sổ (chống leak L2).

**Ý nghĩa:** lead "độc lập nhất còn lại" trong SURVEY (`BTC_TREND_REVERSE` tổng quát) khi đo bằng
ngưỡng cố định (không FIT) cho thấy **edge bounce thô bị chi phí ăn trọn** và **không ổn định**.
Về mặt độc lập thì reversal-bounce thật sự không trùng MOM15, nhưng phần độc lập đó lại vô edge.
→ đóng hướng "reversal-bounce như alpha độc lập"; không có cược mới nào từ nhánh này (power-wall).

---

## 5. Ràng buộc tuân thủ

- Không `claude-run`/Claude Code; không Java trên Oracle (toàn bộ thuần Python đọc Aerospike +
  đo trên `raw/*.f32`). Không push. HOLDOUT 2026 không đụng (data chặn ≤ 2025-12-31).
- Pre-reg commit `a68dc88` có TRƯỚC khi chạy; sau khi chạy không sửa thiết kế (trigger/ngưỡng/HOLD).
- File tạm (signals.csv, rd15_*.npy, logs) nằm ngoài git, sẽ dọn.
