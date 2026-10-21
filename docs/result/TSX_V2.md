# TSX_V2 — biến thể thoát sau 168h cho cụm hoãn X14 (replay DEV) — kết quả 2026-10-22: **KHÔNG CÓ ỨNG VIÊN**

Prereg `docs/prereg/PREREG_TSX_V2.md` (commit **6b7ab1a8**, trước khi tính biến thể). Phase A `docs/result/TSX_V2_PHASE_A.md` (1c90b233).
Script `research/tsx_v2/phase_b.py`, `md_b.py`, `b4_decomp.py` (mô tả bổ sung); dữ liệu `docs/result/tsx_v2/` (`phaseB.json`, `phaseB_clusters.csv` — Δ từng cụm × ô, `b4_decomp.json`).
Thước: direct ΔPnL/seed so X14 = Σ(PnL replay biến thể − PnL replay X14) trên 4 323 cụm chạm 168h/8 seed; **bỏ qua lãi kép, slot, vốn khoá, lệnh vào mới**; giữ lâu hơn run nguồn ⇒ không DCA mới (đóng băng). Trial ledger: +14 ô (tổng họ TS_MKT_EXT = 15).

## Kiểm (PASS, §5)
K1 replay base = Phase A (max|Δ| = 0) và = printDone X14 (100 % trong 1e-3); K2 B4(−0,30/30) ≡ base; K3 B1 trần 504 ≡ base; K4 B3 r = ∞ ≡ base; K5 B2 k = ∞ ≡ base; K7 0 cụm OPEN. X14 direct đợt LUNA +1 625, 06/2024 −249 (= Phase A).

## Bảng B1–B4 (USD/seed; "đợt" = 25 đợt Phase A)
| Ô | ngày ON | Δ vs X14 | seed > 0 | cụm ảnh hưởng/seed | LOO min (đợt) | CI95 bootstrap theo đợt (n đợt) | LUNA | 06/2024 | Δ vs P0 (seed>0) | (i)(ii)(iii)(iv)(v) |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE X14 | 214 | 0 | – | 0 | – | – | 0 | 0 | +6 559 (8/8) | – |
| B1a trần 336h | 214 | **−1 399** | 0/8 | 84,9 | −2 135 (06/2024) | [−4 666; +1 711] (4) | −500 | +737 | +5 161 (8/8) | ✘✘✘✘✘ |
| B1b trần 420h | 214 | **−532** | 0/8 | 68,5 | −564 (LUNA) | [−862; +94] (3) | +31 | −276 | +6 027 (8/8) | ✘✘✘✘✘ |
| B2a ρ ≤ 1,5 | 214 | **−2 423** | 0/8 | 57,8 | −2 715 (06/2024) | [−4 236; −558] (9) | −172 | +292 | +4 137 (8/8) | ✘✘✘✔✘ |
| B2b ρ ≤ 2,5 | 214 | **−296** | 1/8 | 23,4 | −588 (06/2024) | [−1 204; +627] (7) | +17 | +292 | +6 264 (8/8) | ✘✘✘✔✘ |
| B3a hồi ≥ 10 % | 188 | **−1 229** | 0/8 | 41,2 | 0 (chỉ LUNA) | suy biến (1) | −1 229 | 0 | +5 331 (8/8) | ✘✘✘✘✘ |
| B3b hồi ≥ 20 % | 210 | **−170** | 5/8 | 41,2 | 0 (chỉ LUNA) | suy biến (1) | −170 | 0 | +6 389 (8/8) | ✘✘✘✔✘ |
| B4 −0,25/20 | 210 | +3 053 | 8/8 | 164,4 | +1 153 | [−354; +7 485] (11) | +85 | +701 | +9 613 (8/8) | không chọn |
| B4 −0,25/30 | 406 | +4 742 | 8/8 | 164,4 | +2 169 | [−306; +10 727] (14) | +127 | +337 | +11 301 (8/8) | không chọn |
| B4 −0,25/45 | 611 | +3 466 | 8/8 | 185,6 | +2 276 | [−696; +7 273] (15) | +374 | +1 189 | +10 025 (8/8) | không chọn |
| B4 −0,30/20 | 104 | −2 139 | 0/8 | 85,6 | −2 711 | [−3 908; +316] (6) | −439 | +572 | +4 420 (8/8) | không chọn |
| B4 −0,30/45 | 445 | +3 045 | 8/8 | 134,2 | +2 129 | [+58; +5 883] (11) | +374 | +916 | +9 605 (8/8) | không chọn |
| B4 −0,35/20 | 36 | −5 396 | 0/8 | 142,2 | −5 646 | [−8 180; −2 679] (9) | −462 | +249 | +1 163 (8/8) | không chọn |
| B4 −0,35/30 | 91 | −3 917 | 0/8 | 114,1 | −4 166 | [−6 697; −1 323] (8) | −23 | +249 | +2 642 (8/8) | không chọn |
| B4 −0,35/45 | 256 | +1 080 | 8/8 | 147,2 | −497 | [−2 374; +5 133] (10) | +374 | +1 577 | +7 639 (8/8) | không chọn |

Δ theo seed (vs X14): B1a −799…−1 951; B1b −184…−1 780; B2a −1 840…−3 205; B2b −660…+181; B3a −648…−1 900; B3b −1 649…+264 (S777 −1 649 kéo TB âm); B4 −0,25/30 +3 649…+5 914; B4 −0,30/45 +1 989…+4 184. Δ theo đợt đầy đủ: `phaseB.json` (`delta_ep`).

## Luật chọn (§4) ⇒ **không có ứng viên; giữ X14**
- B1: cả hai ô âm 8/8 seed. Cắt trần sớm cắt mất các cụm hồi/arm muộn (336–504h); chỉ 06/2024 được lợi (+737 ở 336h) — khớp DEEP (06/2024 là đuôi xấu duy nhất) nhưng phần lợi đó nhỏ hơn phần mất ở FTX (−1 515) và LUNA (−500).
- B2: âm ở cả hai k (CI95 của k = 1,5 hoàn toàn âm). Lọc "idiosyncratic" loại bỏ đúng nhóm có direct lớn nhất (đã thấy trước ở Phase A §A2c — ghi nhận nhiễm, không đổi kết luận).
- B3: chỉ tác động đợt LUNA (hồi ≥ 10/20 % từ đáy trong lúc cờ còn ON chỉ xảy ra ở LUNA và 02/2025 — 02/2025 không có cụm hoãn) ⇒ là phép thử 1 đợt; cả hai âm.
- **B4 (plateau)**: mọi 9 ô đều có Δ^P0 > 0 ở 8/8 seed ⇒ −0,30/30 NẰM trong plateau dương ⇒ không cần cảnh báo theo §4. NHƯNG base không phải đỉnh: ngưỡng lỏng hơn (−0,25) hoặc lookback dài hơn (45) cho Δ vs X14 dương 8/8 (+3,0…+4,7k), ngưỡng chặt hơn (−0,35/20, −0,35/30) âm mạnh. Theo §4 không chọn ô B4.

## Phân rã B4 (mô tả bổ sung, `b4_decomp.json`, không đổi luật)
| Ô | cụm hoãn LÂU hơn X14 (n / Δ) | cụm MỚI được hoãn (n / Δ) | bỏ hoãn (n / Δ) | Δ từ phần giữ VƯỢT thoát run nguồn |
|---|---|---|---|---|
| −0,25/30 | 88,9 / +3 181 | 75,5 / +1 561 | – | **+4 742 (100 %)**, 164 cụm/seed |
| −0,30/45 | 74,2 / +4 419 | 60,0 / −1 374 | – | **+3 045 (100 %)**, 134 cụm/seed |
| −0,25/20 | 67,1 / +3 051 | 49,1 / −193 | 2,2 / −196 | +2 858 (94 %) |
| −0,35/30 | – | – | 111,2 / −3 800 | 0 |
Toàn bộ phần dương của các ô B4 lỏng đến từ việc giữ cụm VƯỢT thời điểm thoát của run X14 nguồn — chính vùng replay yếu nhất: không có DCA mới, không tính vốn khoá/slot (DEEP: vốn giam đỉnh ~53 % equity, lỡ crash-buy ở LUNA) và không lãi kép. Chỉ sim Java mới đo được; KHÔNG dùng làm bằng chứng để nới ngưỡng.

## Rủi ro overfit / giới hạn
1. Tất cả in-sample DEV; X14 vốn sinh từ chính DEV. Số đơn vị độc lập thật = đợt (≤ 15 đợt có ảnh hưởng); 8 seed tương quan cao (corr ngày 0,975) ⇒ "8/8 seed" gần như 1 quan sát.
2. Replay bỏ qua lãi kép/slot/vốn khoá: biến thể giữ ngắn hơn (B1–B3) bị thiệt nhẹ ở thước này (vốn giải phóng sớm có giá trị ⇒ Δ thực có thể ít âm hơn), biến thể giữ lâu hơn (B4 lỏng) được lợi giả.
3. Nhạy ngưỡng: đi chặt hơn base (−0,35) mất phần lớn hiệu ứng, đi lỏng hơn thì tăng trong replay ⇒ base nằm trên sườn, không trên đỉnh; với 45 % ngày ON sát ngưỡng (DEEP), sai số ±3–5pp ALT_EW live đổi kết quả đáng kể.
4. Δ phân bố theo đợt rất lệch (đợt 2025-10..12 và 06/2024 chi phối LOO min ở B4).

## Bất thường
- Lần chạy đầu `phase_b.py`, điều kiện (ii) dùng `loo_min > 0` ⇒ B3b hiện (ii) ✔ do nhiễu 1e-13 (biến thể chỉ có 1 đợt ⇒ LOO = 0 đúng đại số). Sửa thành `> 1e-6` rồi chạy lại; không đổi trạng thái ứng viên của ô nào.
- 6 cụm STRAX 2024-03-22 (mỗi seed 1): sim thiếu 2 nến ⇒ thoát 168h+3' thay 168h+1' (PnL khớp); không phải cụm hoãn, không ảnh hưởng.
- LIT: sim không có funding (=0); replay theo sim.

## Bước tiếp (đề xuất, cần owner)
Không có ứng viên v1.2 từ B1–B3. Nếu muốn khảo sát nới cờ (−0,25 hoặc lookback 45) thì phải là prereg MỚI chấm bằng sim Java đầy đủ DEV (lãi kép/slot/vốn khoá) — replay không đủ cho hướng này; HO 2026 chỉ mô tả.
