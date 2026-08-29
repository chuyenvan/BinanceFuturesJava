# K-grid khử selection-bias → K5 (không phải K8) + live revert (2026-08-20)

## Bối cảnh
Trước đó chọn K=8 vì FULL_18w total cao nhất (20247) → deploy live K5→K8. User hỏi grid-pick có lỗ hổng không → áp deflated-t / 1-SE / worst-window lên chính K-grid data sẵn có (miễn phí, không run mới).

## Kết quả (5 config × 18 window, cùng jar Aug2, cùng data)
| K | total | mean/win | t-stat | p sau khử×5 | worst window | %dương |
|---|---|---|---|---|---|---|
| **5** | 18748 | 1042 | **3.25** | **0.006 ✓** | **−787** | 16/18 |
| 8 | **20247** | 1125 | 2.65 | 0.041 ✓ | −2450 | 16/18 |
| 10 | 19532 | 1085 | 2.99 | 0.014 ✓ | −2653 | 16/18 |
| 12 | 18852 | 1047 | 2.89 | 0.019 ✓ | −2937 | 15/18 |
| 15 | 17303 | 961 | 2.45 | 0.072 ✗ | −4089 | 14/18 |

## Kết luận
- **1-SE rule: cả K5→K15 nằm trong 1 SE của nhau** → khác biệt là NHIỄU, không phân biệt thống kê. "K=8 max-total" = chọn đỉnh nhiễu (selection bias).
- **K=8: total cao nhất NHƯNG t thấp nhất (2.65) + đuôi xấu gấp 3** (worst −2450 vs K5 −787).
- **K=5 trội risk-adjusted**: t cao nhất (3.25), p khử-nhiễu tốt nhất (0.006), đuôi tốt nhất (−787), 16/18 dương. K5 cũng là baseline frozen gốc.
- → K-grid **không biện minh được rời K5**. Đã **revert live K8→K5** (pid 26572, shadow-off giữ nguyên, env verify K5/SHADOW=true/SIM_RATE=0.05). Backup env.sh.bak_prek5revert_20260820.

## Quy trình chọn từ WFO (áp cho mọi trục sau này — CHỐT)
1. KHÔNG đọc ô max-total.
2. Tính t-stat (mean/SE) + worst-window + %dương mỗi config.
3. Khử multiplicity (trừ theo số config đã thử) → loại cái rớt ý nghĩa.
4. 1-SE rule: nếu nằm trong 1 SE của nhau → coi hoà → chọn cái ít rủi ro đuôi/đơn giản nhất, KHÔNG max-total.
5. Không cái nào sống sót khử nhiễu → trục đó không có edge → giữ baseline.
6. Config chọn → xác nhận 1 phát trên holdout chưa đụng (2026), không phải data vừa dùng chọn.

## Arm — khuyến nghị
- arm là gene [4,8], hiện frozen 5.2185 (=26% với rate-min 0.05). Khi WFO thật sự search (stage1 N=30) nó chọn ~4.8 (≈24%) — sát giá trị hiện tại.
- Order-level cho thấy arm (exit) KHÔNG fix capital-lock (loser rot bất kể arm, không SL); cỗ máy sinh lời là lệnh nhanh ≤7d (95% thắng), không chờ arm.
- → arm gần tối ưu + đòn bẩy thấp. **KHÔNG chạy full arm grid** (lặp bẫy K8 + tốn + selection bias). Nếu muốn chốt: sweep nhỏ 3 điểm, đánh giá bằng deflated-t/1SE/worst-window trên ≤2025, giữ 2026 holdout — nhưng không ưu tiên. Đòn bẩy thật nằm ở entry/DCA-quality (loser-rot), để sau.
