# Giải phẫu maxdd: đuôi lớn = sập đơn-coin, KHÔNG phải basket-đỉnh — 2026-08-19

## Câu hỏi user
Giả thuyết: selector bắt được pump nhưng không tránh được dump; vào N lệnh leo dốc rồi
"mắc ở lệnh cuối leo đỉnh" → maxdd. Yêu cầu: phân tích kĩ lệnh xem đúng không + giải pháp.

## Phương pháp (READ-ONLY, không re-run)
Ghép 3 file có sẵn: entry_paths.csv (2834 lệnh thực + mfe/mae 1d..180d),
entry_pathstats_g008.csv (timing tHitFav/tHitAdv + maxFav/maxAdv 4h..72h),
entry_universe_g008.csv (score + levelChangeOrdinal). Script /tmp/maxdd_anatomy.py trên Oracle.
Caveat: mfe/mae là excursion giá CÔ LẬP, không phải P&L thực sau trailing/SL.

## Kết quả

### A1 — Edge selector CÓ THẬT
- 99% lệnh có pump thật (mfe1d>5%). median mfe1d=+21.1%, mfe3d=+24.7%, mfe7d=+28.2%.
- Chỉ 18–28% lệnh có |mae|>|mfe| → đa số upside excursion > downside.
- NHƯNG 62% lệnh đã-pump sau đó dump sâu (mae3d<−10%).
- => "ăn ít" KHÔNG do chọn coin (nguyên liệu +21% có sẵn) mà do EXIT không gặt được. Lever = trailing/exit.

### A2 — Timing: dip TRƯỚC, pump SAU
- median tHitAdv_24h=210min (3.5h), median tHitFav_24h=720min (12h). Chỉ 36% pump-first.
- 64% lệnh: đáy đến trước đỉnh → path = entry → dip nhẹ (~3.5h) → pump (~12h) → (sau 24h) đuôi sập.
- HỆ QUẢ: arm SL sớm rủi ro bị rũ ở cú dip 3.5h trước khi pump 12h. Cảnh báo cho ý "arm sớm".

### A3 — levelChangeOrdinal vô dụng làm proxy sớm/muộn
- Gần như hằng số (lc=5: 2837 lệnh, lc=3: 138). Không tách được vào sớm/muộn. Test inconclusive.

### A4 — Burst KHÔNG tệ hơn (bác giả thuyết portfolio)
- corr(intensity24h, mae3d) = −0.05 (≈0). corr(intensity, mfe1d)=+0.11.
- BURST top20%: mfe1d +24.4% mae3d −14.2% maeFinal −48.7%.
- QUIET bottom40%: mfe1d +18.8% mae3d −11.6% maeFinal −62.6%.
- => Vào dồn dập (đang pump mạnh) kết quả TỐT HƠN. "Cả rổ mua đỉnh rồi dump" SAI.

### A5 — Re-entry: lệnh CUỐI an toàn hơn lệnh ĐẦU (bác "mắc ở lệnh cuối")
- 111 run re-entry≥3 trong 48h, 420 lệnh.
- FIRST: mfe1d +26.4% mae3d −24.7% maeFinal −57.7%.
- LAST : mfe1d +22.4% mae3d −13.0% maeFinal −44.4%.
- => Lệnh đầu (đầu cơ) nguy hiểm nhất; lệnh cuối coin đã chứng minh nên đỡ. Ngược giả thuyết.

### A6 — Đuôi thật = SẬP ĐƠN-COIN fat-tail
Top 15 maeFinal xấu nhất toàn single-name collapse:
- LUNA/Terra death spiral 5/2022: 4×LUNA + ANC, mae3d −88..−99%, maeFinal −100%, không hồi.
- Meme/coin mới list pump-rồi-chết 2024–25: BANANAS31, AIOT, AIA, HIPPO, MELANIA, MOODENG,
  CHILLGUY, OM — mfe1d dương to (pump thật) rồi sập 90–98%, recoverDay=0.
- => selector chọn trúng momentum cao nhưng lẫn coin sắp chết. Đuôi = idiosyncratic đơn tên,
  KHÔNG phải correlated basket dump ở đỉnh.

## VERDICT
- Giả thuyết user: ĐÚNG "selector bắt pump / ăn ít"; SAI cơ chế maxdd (không phải basket-đỉnh,
  không phải mắc-lệnh-cuối). maxdd = sập đơn-coin (Terra + meme mới list).

## Giải pháp đề xuất (theo chẩn đoán)
1. HARD catastrophic-stop theo entry (~−15/−18%), KHÁC trailing (hiện chỉ arm khi +26% lãi →
   coin sập thẳng không có stop). Phải > ngưỡng dip thường (mae1d median −9%) để không cắt winner (A2).
2. Filter chất lượng coin (selector-side): loại/giảm size coin mới list <N ngày, thanh khoản thấp,
   chưa qua 1 chu kỳ. Đây là chỗ DUY NHẤT selection cứu được đuôi.
3. Position sizing theo tail risk (size nhỏ cho tên mới/rủi ro collapse).

## Next (offered, chưa chạy)
- Sweep hard-stop −10/−15/−18/−20% trên full-range: đo maxdd giảm bao nhiêu vs winner bị cắt bao nhiêu.
- Files: /tmp/maxdd_anatomy.py (Oracle), entry_paths.csv, entry_pathstats_g008.csv, entry_universe_g008.csv
