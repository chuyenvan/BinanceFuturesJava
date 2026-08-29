# Trailing gap gate→pred: Tier-2 path-replay (whipsaw-aware) — 2026-08-20

## Setup
Replay tick-trailing trên PATH 5m THẬT (fetch Binance fapi klines 5m, 4h/entry), N=4524 entry **arm-eligible (maxFav_4h≥5%)** 2022-2025 (chỉ nhóm này policy khác nhau). Peak theo bar-high; SL bị test bởi bar-low mỗi bar → **BẮT được chi phí whipsaw** (gap chặt bị quét oan bởi low intra-bar). So GATE (coin-blind, luôn strong) vs PRED (selector B015 4h prob, weak theo percentile) vs **RAND** (control, weak ngẫu nhiên cùng tỉ lệ). Lưới trange: arm{5..26}%, ratio{.3,.5,.7}, maxgap{.05,.08,.12}, cut{p25,p40,p50}. Scripts: /tmp/tjoin.py, tfetch.py, treplay.py; data /home/ubuntu/tpaths/, claudedata/tsample.csv.

## KẾT QUẢ
best pnl: GATE=296.0, PRED=300.6 (+1.5%), RAND=299.5. best-cell PRED vs RAND = +0.3% (ở arm cao).
**Matched-by-arm PRED−RAND (skill THẬT, whipsaw-aware):**
| arm | GATE | PRED | RAND | P−G | P−R | P−R % |
|---|---|---|---|---|---|---|
|0.05|205.2|208.9|202.2|+3.7|**+6.7**|+3.3%|
|0.075|248.8|254.6|244.6|+5.8|**+10.0**|+4.1%|
|0.10|269.6|277.5|269.9|+7.9|+7.6|+2.8%|
|0.125|279.2|288.9|282.4|+9.7|+6.5|+2.3%|
|0.15|284.9|294.0|289.5|+9.1|+4.5|+1.5%|
|0.20|292.4|300.2|297.3|+7.8|+2.9|+1.0%|
|0.26|292.1|297.7|295.9|+5.6|+1.8|+0.6%|

## VERDICT (flaws-first, LẬT một phần Tier-1)
- **Khác Tier-1**: khi mô hình whipsaw, PRED−RAND KHÔNG còn ~0 — nó **DƯƠNG và đáng kể ở arm thấp** (+3–4% tại arm 5–10%), giảm dần về ~0 ở arm cao. Nghĩa là selector THẬT SỰ route gap chặt đúng phần coin (tránh whipsaw coin chạy tiếp, siết coin đảo). Tier-1 (xấp xỉ summary) đã CHE mất điều này → bài học: summary không đủ, path replay là cần.
- **Nhưng modest + phụ thuộc arm**: edge mạnh nhất ở arm thấp (~+3-4%), teo về <1% ở arm cao. Không "ổn qua mọi arm". PRED không bao giờ THUA RAND (luôn ≥0) — điểm cộng.
- **Caveat quan trọng**: replay CHỈ nhóm winners (maxFav≥5%) → đo tác động lên EXIT của winners, KHÔNG đo downside-protection (losers không arm, giống nhau mọi policy) → không kết luận net-portfolio. pnl-best rơi vào arm CAO (0.2) là do winners-only (arm cao = không cắt winner sớm); trên full population arm cao = ít bảo vệ downside → tối ưu arm ở đây BỊ BIAS, đừng suy ra "dùng arm cao".

## KHUYẾN NGHỊ
Pred-gap là cải thiện **nhỏ nhưng thật**, và nó **cộng hưởng với hướng trange** (hạ arm từ 26% → 10-15%): đúng vùng arm mà trailing active VÀ pred có giá trị (+3-4%). Đề xuất: nếu làm, **gộp** (hạ arm 10-15% + pred-gap percentile-calibrated) thành 1 lần revamp trailing, test shadow. KHÔNG kỳ vọng win lớn (~+2-4% trên captured-profit của winners trailing-active). Nếu ưu tiên chắc chắn hơn, lever arm (26%→10-15%) một mình đã có tác động rõ và đơn giản hơn (không cần nguồn per-coin pred live).

## Wiring live (nếu duyệt) — cần
- Nguồn selector per-coin pred đọc được tại SL-move site (BinanceOrderTradingManager ~L286): hiện chỉ có market gate pred (getAiPredictionAtTime). Selector pred ghi file storage/predictionSymbol/<time> mỗi tick → cần reader by symbol.
- Đổi predReturn15M→selector pred trong calRateLossDynamicBuy; ngưỡng weak/strong = percentile selector (KHÔNG dùng literal 0.004). OrderTargetInfoTest mirror cho sim.
