# Gate A/B — VERDICT (WFO fanout leak-free, Kaggle) 2026-08-18

Pipeline: WFOGateRunner per-fold label → LoadWfoGatePred → set ai_pred_market_gate_ab_* → ExportWfoDataset
(predwf + WFO_SET_PRED) → Kaggle fanout 5 worker (K5/0.008/moveSL0.05/funding ON) → DONE_*.txt.
Window win4-15 = 2023-2025 (apples-to-apples). Pilot oldbasket validated ≈ canonical (win0-17≈18,345 vs ~18,440).

## BẢNG VERDICT gốc (lưới 15m G015, 4 nhánh)
| nhánh | TOTAL_12w (win4-15) | posRatio lenient | ghi chú |
|---|---:|---:|---|
| **gate-off (selector only, KHÔNG gate)** | **−2,779.3** | **39% (7/18)** | LỖ. Không gate = thảm hoạ |
| **oldbasket (max, = gate LIVE hiện tại)** | **+13,812.5** | **89% (16/18)** | **THẮNG** |
| ret60m (net) | +9,590.8 | 89% (16/18) | thua oldbasket |
| ret15m (net) | +7,519.9 | 83% (15/18) | thua nhiều nhất |

## BẢNG MATRIX 5m vs 15m (old=max vs net-all-market) — hoàn tất 2026-08-18 11:50
Aggregator gate_ab_metrics.py, slice win4-15 (12 window), CẢ HAI lưới đều đủ 18 window (win0-17) → apples-to-apples.

| nhánh | TOTAL12w | trades | worstDD% | meanCalmar | pos% | Sharpe | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| old @15m (max) | 13,795.6 | 2128 | 19.1 | 1.038 | 83% | 0.707 | 14.07 |
| net-all @15m | 7,579.8 | 319 | 13.0 | 0.933 | 83% | 0.603 | 25.27 |
| old @5m (max) | 12,659.7 | 1820 | 16.9 | 1.029 | 75% | 1.012 | 14.90 |
| net-all @5m | 4,492.3 | 200 | 1.8 | 0.999 | 75% | 1.042 | 999 (∞) |
| off | −2,779.3 | 8019 | 45.3 | 0.135 | 50% | −0.046 | 0.89 |

### Đọc bảng matrix
- **max (old) THẮNG total PnL trên CẢ HAI lưới** (12,660@5m, 13,796@15m). Net-all thua total ở cả hai.
- **Net thua total KHÔNG phải vì per-trade kém — mà vì VOLUME.** Ở threshold cố định 0.008, model label-net pass
  rất ít tín hiệu: net-all@5m chỉ **200 lệnh** vs old@5m **1820**; net-all@15m 319 vs old 2128. Đây KHÔNG phải
  matched pass-rate → gap total phần lớn là hiệu ứng số lệnh, không phải chất lượng.
- **Chất lượng per-trade của net rất tốt:** net-all@5m DD chỉ **1.8%** (vs old 16.9%), **PF ∞** (không có window âm),
  Sharpe 1.042 > old 1.012. Net-all@15m PF 25.3 > old 14.1. Net = "bắn ít, gần như không trượt".
- **Cross-grid:** lưới 5m Sharpe cao hơn hẳn 15m (old5m 1.01 vs old15m 0.71) nhưng total thấp hơn chút + pos% 75<83.
  5m sạch/nhanh hơn mỗi window; 15m gom total nhiều hơn.
- ⚠️ Caveat "5m chỉ 10-fold" trong ghi chú cũ **SAI** — kiểm lại report: cả hai lưới đều 18 window (win0-17).

## KẾT LUẬN (2 điều, cả 2 quan trọng)

### 1. GATE LÀ THIẾT YẾU — bỏ gate là LỖ. (lật ngược Phase 1)
Không gate (off) = **−2,779** với 39% window dương. Bật gate oldbasket → **+13,812**, 89% window dương —
swing **+16,591**. Gate là bộ lọc regime biến chiến lược từ LỖ thành LÃI. Component quan trọng NHẤT.

### 2. LABEL max (oldbasket) THẮNG total — net label bắn ít nhưng chất.
old 13,812 > net(ret60m) 9,590 > net(ret15m) 7,519, và matrix xác nhận lại: max > net-all trên cả 5m/15m về total.
Net-all cho DD/PF/Sharpe đẹp hơn nhưng total thấp do quá ít lệnh ở cùng threshold. Gate LIVE (fold_20 oldbasket)
ĐÃ là tốt nhất cho mục tiêu total PnL.

## ⚠️ TỰ SỬA: Phase 1 proxy (IC/cold-test) ĐÃ SAI/GÂY HIỂU LẦM
Phase 1 kết luận gate "không có edge" — **Test PnL thật lật ngược hoàn toàn.** Việc thật của gate KHÔNG phải rank
basket return mà là TRÁNH regime xấu nơi chiến lược (đòn bẩy/DCA/funding) chảy máu; IC market-level không bắt được.
Bài học: chấm gate bằng PnL sim đầy đủ, KHÔNG bằng IC/cold-test.

## KHUYẾN NGHỊ
- **KHÔNG đổi gate live.** Nếu mục tiêu là TOTAL PnL: gate hiện tại (oldbasket/max, threshold 0.008) là tốt nhất —
  cái tốt nhất ĐÃ đang chạy.
- **Net-all là "profile" khác, không phải thua:** nếu sau này muốn biến thể siêu bảo thủ (DD cực thấp, ít lệnh, PF∞)
  thì net-all là ứng viên — nhưng phải hạ threshold để match số lệnh mới so công bằng được. Chưa làm.
- Đòn bẩy cải thiện "ăn ít" nằm ở EXIT (moveSL 0.03→0.05 ĐÃ deploy live), KHÔNG ở gate label.
- Track2 gate label (total-PnL objective): ĐÓNG (max thắng). Mở tuỳ chọn: matched-passrate net-all A/B nếu muốn
  đánh giá net ở cùng volume; Phase 2 grid threshold; Phase 3 OI aggregate market feature cho gate.

## Artifacts
- gate pred: /home/ubuntu/claudedata/gate_ab_full/wfo_gate_pred_label_{oldbasket,ret15m,ret60m,retall15m,retall60m}.csv
- reports: /home/ubuntu/claudedata/sweep/REPORT_gateab_{old5m,netall5m,old15m2,netall15m,off}.md (Aug18)
- DONE: /home/ubuntu/claudedata/sweep/DONE_gateab_*.txt (8 nhánh)
- aggregator: /home/ubuntu/gate_ab_metrics.py (slice win4-15); master: gate_ab_5m_master.sh (self-driving nohup)
- predwf: 15m=predwf_G015x26e, 5m=predwf_5m015f09 (cả hai 18 window)
