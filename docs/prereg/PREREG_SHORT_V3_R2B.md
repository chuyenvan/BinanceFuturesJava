# PREREG_SHORT_V3_R2B — Listing chuẩn SL 1m-high (vòng R2b của PROGRAM_SHORT_V3 ADDENDUM 1)

Ngày 2026-10-02 · Chương trình: `docs/research/PROGRAM_SHORT_V3.md` @ df2ce308 (ADDENDUM 1) · Executor: research agent · MASTER: Claude.
Pre-reg này commit TRƯỚC khi chạy script R2b. Đã biết trước (công khai, từ R2 `38a99bca`): bản post-hoc SL 1m của R2 cho D0 +2,10% CI raw [−0,10; +4,69].
Vòng này chính thức hoá chuẩn đo đó với luật GO của ADDENDUM; KHÔNG đổi tham số, KHÔNG thêm biến thể, KHÔNG tune.
Kế thừa nguyên mọi định nghĩa của `docs/prereg/PREREG_SHORT_V3_R2.md` @ ffe806b2 (§2 nguồn dữ liệu, §3 listing_day/D0/L1–L6, §7 thống kê,
excess vs ALL) trừ phần ghi rõ thay đổi dưới đây.

## 1. Chép nguyên ADDENDUM 1 §R2b
> ### R2b — LISTING chuẩn 1m (cùng tham số R2, đổi CHUẨN đo)
> Chiến lược y hệt R2 (short close D0/D1, 7d, SL +15%, phí 0,112, funding exact) nhưng SL kiểm trên HIGH 1m (fill tại mức SL; nếu open 1m vượt SL thì fill tại open). k=2 (D0/D1), inflate 1,18. Thêm: cột "bỏ 10% lệnh tốt nhất" (fragility), và SL-rate.
> GO-R2b ⇔ net > 0 ngoài CI raw & inflate; ≥3/4 năm; n ≥ 120; excess vs ALL > 0; VÀ "bỏ 10% tốt nhất" vẫn > −0,5% (không sống chỉ nhờ đuôi).
> Ghi rõ survivorship (file không có coin delist 2025) — chiều lệch: coin delist thường sập ⇒ thiếu chúng làm KÉM short (bias chống lại chiến lược), nêu nhưng không "sửa".

## 2. Tập lệnh (không đổi so với R2)
Listing, D0/fallback D1, nhánh D0 và D1, t0, P0, loại trừ L3b/L4/L5: tái dùng NGUYÊN hàm `find_listings`/`build_arms` của
`research/analysis/short_v3_r2_listing.py` (import, không sửa). Kỳ vọng n = 489/489 như R2; lệch ⇒ báo, không sửa.

## 3. Dữ liệu 1m
Aerospike `test.kline_1m_opt` (127.0.0.1:3222), đọc bằng hàm `fetch`/`extract` của `research/analysis/short_v3_r2_slcheck.py` (import, không sửa):
mỗi lệnh lấy ma trận phút m = 0..10079, phút m có open time = t0 + m·60s (phút đầu tiên SAU entry; phút cuối đóng tại t0 + 168h).
Field O/H/C (float32). Chỉ đọc ngày ≤ 2025-12-31 (L4 đảm bảo t0+168h ≤ 2026-01-01 00:00).

## 4. Quy ước fill 1m (KHÓA)
- `lvl = 1,15 · P0`. Duyệt phút m = 0..10079 theo thứ tự; SL tại phút ĐẦU TIÊN có `high_m ≥ lvl`.
- **Fill**: nếu `open_m ≥ lvl` (gap qua mức) ⇒ fill = open_m; ngược lại fill = lvl. Lỗ giá = fill/P0 − 1 + 0,002
  (giữ nguyên trượt 0,2% của quy ước R2/P0A — "tham số y hệt R2"). Open thiếu (NaN) ⇒ fill = lvl.
- **Cùng nến SL ưu tiên**: chiến lược không có TP/trailing; nếu SL chạm ở phút cuối (m = 10079) ⇒ SL thắng thoát thời gian.
- **Thoát thời gian** (không SL): tại close phút m = 10079 (đóng t0 + 168h); NaN ⇒ close 1m hữu hạn cuối cùng trong cửa sổ;
  không có phút nào ⇒ dùng giá thoát 1h của R2 (`pend`). Báo số lệnh mỗi trường hợp.
- **Phút thiếu (fallback 1h)**: nếu có close 1h với ts = t0 + k·1h (k = 1..168) mà close ≥ lvl và trước đó chưa có SL 1m (trường hợp chỉ xảy ra
  khi phút của giờ đó thiếu), SL tại ts đó với fill = close 1h đó (bảo thủ, như độ nhạy 4.i của R2). Thời điểm SL = min(phút 1m, giờ fallback). Báo số lệnh.
- `t_exit` cho funding: SL tại phút m ⇒ t0 + (m+1)·60s; fallback giờ ⇒ ts giờ đó; thời gian ⇒ t0 + 168h. fund = Σ rate settle ∈ (t0, t_exit], rate>0 ⇒ short NHẬN.
- `net = −(lỗ giá nếu SL, ngược lại ret_7d) − 0,00112 + fund`, ret_7d = giá thoát/P0 − 1.

## 5. Thống kê (như R2 §7)
- Mỗi nhánh: n, net mean/median, win%, SL-rate (1m), tail (min, p1, p5), fund mean, ret7 mean/median, excess mean/median + CI raw.
- **CI block theo THÁNG** (tháng UTC của t0, nb = 48): `default_rng(20260905)`, `integers(0, 48, (2000, 48))`, replicate = Σnet/Σcount, percentile 2,5/97,5;
  **inflate k=2 (D0/D1) = 1,18**: `[μ − 1,18(μ−lo), μ + 1,18(hi−μ)]`. Dùng nguyên `ci_block` của R2.
- **Theo năm** (năm t0): n, mean, median, SL-rate, CI raw block tháng trong năm, fund, excess.
- **"Bỏ 10% tốt nhất"**: sắp net giảm dần, bỏ `ceil(0,10·n)` lệnh đầu (n = 489 ⇒ bỏ 49), báo mean (và median) phần còn lại.
- **excess vs ALL cùng ngày**: y hệt R2 (ALL_t0 = mean ret 7d raw 1h của mọi coin universe có close tại t0; excess = ALL_t0 − ret_7d(listing), ret_7d
  tính trên close 1h tại t0+168h như R2 — độc lập với SL). Dùng nguyên cột `excess` của `build_arms`.
- **So với R2 1h**: cùng bảng với chuẩn 1h (chế độ tắt 1m); số lệnh SL theo 1m nhưng không SL theo 1h ("quét intrabar"), net 1h vs net 1m của nhóm đó;
  phân rã Δmean = Σ(net1m − net1h)/n theo nhóm (quét intrabar / SL cả hai / không SL) ⇒ phần "SL-convexity" đã mất.

## 6. Luật GO (áp cơ học)
Mỗi nhánh X ∈ {D0, D1}, PASS_X ⇔ đồng thời (tất cả trên chuẩn 1m):
- **G1** net mean > 0 VÀ cận dưới CI raw > 0 VÀ cận dưới CI inflate (×1,18) > 0;
- **G2** net mean theo năm > 0 ở ≥ 3/4 năm 2022–2025 (năm không lệnh = không dương);
- **G3** n ≥ 120;
- **G4** mean excess vs ALL cùng ngày > 0;
- **G5** mean net sau khi bỏ 10% lệnh tốt nhất > −0,5%.
**GO-R2b ⇔ ≥ 1 nhánh PASS** (như R2; inflate 1,18 đã trả giá chọn 1 trong 2 nhánh). Ngược lại NO-GO. Báo từng điều kiện từng nhánh.
Không thêm nhánh, không lọc thêm, không đổi SL/T/fill sau khi thấy số.

## 7. Sanity bắt buộc (báo trong RESULT trước kết luận; FAIL ⇒ dừng, báo, không kết luận)
- **SA (tái lập R2)**: cùng code ở chế độ tắt chuẩn 1m (SL trên close 1h, lỗ cố định 15,2%) ⇒ net mean D0 = +4,41% ±0,05 và D1 = +3,49% ±0,05;
  so từng lệnh với `trades_D0` của `RESULT_SHORT_V3_R2.json` (max |Δpnl| báo). Lệch ⇒ FAIL.
- **SB (10 lệnh SL mẫu)**: rút 10 lệnh SL-1m nhánh D0 (seed 20260905), in sym, t0, P0, lvl, phút SL (UTC), open/high phút đó, fill, close 1h của giờ đó,
  có SL 1h hay không ⇒ kiểm tay (high ≥ lvl; phút trước đó high < lvl).
- **SC (parse 1m)**: close phút cuối mỗi giờ = CLOSES_1H (tỉ lệ |rel| > 1e-4 < 1%); high ≥ max(open, close) (vi phạm < 0,1%); tỉ lệ phút thiếu;
  mọi lệnh SL theo 1h phải SL theo 1m tại thời điểm ≤ (trừ khi phút thiếu ⇒ fallback, đếm). Giá thoát thời gian 1m = 1h (đếm lệch > 1e-4).
- **SD (nhất quán post-hoc)**: so với `posthoc_SL1m` của R2 (D0 +2,10, D1 +1,74); lệch nhỏ chấp nhận được vì khác quy ước fallback — giải thích nếu |Δ| > 0,05.

## 8. Giới hạn đã biết (ghi trước)
- **Survivorship**: CLOSES_1H/kline_1m_opt gần như không có sym delist năm 2025 (R2: 0 sym kết thúc 2025). Chiều lệch: coin bị delist thường sập
  ⇒ thiếu chúng làm short trông KÉM hơn thực (bias CHỐNG lại chiến lược). Nêu, không sửa. Ngược lại, rename (KAIA) lọt vào mẫu: nêu, không loại.
- Slippage/spread ngày niêm yết (ngoài 0,2% ở SL), cap đòn bẩy/notional ngày đầu, khả năng thực sự mở short tại close D0: CHƯA mô hình.
- Stop 1m-high vẫn lạc quan so với stop-market thật trong phút spike (fill tại mức nếu open < mức; trượt thật có thể lớn hơn 0,2%).
- Script: `research/analysis/short_v3_r2b_listing1m.py` → `docs/result/RESULT_SHORT_V3_R2B.json` + `docs/result/RESULT_SHORT_V3_R2B.md`. Python `logging`, RAM < 4G.
