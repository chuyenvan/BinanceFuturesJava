# DECISION 0013 — GIỮ `G2` làm baseline; KHÔNG nhận K24; chuyển sang CẤU TRÚC (OFI V3)

Ngày **2026-09-30** · owner: *"c giữ G2. chạy ofi đi nhé"*.

## Quyết định
1. **Baseline nghiên cứu GIỮ NGUYÊN `G2`** = `profiles/g2_flat3.properties` (= nền `r4_kg0_k16_f015_g155`
   + GDV2 rolling gate `SIM_GATE_ROLLING_MODE=ratio PCT=0.99995083 DAYS=90`).
   - `G2` @base: **n 2 509 · CAGR 34,18 % · ddPhút −18,00 % · UW 128,9 · conc 4,09 % · Calmar_MTM 1,900 · PASS 4 tầng**.
2. **KHÔNG nhận `K24` (P2)**, **KHÔNG nới T4**.
   - Lý do: `K24` = **+40 % n** (2 517→3 526) nhưng **trượt T4** (`Calmar_MTM 1,673 < 0,90×1,940 = 1,746`),
     và **2022 ÂM** (−2 233 $ so K16) — lệnh biên tập trung vào giai đoạn xấu (`RESULT_DOUBLE_ENTRIES_QY.md`, `88606ba1`).
3. **Lever CONFIG đã CẠN cho mục tiêu ×2** (`RESULT_DOUBLE_ENTRIES.md`, `60384406`: trần **1,83×** = P5,
   và đúng arm đó vỡ T3).
4. ⇒ **Chuyển sang hướng CẤU TRÚC: OFI V3 như NGUỒN SỰ KIỆN THỨ 2** (mở được TUẦN GATE ĐÓNG —
   `K_DENSITY` chứng minh burstiness là thuộc tính của GATE, không phải của K).

## Ghi chú
- Quyết định này **KHÔNG** chạm production/`242`/ONNX/LIVE. Baseline sim/live hiện hành không đổi.
- Trạng thái `G2` được giữ làm **mốc parity + mốc so của mọi vòng sau**.
