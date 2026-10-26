# PREREG NUP3-S0: tập lệnh thêm chạy SLEEVE RIÊNG, dừng khi "sóng lớn" (MASTER 2026-10-26)

## Ý tưởng (owner 10-26)
Lệnh thêm của A2 (gate ×3) có edge riêng: ROI khoảng +1,4 %/lệnh trên DEV. A2 thua vì lệnh thêm GIÀNH vốn/slot của lệnh nền (+3,5 %/lệnh).

Đề xuất của owner:
- Cho lệnh thêm chạy ĐỘC LẬP: sleeve riêng, vốn riêng.
- Chỉ mở lệnh khi thoả điều kiện.
- DỪNG HẲN khi có tín hiệu thị trường sắp có sóng lớn. Lúc đó lệnh nền (crash-buy) là ưu tiên, và lệnh thêm vào trong sập là tương quan, ΣPnL ≈ 0 (N_DEEP).

S0 là bước ĐO RẺ trên artefact sẵn có, không sim mới. Mục đích: lệnh thêm còn lãi không, nhất là ở HO 2026, khi tách khỏi lúc "sóng lớn".
- Nếu S0 trượt: đóng ý tưởng sleeve mà không tốn sim.
- Nếu S0 đạt: viết prereg NUP3 (code sleeve trong sim Java, có vốn riêng) và sim.

## Dữ liệu (chỉ đọc, đã có)
- A2: `~/kaggle_sim/out/nup-a2-{a1,s7,s13,s21,s99,s123,s777,s2024}` (DEV), `nup-ho-a2-s{42,7,13,21,99,123,777,2024}` (HO).
- B0: `tsx-x14-*` (DEV), `tsx-ho-x14-*` (HO), cùng seed.
- **"Lệnh thêm"** = leg đầu cụm của A2 không khớp B0 cùng seed. Khớp = cùng symbol, giờ vào lệch ±1′, đúng cách match của NUP.
- Kỳ:
  - DEV: 2022-01-01 → 2025-12-31.
  - HO: 2026-01-01 → 2026-09-30.
  - Lệnh tính theo giờ VÀO (+07). printDone `start` là +07, nên UTC = start − 7h.

## Tín hiệu "sóng lớn" tại thời điểm vào t (CHỈ dùng dữ liệu < t, nhân quả)
Đúng 4 định nghĩa (3 "sóng" + 1 điều kiện mở), không thêm:
- **W_burst:** số leg đầu cụm mới mà CHÍNH A2 mở trong [t−60′, t) ≥ 10. Đếm từ printDone, chỉ các lệnh có giờ vào < t.
- **W_mkt:** return ALT_EW 24h tính tới phút t−1 ≤ −8 %.
  - ALT_EW = trung bình đều return phút các coin USDT-M đang giao dịch, theo cách đã dùng ở EDGE_ATTR (`~/claude_master/edge_attr/index.npz` cho 2021–2025).
  - 2026: dựng lại cùng công thức trong kernel Kaggle PRIVATE (dataset `chuyendinh/vz-kline1m-2026`), chỉ kéo về chuỗi ALT_EW phút (nhỏ). KHÔNG tải kline 2026 về Oracle.
  - Không dựng được 2026 ⇒ W_mkt chỉ DEV, ghi rõ.
- **W_book:** U của sổ NỀN (B0 cùng seed) tại t ≥ 0,20. U = Σ notional vị thế B0 đang mở tại t ÷ equity realized B0 tại t, dựng từ printDone B0.

- **W_quiet (điều kiện MỞ, owner bổ sung 10-26):** sleeve chỉ mở khi sổ nền B0 KHÔNG mở leg đầu cụm nào trong [t−24h, t). Đây là proxy nhân quả cho "ngày khác ngày của baseline".
  - Với W_quiet, nhóm "NGOÀI sóng" = các lệnh thoả điều kiện này.

## Phân bố theo ngày (owner 10-26: "có dải đều các ngày khác ngoài các ngày baseline không")
Chỉ MÔ TẢ, báo cho DEV (từng năm) và HO, median seed:
- % lệnh thêm rơi vào ngày UTC mà B0 KHÔNG có leg đầu nào. Đây là thước hậu nghiệm trong ngày, nên chỉ dùng để mô tả, không dùng để chọn.
- Số ngày/năm có lệnh thêm, chia ra: ngày B0 có lệnh / ngày B0 không có lệnh.
- Phân bố theo tháng: lệnh thêm có dàn đều không, hay dồn vào vài tháng? Báo thêm Gini/top-10 tháng % số lệnh.
- Tương quan PnL ngày giữa tập thêm và B0.
- Top-10 ngày % ΣPnL của tập thêm.
- Số đợt riêng biệt/năm, với đợt = các lệnh cách nhau < 6h. Tính cho tập thêm, B0, và phần đợt của tập thêm KHÔNG giao đợt nào của B0.

## Thước đo
Với mỗi định nghĩa W và mỗi kỳ (DEV từng năm, DEV tổng, HO), chia lệnh thêm thành 2 nhóm: TRONG sóng và NGOÀI sóng. Mỗi nhóm báo:
- số lệnh/năm;
- ROI/lệnh;
- ΣPnL;
- ΣPnL_stress (trừ 20 bps khứ hồi trên notional);
- % seed có ΣPnL_stress > 0.
Lấy median qua seed. Báo thêm như vậy cho lệnh nền B0, để so sánh.

## Luật S0 (chốt)
Một định nghĩa W **ĐẠT** khi nhóm NGOÀI sóng thoả CẢ BA:
1. DEV: ROI_stress/lệnh ≥ +1,0 %, VÀ ΣPnL_stress > 0 ở ≥ 3/4 năm 2022–2025 (median seed).
2. HO 2026: ΣPnL_stress median > 0, VÀ ≥ 5/8 seed > 0.
3. Số lệnh NGOÀI sóng ≥ 0,5× số lệnh nền B0/năm (đủ lớn để đáng làm, mục tiêu tăng lệnh).

Kết luận:
- Nhiều W đạt ⇒ chọn W có nhiều lệnh ngoài sóng nhất.
- Không W nào đạt ⇒ ĐÓNG hướng sleeve, ghi bảng.
- Đạt ⇒ MASTER viết prereg NUP3 (sim sleeve thật). S0 KHÔNG phải GO tiền thật.

## Giới hạn đã biết (ghi để không tự lừa)
- PnL lệnh thêm ở đây đo trong sổ CHUNG (size theo throttle U chung). Sleeve vốn riêng sẽ có size và đường đi khác ⇒ chỉ là ước lượng hướng.
- "Dừng khi sóng lớn" chỉ chặn mở MỚI. Lệnh sleeve đã mở trước sóng vẫn ăn lỗ của sóng. Phần này đã nằm trong PnL đo ở đây, vì PnL là của lệnh đã mở, gán theo giờ vào.
- HO 2026 đã bị nhìn ở NUP (A2 tổng). Đây là lần dùng thứ 2, cho TẬP CON. Ghi vào ledger.
