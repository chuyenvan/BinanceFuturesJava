# E2E_REPLAY_V12 — KẾT QUẢ LƯỢT CHÍNH THỨC (fixture 2026-11-05) — MASTER, 2026-11-17

**Kết luận theo đúng chữ prereg: (iii) = FAIL**, do tiêu chí E2 (22/23; 1 SUBMIT lệch budget 1,35e-4 > 1e-4, không gán được nhãn khai trước).
Mọi tiêu chí về LOGIC của jar (C1, E1, S1, D1 S-DCA, X1, F1, K1) PASS. Không tiêu chí nào được sửa sau khi thấy kết quả.

## 1. Lượt chạy
- Prereg: `vz_e1_wt/docs/prereg/PREREG_E2E_REPLAY_V12.md` (ea6c7a5b) + ERRATA1 (33633d41), ERRATA2 (593e7f45), ERRATA3 (409e1144),
  ERRATA4 (d663394f) — tất cả commit TRƯỚC khi dựng fixture 11-05.
- Harness `def1f034` (nhánh test/e2e-replay-v12), A1 duyệt (`~/claude_master/v12/A1_E2E_V12_R3.md`).
- Chạy 1 lần: 2026-11-17 01:32:27 +07, khoá `~/claude_master/e2e_v12/OFFICIAL_1105.lock` (errata rỗng), output
  `~/claude_master/e2e_v12/out1105_1117_0132/`, fixture `~/claude_master/e2e_v12/fx1105` (dựng trong lượt này).
- Jar trên classpath: md5 `641803565297d4065d90245e04a00f11`, 10/10 class nạp từ jar. md5 env 242 `8956befdffb7949676b1de392c82ddc7`,
  md5 nhãn (rỗng) `7af0c00e2e7e7fd072c8565acb7ed703`.
- Kiểm nguyên vẹn + phân xử độc lập: `~/claude_master/v12/A1_E2E_OFFICIAL_1105.md` (A1 Opus): nguyên vẹn PASS; tự tính lại từ file thô khớp.

## 2. Bảng tiêu chí
| Tiêu chí | Kết quả | Số chính |
|---|---|---|
| C1 cấu hình | PASS | jar đúng; banner LIVE-SIZING / LIVE-DCA-GRID / MINUTE-FIN / GATE-RATIO có; 0 tên biến thiếu |
| E1 chọn coin (R0, R0-DRY) | PASS | 24 leg PREDICT ≡ REF (tập + thứ tự) |
| S1 sizing (R0, R0-DRY, S-DCA) | PASS | 24 SUBMIT, lệch budget lớn nhất 0 (A1 tự tính: 1,4e-7); 3 leg đầu 225,0000 / 216,5647 / 208,4436 (tính tay prereg: 225,00 / 216,56 / 208,44); U lệch ≤ 1,1e-16; eq_at khớp |
| D1 tự nhiên | KHÔNG XẢY RA | không có DCA grid tự nhiên trong cửa sổ |
| D1 S-DCA | PASS | 2 cụm × 3 bậc đúng phút, legIdx, budget |
| X1 thoát (R0) | PASS | 24 cụm: 21 TRAIL + 3 TIME_STOP; lý do, phút, nhãn ≡ REF; stopPrice lệch lớn nhất 0,97 tick (ngưỡng 2) |
| F1 fin | PASS | đúng 1 leg (UAIUSDT) bị chặn, không thế chỗ |
| K1 | PASS | 0 ERROR, 0 latch, 0 KHAN |
| **E2 trung thực (R-OLD ↔ log dry thật)** | **FAIL** | 23/23 khớp symbol + phút + thứ tự; 22/23 khớp budget ≤ 1e-4; AINUSDT lệch 1,35e-4 (35,2176 vs 35,2224 USDT); 0 nhãn áp được |
| §6 vốn micro | micro = 1 000 | R-1000: 24/24 leg SUBMITTED (100 % ≥ 90 %) |

## 3. Lệch E2 (phân xử A1 độc lập, ERRATA 4 E14)
- Không nhãn khai trước nào áp được (LEGACY, exchangeInfo, khác jar r4q↔fin2: `git diff bc030d76..5e10325b` không khác ở C3LiveHook,
  C3MainEquity, C3LiveEntry, LiveBookC3) ⇒ E2 FAIL giữ nguyên.
- Nguyên nhân gốc (A1, chắc chắn cao về cơ chế): THIẾU SÓT ĐẦU VÀO của harness, không phải lỗi jar.
  - Bản dry thật cache equity 60 s theo markPrice và làm mới đúng giữa leg AIN và leg Q ⇒ 8 leg dùng C_eff 9 999,50, các leg sau
    9 998,40; replay dùng một giá trị 9 998,43 cho cả phút ⇒ lệch −1,07e-4.
  - Giá size ở bản thật là price_realtime tại giây quyết định; replay dùng giá nến ⇒ qty lệch (JCT 11 860 vs 11 642) ⇒ U lệch ±2,8e-5;
    riêng ở AIN hai phần lệch cùng dấu ⇒ 1,35e-4 (CLANKER sát ngưỡng 9,7e-5).
- Không có nguồn độc lập cho giá theo giây và pha cache trong dữ liệu đã kéo về (`pull242/2026-11-05`: chỉ sel_dump + feat_dump; log có
  1 dòng `[C3-LIVE-EQ]` cả ngày). Nạp C_eff suy ngược từ budget thật là khớp ngược ⇒ không làm.

## 4. Khác biệt live so với sim quan sát được trong lượt này (báo cáo, không phải tiêu chí)
- 3 cụm `ARM_CUNG_NEN` (jar ≡ REF-nhịp): JCTUSDT thoát sớm 4 phút so với ngữ nghĩa nến của sim; UAIUSDT sớm 1 phút; CAPUSDT dời SL trong
  phút thoát (+53,9 tick, +0,47 %).
- Giá khớp ở sàn giả so với REF: trung bình −0,53 %, thấp nhất −2,06 % (mô hình sàn giả khớp ở giá nhịp; chỉ báo cáo theo ERRATA 1 E4).

## 5. Việc tiếp
- Theo ADD22 §3, chưa có (iii) PASS ⇒ CHƯA được tạo gate file. Quyết định xử lý E2 thuộc owner (khẩu vị rủi ro) — xem status_1117.md.
