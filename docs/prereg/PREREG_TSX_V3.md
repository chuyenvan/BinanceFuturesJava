# PREREG_TSX_V3 — "giữ lâu ⇒ vốn giam ⇒ ít lệnh mới?": V0–V4 của TS_MKT_EXT X14 chấm bằng SIM JAVA ĐẦY ĐỦ — 2026-10-22

Viết + commit TRƯỚC khi đẩy bất kỳ kernel mới nào của TSX_V3 và TRƯỚC khi đọc bất kỳ chỉ số kết quả nào của các run được tái dùng.
Nền: X14 (prereg 1e138619; DEV c1ab8eda; HO 46ebc1ee; DEEP 40b12804), replay TSX_V2 (prereg 6b7ab1a8, kết quả f620575c, engine
`research/tsx_v2/` validate 100 %), TSX_V2_SIM (prereg bfa59d4a, pipeline đang chạy). Không 2020 (`bcast-*` niêm phong), không đụng 242/shadow,
không Binance REST. HO 2026 CHỈ MÔ TẢ.

## 0. Trung thực / thiên lệch đã biết
- Câu hỏi của owner: giữ lệnh lâu hơn ⇒ vốn bị giam ⇒ ít lệnh mới / khối lượng giảm. Replay TSX_V2 KHÔNG tính lãi kép, slot, vốn giam,
  DCA mới ⇒ đánh giá THẤP biến thể giữ ngắn hơn (V1, V2: vốn giải phóng ⇒ thêm lệnh) và đánh giá CAO biến thể cờ rộng hơn (V3, V4: vốn giam
  ⇒ mất lệnh). DEEP: X14 vs P0 = direct +6 493 + lãi kép ~+8 239 + phần dư "ít slot/cụm" −3 229 /seed; LUNA lỡ ~15,5 cụm mới/seed.
- **V3 (−0,25/30) và V4 (−0,30/45) được chọn SAU khi xem replay TSX_V2 (B4 +4 742 / +3 045 /seed, 8/8) ⇒ in-sample, data-snooping.**
  V1 (B1b) / V2 (B3b) có replay âm (−532 / −170 /seed) nhưng thiên lệch replay chống lại chúng.
- **Trùng lặp với TSX_V2_SIM (bfa59d4a)**: pipeline `research/tsx_v2_sim/run.py` (PID 758938, khởi chạy 07:03, 23/66 run xong lúc 10:21) đang
  chạy V336/V420/VT25/VL45 × 8 seed DEV + HO W9. **V1 ≡ V420, V3 ≡ VT25, V4 ≡ VL45**: cùng jar (sha256 cc0f9d11…), cùng `OV_BASE`, cùng
  `SIM_LOSER_TS_EXT_HOURS`, chuỗi `SIM_LOSER_TS_EXT_DAYS` DEV và HO trùng từng byte (kiểm trong `research/tsx_v3/flags.py`, PASS). Sim tất định
  (ctl bit-exact md5) ⇒ TSX_V3 **tái dùng** các run `tsx2-{v420,vt25,vl45}-*` (DEV + HO) thay vì chạy lại ~48 kernel. Chỉ dùng run PASS parity
  (`res_*.json` `passed=True`) và kiểm lại chuỗi khoá trong `prof_run` = danh sách TSX_V3. Agent TSX_V3 CHƯA đọc chỉ số kết quả nào của chúng
  trước commit này (chỉ thấy trong `run.log`: md5, n_trades, bộ đếm `[TSX]` cơ học); không mở `docs/result/tsx_v2_sim/smoke.json|tables_smoke.md`.
  V336 không thuộc TSX_V3. Hai prereg (TSX_V2_SIM C1–C5 và TSX_V3 dưới đây) áp lên cùng run: TSX_V3 báo verdict theo luật TSX_V3, không chọn luật theo kết quả.
- **V2 trên HO**: B3b không tắt ngày HO nào (15/15 ngày X14 giữ nguyên) ⇒ overrides HO V2 ≡ X14 HO ⇒ HO V2 = `tsx-ho-x14-s*`, ΔHO ≡ 0. Không đẩy kernel HO V2.
- **Diễn giải V2**: "tắt cờ từ ngày sau EOD mà ALT_EW đã hồi ≥ 20 % so với đáy kể từ ngày cờ đầu của đợt (bản theo ngày của B3-20 %)" ⇒ dùng
  ĐÚNG B3b của PREREG_TSX_V2 §2 (đánh giá từng ngày; đợt = chuỗi ngày ON_base liên tiếp) ⇒ bỏ 4 ngày DEV 2022-05-16, 05-18, 05-31, 06-01 (210/214).
  Bản "tắt vĩnh viễn tới hết chuỗi" khác (bỏ 24 ngày 2022-05-16..06-08, 190/214) — KHÔNG chạy (không thêm thử; replay direct chỉ có cho B3b). Ghi để MASTER biết.
- Trial ledger họ TS_MKT_EXT: 15 (X14 + 14 ô TSX_V2) + 4 (TSX_V2_SIM) = 19. TSX_V3: V1/V3/V4 trùng run đã đếm ⇒ không đếm lại; V2 (sim B3b) mới ⇒ **20**.
  (Brief ghi "+4, tổng 19" — lệch vì trùng lặp; ghi ledger trung thực = 20.)
- Kỳ vọng trước (agent): V2 thay đổi rất nhỏ (4 ngày LUNA) ⇒ ΔCAGR22 ≈ 0, khó đạt 8/8 > 0. V1 có thể bớt âm so với replay. V3/V4 có thể mất
  một phần lợi replay (vốn giam). P(≥ 1 ứng viên) thấp (~15–25 %). Mọi kết quả IN-SAMPLE DEV; ứng viên chỉ là ứng viên in-sample v1.2, không đổi shadow/X14.

## 1. Biến thể (cố định)
Jar `sim-jar-tsx` (sha256 cc0f9d11…, code a8690d46); overrides = `OV_BASE` (B0OV + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true`)
+ `SIM_LOSER_TS_EXT_HOURS` + `SIM_LOSER_TS_EXT_DAYS`. Tổng giữ tối đa = 168 + EXT. ON_{thr,L}(D) ⟺ exp(EOD(D−1) − max EOD(D−1−L..D−1)) − 1 ≤ thr
(ALT_EW `edge_attr/index.npz`; HO nối `tsx/ho/ew_out/ew_2026.npz`), cùng công thức `tsx/tsx_flags.py` / `tsx/ho/tsx_ho.py`.
File cờ `~/claude_master/tsx_v3/flags_v3.json` (sha256 5d963184…; bản sao `docs/result/tsx_v3/flags_v3.json`).

| Arm | Định nghĩa | EXT | Tổng giữ | Cờ DEV (ngày / khoảng / sha8 / Δngày vs V0) | Cờ HO (ngày / sha8) | Run DEV | Run HO W9 |
|---|---|---|---|---|---|---|---|
| **V0** | X14 | 336 | 504h | 214 / 42 / c79ef302 / 0 | 15 / ecaced06 | `tsx-x14-*` (+ ctl mới `tsx3-ctl-s13`) | `tsx-ho-x14-s*` |
| **V1** | trần giữ 420h | 252 | 420h | = V0 | = V0 | `tsx2-v420-*` (tái dùng) | `tsx2-ho-v420-s*` |
| **V2** | X14 ∧ reb < 20 % (B3b) | 336 | 504h | 210 / 45 / 2ba530f6 / 4 | = V0 (15 / ecaced06) | `tsx3-v2-*` (MỚI, 8) | = `tsx-ho-x14-s*` |
| **V3** | thr −0,25, L 30 | 336 | 504h | 406 / 57 / 59a9db07 / 192 | 34 / 84dfa414 | `tsx2-vt25-*` (tái dùng) | `tsx2-ho-vt25-s*` |
| **V4** | thr −0,30, L 45 | 336 | 504h | 445 / 41 / c4ab507b / 231 | 37 / d0d0e30a | `tsx2-vl45-*` (tái dùng) | `tsx2-ho-vl45-s*` |

Dự đoán replay (direct ΔPnL/seed vs X14, `phaseB.json`; ô): V1 = B1b_420h −532 (0/8); V2 = B3b_r0.20 −170 (5/8; 1 đợt = LUNA);
V3 = B4_−0.25_30 +4 742 (8/8); V4 = B4_−0.30_45 +3 045 (8/8). Cụm bị ảnh hưởng/seed (replay): V2 41 < V1 69 < V4 134 < V3 164.

## 2. Chạy
- Kernel MỚI (chỉ CPU, `research/tsx_v3/run.py`, = `tsx_driver` B.push): `tsx3-ctl-s13` (V0, kiểm md5 = `tsx-x14-s13`) rồi `tsx3-v2-{a1,s7,s13,s21,s99,s123,s777,s2024}`.
  Chia slot với TSX_V2_SIM: đẩy khi (kernel RUNNING/QUEUED của tài khoản) − (GPU đang PUSHED của tsx2sim) < 5. Không đụng pipeline tsx2sim.
- Parity mỗi run (fail ⇒ VOID, không chấm; lỗi hạ tầng ⇒ chạy lại 1 lần cfg y hệt): jar sha, ok, TOPK 24, skipFull, khoá TSX đúng giá trị,
  B0OV, dòng log `[TSX] extHours=<EXT> extDays=<n_days>`. Run tái dùng: `res_*.json` passed + kiểm lại khoá = flags_v3.json. HO tái dùng: q.check + printDone trước 2025-12-24 = `ho4-k24-b-s*`.
- Chờ đủ run tái dùng của TSX_V2_SIM (DEV 24 + HO 24). Run VOID ⇒ seed đó thiếu ⇒ (i) không thể 8/8 ⇒ không ứng viên (không chạy bù ngoài luật retry hạ tầng).

## 3. Validate (fail ⇒ dừng, không báo kết quả)
- VA1 V0 tái lập từ printDone `tsx-x14-*` + MTM phút mới (`gvz_mtm` import TRƯỚC, `R._work is MT._work_vision`, missing = 0): TB 8 seed CAGR22 39,49 và DD22 −22,55, sai ≤ 0,1pp.
- VA2 md5 printDone `tsx3-ctl-s13` = `tsx-x14-s13` (DEV, CPU); ghi kèm `tsx2-ctl-a1` = `tsx-x14-a1` và `tsx2-ho-ctl-s7` = `tsx-ho-x14-s7` (TSX_V2_SIM).
- VA3 danh sách cờ V0 sinh lại = `tsx/flags.json` (sha c79ef302…) và `ho_flags.json` (ecaced06…) — PASS trước commit này.
- VA4 MTM mọi run missing = 0; ΣPnL MTM = Σ pnl printDone (< 1e-6).
- VA5 cụm hoãn tái dựng từ printDone (quy ước DEEP §1, cờ + trần của biến thể) = `deferClusters` log Java, mỗi run DEV.
- VA6 direct theo seed tính lại từ `phaseB_clusters.csv` = `phaseB.json` delta_seed (≤ 1e-6).

## 4. Chỉ số (mỗi biến thể × 8 seed DEV; median + min/max; Δ so V0 cùng seed)
- CAGR22, ΣPnL, DD22 MTM phút (median + seed tệ nhất; + DD toàn kỳ), Calmar22, UW22 (`n700.arm_metrics`).
- Số cụm / số đợt vào (anchor phân biệt) / số leg (định nghĩa DEEP §1): tổng DEV + theo năm (2021H2, 2022, 2023, 2024, 2025).
- Khối lượng = tổng notional giao dịch Σ q·entry các leg: tổng + theo năm.
- Lệnh bị lỡ: với 25 đợt Phase A, khoá (sym, anchor) cụm vào MỚI ở V0 mà không ở V và ngược lại (+ ΣPnL), tách TRONG đợt [đầu, cuối] và SAU đợt (cuối, cuối + 15 ngày]; và toàn DEV.
- Vốn giam bởi cụm hoãn: notional mở của cụm đang hoãn (tuổi > 168h, ngày cờ) / equity MTM — TB trong giờ ON và đỉnh (DEEP `flag_exposure`).
- Phơi nhiễm TB / max: notional mở / equity MTM, mẫu theo giờ (DEEP `period`).
- Chạm trần U_MAX (0,60): U(t) = Σ margin printDone của leg đang mở tại t / equity MTM(t), mẫu theo giờ ⇒ số giờ U ≥ 0,60 và số lần chạm
  (chuyển < 0,60 → ≥ 0,60). Xấp xỉ (sim dùng equity nội bộ tại tick) — ghi rõ; chỉ mô tả.
- **Phân rã ΔΣPnL (cùng phương pháp DEEP `deep_extra.py`)** = direct + lãi kép (sizing) + phần dư:
  direct = Σ Δ replay của ô tương ứng theo seed (`phaseB.json` delta_seed; V1 B1b_420h, V2 B3b_r0.20, V3 B4_−0.25_30, V4 B4_−0.30_45);
  sizing = Σ trên leg V0 KHÔNG thuộc cụm bị ảnh hưởng (|Δ replay| > 1e-9) của pnl·(bal_V(t)/bal_V0(t) − 1), bal = CAP0 + PnL thực hiện trước t
  (t = thời điểm vào leg); phần dư = ΔΣPnL − direct − sizing (slot/vốn/lệnh khác).
- Δ theo năm đóng (2021H2…2025) và theo đợt (direct_e từ `phaseB_clusters.csv`; Δ đoạn = ΔPnL thực hiện theo giờ đóng UTC trong [đầu đợt k, đầu đợt k+1));
  riêng LUNA (2022-04-27..2022-07-06) và 06/2024 (2024-06-18..2024-07-26).
- Replay vs sim: ΔΣPnL_sim − direct (chiều + độ lớn) theo seed.
- HO W9 (mô tả): ΔPnL / ΔROI / ΔmaxDD vs `tsx-ho-x14-s*` theo seed (scorer HO4 `ecm_mtm_h.py`, như X14 HO), số cụm hoãn (log Java).

## 5. Luật ỨNG VIÊN v1.2 (cố định)
Biến thể là ỨNG VIÊN ⟺ (i)–(iv) đều đạt; (v) là cờ cảnh báo:
- (i) ΔCAGR22 > 0 ở 8/8 seed DEV.
- (ii) DD22 MTM seed tệ nhất của V ≥ DD22 seed tệ nhất của V0 − 1,0pp.
- (iii) Leave-one-episode-out theo direct: e* = argmax_e TB-8-seed direct_e (25 đợt Phase A); yêu cầu TB 8 seed của (ΔΣPnL_sim − Δ đoạn_{e*}) > 0.
- (iv) Số đợt vào DEV: TB 8 seed của (n_V / n_V0 − 1) ≥ −3 %.
- (v) HO W9 ΔPnL ≥ 0 ở ≥ 6/8 seed — MÔ TẢ, không chặn; không đạt ⇒ "ứng viên + CẢNH BÁO HO". Ứng viên luôn chỉ là in-sample.
Nhiều ứng viên ⇒ chọn cái ít thay đổi nhất so X14, thứ tự cố định theo số cụm bị ảnh hưởng/seed trong replay: V2 < V1 < V4 < V3.
0 ứng viên ⇒ ĐÓNG hướng tinh chỉnh TS_MKT_EXT (giữ X14). Không thử thêm ô, không đổi ngưỡng sau khi thấy kết quả.

## 6. Xuất
`docs/result/TSX_V3.md` + `docs/result/tsx_v3/` (JSON/CSV/bảng + bản sao script). Commit; không push.
