# PREREG_TSX_V3_JAVA — T25 / L45 / C420 của TS_MKT_EXT chấm bằng SIM JAVA ĐẦY ĐỦ (lãi kép, slot, vốn giam, số lệnh/khối lượng) — 2026-10-22

Viết + commit TRƯỚC khi đọc bất kỳ chỉ số kết quả nào của các run biến thể. Brief: owner 10-22 qua MASTER. Nền: X14 (TS_MKT_EXT, run DEV
`tsx-x14-*` 8 seed, HO `tsx-ho-x14-s*` 8 seed, jar `sim-jar-tsx` sha256 cc0f9d11…), replay TSX_V2 (prereg 6b7ab1a8, kết quả f620575c).
Không 2020 (`bcast-*` niêm phong), không đụng 242/shadow, không Binance REST, không push. HO 2026 W9 CHỈ MÔ TẢ.

## 0. Trung thực / trùng lặp / thiên lệch đã biết
- **Trùng lặp (phát hiện khi bắt đầu, ghi để MASTER biết):** cùng ngày đã có 2 prereg trên ĐÚNG các biến thể này, cùng session:
  TSX_V2_SIM (bfa59d4a; pipeline `research/tsx_v2_sim/run.py` PID 758938 đang chạy V336/V420/VT25/VL45 × 8 seed DEV + HO W9) và
  TSX_V3 (26b97f10; V0–V4, tái dùng run tsx2 cho V1 ≡ V420, V3 ≡ VT25, V4 ≡ VL45, thêm V2 = B3b mới; pipeline PID 766935).
  **T25 ≡ VT25 ≡ V3, L45 ≡ VL45 ≡ V4, C420 ≡ V420 ≡ V1**: cùng jar, cùng `OV_BASE`, cùng `SIM_LOSER_TS_EXT_HOURS`, chuỗi
  `SIM_LOSER_TS_EXT_DAYS` DEV + HO trùng từng byte (kiểm trong `research/tsx_v3_java/flags.py`, PASS — §1). Sim tất định (ctl bit-exact md5)
  ⇒ TSX_V3_JAVA **không đẩy kernel mới**, tái dùng run `tsx2-{vt25,vl45,v420}-*` (DEV) và `tsx2-ho-{vt25,vl45,v420}-s*` (HO).
- **Agent này CHƯA đọc chỉ số kết quả nào của các run biến thể** trước commit này. Đã thấy (không chủ ý) trong `tsx2sim/run.log` tail:
  md5, `n` (số leg printDone: vl45-s2024 = 3508, v420-s2024 = 3506) và bộ đếm cơ học `[TSX]` của 2 run đó. Không mở `res_*.json`
  biến thể, `docs/result/tsx_v2_sim/*`, `docs/result/tsx_v3/dev_smoke.json|dev_rows_smoke.csv`.
- **Ba prereg trên cùng run** ⇒ rủi ro chọn luật theo kết quả. Cam kết: TSX_V3_JAVA báo verdict theo luật §5 DƯỚI ĐÂY (luật brief owner 10-22);
  đồng thời báo verdict theo luật TSX_V2_SIM (C1–C5) và TSX_V3 ((i)–(iv)) để MASTER thấy đủ, không chọn luật nào "đẹp hơn".
- **Trial ledger họ TS_MKT_EXT**: brief ghi 15 → 18; thực tế T25/L45/C420 đã được đếm trong TSX_V2_SIM (15 + 4 = 19) và TSX_V3 thêm V2 (= 20).
  TSX_V3_JAVA không thêm phép thử mới ⇒ **ledger giữ 20** (ghi trung thực; lệch so brief vì trùng lặp).
- **T25 (−0,25/30) và L45 (−0,30/45) được chọn SAU khi xem replay TSX_V2 (ô B4 +4 742 / +3 045 /seed, 8/8) ⇒ in-sample, data-snooping.**
  C420 (B1b_420h) replay −532/seed (0/8). Replay KHÔNG tính lãi kép/slot/vốn giam/DCA mới ⇒ đánh giá CAO biến thể cờ rộng hơn (T25, L45:
  vốn giam ⇒ mất lệnh) và đánh giá THẤP biến thể giữ ngắn hơn (C420: giải phóng vốn ⇒ thêm lệnh). Mọi kết quả là IN-SAMPLE DEV;
  ứng viên chỉ là ứng viên v1.2, không đổi shadow, không đổi X14 đang chạy.
- Kỳ vọng trước (agent): T25/L45 mất một phần lợi replay do vốn giam; C420 bớt âm; P(≥ 1 ứng viên) ~20–30 %.

## 1. Biến thể (cố định) — cờ tính bằng ĐÚNG biểu thức của `tsx/tsx_flags.py` (DEV) / `tsx/ho/tsx_ho.py flags()` (HO)
ON(D+1) ⟺ exp(EOD(D) − max EOD(D−L..D)) − 1 ≤ thr, EOD = cumsum log-ret ALT_EW (`edge_attr/index.npz`; HO nối `tsx/ho/ew_out/ew_2026.npz`).
Tổng giữ tối đa cụm hoãn = 168 + EXT giờ. X14 tái lập trước: 214 ngày / 42 khoảng / sha c79ef302 = `tsx/flags.json`; HO 15 ngày = `ho_flags.json`.
File: `~/claude_master/tsx_v3_java/flags.json` (sha256 077ef451…), bản sao `docs/result/tsx_v3_java/flags.json`.

| Arm | thr / L | EXT (tổng) | DEV ngày ON (khoảng, sha8) | 2021H2 | 2022 | 2023 | 2024 | 2025 | +ngày vs X14 | HO 2026 (sha8) | Run DEV | Run HO W9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **X14** | −0,30 / 30 | 336 (504h) | 214 (42, c79ef302) | 14 | 78 | 4 | 51 | 67 | 0 | 15 (ecaced06) | `tsx-x14-*` | `tsx-ho-x14-s*` |
| **T25** | −0,25 / 30 | 336 (504h) | 406 (57, 59a9db07) | 29 | 120 | 20 | 81 | 156 | +192 | 34 (84dfa414) | `tsx2-vt25-*` | `tsx2-ho-vt25-s*` |
| **L45** | −0,30 / 45 | 336 (504h) | 445 (41, c4ab507b) | 19 | 146 | 14 | 77 | 189 | +231 | 37 (d0d0e30a) | `tsx2-vl45-*` | `tsx2-ho-vl45-s*` |
| **C420** | −0,30 / 30 | 252 (420h) | 214 (42, c79ef302) | 14 | 78 | 4 | 51 | 67 | 0 | 15 (ecaced06) | `tsx2-v420-*` | `tsx2-ho-v420-s*` |

T25 và L45 là tập cha của X14 (0 ngày X14 bị mất). Seed DEV: a1, s7, s13, s21, s99, s123, s777, s2024; HO: 42, 7, 13, 21, 99, 123, 777, 2024.

## 2. Chạy
- Không đẩy kernel. Chờ pipeline TSX_V2_SIM hoàn tất các run cần (DEV 24 + HO 24). Không can thiệp pipeline TSX_V2_SIM / TSX_V3.
- Parity mỗi run (từ `res_*.json` của pipeline + kiểm lại): `passed=True` (jar sha, ok, TOPK 24, skipFull, B0OV, dòng log `[TSX]`) VÀ
  `prof_run` khoá `SIM_LOSER_TS_EXT_DAYS`/`HOURS` = `flags.json` TSX_V3_JAVA. Fail ⇒ VOID (không chấm). Run thiếu do lỗi hạ tầng sau khi
  pipeline TSX_V2_SIM kết thúc ⇒ đẩy lại đúng 1 lần cfg y hệt (driver `tsx_driver`/`tsx_ho`); vẫn thiếu ⇒ seed thiếu ⇒ không thể 8/8 ⇒ không ứng viên.

## 3. Validate (fail ⇒ dừng, không báo kết quả)
- VA1: X14 qua đường chấm mới (MTM phút `gvz_mtm` import TRƯỚC, `R._work is MT._work_vision`, missing = 0): TB 8 seed CAGR22 = 39,49 và
  DD22 = −22,55, sai ≤ 0,1pp; dd_total/dd_win từng seed = `tsx/mtm_vision.json` (≤ 1e-6).
- VA2: X14 qua đường chạy mới tái lập md5 printDone run X14 cũ: DEV `tsx2-ctl-a1` = `tsx-x14-a1`, HO `tsx2-ho-ctl-s7` = `tsx-ho-x14-s7`
  (+ `tsx3-ctl-s13` = `tsx-x14-s13` nếu đã xong — ghi kèm, không chặn).
- VA3: cờ X14 sinh lại = `tsx/flags.json` (c79ef302) + `ho_flags.json`; T25/L45/C420 = `tsx2sim/flags_variants.json` = `tsx_v3/flags_v3.json` (PASS trước commit).
- VA4: mọi run MTM missing = 0; ΣPnL MTM = Σ pnl printDone (< 1e-6). HO: X14 HO tái lập = `tsx/ho/ts_mkt_ext_ho.json` (< 1e-6).
- VA5: số cụm hoãn tái dựng từ printDone (quy ước DEEP §1, cờ + trần của biến thể) = bộ đếm `deferClusters` Java, mỗi run DEV.

## 4. Chỉ số (mỗi biến thể vs X14, cùng seed; median + min/max 8 seed; DEV tổng + theo năm 2021H2/2022/2023/2024/2025)
Định nghĩa (DEEP `deep_analysis.py`): leg = dòng printDone; cụm = (sym, te) các leg DCA đóng cùng phút; **đợt vào** = phút anchor t0
phân biệt (một đợt crash-buy = mọi cụm có cùng t0); theo năm = theo ngày đóng.
- Số cụm, số đợt vào, số leg; **khối lượng** = Σ notional vào (quantity × entry) các leg; win % (leg profit > 0, = n700 win22; + % cụm pnl > 0).
- ΣPnL, CAGR22, maxDD MTM phút (DD22 = 2022–2025: median + seed tệ nhất; + DD toàn kỳ), Calmar22, UW22 (`n700.arm_metrics`); theo năm: PnL, ROI, DD MTM, Calmar năm.
- Phơi nhiễm = notional mở / equity MTM (mẫu theo giờ): TB / max, DEV và theo năm.
- **Vốn bị giam bởi cụm hoãn** = notional mở của leg thuộc cụm hoãn từ mốc 168h đến khi đóng / equity MTM: TB trên giờ cờ ON của chính biến thể,
  TB trên MỌI giờ DEV (so sánh được giữa biến thể), đỉnh. Số cụm hoãn, giờ giữ thêm TB, PnL cụm hoãn, kiểu thoát.
- **Đối chiếu từng đợt vào** (khoá = phút t0): với mỗi đợt của X14 — BỎ (V không có cụm nào tại t0); THU NHỎ-số-mã (V ít mã hơn);
  THU NHỎ-size (đủ mã nhưng Σ notional leg anchor / số dư thực hiện tại t0 < 0,99 × của X14); và đợt MỚI chỉ có ở V. Báo số đợt, Σ notional,
  Σ PnL X14 của đợt bỏ; tách trong đợt cờ (25 đợt Phase A [đầu, cuối]) / 15 ngày sau / ngoài; mô tả nguyên nhân: U(t) = margin mở / equity
  và số cụm hoãn đang mở của V tại t0 so X14 (mô tả, không chứng minh nhân quả).
- **ΔPnL tách direct vs phần còn lại** (sim): direct_sim = Σ trên cụm (sym, t0) bị hoãn ở V HOẶC X14 và có mặt ở CẢ HAI run của (pnl_V − pnl_X14);
  phần còn lại = ΔΣPnL − direct_sim (lệnh mới/bị bỏ, lãi kép trên cụm khác, slot). Ghi chú: direct_sim chứa cả hiệu ứng size trên cụm hoãn.
  Gán đợt: mark_day (ngày cụm vượt 168h) ∈ 25 đợt Phase A (`research/tsx_v2/common.py episodes`, bao trùm mọi ô B4 ⇒ mọi ngày cờ T25/L45/X14).
  Kèm mô tả: direct replay (phaseB) + sizing (DEEP deep_extra) + dư như TSX_V3; replay vs sim (ΔΣPnL_sim − direct_replay).
- HO W9 (mô tả, scorer HO4 `ecm_mtm_h.py`, như X14 HO): ΔPnL, ΔROI, ΔmaxDD theo seed (median/min/max, số seed ≥ 0), số cụm hoãn (log Java), số leg.

## 5. Luật ỨNG VIÊN v1.2 (cố định; DEV 8 seed; cả 5 đều đạt)
- (R1) ΔCAGR22 > 0 ở 8/8 seed.
- (R2) DD22 MTM phút seed tệ nhất của V ≥ DD22 seed tệ nhất của X14 − 1,0pp.
- (R3) ΔCalmar22 ≥ 0 ở ≥ 6/8 seed.
- (R4) Số đợt vào DEV: TB 8 seed của (n_V / n_X14 − 1) ≥ −2 %.
- (R5) Direct dương sau leave-one-episode-out: min_e TB-8-seed(direct_sim − direct_sim_e) > 0 (e ∈ 25 đợt Phase A; tương đương bỏ đợt đóng góp lớn nhất).
- Seed VOID/thiếu ⇒ không ứng viên. HO W9 chỉ mô tả (đã bị nhìn nhiều lần): ΔROI, ΔDD, số cụm hoãn — không chặn, không cứu.
- Nhiều ứng viên ⇒ chọn ΔCalmar22 median lớn nhất; hoà (chênh < 0,005) ⇒ đơn giản nhất theo thứ tự cố định C420 < T25 < L45.
- 0 ứng viên ⇒ giữ X14; không thử thêm ô, không đổi ngưỡng/luật sau khi thấy kết quả. Ứng viên (nếu có) chỉ vào v1.2, không đổi shadow.

## 6. Xuất
`docs/result/TSX_V3_JAVA.md` + `docs/result/tsx_v3_java/` (flags.json, validate.json, dev.json, dev_rows.csv, batches.csv, ho.json, bảng) và
script `research/tsx_v3_java/` (flags.py; score.py, ho_score.py, md.py viết sau commit này, chỉ hiện thực §3–§5, dựa trên `research/tsx_v3/score.py`).
Commit; không push.
