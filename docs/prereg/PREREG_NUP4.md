# PREREG NUP4 — sleeve tăng số lệnh trên MỘT tài khoản one-way (MASTER 2026-10-31)

Viết TRƯỚC mọi phép đo của NUP4. Căn cứ: NUP3B_P1 (759ee1b6), PREREG_NUP3 (c2b4c462), PREREG_NUP3B (9b49f7a9),
code sleeve 6d0b4802 (nhánh `research/nup3-sleeve`), jar `sim-jar-nup3b` 8aba4090, GOLIVE_QUARTERLY_2026_A1 (428ad486),
PREREG_HO2026_NOTF.

## 1. Lý do và câu hỏi
- NUP3b: S1b (V1, size 0,574) cụm ×1,71, PnL ×1,42 nhưng maxDD median −32,20 % ⇒ trượt G3 đúng 0,20 pp; chạy trên
  **universe CŨ (có TradFi)** và **giả định sổ tách**. S1x (nền bỏ symbol sleeve) phá PnL nền (×0,586) ⇒ không dùng.
- Owner: ưu tiên SỐ LỆNH; chấp nhận ROI/lệnh thấp hơn nếu tổng PnL không giảm; DD sâu hơn nhưng KHÔNG nới cổng.
  BẮT BUỘC chung 1 tài khoản (one-way: 1 symbol = 1 vị thế).
- Q1: trên universe A1 (bỏ TradFi+INDEX từ 2026), S1b-SEP còn đạt G1/G2/G4, DD bao nhiêu?
- Q2: chi phí thật của trùng symbol khi chung tài khoản one-way là bao nhiêu; cách gộp nào giữ được lợi ích?
- Q3 (chỉ báo cáo): so với "tăng size nền tới cùng DD" (iso-DD), biến thể thắng có hơn không?

## 2. Nền B0, universe, đường chạy (chốt)
- **B0 = K24 + skipFull + X14** (cấu hình go-live), universe **A1**, profile `r4_kg0_k16_f015_g155`.
- **Đường chạy:** sim jar NUP4 trên pipeline HO2026 A1 (`market_ds=nt-chain-y26`, `pred_ds=pred_s<seed>` của chain,
  ticker `nt-tk26`, `sim_end_date=20261001`, `HOLDOUT_UNSEAL` — 2026 đã unseal, KHÔNG phải 2020), để **một run cho cả
  DEV 2022–25 và HO 2026**.
- **X14 dùng HỢP của hai danh sách ngày**: 42 khoảng 2021–25 (`~/claude_master/tsx/flags.json`, sha256 c79ef302…) +
  5 khoảng 2026 (`FLAGS1` của HO2026_NOTF, 18 ngày) = 47 khoảng. Lý do: luật X14 là luật theo NGÀY; B0 DEV hiện có
  (`tsx-x14-*`) dùng danh sách 2021–25, B0 2026 hiện có (`nt-x14-*`) dùng danh sách 2026 — mỗi bản đúng cho kỳ của nó.
  Hợp hai danh sách cho một run liên tục là cùng một luật, không đổi ngưỡng.
- **Mốc so sánh (không chạy lại):** DEV 2022–25 so `tsx-x14-<seed>`; HO 2026 so `nt-x14-<seed>`. Đây là hai mảnh thời
  gian của CÙNG cấu hình B0 go-live, không phải hai chiến lược.
- **Cổng bắt buộc trước Pha 1a (1 run B0 hợp danh sách, seed 42):**
  - **G-DEV**: mọi dòng printDone có `start < 20260101` trùng từng byte với `tsx-x14-a1` (md5 `dc62609b6d7169093c001f2ce0d198ed`).
  - **G-2026**: các dòng có `start >= 20260101` trùng từng byte với phần 2026 của `nt-x14-s42`.
  - Fail ⇒ DỪNG, báo MASTER (không tự sửa luật).
- **G-OFF** (sleeve tắt): `SLEEVE_ENABLED=false` trên jar NUP4 ⇒ printDone trùng byte B0 cùng seed (seed 42 và 7).

## 3. Định nghĩa biến thể (chốt; KHÔNG tune)
Ký hiệu: "sổ nền"/"sổ sleeve" = hai sổ phần mềm như NUP3, dùng chung equity. "Vị thế vật lý" trên sàn one-way của một
symbol = tổng qty hai sổ.

- **S1b-SEP** (mốc trần lý thuyết): y nguyên NUP3b S1b — V1, size ×0,574, sổ tách, KHÔNG xử lý trùng symbol (nền vẫn mở
  symbol sleeve đang giữ). Dùng để đo lại trên A1.
- **M1 (gộp, theo nền).** Khi **nền** muốn mở leg trên symbol **sleeve đang giữ** (và nền chưa giữ):
  - leg nền được tạo với **sizing của nền** (không nhân SLEEVE_SIZE_MULT);
  - toàn bộ leg sleeve + leg nền trở thành **MỘT cụm trong sổ nền**; từ tick đó cụm do **luật nền** quản (exit, DCA,
    trailing, time-stop/X14);
  - **trạng thái stop bị RESET** khi gộp: cụm gộp chưa arm, `priceEntry` = entry bình quân qty, `firstEntryPrice` =
    leg đầu (của sleeve), `clusterFirstLegTime` = leg đầu (của sleeve) ⇒ đồng hồ time-stop/X14 tính từ leg sleeve;
  - margin của cụm gộp nằm trong **sổ nền**; sổ sleeve giải phóng margin tương ứng;
  - DCA sau gộp do nền tạo ⇒ leg mới thuộc **nền**.
  Sleeve KHÔNG mở symbol nền đang giữ (giữ nguyên luật NUP3).
- **M2 (gộp, theo sleeve).** Như M1 nhưng cụm gộp nằm trong **sổ sleeve**, do **luật sleeve** quản; DCA sau gộp do sleeve
  tạo (size sleeve); margin nằm trong sổ sleeve. Leg nền đầu tiên vẫn sized theo nền.
- **M3 (gộp, đóng tách).** Như M1 ở điều kiện mở (nền mở được trên symbol sleeve đang giữ, leg nền sized theo nền) nhưng
  **KHÔNG gộp sổ**: hai phần nằm ở hai sổ, mỗi phần do luật của sổ mình quản; khi một phần đạt điều kiện exit của chính nó
  thì đóng **đúng qty phần đó** (mô hình reduceOnly); phần còn lại tiếp tục. "1 stop chung" được mô phỏng bằng: sau khi một
  phần đóng, mức stop còn hiệu lực = mức của phần còn lại; báo cáo số tick hai phần cùng mở.
- **Dừng khẩn cấp A40** (owner): tính trên **equity GỘP** (nền + sleeve). Sim không có kill-switch; NUP4 **đo** đường equity
  gộp và báo số tick DD ≥ 40 %. Mọi biến thể qua G3 (DD tệ nhất ≥ −36 %) không thể chạm −40 %; nếu chạm thì đã trượt G3
  và không cần mô phỏng dừng. Đây là kiểm nhất quán, không phải nới cổng.
- **Size sleeve cố định: ×0,574 và ×0,45** cho mỗi M1/M2/M3. S1b-SEP chỉ ×0,574.
- **Gắn chủ sở hữu:** mỗi leg ghi `storage/leg_owner.csv` (`sym,tOpen,owner` với owner `B`/`S`). Mọi dòng printDone giữ
  nguyên định dạng (cột cuối `book=sleeve` như NUP3). Gộp ghi `storage/merge_log.csv` (`tMs,sym,mode,n_legs_from,n_legs_to`).
- **Phân bổ funding:** sim gán funding của cụm vào leg đầu. Khi chấm, funding của cụm được chia **pro-rata theo qty** cho
  các leg của cụm (và do đó cho owner). Quy ước này áp cho cả B0 và biến thể.

## 4. Thước đo (giữ NUP3 §5)
- Toàn danh mục (nền+sleeve) so B0 cùng seed: cụm/năm từng năm 2022–25, ΣPnL, ΣPnL stress −20 bps, CAGR22, maxDD MTM
  (missing = 0), Calmar, U notional@mark max, U margin@entry max, số vị thế max.
- Riêng sleeve: cụm/năm, ROI/lệnh, ROI_stress, ΣPnL_stress theo năm/seed, overlap, N_eff (đợt <6 h, ngày có lệnh, tương quan
  PnL ngày với nền), top-3 đợt % PnL thêm.
- M*: PnL phần nền (theo owner) và phần sleeve; số lần gộp; PnL vị thế gộp vs không gộp; số tick hai phần cùng mở (M3).
- Kỳ DEV gán theo giờ đóng +07; equity tính từ 2021-07 (gồm 2021H2, như NUP3B).
- HO 2026: cửa sổ 2026-01-01 → 2026-09-30 (sim_end 20261001), cùng quy ước.

## 5. Cổng (NGUYÊN NUP3, KHÔNG nới)
- **G1:** cụm/năm toàn danh mục ≥ **1,30×** B0 VÀ mỗi năm 2022–25 ≥ **1,15×**.
- **G2:** ΣPnL DEV ≥ **1,00×** B0 (median seed); ΣPnL_stress của sleeve > 0 ở ≥ 3/4 năm DEV và ≥ 3/4 seed (Pha 1a),
  ≥ 6/8 seed (Pha 1b).
- **G3:** maxDD MTM toàn danh mục median ≥ **−32 %**, seed tệ nhất ≥ **−36 %**, U notional@mark max ≤ 1,0.
- **G4 (Pha 1b, HO 2026 A1):** ΣPnL_stress phần sleeve > 0 ở **≥ 6/8 seed**, ROI_stress sleeve ≥ **+0,5 %/lệnh**,
  maxDD realized toàn danh mục HO ≥ **−15 %**.
- **G5 (chỉ M1/M2/M3):** ΣPnL phần **NỀN** ≥ **0,97×** B0 (median seed; so B0 cùng seed).
- Stress trượt +0,1 %/chiều: chạy 1 lần cho biến thể thắng (báo cáo, không dùng để chọn).

## 6. Luật chọn (chốt trước khi đo)
- Trong các biến thể **đạt đủ G1–G5** (Pha 1b, 8 seed): chọn **Calmar cao nhất** (DEV, median seed).
- **Không có biến thể nào đạt ⇒ NO-GO**, không thêm biến thể mới, không đổi ngưỡng, không đổi size.
- Không dùng Q3/iso-DD để chọn. Q3 chỉ để báo cáo.

## 7. Quy trình
- **Pha 0:** file này + code M1/M2/M3 + unit test; commit **trước** khi push run.
- **Pha 1a:** 4 seed a1(42), s7, s21, s99: S1b-SEP + M1/M2/M3 × {0,574; 0,45} = 7 arm × 4 = 28 run (mỗi run phủ DEV+2026).
  Loại ngay biến thể trượt G1 **hoặc** G2 **hoặc** G5 (và báo G3).
- **Pha 1b:** tối đa 2 biến thể còn sống tốt nhất theo Calmar; thêm 4 seed (s13, s123, s777, s2024) = ≤ 8 run; chấm đủ
  G1–G5 + G4 trên 8 seed (4 seed Pha 1a đã có HO trong chính run đó). Stress trượt cho biến thể thắng.
- **Báo cáo:** `docs/result/NUP4.md` — bảng theo năm, theo quý 2026, iso-DD, danh sách "CHƯA GIẢI THÍCH".

## 8. Ngân sách và dừng
- Tối đa **~40 run**. Ước tính: 1 (G-DEV/G-2026) + 1 (G-OFF) + 28 (Pha 1a) + ≤8 (Pha 1b) = **≤ 38**. Vượt 40 ⇒ dừng, báo.
- Tối đa 2 kernel Kaggle cùng lúc. Sim chạy trên Kaggle, không chạy trên Oracle.

## 9. Validate bắt buộc trước khi chấm
| kiểm | điều kiện |
|---|---|
| G-OFF | sleeve tắt, printDone = B0 seed 42/7 từng byte |
| G-DEV / G-2026 | như §2 (1 run B0 hợp danh sách) |
| G-INV | mỗi run S1b-SEP và M*: lọc bỏ dòng `book=sleeve` ⇒ phần nền = B0 cùng seed từng byte (chỉ áp cho S1b-SEP và M3; M1/M2 sổ nền ĐỔI do gộp ⇒ so riêng, xem dưới) |
| M1/M2 | `merge_log` khớp `sleeve_summary`; Σ PnL theo owner = Σ PnL printDone (sai số < 1e-6) |
| MTM | missing = 0 mọi sổ |
| tổng | Σ quý = Σ năm = tổng (sai số < 1e-6) |
| tái lập tay | 1 run (M1 s7 ×0,574) đếm tay cụm/PnL từ csv độc lập |
- G-INV cho M1/M2: phần nền KHÔNG thể trùng B0 (đã gộp). Thay bằng: **(i)** số leg nền + leg sleeve = số leg printDone;
  **(ii)** mọi leg nền không gộp trùng B0 theo (sym,tOpen); **(iii)** PnL owner cộng lại = tổng.

## 10. Giới hạn đã biết (ghi trước)
- `mergeOrder` reset trạng thái arm/stop khi gộp ⇒ M1/M2 có thể lệch so với "giữ stop cũ"; đây là quy ước đã đăng ký,
  không sửa sau khi thấy số.
- M3 mô hình hoá 1 stop bằng reduceOnly từng phần; sàn thật có thể từ chối/ghi đè stop thứ hai — chưa mô phỏng được.
- Throttle sizing phi tuyến (bài học NUP3b); size nhỏ không giảm DD tuyến tính.
- Sim không mô hình từ chối lệnh khi margin@entry > equity; báo số leg bị ảnh hưởng.
- A40 chỉ kiểm ở tầng đo equity gộp (§3).
- HO 2026 đã dùng ở NUP/S0/NUP3b/GOLIVE ⇒ đây là lần thứ 4; trial ledger họ NUP +7 (7 arm Pha 1a) + ≤2 (Pha 1b).
