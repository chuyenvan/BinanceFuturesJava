# PREREG LIQX_S1 — AMEND1 (trước khi tính bất kỳ return/PnL nào)

Ngày: 2026-10-24. Agent liqx1. Áp cho `docs/prereg/PREREG_LIQX_S1.md` (ad10cc97, sha256 991cd816…ffdf7). Commit TRƯỚC khi chạy s1_episodes/s1_returns/s1_x14 (chưa có return, rank, PnL nào được tính).

## Lý do (chỉ dựa trên độ phủ dữ liệu, không nhìn kết quả)
- Chạy s1_build lần 1 (đúng chữ prereg §2): 2022-01…05 có 1 375–1 809 (sym, ngày) AMBIG/tháng (≈ 45–60 % top-100) ⇒ ≈ 55 % bucket A tháng 1–4/2022 NaN (gồm cả tuần LUNA 2022-05 một phần).
- Nguyên nhân: `taker_ls_vol` của Vision metrics NaN ≈ 96 % các ngày 2022-01 (đo trực tiếp) ⇒ phép taker không chạy; phép phụ giá ngầm chỉ tách ≈ 7,9× (median perr_new/perr_old của nhóm AMBIG; p5 = 4,3×) < ngưỡng 10× do agent tự đặt (OI_FIX_LOG ghi 10–20× cho mẫu 2024–2025).
- Hiệu chuẩn phép phụ trên 134 109 (sym, ngày) mà phép taker đã kết luận (`research/liqx_s1/diag_conv.py`, n_p ≥ 144): ngưỡng 3× ⇒ **0 ca SAI**, đồng ý 96,7 % (OLD) / 98,5 % (NEW), còn lại chưa kết luận; ngưỡng 2× cũng 0 sai; ngưỡng 10× để 54 % OLD chưa kết luận.

## Thay đổi
- Prereg §2, phép phụ giá ngầm: luật "10×, ≥ 12 cặp" ĐỔI THÀNH "perr bên này < perr bên kia / 3, ≥ 144 cặp". Phép chính (taker, 10×, ≥ 12 cặp) giữ nguyên. Không kết luận ⇒ vẫn NaN; vẫn không hardcode ngày.
- Báo cáo kèm độ phủ theo luật gốc (lần 1) và theo AMEND1.
- Ghi nhận thêm (không đổi luật): metrics 2024-02-16 thiếu ≈ 10,5h cho mọi symbol ⇒ bucket NaN; 2022-03-01 và 2022-04-01/02 như đã biết.
