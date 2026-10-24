# PREREG_PARITY_V11_WINDOW — ADDENDUM 3 (MASTER, 2026-10-25)

- **Quyết định:** MASTER. Agent parD2 chỉ viết lại thành văn bản theo quyết định đó.
- **Thời điểm chốt:** commit **trước** khi chấm bất kỳ ngày mới nào (10-24 trở đi).
- **Phạm vi:** ngưỡng P1/P2/P3/TSX/S1-I/GV-I/CTL và mọi điều khác của prereg gốc (`481701b2`), ADDENDUM 1 (`fea9fb97`), ADDENDUM 2 (`4eef2788`) **giữ nguyên**, trừ điểm nêu ở §2.

## 1. Lý do

ADDENDUM 2 §2 mục 2 định nghĩa nhánh score-only của K6′ là "feature khớp dung sai, score ONNX lệch ≤ max(1e-6·|score|, 1e-7)".

Một dòng S1-V chỉ bị tính là lệch score khi |Δscore| > 1e-6·(1+|score|). Ngưỡng này luôn lớn hơn max(1e-6·|score|, 1e-7). Vì vậy, đọc đúng chữ thì nhánh score-only **không bao giờ xảy ra**: đây là mâu thuẫn nội tại của câu chữ, không phải một quan sát.

Quyết định được đưa ra sau khi đã thấy số 10-21..10-23. Do đó ADDENDUM này **chỉ áp từ 10-24**.

## 2. Thay đổi

**K6′, nhánh score-only.** Một dòng S1-V lệch score được tính K6′ khi đồng thời:
- mọi feature f0..f6 khớp dung sai `|a−b| ≤ 1e-6·(1+|b|)`;
- top-24 trùng **tập** và trùng **thứ tự** với live;
- **không** có cận |Δscore|.

Nhánh hoán đổi kề và tie-split giữ nguyên như ADDENDUM 2, kể cả dung sai |Δv| ≤ max(1e-6·|v|, 1e-7) và điều kiện top-24 trùng tập + thứ tự.

K6′ vẫn chỉ để mô tả, không tính vào K5.

## 3. Áp dụng

| ngày | luật nhãn chính thức | ghi chú |
|---|---|---|
| 10-21, 10-22, 10-23 | ADDENDUM 2, **đọc đúng chữ** (score-only không bao giờ đạt) | Số theo cách đọc ADDENDUM 3 chỉ báo kèm (mô tả). Verdict trong sổ không đổi. |
| từ 10-24 | ADDENDUM 2 cộng §2 của văn bản này | chính thức |
