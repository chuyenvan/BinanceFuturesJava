# PREREG_HO2026_NOTF — sensitivity HO 2026 trên universe không TradFi, không INDEX (2026-10-28)

Nguồn: `docs/result/HO2026_TRADFI_AUDIT.md` §7 (commit 06d6edea). MASTER duyệt nguyên văn ngày 10-28 và thêm D5 (mô tả).
Tài liệu này được commit TRƯỚC khi dựng dữ liệu hay đẩy kernel nào.
**Trạng thái nhìn số (khai thật):** đã nhìn số HO4, X14, ECMEAS và GOLIVE 2026, cùng mọi số trong audit: leg TF, ước lượng thô, và 18 ngày cờ noTFIDX. Đây là **sensitivity, KHÔNG phải holdout mới**.

## 1. Tập loại X (thay đổi DUY NHẤT so với HO4-P1)
- Nguồn phân loại: `v12/fixtures/exchangeInfo_20261027_1140.json.gz` (md5 `115dd8e5d3ec1b2f5be41df995fb76a2`).
- Luật:
  - s là TF ⇔ `contractType` chứa TRADIFI/TRADFI;
  - s là INDEX ⇔ `underlyingType=INDEX`.
- Phân loại **point-in-time**: s ∈ X tại t ⇔ s có nhãn TF/INDEX và t ≥ onboardDate của hợp đồng mang nhãn đó.
- **Đính chính so với audit:** MDTUSDT là ticker dùng lại. Nó là crypto Measurable Data, SETTLED 2026-10-13. Mã TF MDT (Medtronic) mới niêm yết 2026-10-21, tức sau cửa sổ. Vì vậy trong cửa sổ HO, MDTUSDT là crypto và KHÔNG thuộc X.
  - Mọi symbol còn lại của X không có dữ liệu Vision nào trước onboardDate (đã kiểm 231/231), nên luật point-in-time tương đương loại tĩnh.
  - MDTUSDT có 0 leg trong mọi run HO 2026, nên số leg/PnL trong audit không đổi. Số symbol TF mỗi tháng trong audit thừa 1.
- **X = 230 symbol** (227 TF USDT + ALLUSDT, BTCDOMUSDT, DEFIUSDT). Danh sách sắp xếp, mỗi dòng một symbol, md5 `6e296227a3a4789f7602bcb38e4f00b7`. File trên Oracle: `~/claude_master/ho_tradfi_wk/X_notf_v2.txt`; kernel nhúng nguyên danh sách và assert md5.
- Universe A1 = universe HO4-P1 (`ho4p1-x26-q*/run.py:69-73`: Vision ∩ USDT ∩ `^[A-Z0-9]+$` ∩ ∉ {BTCDOM, USDC} ∩ mapper 863) \ X.

## 2. Áp ở mọi tầng
- **Ticker 2026:** dựng lại bằng chính chuỗi HO4-P1, gồm exporter quý q1/q2/q3 (`in_uni` thêm `s ∉ X`) và kernel copy tk26.
- **Sinh tự động từ ticker A1:** market.bin, gate store, Tool1, nhãn, CLOSES_1H, funding Vision, lifecycle cửa sổ.
- **Chuỗi hạ nguồn:** chuỗi `ho4p1_chain` y26, cùng model, seed và mã. Thêm một bước: id mapper của X bị loại khỏi OI ghép, Tool1, CLOSES và bins, giống cách đang làm với 16 id trùng (§6.2a ADDENDUM-6). Pred p15 8 seed, feat_v2, pool S1, net015, bins và funding.bin dựng lại.
- **Không đổi:** đoạn ≤ 2025-12-31 của mọi artefact giữ NGUYÊN byte như chuỗi gốc.
- **ALT_EW cho cờ X14:** biến thể noTFIDX, tức ALT_EW tính theo luật `build_index` sau khi bỏ X (MDT là crypto). Đã dựng lại từ Vision, khớp `ew_2026.npz` max|Δ| 4,9e-17 khi không bỏ gì.
  - Có **18 ngày cờ**: `20260205-20260214,20260216-20260217,20260224-20260225,20260606-20260607,20260610-20260611`.
  - Series lưu tại `~/claude_master/ho_tradfi_wk/a2v2/`.

## 3. Cấu hình
- Các cấu hình: **k24-s** (bản chính HO4), **k24-b** (nền của X14) và **x14** (k24-b + `SIM_LOSER_TS_EXT_HOURS=336` + `SIM_LOSER_TS_EXT_DAYS` = 18 ngày trên), mỗi cấu hình × 8 seed {42, 7, 13, 21, 99, 123, 777, 2024}. Tổng 24 kernel A1: `nt-k24-s-s*`, `nt-k24-b-s*`, `nt-x14-s*`.
- Override y hệt run gốc (`ho4p1_queue.CFGS`, penalty 0,01675 cho bản s), `SIM_END_DATE=20261001`, `ticker_min_days=2099`, `HOLDOUT_UNSEAL` chỉ trong extra_env. Không đổi tham số chiến lược nào.

## 4. Hạ tầng (chốt trước khi dựng)
- **Jar, bảo mật:**
  - Không upload jar nào chưa qua `nup3_wk/jar_sec_check.py` ok=true.
  - Bản sao dataset `ho4p1-jar-exp` (exporter 99c5f040) **FAIL** sec check, nghi chứa key thật. Vì vậy KHÔNG dùng lại; đã báo MASTER.
  - Dataset `sim-jar-nsel` (sim b7c89f09) không còn truy cập được (403).
- **Exporter:** build lại từ đúng commit `0594986e` với `PrivateConfig` STUB. Điều kiện: sec check ok=true VÀ mọi `.class` trùng md5 với jar 99c5f040 ngoại trừ `com/binance/chuyennd/config/PrivateConfig*.class` (so trên bản sao dataset đã tải về). Không đạt ⇒ DỪNG, báo MASTER.
- **Sim:** dataset `sim-jar-tsx` (cc0f9d11, sec check ok=true) dùng cho cả 3 cấu hình. Căn cứ: P0 `tsx-ho-p0-s42` (k24-b, không key X14) cho md5 printDone = `ho4-k24-b-s42`. k24-s được kiểm bằng cổng A0'.
- **Cổng tất định A0'** phải PASS trước khi đẩy bất kỳ kernel A1 nào:
  - (a) Exporter `a0p-x26-q1`: cfg y hệt `ho4p1-x26-q1`, chỉ đổi jar sang bản STUB. `MANIFEST.json` phải trùng md5 137/137 với `ho4p1-x26-q1`.
  - (b) Sim `a0p-k24-s-s42`, `a0p-k24-b-s42`, `a0p-x14-s42` trên artefact gốc HO4-P1 (chain `ho4p1-chain-y26`, tk `ho4p1-tk26`) với jar tsx. md5 printDone phải bằng lần lượt `6989a312…` (ho4-k24-s-s42), `7cc8864c…` (ho4-k24-b-s42), `bb609455…` (tsx-ho-x14-s42).
  - Nếu (a) FAIL ⇒ dựng A0' đầy đủ (exporter q1–q3 + chain không loại X) và dùng làm nền.
  - Nếu (b) FAIL ⇒ chạy A0' đủ 24 kernel làm nền.
  - Không dùng run gốc làm nền khi cổng tương ứng FAIL.
- **Chạy lại:** chỉ khi lỗi hạ tầng (rc≠ok, mapper < 800, timeout, lỗi Kaggle), một lần, cfg y hệt. Ghi lại mọi lần.

## 5. Validate (phải PASS trước khi chấm)
- **V1.** Ticker A1 có 0 symbol ∈ X. Với mọi ngày, tập con symbol ∉ X của ticker A1 trùng từng ô với ticker gốc: so (ts, sym, o, h, l, c, qv) trên mẫu ≥ 10 ngày phủ T1–T9, cộng đếm toàn bộ 273 ngày.
- **V2.** ALT_EW A1 = series a2v2 noTFIDX (max|Δ| ≤ 1e-12); chuỗi cờ trong cfg x14 = 18 ngày ở §2.
- **V3.** 0 leg ∈ X trong printDone A1.
- **V4.** Scorer tự kiểm như HO4: E MTM vs equity_final ≤ 0,01 %, thiếu giá = 0.
- **V5.** Parity tự động như `ho4p1_queue.check`: jar, override, pred md5 theo seed, ticker 273/273 (md5 A1 mới), FUND selfcheck, mapper, penalty, UNSEAL. Với x14 thêm dòng `[TSX] extHours=336`.

## 6. Thước
- **Scorer:** HO4 `ho4_score_a.py` (k24-s, k24-b) và scorer TS_MKT_EXT HO (`tsx_ho_score.py` / `ecm_mtm_h`) cho x14, giá close 1m Vision, giữ y nguyên.
- **Đo trên W9/H1/Q3:** mean ΣPnL_S, số seed > 0, ROI MTM, maxDD MTM.
- **So sánh:** Δ paired A1 − A0 theo seed (ΔROI pp, ΔmaxDD pp); ΔX14 = x14 − k24-b trong từng universe.
- **Nền A0:** run gốc (ho4-k24-s-*, ho4-k24-b-*, tsx-ho-x14-*) nếu cổng A0' PASS.

## 7. Luật quyết (chốt trước)
- **D1 HO4 E0 (k24-s).** E0 = mean ΣPnL_S > 0 VÀ ≥ 6/8 seed > 0, tính trên A1 cho W9/H1/Q3.
  - W9/H1 giữ PASS ⇒ "HO4 vững với TF".
  - Đổi ⇒ báo MASTER; số go-live lấy theo A1.
- **D2 X14** (luật §7 TS_MKT_EXT addendum 1, y nguyên). Trên A1:
  - CONFIRM giữ nếu: mean ΔPnL(x14 − k24-b) > 0 VÀ 8/8 seed ≥ 0 VÀ mean ΔmaxDD ≥ −1 pp.
  - Ngược lại ⇒ "chưa xác nhận trên universe go-live"; MASTER quyết trước go-live.
- **D3 Vật chất.**
  - "Không vật chất" ⇔ |mean ΔROI_W9 (A1 − A0)| ≤ 1,0 pp VÀ |mean ΔmaxDD_W9| ≤ 1,0 pp, đúng cho CẢ k24-s và x14.
  - Ngược lại ⇒ phát hành lại GOLIVE_QUARTERLY 2026 và ECMEAS H theo A1.
- **D4 Q3.** Chỉ mô tả, vì đã nhìn. Q3 PASS trên A1 KHÔNG được dùng làm bằng chứng nâng hạng.
- **D5 (mô tả, MASTER thêm 10-28).** Tính cho mỗi cấu hình × cửa sổ, gộp 8 seed và theo seed, khoá leg (sym, start):
  - (i) leg TF bị bỏ: leg A0 ∈ X, gồm số leg và PnL realized;
  - (ii) **leg thay thế**: leg A1 có khoá không có trong A0 cùng seed (slot giải phóng cho crypto), gồm số leg và PnL realized;
  - (iii) leg crypto mất: leg A0 ∉ X không có trong A1.
  - Không dùng D5 để quyết.
- **Không tune:** không đổi ngưỡng, cửa sổ, seed, model, TOPK, quota, giờ X14 hay luật cờ. Chấm một lần.

## 8. Ngoài phạm vi
Universe "như shadow v1.1" (khoảng 223 TF, ngoài mapper 863) không mô phỏng được khi mapper khoá; đây là khoảng trống đã biết.
