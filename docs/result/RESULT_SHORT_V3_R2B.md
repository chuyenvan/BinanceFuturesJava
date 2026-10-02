# RESULT_SHORT_V3_R2B — Listing chuẩn SL 1m-high (vòng R2b, PROGRAM_SHORT_V3 ADDENDUM 1)

Ngày 2026-10-02 · Pre-reg `docs/prereg/PREREG_SHORT_V3_R2B.md` @ 54f64e07 (commit TRƯỚC khi chạy) · Script `research/analysis/short_v3_r2b_listing1m.py`
→ `docs/result/RESULT_SHORT_V3_R2B.json` (kèm toàn bộ lệnh D0/D1). Tham số y hệt R2; chỉ đổi chuẩn SL: HIGH 1m, fill tại mức (open ≥ mức ⇒ fill open) + trượt 0,2%.

**VERDICT (cơ học): NO-GO — cả D0 và D1 trượt G1 (CI raw/inflate chứa 0) và G5 (bỏ 10% lệnh tốt nhất ⇒ −2,8% / −2,9%).**
Listing short không phải edge trung vị: payoff nhị phân ~52% lệnh SL ≈ −15,7%, ~48% lệnh không SL ≈ +21%; mean dương chỉ nhờ đuôi phải.

## Sanity (tất cả PASS)
- **SA tái lập R2**: cùng code, chế độ tắt 1m ⇒ D0 +4,410% (R2 +4,41), D1 +3,488% (R2 +3,49); khớp từng lệnh với `trades_D0` của R2 JSON 489/489, max |Δpnl| 5e−7 (làm tròn JSON).
- **SB 10 lệnh SL mẫu** (D0, seed 20260905; bảng cuối file): mọi mẫu high phút SL ≥ mức và max high các phút trước < mức; 10/10 fill tại mức (open < mức).
  DODOX 2023-08-09: chạm 02:04 (high 0,1605 > mức 0,1473) nhưng close 1h giờ đó 0,1330 và không giờ nào close ≥ mức ⇒ R2 1h tính +12,1%, chuẩn 1m −15,3% (đúng kiểu "quét intrabar").
- **SC parse 1m**: 814 (sym, t0) duy nhất, 136 372 cặp giờ: close phút cuối = CLOSES_1H 100% (|rel|>1e−4: 0); high ≥ max(open, close) 100%; phút thiếu 0,28%.
  Mọi lệnh SL theo 1h đều SL theo 1m tại thời điểm ≤ (0 vi phạm); fallback 1h dùng 0 lần; giá thoát thời gian 1m = 1h (0 lệch > 1e−4).
  Nguồn thoát D0: SL 1m 253 · close 1m cuối 235 · 1h 1 (`币安人生USDT`: tên non-ASCII, bộ parse 1m của slcheck dùng độ dài ký tự thay byte ⇒ không đọc được 1m;
  lệnh này không SL theo 1h, thoát bằng close 1h — ảnh hưởng không đáng kể). Gap-fill: 1 lệnh/nhánh (RAVE 2025-12-15, open phút chạm = +29,6% ⇒ lỗ 29,7%).
- **SD so với post-hoc R2**: trùng tuyệt đối (D0 +2,097%, SL 51,74%; D1 +1,737%, SL 50,72%) ⇒ quy ước pre-reg không khác post-hoc.
- **n**: 489/489 như R2 (loại L5 1: BTCDOMUSDT; L3b 0; L4 0).
- Ghi chú "bỏ top 10%" của R2 (−0,26%) khác số 1h ở đây (−0,34%) do quy ước số lệnh bỏ (pre-reg R2b chốt `ceil(0,1·n)` = 49); không ảnh hưởng kết luận.

## Chiến lược — chuẩn SL 1m-high (net %/lệnh sau phí 0,112 + funding exact)

| nhánh | n | net mean | net med | CI raw | CI inflate ×1,18 | win% | SL-rate | min | p5 | funding mean | excess mean/med | excess CI raw | bỏ top10% mean/med |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | 489 | **+2.10** | -14.59 | [-0.10;+4.69] | [-0.49;+5.16] | 44.8 | 51.7 | -29.61 | -16.64 | -0.388 | +2.45 / +10.36 | [-1.56;+6.54] | -2.81 / -15.10 |
| D1 | 489 | **+1.74** | -14.16 | [-0.35;+4.18] | [-0.72;+4.62] | 44.8 | 50.7 | -29.61 | -16.69 | -0.286 | +1.88 / +8.86 | [-1.79;+5.64] | -2.94 / -15.05 |

## Theo năm (năm của t0, chuẩn 1m)

| nhánh | năm | n | net mean | net med | CI raw | SL-rate | funding | excess |
|---|---|---|---|---|---|---|---|---|
| D0 | 2022 | 24 | +7.54 | +5.71 | [-0.90;+18.16] | 33.3 | -0.268 | +2.23 |
| D0 | 2023 | 95 | +0.50 | -0.75 | [-3.26;+3.65] | 43.2 | -0.441 | +5.31 |
| D0 | 2024 | 131 | +2.41 | -1.61 | [-0.58;+5.57] | 47.3 | +0.153 | +1.40 |
| D0 | 2025 | 239 | +2.01 | -15.14 | [-1.99;+6.52] | 59.4 | -0.675 | +1.91 |
| D1 | 2022 | 24 | +8.64 | +9.41 | [+0.52;+16.02] | 29.2 | -0.415 | +8.00 |
| D1 | 2023 | 95 | -1.21 | -7.63 | [-4.80;+1.95] | 45.3 | -0.269 | +3.06 |
| D1 | 2024 | 129 | +2.32 | -4.21 | [-0.44;+5.39] | 47.3 | +0.191 | +2.37 |
| D1 | 2025 | 241 | +1.90 | -15.05 | [-1.89;+5.93] | 56.8 | -0.536 | +0.55 |

## Luật GO (G1–G5, chuẩn 1m)

| nhánh | G1 (mean>0, lo raw>0, lo infl>0) | G2 (≥3/4 năm) | G3 (n≥120) | G4 (excess>0) | G5 (bỏ top10% > −0,5%) | PASS |
|---|---|---|---|---|---|---|
| D0 | False (+2.10; -0.10; -0.49) | True (4/4) | True (489) | True (+2.45) | False (-2.81) | **False** |
| D1 | False (+1.74; -0.35; -0.72) | True (3/4) | True (489) | True (+1.88) | False (-2.94) | **False** |

**VERDICT: NO-GO**

## So với R2 1h (cùng code, chế độ tắt 1m) — phần "SL-convexity" đã mất

| nhánh | chuẩn | net mean | net med | CI raw | CI infl | SL-rate | năm dương | bỏ top10% mean |
|---|---|---|---|---|---|---|---|---|
| D0 | 1h (R2) | +4.41 | +1.24 | [+2.22;+6.99] | [+1.83;+7.46] | 44.2 | 4/4 | -0.34 |
| D0 | 1m (R2b) | +2.10 | -14.59 | [-0.10;+4.69] | [-0.49;+5.16] | 51.7 | 4/4 | -2.81 |
| D1 | 1h (R2) | +3.49 | -0.29 | [+1.23;+5.88] | [+0.82;+6.31] | 44.2 | 4/4 | -1.05 |
| D1 | 1m (R2b) | +1.74 | -14.16 | [-0.35;+4.18] | [-0.72;+4.62] | 50.7 | 3/4 | -2.94 |

Phân rã Δmean (1m − 1h) theo nhóm lệnh:

| nhánh | nhóm | n | net 1h mean | net 1m mean | đóng góp vào Δmean |
|---|---|---|---|---|---|
| D0 | sweep_1m_only | 37 | +14.74 | -15.62 | -2.30 |
| D0 | both_SL | 216 | -15.69 | -15.72 | -0.02 |
| D0 | none_SL | 236 | +21.18 | +21.18 | +0.00 |
| D0 | sl1h_only | 0 | — | — | +0.00 |
| D0 | **tổng Δ** | | | | **-2.31** |
| D1 | sweep_1m_only | 32 | +11.49 | -15.50 | -1.77 |
| D1 | both_SL | 216 | -15.70 | -15.67 | +0.02 |
| D1 | none_SL | 241 | +19.63 | +19.63 | +0.00 |
| D1 | sl1h_only | 0 | — | — | +0.00 |
| D1 | **tổng Δ** | | | | **-1.75** |

## SB — 10 lệnh SL-1m mẫu (D0, seed 20260905)

| sym | t0 | P0 | mức SL | phút SL (open UTC) | open | high | max high trước | fill | close 1h giờ đó | SL 1h? | net 1m | net 1h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DODOXUSDT | 2023-08-09 00:00 | 0.1281 | 0.147315 | 2023-08-09 02:04 | 0.141 | 0.1605 | 0.1439 | 0.147315 | 0.133 | False | -15.31 | +12.07 |
| 1MBABYDOGEUSDT | 2024-09-17 00:00 | 0.0018664 | 0.00214636 | 2024-09-17 16:28 | 0.002062 | 0.00215 | 0.0020773 | 0.00214636 | 0.0020933 | True | -15.79 | -16.03 |
| HIPPOUSDT | 2024-11-14 00:00 | 0.02108 | 0.024242 | 2024-11-14 17:33 | 0.02412 | 0.02433 | 0.0242 | 0.024242 | 0.0233 | True | -14.81 | -14.61 |
| MORPHOUSDT | 2024-11-29 00:00 | 1.2489 | 1.43624 | 2024-11-30 01:08 | 1.4298 | 1.4404 | 1.43 | 1.43624 | 1.5189 | True | -15.22 | -15.22 |
| TRUMPUSDT | 2025-01-20 00:00 | 46.618 | 53.6107 | 2025-01-20 04:47 | 51.684 | 54.176 | 52.363 | 53.6107 | 51.829 | True | -15.20 | -15.20 |
| CUDISUSDT | 2025-08-21 00:00 | 0.09543 | 0.109745 | 2025-08-22 14:05 | 0.10499 | 0.11228 | 0.10788 | 0.109745 | 0.11456 | True | -16.29 | -16.29 |
| VFYUSDT | 2025-10-01 00:00 | 0.11943 | 0.137344 | 2025-10-01 08:03 | 0.13337 | 0.14136 | 0.13692 | 0.137344 | 0.13181 | True | -15.50 | -15.13 |
| TRUTHUSDT | 2025-10-02 00:00 | 0.014655 | 0.0168532 | 2025-10-02 03:47 | 0.016457 | 0.0172 | 0.016597 | 0.0168532 | 0.018499 | True | -15.31 | -15.31 |
| APRUSDT | 2025-10-24 00:00 | 0.6246 | 0.71829 | 2025-10-24 04:47 | 0.69762 | 0.73327 | 0.7038 | 0.71829 | 0.72449 | True | -15.27 | -15.27 |
| BEATUSDT | 2025-11-13 00:00 | 0.36571 | 0.420566 | 2025-11-13 14:23 | 0.40331 | 0.4245 | 0.4194 | 0.420566 | 0.43239 | True | -15.17 | -15.17 |

## Kết luận theo từng điều kiện (luật pre-reg, cơ học)
- **D0**: G1 ✘ (mean +2,10%; lo CI raw −0,10; lo CI inflate −0,49) · G2 ✔ 4/4 năm (2023 chỉ +0,50) · G3 ✔ n = 489 · G4 ✔ excess +2,45% (CI raw [−1,56; +6,54] chứa 0)
  · G5 ✘ bỏ 49 lệnh tốt nhất ⇒ mean −2,81% (ngưỡng −0,5%) ⇒ **FAIL**.
- **D1**: G1 ✘ (+1,74%; −0,35; −0,72) · G2 ✔ 3/4 (2023 −1,21) · G3 ✔ 489 · G4 ✔ +1,88% · G5 ✘ −2,94% ⇒ **FAIL**.
- **GO-R2b: NO-GO.** Không có nhánh nào qua; trượt 2/5 điều kiện ở cả hai nhánh, trong đó G5 trượt xa (−2,8% vs −0,5%), không phải sát biên.

## Phần "SL-convexity" đã mất (so với R2 1h)
- Δmean D0 = −2,31 điểm %, gần như TOÀN BỘ từ 37 lệnh (7,6%) bị quét intrabar ≥ +15% nhưng close 1h không bao giờ ≥ mức: R2 1h tính chúng +14,7%/lệnh
  (squeeze rồi sập — chính kịch bản listing), chuẩn 1m tính −15,6%/lệnh. 216 lệnh SL ở cả hai chuẩn: Δ ≈ 0 (fill tại mức như nhau, gap hiếm);
  236 lệnh không SL: Δ = 0. D1 tương tự: 32 lệnh quét, Δ −1,75.
- Tức là ~52% edge R2 1h đến từ việc quy ước 1h "không nhìn thấy" squeeze trong giờ. Với stop thật, short listing phải chọn: stop ⇒ bị quét đúng lúc trước khi sập;
  không stop ⇒ đuôi phải của giá (maxFav D+7 mean +29% trên 1h close) — vòng này không đo, và không được thêm biến thể.
- Median net 1m −14,6% (D0): lệnh "điển hình" là lệnh SL. Phân phối hai đỉnh: không-SL mean +21,2% (n 236) vs SL ≈ −15,7% (n 253).

## Đánh giá rủi ro (không đổi verdict)
1. **Đuôi phải + funding**: bỏ 10% tốt nhất ⇒ −2,8%; funding short trả TB −0,39%/lệnh (D0), đuôi trái tới −8..−10% ở lệnh squeeze dài.
2. **2025 (n 239, 49% mẫu)**: SL-rate 59%, median −15,1%, mean +2,01% CI [−1,99; +6,52] — năm nhiều listing nhất cũng là năm squeeze dày nhất.
3. **Excess vs ALL** dương (mean +2,45%, median +10,4%) nhưng CI chứa 0 — listing có kém thị trường ở trung vị (ret7 median −10,6%), nhưng không khai thác được
   bằng short + stop 15% vì đường đi qua vùng +15% trước.
4. **Còn lạc quan**: fill tại mức khi open < mức (stop-market thật trong phút spike trượt > 0,2%); 1 lệnh non-ASCII không có 1m.

## Giới hạn (ghi trước trong pre-reg, chưa mô hình)
- **Survivorship**: CLOSES_1H/kline_1m_opt gần như không có sym delist năm 2025 (R2: 0 sym kết thúc 2025, 36 sym kết thúc trước 2025-12-20 tổng).
  Chiều lệch: coin bị delist thường sập ⇒ thiếu chúng làm short trông KÉM hơn thực (bias CHỐNG lại chiến lược). Không sửa. Độ lớn chưa định lượng;
  muốn lật NO-GO cần đủ coin delist thiếu để kéo mean lên ~+2,5 điểm VÀ bỏ-top10% lên > −0,5% — không thể suy từ dữ liệu này.
- Rename (KAIA = KLAY) lọt vào mẫu (R2 S5); không loại.
- Slippage/spread ngày niêm yết, cap đòn bẩy/notional ngày đầu, khả năng thực sự mở short tại close D0: chưa mô hình — đều làm kết quả KÉM thêm, không cứu được NO-GO.

Không thêm biến thể / không tune sau khi thấy số. Theo PROGRAM: R2 không còn là ứng viên gate/sự kiện cho R1 dưới chuẩn SL 1m.
