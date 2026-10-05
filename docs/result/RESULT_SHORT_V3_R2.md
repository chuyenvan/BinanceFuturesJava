# RESULT_SHORT_V3_R2 — Niêm yết mới (listing effect), vòng R2 của PROGRAM_SHORT_V3

Ngày 2026-10-02 · Pre-reg `docs/prereg/PREREG_SHORT_V3_R2.md` @ ffe806b2 (commit TRƯỚC khi đo) · Script `research/analysis/short_v3_r2_listing.py`
→ `docs/result/RESULT_SHORT_V3_R2.json` · Kiểm định fidelity POST-HOC (không vào luật GO): `research/analysis/short_v3_r2_slcheck.py` → khoá `posthoc_SL1m`.

**Verdict cơ học theo luật GO pre-reg: GO — cả nhánh D0 và D1 PASS G1–G4.**
**Nhưng KHÔNG BỀN:** khi SL +15% được kiểm trên HIGH 1m (stop thật) thay vì close 1h, SL-rate 44% → 52%, net D0 +4,41% → +2,10%
với CI raw [−0,10; +4,69] chạm 0 ⇒ G1 trượt (D1 +1,74%, CI [−0,35; +4,18], 2023 âm). Edge nằm trọn ở đuôi phải của short:
bỏ 10% lệnh tốt nhất ⇒ mean −0,26%; median net (1m) −14,6%.

## Sanity
- **S1** File 627 sym (625 universe), 133 sym có từ 2021 (không phải listing). D0 ∈ [2022-01-01; 2025-12-24]: **490 listing — 2022: 24 · 2023: 96 · 2024: 131 · 2025: 239**.
  Loại: L3b (gap) 0; L5 1 (BTCDOMUSDT: D0 <12 nến, D1 trống); L4 0. Lệnh hợp lệ D0 = 489, D1 = 489. Fallback D0→D1 (<12 nến ở D0): 165/490 (34%).
- **S2** 10 mẫu (seed 20260905): BLUR 2023-04-28, LISTA 2024-06-20, AERGO 2024-09-10, REI 2024-09-27, KAIA 2024-12-04, A2Z 2025-07-30,
  LYN 2025-10-06, YB 2025-10-10, CC 2025-10-31, SENT 2025-11-14 — close cuối ngày D0..D7, P0, ret7, SL, funding, pnl trong `sanity.S2_samples`.
  Kiểm tay: SL nhất quán với chuỗi close (LISTA D5 +17,8%, A2Z D4 +16,7%, CC D2 +21% ⇒ SL); YB fallback D1, ret7 −64,5% không SL; LYN SL dù ret7 −35% (squeeze trong giờ trước khi sập).
- **S3** Ngày đầu Aerospike `kline_1m_opt` khớp D0 cho 490/490 (lệch 0 ngày); lastc 1m ngày D0 = close cuối ngày CLOSES_1H (|rel| median 0, p99 0).
  ⇒ CLOSES_1H và kline_1m_opt CÙNG GỐC: kiểm này chỉ xác nhận nhất quán nội bộ, KHÔNG phải đối chiếu độc lập với lịch niêm yết Binance (chưa có nguồn ngoài).
- **S4** Lệnh có ≥1 kỳ funding: D0 97,3%, D1 98,2%; trunc 1; SL ⇔ maxFav7 ≥ 15%: 0 lệch; ALL cùng ngày: n coin min 64, median 342; funding cache 0 trùng (sid, ts).
- **S5** "Giống đổi tên" (±3 ngày, tỉ giá ×1/×1000): 0 — nhưng KAIA (= KLAY đổi tên) vẫn lọt vì sym cũ ngừng lệch > 3 ngày; quy tắc chỉ bắt được migration cùng ngày.
- **Fidelity 1m** (cho post-hoc): close phút cuối mỗi giờ = CLOSES_1H ở 136 372/136 372 cặp; high ≥ max(open, close) 100%; phút thiếu 0,28%.
- **Survivorship**: CLOSES_1H chỉ có 36 sym kết thúc trước 2025-12-20 (2021: 2, 2022: 8, 2023: 1, 2024: 25, **2025: 0**) ⇒ gần như chắc thiếu sym đã delist
  (nhất là 2025). Coin bị delist thường sụp ⇒ có lẽ làm short trông KÉM hơn thực (bảo thủ), nhưng chưa định lượng.

## Đường giá sau close D0 (anchor nhánh chính; %; maxFav trên 1h close = cận dưới)

| horizon | n | retEnd mean | retEnd med | maxFav mean | maxFav med | pSQ10 | P(ret≤−10%) |
|---|---|---|---|---|---|---|---|
| D+1 | 488 | -1.36 | -4.28 | +10.47 | +4.42 | 29.9 | 29.3 |
| D+3 | 488 | -0.84 | -6.55 | +19.67 | +9.00 | 46.5 | 41.0 |
| D+7 | 489 | -2.05 | -10.57 | +29.01 | +11.70 | 53.6 | 51.7 |
| D+14 | 486 | +0.54 | -16.40 | +44.93 | +16.49 | 61.3 | 58.4 |
| D+30 | 478 | +0.84 | -21.53 | +75.34 | +21.91 | 66.5 | 63.2 |

ret D0 intraday (P0 / close nến đầu − 1): mean +0.83, median -2.86, n 489

## Chiến lược (net %/lệnh sau phí 0,112 + funding exact)

| nhánh | n | net mean | net med | CI raw | CI inflate ×1,18 | win% | SL-rate | min | p5 | ret7 mean | funding mean | excess vs ALL (mean/med) | excess CI raw |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | 489 | **+4.41** | +1.24 | [+2.22;+6.99] | [+1.83;+7.46] | 51.3 | 44.2 | -25.56 | -16.33 | -2.05 | -0.444 | +2.45 / +10.36 | [-1.56;+6.54] |
| D1 | 489 | **+3.49** | -0.29 | [+1.23;+5.88] | [+0.82;+6.31] | 49.9 | 44.2 | -23.68 | -16.79 | -1.75 | -0.335 | +1.88 / +8.86 | [-1.79;+5.64] |

## Theo năm (năm của t0)

| nhánh | năm | n | net mean | net med | CI raw | SL-rate | funding | excess |
|---|---|---|---|---|---|---|---|---|
| D0 | 2022 | 24 | +8.92 | +6.89 | [+1.39;+18.34] | 29.2 | -0.267 | +2.23 |
| D0 | 2023 | 95 | +2.29 | +4.78 | [-1.17;+6.03] | 35.8 | -0.670 | +5.31 |
| D0 | 2024 | 131 | +4.35 | +4.28 | [+1.44;+7.43] | 42.0 | +0.173 | +1.40 |
| D0 | 2025 | 239 | +4.83 | -12.93 | [+0.85;+9.19] | 50.2 | -0.711 | +1.91 |
| D1 | 2022 | 24 | +10.51 | +10.11 | [+3.78;+16.59] | 20.8 | -0.435 | +8.00 |
| D1 | 2023 | 95 | +0.32 | +1.13 | [-3.58;+4.55] | 40.0 | -0.436 | +3.06 |
| D1 | 2024 | 129 | +3.71 | +4.28 | [+0.65;+6.95] | 41.1 | +0.191 | +2.37 |
| D1 | 2025 | 241 | +3.92 | -6.31 | [-0.05;+8.02] | 49.8 | -0.567 | +0.55 |

## Độ nhạy (CHỈ BÁO, không vào GO)

| nhánh | biến thể | n | net mean | CI raw | năm dương |
|---|---|---|---|---|---|
| D0 | sens_SLclose | 489 | +2.10 | [-0.27;+4.90] | 4/4 |
| D0 | sens_nofund | 489 | +4.85 | [+2.60;+7.39] | 4/4 |
| D0 | sens_no_rename | 489 | +4.41 | [+2.22;+6.99] | 4/4 |
| D1 | sens_SLclose | 489 | +1.18 | [-1.53;+3.89] | 3/4 |
| D1 | sens_nofund | 489 | +3.82 | [+1.58;+6.19] | 4/4 |
| D1 | sens_no_rename | 489 | +3.49 | [+1.23;+5.88] | 4/4 |

## Luật GO

| nhánh | G1 (mean>0, CI raw & infl lo>0) | G2 (≥3/4 năm) | G3 (n≥120) | G4 (excess>0) | PASS |
|---|---|---|---|---|---|
| D0 | True (+4.41; lo raw +2.22; lo infl +1.83) | True (4/4) | True (489) | True (+2.45) | **True** |
| D1 | True (+3.49; lo raw +1.23; lo infl +0.82) | True (4/4) | True (489) | True (+1.88) | **True** |

**VERDICT: GO**

## Funding D0..D+7 (21 830 kỳ settle của 488 listing)
Rate/kỳ: mean −0,037%; p1 −1,07%; p5 −0,25%; p25 −0,003%; p50 +0,005%; p75 +0,010%; p95 +0,065%; p99 +0,150%; 26% kỳ âm; 12,6% kỳ |rate| ≥ 0,1%.
Chu kỳ settle trung vị 4h (4h: 17 369 · 8h: 1 946 · 1h: 1 923 khoảng). Theo lệnh D0 (Σ trong cửa sổ giữ thực): mean −0,44%, median +0,05%, p5 −4,27%, p95 +1,32%;
theo năm 2022 −0,27 · 2023 −0,67 · 2024 +0,17 · 2025 −0,71 (%). ⇒ Đa số lệnh nhận funding nhỏ, nhưng đuôi trái (short đông, rate −1%/kỳ) làm short TRẢ trung bình
~0,44%/lệnh (≈10% gross edge). Lệnh lỗ nặng nhất (FUN −25,6%, IP −23,7%) = SL −15,2% + funding −8..−10%.

## Kiểm định fidelity SL (POST-HOC, KHÔNG vào luật GO)
Cùng lệnh, SL +15% kiểm trên HIGH 1m như stop-market: fill = max(1,15·P0, open phút chạm) + 0,2%; funding cắt tại phút thoát; không chạm ⇒ như bản chính.

| nhánh | n | SL-rate 1h | SL-rate 1m | net mean 1h (chính) | net mean 1m | net med 1m | CI raw 1m | CI infl 1m | năm dương 1m | lỗ SL TB 1m |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 | 489 | 44.2 | 51.7 | +4.41 | **+2.10** | -14.59 | [-0.10;+4.69] | [-0.49;+5.16] | 4/4 | +15.26 |
|  | theo năm 1m: 2022 +7.54 · 2023 +0.50 · 2024 +2.41 · 2025 +2.01 |
| D1 | 489 | 44.2 | 50.7 | +3.49 | **+1.74** | -14.16 | [-0.35;+4.18] | [-0.72;+4.62] | 3/4 | +15.26 |
|  | theo năm 1m: 2022 +8.64 · 2023 -1.21 · 2024 +2.32 · 2025 +1.90 |

## Kết luận theo từng điều kiện (luật pre-reg, cơ học)
- **D0**: G1 ✔ (mean +4,41%; lo CI raw +2,22; lo CI inflate +1,83) · G2 ✔ 4/4 năm · G3 ✔ n = 489 · G4 ✔ excess +2,45% (CI raw [−1,56; +6,54] chứa 0; G4 chỉ đòi mean > 0) ⇒ **PASS**.
- **D1**: G1 ✔ (+3,49%; +1,23; +0,82) · G2 ✔ 4/4 · G3 ✔ 489 · G4 ✔ +1,88% ⇒ **PASS**.
- **GO-R2 (cơ học).**

## Đánh giá rủi ro (không đổi verdict cơ học — MASTER quyết)
1. **Phụ thuộc quy ước SL.** "Kiểm trên close 1h + fill tại mức" lạc quan kép (bỏ sót chạm intrabar, rồi fill đẹp khi chạm). Hai cách nhất quán hơn đều làm G1 trượt:
   fill tại close 1h kích hoạt ⇒ D0 +2,10% CI [−0,27; +4,90]; stop thật trên HIGH 1m ⇒ D0 +2,10% CI [−0,10; +4,69], D1 +1,74% CI [−0,35; +4,18].
   ~7,5 điểm % lệnh bị quét intrabar ≥ +15% rồi về — mô hình 1h tính chúng là lệnh thắng. Fill gap hiếm (lỗ SL 1m TB 15,26% ≈ mức).
2. **Payoff đuôi phải.** Win 51%, SL 44% (1h) / 52% (1m); median net D0 +1,24% (1h) / −14,6% (1m); bỏ top 10% lệnh ⇒ −0,26%.
   Đường giá: median retEnd D+7 −10,6% nhưng mean chỉ −2,1%; pSQ10 D+7 54%, maxFav mean D+7 +29% ⇒ "pump-rồi-xả" đúng ở trung vị, nhưng squeeze phải dày; D+14/D+30 mean dương (đuôi phải tăng mạnh).
   2025 (n 239): mean +4,83% nhưng median −12,93% và SL 50%.
3. **Excess vs ALL** dương (mean +2,45%, median +10,36%) nhưng CI chứa 0 — phần "COIN NÀY giảm" có, chưa chắc.
4. **Chưa mô hình**: slippage/spread ngày niêm yết; giới hạn đòn bẩy/notional ngày đầu (Binance thường cap thấp cho hợp đồng mới) và khả năng thực sự mở short tại close D0;
   survivorship (thiếu sym delist); đổi tên (KAIA) lọt vào mẫu.

Không thêm biến thể / không tune sau khi thấy số. Nếu đi tiếp, đề xuất pre-reg lại R2 với SL trên HIGH 1m làm chuẩn (tham số giữ nguyên) trước khi dùng listing làm gate/sự kiện cho R1.
