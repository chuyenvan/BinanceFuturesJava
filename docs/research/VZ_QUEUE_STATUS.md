# VZ QUEUE STATUS — VZ_QUEUE_1014 (Q1→Q6)

Mỗi Q xong ghi 1 dòng: Q | trạng thái | commit | số chính. Trạng thái: DONE / BLOCKED / WAITING.

| Q | trạng thái | commit | số chính |
|---|---|---|---|
| Q1 | DONE | 997f18f3 | `SIM_RATE_FEE=0.000982` là phí **khứ hồi** (sim trừ 1 lần) ⇒ E1 cũ đếm gấp đôi; `cost_of` sửa cộng 1 lần; T3–T9 tính lại, spread nhóm bất biến max|Δ|=2,8e-17 (≤1e-9), chỉ mức dịch +0,000982. Proof `reports/fee_recompute.json` |
