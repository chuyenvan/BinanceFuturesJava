# PREREG_SHORT_REGIME — SHORT + TÍN HIỆU REGIME THẬT (0-sim trước)

Chốt: **2026-10-01**, branch `module`. Commit **TRƯỚC** khi đo; sau đo KHÔNG sửa thiết kế.
Nền: `RESULT_SHORT_PATHEXIT_PSOFT` (`05169026`) — gate `predRisk4H` FAIL cả 2 hướng; nay thử
**regime TỰ DỰNG từ dữ liệu giá**.

## 1. Ràng buộc
DEV ≤ 2025-12-31 · không `.java`/ONNX/242/LIVE · không push dữ liệu · chỉ `git add` file của mình ·
**0-sim trước** (chỉ chạy sim 1m nếu cắt đuôi RÕ).

## 2. Pick + đo (0-sim)
- Pick = **`PA_t15_E10_S42`** (bins Kaggle `sm-pathexit` có sẵn), **top-8/tick**; (P-soft `sm-pw` bins
  không có local ⇒ dùng P-hard proxy; SL-rate 11,6 % khớp số owner nêu).
- Thoát = **LABEL-exit TP −1,5 % / SL +10 %** tính từ nhãn `.pb` (`maxAdv/maxFav/tHit`, first-hit xấp xỉ).
- Chi phí: fee **0,112 %**/vòng + funding **pro-rata −0,585 %·(h/72)**. CI block-72h (2000 rep, seed 20260905, ×1,21).

## 3. Regime "DOWN" — 5 biến thể **CỐ ĐỊNH** (không quét mũ)
Từ `CLOSES_1H.bin` (causal, close nến ≤ ts):
`R1` BTC dưới SMA200 **và** ret30d<0 · `R2` breadth (tỷ lệ coin ret7d>0) < 0,40 ·
`R3` R1 **và** breadth<0,50 · `R4` BTC drawdown từ đỉnh 90d < −20 % · `R5` R1 **và** vol7d>median.
Chỉ vào short khi regime = DOWN.
⚠️ **Funding-aggregate BỎ ở 0-sim** (không có nguồn funding toàn-sàn DEV rẻ local); ghi rõ + thêm ở bước sim nếu qua.

## 4. Chỉ số + luật
Báo: **SL-rate** (so baseline 11,6 %), **net**, **CI95**, **theo năm 2022–2025**, **tail** (`max_loss`/p01),
**n**. **GO** chỉ khi tồn tại 1 biến thể đạt: net **> 0 ngoài CI** (raw **và** ×1,21) · ≥3/4 năm dương ·
SL-rate **≤ 0,6×** baseline. Nếu **> 1** biến thể đều GO ⇒ nghi **overfit**.
Ngược lại ⇒ **NULL** (chốt đóng hướng short).

## 5. Sản phẩm
`research/analysis/short_regime_0sim.py` · `docs/result/RESULT_SHORT_REGIME.md` (+`.json`).
