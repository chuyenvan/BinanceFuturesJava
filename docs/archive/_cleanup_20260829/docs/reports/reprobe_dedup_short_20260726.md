# REPORT — Reprobe DEDUP + Short-probe (2026-07-26)

> Đo lại selectability với **sửa overlap**, và đo **short bottom-decile**. Nguyên tắc "đo không đoán".
> Kernel: `chuyendinh/reprobe-unfiltered-wf-dedup`, `chuyendinh/short-probe-bottom-decile` (COMPLETE).
> Code repo: `ml/funding_selector/kaggle_reprobe_unfiltered/`, `ml/funding_selector/kaggle_short_probe/`.
> JSON: `D:\claudedata\reprobe_dedup\`, `D:\claudedata\short_probe\`.

## 1. Reprobe — overlap vs dedup (18 fold 2022Q1→2026Q2, unfiltered, f0..f39, no OI)

| mode | H | xsecIC med | IC posfrac | pooledIC | alpha med | alpha posfrac | net (sau flat cost) | spread top−bot | n_event top | n_indep |
|---|---|---|---|---|---|---|---|---|---|---|
| overlap | 4h | 0.187 | 18/18 | 0.204 | +0.0005% | 0.50 | −0.15% | ~0 | 113,269 | 427 |
| dedup   | 4h | 0.187 | 18/18 | 0.204 | −0.009%  | 0.39 | −0.16% | ~0 | 12,984  | 427 |
| overlap | 12h| 0.222 | 18/18 | 0.265 | +0.0025% | 0.50 | −0.15% | ~0 | 113,253 | 176 |
| dedup   | 12h| 0.222 | 18/18 | 0.265 | −0.022%  | 0.39 | −0.17% | ~0 | 5,854   | 176 |

**Kết luận:**
- **Overlap KHÔNG phải artifact của selectability.** Overlap thổi *số event* ~9–19× (113k → 6–13k) nhưng `xsecIC` gần như không đổi so với pooled (0.20→0.19, 0.27→0.22) và **18/18 quý dương giữ nguyên ở cả hai mode**. `n_indep` 176–427 cross-section độc lập/fold → độ ổn định là thật. (Giả thuyết ban đầu "18/18 bị thổi phồng" → BÁC BỎ.)
- **Endpoint vẫn không monetize:** alpha ~0 (dedup nhích âm, posfrac 0.50→0.39), **âm sau cost** (−0.15…−0.17%). WEAK cả 4.
- **Spread top−bottom ≈ 0** → biểu hiện long-short thuần không có edge ở endpoint.

## 2. Short-probe — bottom-decile pwin (event-level, SL-sim + cost)

| H | pnl sau SL med | posfrac | short_excess | short_ret_end | squeeze_frac | MAE med | winrate | VERDICT |
|---|---|---|---|---|---|---|---|---|
| 4h | −0.164% | 0/18 | +0.044% | −0.014% | 0.01 | 0.86% | 0.486 | **SHORT_NOT_VIABLE** |
| 12h| −0.174% | 1/18 | +0.126% | −0.023% | 0.06 | 1.62% | 0.493 | **SHORT_NOT_VIABLE** |

**Kết luận:** `short_excess` dương nhẹ (coin điểm thấp underperform universe ~0.04–0.13%) NHƯNG `short_ret_end` âm (median các coin đó vẫn **tăng nhẹ tuyệt đối** → short lỗ). "pwin thấp = tăng ít hơn, KHÔNG phải sẽ dump." Short cần downside tuyệt đối — không có. Squeeze không phải thủ phạm chính (frac 1–6%); thủ phạm là coin không giảm + mất phí. Short **NOT_VIABLE**. → củng cố quyết định KHÔNG thêm short-leg; bottom-decile chỉ dùng làm gate/diagnostic.

## 3. Rà soát code đo — lỗ hổng CÒN LẠI ngoài overlap

| # | Lỗ hổng | Mức độ | Hướng vá |
|---|---|---|---|
| A | **Fixed-horizon H ≠ variable-hold production.** Label giữ đúng H giờ từ anchor; production/WFO thoát bằng exit machine (trailing/time-stop → hold biến thiên). retEnd_H **về bản chất không khớp** cái production realize. | **Cao nhất** | Track A-lite (first-touch barrier maxFav/maxAdv/tHit) → Track A (path 1m). |
| B | Alpha core **không trừ cost/funding** (chỉ có net_alpha_crude flat 0.15%, funding vắng). | Cao | Bake cost+funding vào label/verdict (Track A-lite). |
| C | Benchmark = **mean toàn universe unfiltered** (gồm coin illiquid/không giao dịch được) → bench nhiễu, alpha đo so với chuẩn không tradeable. | Trung | Bench trên tập tradeable (lọc thanh khoản) hoặc dùng BTC/beta-adjust. |
| D | **Entry-timing dưới 15m không đo được** — anchor cố định 1 phase 15m; không biết vào phút 5 vs phút 8 khác ra sao. | Trung (cần 1m) | Track A (path 1m) + anchor-phase jitter test. |
| E | **maxFav/maxAdv là extreme cả cửa sổ, không path-ordered** → SL-sim short & first-touch proxy lạc quan/bi quan tuỳ ca. | Trung | Path 1m xác nhận thứ tự. |
| F | Cross-section mỏng giai đoạn sớm (ít coin) → top-decile vài coin, variance cao (đã lọc MIN_XSEC=10 nhưng vẫn ảnh hưởng đuôi). | Thấp | Report coins/ts; weight theo breadth. |
| G | Không fill/slippage model; retEnd giả định vào/ra tại close. | Thấp | Fill model ở Track A. |

Overlap đã vá (dedup). Leakage: purge H trước cut OK; không thấy leak train↔test. IC estimator đã đúng (xsec).

## 4. Câu hỏi 15m ↔ WFO/production + có nên "đo full đối chiếu"

Điểm mấu chốt Uni nêu (vào BTC phút 5 giữ 3h vs phút 8 giữ 27h) = **entry-timing + hold-length variability**. Reprobe dùng anchor 15m cố định + hold cố định H → là **PROXY**, không phải cái WFO/production làm (entry theo signal, hold theo exit machine). Vì vậy:

- **Không kỳ vọng reprobe endpoint tương quan chặt với WFO realized** (scar: "backtest-lite không transfer sang Java WFO"). WEAK-at-endpoint KHÔNG tự kết tội chiến lược; nó chỉ nói "endpoint cố định không phải cách monetize".
- **"Đo full đối chiếu" đúng nghĩa = correlation test 3 tầng** trên CÙNG tập event top-decile:
  1. fixed-H endpoint (đã có),
  2. Track A-lite first-touch barrier (variable hold + cost),
  3. một slice Java WFO thật (ground truth exit machine).
  Nếu (2) tương quan (3) → harness Python tin được để iterate exit rẻ. Nếu không → chỉ Java WFO đáng tin (đắt). Đây là thí nghiệm quyết định "được phép iterate ở Python hay buộc ở Java".
- **KHÔNG nên** tốn công chạy lại reprobe ở nhiều anchor-phase sub-15m — cần 1m mới làm được, và nó không chạm gap lớn nhất (hold/exit). Ưu tiên Track A-lite.

## 5. Next (đề xuất)

1. **Track A-lite** (spec `SPEC_TRACK_A_LITE.md`): first-touch từ maxFav/maxAdv/tHit + trừ cost/funding, trên top-decile dedup. Trả lời go/no-go monetize.
2. **Correlation test** (mục 4): thêm 1 slice Java WFO đối chiếu Track A-lite → quyết định iterate Python vs Java.
3. Nếu Track A-lite net-âm mọi exit → đóng nhánh entry-alpha thật. Nếu dương → build path 1m (Track A) + relabel selector theo exit đó.

=== RESULT ===
STATUS: REVIEW
VERDICT: selectability THẬT (18/18, không phải overlap artifact); endpoint WEAK confirmed; long-short spread~0; short NOT_VIABLE.
NEXT: Track A-lite + correlation test 3 tầng (endpoint / A-lite / Java WFO slice).
=== END ===
