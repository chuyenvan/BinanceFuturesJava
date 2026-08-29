# 2026Q2 vào WFO — trạng thái + kết quả K5 tới 2026Q1 (2026-08-16)

## 1. Kết quả K5 canonical (tag G015x26q2, 17 window 2022Q1→2026Q1, FAILED=0)
| win | quý | PnL | trades | DD% |
|---|---|---:|---:|---:|
|0|2022Q1|+778.5|116|5.5|
|1|2022Q2|+1525.2|368|15.9|
|2|2022Q3|+391.0|38|0.3|
|3|2022Q4|+530.4|167|6.7|
|4|2023Q1|+469.4|50|1.4|
|5|2023Q2|+507.7|83|7.8|
|6|2023Q3|+396.1|47|2.5|
|7|2023Q4|+1521.3|98|0.7|
|8|2024Q1|+1145.6|76|2.9|
|9|2024Q2|+16.4|85|2.4|
|10|2024Q3|+1935.6|131|5.6|
|11|2024Q4|+1584.7|241|5.3|
|12|2025Q1|**-786.9**|336|19.1|
|13|2025Q2|+1462.0|177|3.5|
|14|2025Q3|**-269.9**|64|3.0|
|15|2025Q4|+5867.7|737|18.0|
|16|**2026Q1**|**+808.4**|270|10.8|

- **Tổng ≈ +17,883** / 35k vốn, **15/17 quý dương**, chỉ 2 quý âm (2025Q1, 2025Q3). posRatio lenient 88%.
- **2026Q1 (+808, DD 10.8%) DƯƠNG** → 2026 (ít nhất tới hết Q1) **vẫn giữ edge**, không vỡ.
- ⚠️ Concentration: win15 (2025Q4) = +5868 ≈ 33% tổng. Rủi ro "edge dồn mùa pump" (doc canonical đánh dấu #1) vẫn hiện rõ.

## 2. 2026Q2 (win17) vì sao CHƯA vào — chẩn đoán chính xác
- Market data: OK tới **2026-08-13** (không phải blocker).
- buildJobs vẫn tạo **17 window** dù đã pad selector fold tới 2026-06-30 17:45 UTC.
- **Cap thật = GATE pred `ai_pred_market_gate_wfo`** (layer độc lập, đọc từ Aerospike): kết thúc ts=1782838740000 = **2026-06-30 16:59 UTC**, thiếu **1 phút** so với biên window 2026-07-01 GMT+7 (2026-06-30 17:00 UTC). buildJobs đòi OOS_end ≤ min(market, gate, funding) → gate là binding → win17 rớt đúng 1 phút.
- gatecount.jar không có source/không đọc được bằng javap để sửa buildJobs → không patch jar được sạch.

## 3. Cách nới 2026Q2 (nếu quyết làm) — 1 cycle nữa
Pad GATE pred cho chạm biên: append ~4 bar (17:00–17:45 UTC) vào `wfo_gate_pred.csv` (copy predReturn15M/predRisk4H bar cuối) → `LoadWfoGatePredTool` nạp lại vào set `ai_pred_market_gate_wfo` → re-fanout G015x26q2. Các bar pad nằm ngoài window [.., 17:00) nên **PnL Q2 không đổi**, chỉ để buildJobs sinh win17. (Selector fold đã pad sẵn trong predwf_G015x26q2.)
- Rủi ro: LoadWfoGatePredTool nạp lại 2.76M record vào Aerospike có thể chậm; + 1 fanout ~30'.
- Giá trị biên: 2026Q1 đã cho tín hiệu 2026-giữ-edge; 2026Q2 chỉ thêm 1 quý.

## 4. Song song
- Train 5m GPU (selector-5m-stream-gpu, QuantileDMatrix streaming 4h-only) đang chạy — xem task #12.
