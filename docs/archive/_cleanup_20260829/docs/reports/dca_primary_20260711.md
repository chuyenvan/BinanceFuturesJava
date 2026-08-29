# REPORT §2 — DCA-primary (mean-reversion đứng riêng) — 2026-07-11

## Pre-register
Pass: DCA-only cho nhiều quý dương hơn / CAGR cao hơn full-system với maxDD chịu được.

## Kết quả (v4 ret2 + giveback 1.0)

| Cấu hình | CAGR | maxDD | năm+ | 6th+ | quý+ |
|---|---|---|---|---|---|
| DCA-only, size 50 | −0.01% | 0.4% | 1/6 | 1/11 | 1/22 |
| DCA-only, size 25 | −0.03% | 0.8% | 1/6 | 1/11 | 1/22 |
| FULL (PST bật), size 25 | +4.21% | 0.9% | 4/6 | 7/11 | 9/22 |

## Verdict: **FAIL — DCA-primary gần như bằng 0.**

## Chẩn đoán (đảo ngược giả thuyết trước, ghi nhận sai)

Giả thuyết "`DCA_LEVEL1` là sleeve khỏe bị bỏ quên" **SAI**. Lỗi attribution của tôi: `DCA_LEVEL1` kiếm
+5295 KHÔNG phải vì tự nó có edge, mà vì nó **DCA nhồi vào các lệnh PST đã mở**. Tắt PST → DCA không có
gì để nhồi → không lệnh → phẳng lì (1/22 quý dương).

**Hai sleeve KHÔNG độc lập:** DCA là cơ chế *nuôi vốn* của PST, không phải nguồn edge riêng. +5295 là
"lãi của việc bình quân giá vào lệnh pump", không phải "sleeve mean-reversion".

## Hệ quả cho khung giải pháp
- **§2 đóng lại (fail).** Không có nguồn edge thứ 2 ẩn trong mean-reversion.
- Toàn bộ edge của hệ = **PST (pump selector) + DCA nuôi nó**. Một nguồn duy nhất.
- → §1 (cải thiện chính PST: candidate 0.01|72h|pump) là hy vọng thực chất DUY NHẤT trong kiến trúc
  hiện tại. Nếu §1 cũng không nâng bậc thang → §3 (sleeve 2 THẬT SỰ khác loại, cần short/majors) hoặc §6.
- §3 phải là nguồn edge **thực sự độc lập** (không phải biến thể của cùng cơ chế pump+DCA) — bài học từ
  cú nhầm này: kiểm tính độc lập TRƯỚC khi coi là sleeve riêng.

=== RESULT ===
STATUS: REVIEW
ARTIFACTS: /home/ubuntu/claudedata/dca_primary_result.md
VERIFY: DCA-only CAGR -0.01%, 1/22 quy duong; edge chi ton tai khi PST bat
DECISIONS: §2 fail; edge = PST+DCA (1 nguon); §1 candidate la hy vong con lai
=== END ===
