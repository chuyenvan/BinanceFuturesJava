# OVERNIGHT BRIEF — 2026-07-12 (đọc sáng)

## KẾT LUẬN ĐIỀU TRA TẦN SUẤT (số thật, data sạch)

**Thủ phạm chính = CIRCUIT BREAKER margin** (config drift June-27 → nay):
- `BREAKER: OFF→MARGIN@0.50` (commit 3041257, 28-06) + `OFF_FLAT_HARD false→true` + gene `MIN_MOMENTUM_15M` range cấm vùng 0.010-0.020.
- **Xác nhận bằng sim breaker OFF (C_JUNE):** PREDICT lệnh 4,460 (baseline) → **31,667** (breaker OFF) ≈ đúng June (35,406). → breaker LÀ cái cap tần suất.

**NHƯNG breaker OFF = gần cháy:** C_MAXFAV3 breaker-off maxDD unPMin **−26,134 (~−75%)**; C_RET2WF −13,023 (~−37%). Đúng lý do breaker được thêm (chống ruin). → **không thả hẳn được.**

**Selector vẫn yếu (mọi cấu hình):** PREDICT_SYMBOL_TRADE âm khi nới (maxfav3 −21,109 / ret2 −2,958); lãi do **DCA** cõng (+12.8k/+20.2k). **ret2 > maxfav3 nhất quán** (balance 53,560 vs 45,168; PREDICT ít âm hơn). → edge thật = DCA (mean-reversion), selector thứ yếu; nếu chọn thì ret2.

## ⚠️ LỖI RIÊNG CHƯA GIẢI THÍCH (cần soi sáng)
**BIG_DOWN 159 lệnh (June) → 12 (nay), breaker OFF KHÔNG khôi phục.** Vậy BIG_DOWN không do breaker. Nghi: sau ghost-clean/survivorship, basket `rateDownAvg` đổi → `rateDownAvg < MS_DOWN_BIG_AVG(-0.03157)` hiếm kích hoạt; hoặc logic detect BIG_DOWN đổi. → điều tra: so `MarketBigChangeDetector.getMarketStatus1M` + cách tính rateDownAvg June vs nay.

## ĐANG CHẠY OVERNIGHT (WFO cả 2 model, data sạch)
`wfo_freqfix.sh` (PID `wfo_freqfix.pid`), tuần tự maxfav3 → ret2wf, config **loosen-có-kiểm-soát**:
- BREAKER 0.70 (nới từ 0.50, không thả hẳn để chặn ruin) + OFF_FLAT_HARD=false (env) + gene MIN_MOMENTUM_15M nới [0.010,0.045] (cho HPO chọn tần suất cao) + NUMBER_ORDER_BUDGET=100 (size/lệnh nhỏ hơn).
- WFO KHÔNG dùng fitness-cache → không dính bug CONFIG_VERSION. Data = wfo_ds_{maxfav3,ret2wf}_4h (gate-fixed, đã validate).
- **Sáng đọc:** `~/claudedata/wfo_freqfix_summary.txt` + `wfo_report_freqfix_{maxfav3,ret2wf}.md` → %OOS-dương / WFE / maxDD / MIN_MOMENTUM HPO chọn (xem HPO có chọn vùng <0.020 không) / tổng trade. → chốt maxfav3 vs ret2 khi tần suất được nới + HPO tự cân DD.

## CÂU HỎI QUYẾT ĐỊNH (sáng)
1. WFO freqfix: nới phễu (breaker 0.70 + gene + budget) có tăng %OOS-dương/PnL vs baseline (11.8%/29%) mà DD ≤50%? → hyp B (siết oan, sửa được) hay vẫn FAIL (hyp A / trần).
2. maxfav3 vs ret2: cái nào thắng khi tần suất fair?
3. BIG_DOWN 159→12: bug thật cần sửa (điều tra rateDownAvg/basket).

## LỆNH KIỂM
```
ssh -i ~/.ssh/id_rsa_chuyennd ubuntu@161.118.212.3
cat ~/claudedata/wfo_freqfix_summary.txt
tail -40 ~/claudedata/wfo_freqfix.log
```
Monitor `brlaak3y5` báo khi xong.
