# PRE-REG — Trailing trên nền G2 (owner 09-29: trọng tâm G2, đi lại trailing; arm ∈ {5%,7%})
Chốt TRƯỚC khi xem bất kỳ số kết quả nào. Baseline vòng này = **G2** (gate GDV2 ratio W90, nhịp 1', phí base).
Jar DÙNG LẠI `sim-jar-gdv2` (sha256 7368be46…) — mọi thay đổi là KEY runtime (arm/giveback/ladder), KHÔNG build lại, KHÔNG đổi gate/entry.

## Bối cảnh chẩn đoán (đã đo trên gdv2-g2 printDone, ghi TRƯỚC)
- 355/2509 lệnh (14.1%) chết TRƯỚC arm (STOP_LOSS_DONE), lỗ TB −14.0%/lệnh, min −72.8% — rò rỉ lớn nhất.
- 2154 lệnh đã arm (STOP_MARKET_DONE): thoát trung vị +5.5%, sàn ~+3.5–4%, đuôi phải p95 +18.5%, max +207%.
- Giả thuyết: (H1) arm 7% quá cao ⇒ nhiều lệnh không kịp arm ⇒ arm 5% cứu bớt loser; (H2) giveback 0.5 (cap 3/8%)
  trả lại quá nhiều ở vùng winner phổ biến ⇒ khoá chặt hơn (giveback 0.3 HOẶC ladder) giữ thêm lợi.

## LƯU Ý CHẤM (khác GDV2): trailing KHÔNG đổi số ENTRY (gate quyết định n). n có thể xê dịch NHẸ qua ngân sách vốn.
⇒ KHÔNG chấm theo T4 (n mục tiêu). Chấm theo: T1 rủi ro (tuyệt đối §9) + Calmar_MTM (có CI) so G2.

## Arm (5 cấu hình; k=4 ứng viên ⇒ inflate = sqrt(2 ln 4) = 1.665)
Mọi arm = G2 profile, CHỈ đổi khối exit dưới đây:
| arm | SIM_RATE_PROFIT_STOP_MARKET | TS_GIVEBACK_RATIO | TS_LADDER (+LO/GAPS) | ghi chú |
|---|---|---|---|---|
| **T0** (=G2, parity) | 0.07 | 0.5 | off | md5 BẮT BUỘC = 853aaa086be7d2d811162879df0653f6, n 2509, eq 131374 |
| **A5** | 0.05 | 0.5 | off | H1: arm sớm cứu pre-arm loser |
| **GV3** | 0.07 | 0.3 | off | H2: khoá chặt hơn, thoát sát đỉnh |
| **LAD** | 0.07 | (bỏ qua) | TS_LADDER=1, TS_LADDER_LO=0.05,0.10,0.20, TS_LADDER_GAPS=0.02,0.04,0.08 | H2: gap bậc thang — khoá chặt vùng thấp, nới đuôi |
| **A5LAD** | 0.05 | (bỏ qua) | TS_LADDER=1, LO/GAPS như LAD | kết hợp H1+H2 |

## Luật kết luận (chốt trước)
1. Cổng hợp lệ: T0 md5 = 853aaa08… (byte-identical G2). |n_arm − 2509| > 5% ⇒ ghi rõ (exit đổi ngân sách → entry).
2. Tầng 1 rủi ro (tuyệt đối §9, mỗi arm phải ĐẠT): maxDD MTM-phút ≤ 40%/năm; UW ≤ 250 ngày; quý xấu nhất ≥ −20%;
   0 năm âm; conc ≤ 15%. FAIL T1 ⇒ loại thẳng.
3. Ứng viên "thắng" G2 ⇔ ĐẠT T1 VÀ Calmar_MTM > G2 VÀ bootstrap CI95 ΔCalmar_MTM (paired block-72h, NREP 2000,
   seed 20260905, inflate 1.665) KHÔNG chứa 0. Thiếu ⇒ "≈ G2".
4. Báo mô tả cho MỌI arm (kể cả không thắng — đây là giá trị chính): số pre-arm loser & lỗ TB; phân phối lệnh armed
   (med/p25/p75/p95/max); Calmar_MTM, CAGR, maxDD phút, UW, quý xấu nhất; bảng quý + năm (qstat_r4.py).
5. Nếu KHÔNG arm nào qua CI ⇒ kết luận thẳng: "trailing hiện tại KHÔNG tệ rõ rệt trên DEV; khác biệt trong nhiễu" —
   trả lời đúng câu hỏi owner. Không tune thêm sau khi thấy số (đổi thiết kế = amendment commit trước).
6. Không đụng 242/shadow-c3/holdout 2026. DEV ≤ 2025-12-31.
