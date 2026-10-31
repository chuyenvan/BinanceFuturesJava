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

## ADDENDUM_TECH-1 (2026-10-31, viết TRƯỚC khi có bất kỳ kết quả biến thể nào)

**Sửa một kiểm kỹ thuật, không sửa luật/cổng.** §2 đặt G-2026 = "phần 2026 trùng `nt-x14-s42`". Kiểm này **không thể
đúng về mặt cấu trúc**, không phải vì biến thể:
- `nt-x14-s42` dùng X14 chỉ với 5 khoảng 2026 ⇒ đoạn DEV **không hoãn** time-stop ngày nào, nên equity bước vào 2026 khác.
- Run NUP4 dùng hợp 47 khoảng ⇒ đoạn DEV hoãn đúng như B0 go-live (`tsx-x14-*`), nên equity vào 2026 khác `nt-x14`.
- Vì sizing là compounding trên equity, hai đường không thể trùng nhau ở 2026 dù cùng "luật".

**Thay bằng:**
- **G-DEV (giữ nguyên, chặt):** mọi dòng `start < 20260101` của `n4b-b0union-a1` phải trùng từng byte `tsx-x14-a1`
  (`dc62609b…`). Đây là kiểm đường dữ liệu + X14 DEV + universe.
- **B0 cho HO 2026 = chính `n4b-b0union-a1`** (cùng lịch sử, cùng equity vào 2026). Mọi so sánh 2026 của biến thể là so với
  run này. `nt-x14-s42` chỉ dùng để **chẩn đoán** (báo Δ do khác danh sách X14 DEV), không dùng làm cổng.
- **G-2026:** run phải có ≥ 800 cụm 2026 và `equity_summary.json` hợp lệ; không so md5 với `nt-x14`.

Lý do ghi bổ sung này: nó được viết **trước** khi gate chạy xong và trước mọi số của biến thể; nó không nới bất kỳ ngưỡng
G1–G5 nào, chỉ thay một tham chiếu không hợp lệ bằng tham chiếu đúng (cùng đường).


## ADDENDUM-2 (2026-10-31, audit Opus theo lệnh MASTER — viết TRƯỚC mọi run biến thể; chưa có số biến thể nào)

**Căn cứ.** `~/claude_master/oc1031/AUDIT_NUP4.md`. Code sửa trên nhánh `fix/nup4-audit` (worktree
`~/claude_master/nup4_fix/wt`, gốc 45f6ce90): `c4481bd5` đưa patch đo equity (dirty trong `~/src_nup3`, đã vào jar 9f6f028b)
thành commit; `7213a5d6` STUB config (không còn host 242/226); `eaa614d6` sửa lỗi. Jar mới build từ `eaa614d6` (sạch), khi build
thay hằng token Telegram bằng "" (không commit): sha256 `e7fe5257554f8d75c30b44c419cebe0142309365777bcce48a41e3604cb7cc10`,
md5 `40702ab178ff5148be001121616668e9`. Jar 9f6f028b / e7f69618 của claw **không dùng nữa**.
ADDENDUM-2 **thay** ADDENDUM_TECH-1 ở các điểm dưới; mọi điểm không nhắc giữ nguyên §1–§10.

### A. Bỏ G-2026 do claw tự đặt; G4 về đúng task
- Bỏ "G-2026: ≥ 800 cụm 2026" (ADDENDUM_TECH-1). Ngưỡng không có căn cứ (B0-A1 s42 chỉ có 396 cụm 2026).
- Kiểm kỹ thuật cho mọi run B0-A1: **G-DEV** = header + mọi dòng `start < 20260101` trùng từng byte `tsx-x14-<seed>`.
  Phần 2026 KHÔNG so md5 với `nt-x14` (đã chứng minh lệch qty 404/404 do equity vào 2026 khác — hợp lệ).
- **G4 (giữ đúng task/§5):** HO 2026 A1, phần sleeve: ΣPnL_stress sleeve > 0 ở ≥ 6/8 seed, ROI_stress sleeve ≥ +0,5 %/lệnh,
  maxDD toàn danh mục HO ≥ −15 %.

### B. Bỏ M3
- Code 45f6ce90: nhánh SPLIT chỉ đếm/log ⇒ M3 ≡ S1b-SEP (2 vị thế, 2 stop trên cùng symbol — trái one-way).
  M3 thật cần mô phỏng đóng reduceOnly từng phần + MỘT stop closePosition dời theo phần còn lại ⇒ để vòng sau.
- `MERGE_MODE=M3` nay ném lỗi. Bỏ 8 run M3 (Pha 1a: 4 seed × 2 size). Trial ledger họ NUP: Pha 1a còn 5 arm (S1b-SEP, M1×2, M2×2).

### C. M1 và funding (sửa lỗi, không phải tham số mới)
- M1: leg NỀN gộp vào cụm sleeve dùng **đồng hồ time-stop/cond-exit/DCA-signal và neo hard-SL/TP (firstEntryPrice) của chính
  leg nền đầu tiên**, giữ qua DCA sau gộp. Cửa sổ funding vẫn từ leg đầu của cụm (clusterFirstLegTime).
- Funding cụm có hai chủ sở hữu (M1/M2): chia tổng funding theo **qty** B/S, ghi vào leg đầu của mỗi phần; tổng bảo toàn.
  Cụm một chủ: như cũ. §3 "chia khi chấm" được thay bằng chia trong sim.
- Bất biến one-way: `merge_overlap_ticks` (số tick có symbol mà cả 2 sổ cùng giữ) **phải = 0** ở mọi run M1/M2, khác 0 ⇒ run hỏng.

### D. Kill-switch A40 (mô phỏng tối thiểu)
- `KILLSW_A40_DD=0.40` cho **MỌI** run NUP4 (B0 và biến thể). Equity GỘP (nền + sleeve, mark close) đo cuối mỗi tick;
  DD từ đỉnh ≥ 40 % ⇒ tick sau chặn MỞ CỤM MỚI (nền, sleeve, cả gộp); DCA vào cụm đang mở vẫn chạy; DD < 40 % ⇒ mở lại.
- Báo `killsw_triggers`, `killsw_blocked` trong `equity_summary.json`. B0 (DD ~22 %) không kích ⇒ vẫn trùng byte.

### E. Cách đo DD (G3)
- Hiệu chỉnh trên B0-A1 s42: DD trong sim (đỉnh eq_low, jar 9f6f028b) = **−21,40 %** (đáy 2025-10-11); MTM legacy phút-close
  (`golive_quarterly`, Vision, missing = 0) cho `tsx-x14-a1` — phần DEV trùng byte — = **−22,203 %** (đáy 2022Q2).
  Lệch **0,80 pp > 0,2 pp** và khác ngày đáy ⇒ **G3 chấm bằng MTM legacy phút-close (gvz_mtm / golive_quarterly mtm_dev),
  missing = 0, trên printDone gộp hai sổ.** Giá kline1m không còn trên Oracle và cấm tải > 1 GB ⇒ MTM chạy trong Kaggle kernel
  (đếm vào ngân sách kernel, không phải run sim).
- `maxdd_close_pct` (mới, kiểu close/close trong sim) và `maxdd_mtm_low_pct` chỉ để báo cáo, không dùng để chấm G3.
- G4 "maxDD toàn danh mục HO" cũng chấm bằng MTM legacy.

### F. Ngân sách run sim mới (trần 40)
| bước | run |
|---|---|
| Gate hồi quy: B0-A1 s42 jar mới, printDone **trùng từng byte** `n4b-b0union-a1` + G-DEV | 1 |
| B0-A1 7 seed còn lại (s7, s13, s21, s99, s123, s777, s2024) ⇒ baseline B0-A1 8 seed | 7 |
| Pha 1a: S1b-SEP + M1×{0,574; 0,45} + M2×{0,574; 0,45} × 4 seed (a1, s7, s21, s99); B0 lấy từ dòng trên | 20 |
| Pha 1b: ≤ 2 biến thể × 4 seed (s13, s123, s777, s2024) | ≤ 8 |
| Stress trượt +0,1 %/chiều cho biến thể thắng | 1 |
| **Tổng** | **≤ 37** |
- Gate s42 FAIL ⇒ dừng, báo MASTER. Mọi run phải được Opus pre-review (G-PRE) và MASTER duyệt trước khi push Kaggle.
- G1, G2, G5, luật chọn Calmar, §6: giữ nguyên. Không thêm biến thể, không đổi size.
