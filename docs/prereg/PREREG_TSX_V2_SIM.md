# PREREG_TSX_V2_SIM — 4 biến thể giữ/cờ của TS_MKT_EXT X14, chấm bằng SIM JAVA ĐẦY ĐỦ (DEV 8 seed) — 2026-10-22

Viết + commit TRƯỚC khi đẩy bất kỳ kernel biến thể nào. Nền: TS_MKT_EXT X14 (prereg 1e138619; DEV c1ab8eda; HO 46ebc1ee; DEEP 40b12804), TSX_V2 replay (prereg 6b7ab1a8, kết quả f620575c — 0 ứng viên). Không 2020 (`bcast-*` niêm phong), không đụng 242/shadow, không Binance REST. HO 2026 CHỈ MÔ TẢ.

## 0. Trung thực / thiên lệch đã biết
- Replay TSX_V2 KHÔNG tính vốn giam/slot/lãi kép/DCA mới ⇒ đánh giá THẤP biến thể giữ ngắn hơn (vốn giải phóng ⇒ thêm lệnh) và đánh giá CAO biến thể giữ lâu/nhiều hơn (vốn giam ⇒ mất lệnh). DEEP: phần dư X14 vs P0 −3,2k/seed (ít slot/cụm), LUNA lỡ crash-buy ~−0,7k/seed.
- **VT25 và VL45 được chọn SAU khi xem bề mặt replay B4** (B4 −0,25/30 +4 742/seed, −0,30/45 +3 045/seed) ⇒ in-sample, có data-snooping; 100 % phần dương replay của chúng đến từ giữ VƯỢT thời điểm thoát run nguồn (vùng replay yếu nhất). V336/V420 có replay âm (−1 399 / −532, 0/8) nhưng thiên lệch replay chống lại chúng ⇒ sim là phép thử công bằng hơn.
- Trial ledger họ TS_MKT_EXT: 15 trước đó (X14 + 14 ô TSX_V2) + 4 biến thể này = **19**. Mọi kết quả là IN-SAMPLE DEV; ứng viên (nếu có) chỉ là ứng viên in-sample v1.2, không đổi shadow/X14 đang chạy.
- Kỳ vọng trước (MASTER): V336/V420 có thể bớt âm hoặc dương trong sim (vốn giải phóng), VT25/VL45 có thể mất một phần lợi replay (vốn giam, lỡ crash-buy). Không có ước lượng xác suất chính thức.

## 1. Biến thể (cố định)
Jar `sim-jar-tsx` (sha256 cc0f9d11…, code a8690d46), overrides = `OV_BASE` (B0OV + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true`) + `SIM_LOSER_TS_EXT_HOURS` + `SIM_LOSER_TS_EXT_DAYS`. Tổng giữ tối đa = 168 + EXT.
Cờ ngày: CÙNG công thức `tsx/tsx_flags.py` (DEV) và `tsx/ho/tsx_ho.py flags()` (HO 2026), chỉ đổi (ngưỡng, lookback): ON(D) ⟺ exp(EOD(D−1) − max EOD(D−1−L..D−1)) − 1 ≤ thr (rolling L+1). Script `research/tsx_v2_sim/flags.py` → `flags_variants.json`; tự kiểm (−0,30/30) trùng `flags.json`/`ho_flags.json` 100 % (PASS trước commit này).

| Arm | EXT_HOURS | Tổng giữ | thr | L | Cờ DEV (ngày / khoảng / sha8) | Cờ HO 2026 (ngày / khoảng / sha8) |
|---|---|---|---|---|---|---|
| X14 (nền, có sẵn) | 336 | 504h | −0,30 | 30 | 214 / 42 / c79ef302 | 15 / 4 / ecaced06 |
| **V336** | 168 | 336h | −0,30 | 30 | = X14 | = X14 |
| **V420** | 252 | 420h | −0,30 | 30 | = X14 | = X14 |
| **VT25** | 336 | 504h | −0,25 | 30 | 406 / 57 / 59a9db07 | 34 / 2 / 84dfa414 |
| **VL45** | 336 | 504h | −0,30 | 45 | 445 / 41 / c4ab507b | 37 / 3 / d0d0e30a |

Dự đoán replay (direct ΔPnL/seed vs X14, `phaseB.json`): V336 = B1a −1 399 (0/8); V420 = B1b −532 (0/8); VT25 = B4 −0,25/30 +4 742 (8/8); VL45 = B4 −0,30/45 +3 045 (8/8).

## 2. Chạy
- DEV: `tsx2-{v336,v420,vt25,vl45}-{a1,s7,s13,s21,s99,s123,s777,s2024}` (32 kernel; pred/seed như X14; A1 CPU, seed khác CPU hoặc GPU — GPU đã kiểm bit-exact với jar này `tsx-gpuchk-s7` = `gqsf-s7`). Nền so sánh = `tsx-x14-*` có sẵn.
- HO W9: `tsx2-ho-{arm}-s{42,7,13,21,99,123,777,2024}` (32 kernel, `ho4p1_queue`, end 20261001, cfg k24 + 2 khoá với cờ HO). Nền = `tsx-ho-x14-s*` (+ `ho4-k24-b-s*`).
- Parity từng run (fail ⇒ VOID, không chấm): jar sha, ok, TOPK 24, skipFull, khoá TSX đúng giá trị, dòng log `[TSX] extHours=<EXT> extDays=<n_days>`; HO: `q.check` + printDone trước 2025-12-24 trùng `ho4-k24-b-s*`.

## 3. Validate (fail ⇒ dừng, không báo kết quả)
- V1: X14 tái lập từ printDone + MTM phút mới (gvz_mtm import trước, `R._work is MT._work_vision`, missing = 0): TB CAGR22 39,49 và DD22 −22,55, sai ≤ 0,1pp.
- V2: driver mới với tham số = X14 ⇒ md5 printDone bit-exact: `tsx2-ctl-a1` = `tsx-x14-a1` (DEV); `tsx2-ho-ctl-s7` (GPU) = `tsx-ho-x14-s7` (nếu GPU lệch ⇒ chạy lại CPU; CPU khớp ⇒ HO chỉ dùng CPU).
- V3: MTM mọi run missing = 0; ΣPnL = Σ pnl printDone.
- V4: tái dựng số cụm hoãn từ printDone = `deferClusters` log Java (mỗi run DEV, quy ước DEEP §1).

## 4. Chỉ số (median + min/max 8 seed; Δ so X14 cùng seed)
CAGR22, ΣPnL, DD22 MTM phút (+ seed tệ nhất; DD toàn kỳ), Calmar22, UW22 (`n700.arm_metrics`); số cụm / số đợt vào (anchor phân biệt) / số leg (định nghĩa DEEP §1); notional giao dịch tổng (Σ q·entry các leg); phơi nhiễm TB/max (notional mở / equity MTM, mẫu theo giờ); cụm hoãn (quy ước DEEP với cờ + trần của biến thể) và vốn giam bởi cụm hoãn / equity (TB trong giờ ON, đỉnh); **cụm crash-buy lỡ so X14**: trong cửa sổ [đầu đợt, cuối đợt + 15 ngày) của 25 đợt Phase A, khoá (sym, anchor) vào ở X14 mà không ở biến thể và ngược lại, kèm ΣPnL; cũng báo cho toàn DEV.
**Phân rã ΔΣPnL** = direct (replay `research/tsx_v2/`, `phaseB.json` delta_seed của ô tương ứng) + phần còn lại (slot/lãi kép/lệnh khác) = ΔΣPnL_sim − direct. Theo năm (ΔPnL theo năm đóng 2021H2…2025) và theo đợt (25 đợt Phase A; Δ đoạn = ΔPnL thực hiện theo giờ đóng UTC trong [đầu đợt k, đầu đợt k+1); direct theo đợt từ `phaseB_clusters.csv`; nêu LUNA, FTX, 04/2024, 06/2024, 03/2025, 10–12/2025).

## 5. Luật ỨNG VIÊN v1.2 (cố định)
Ứng viên ⟺ cả 5:
- C1 ΔCAGR22 > 0 ở ≥ 7/8 seed.
- C2 ΔCalmar22 ≥ 0 ở ≥ 6/8 seed.
- C3 DD22 seed tệ nhất của biến thể ≥ DD22 seed tệ nhất của X14 − 1,0pp.
- C4 leave-one-episode-out: với CẢ HAI thước M ∈ {direct, Δ đoạn}, lấy M_e = TB 8 seed theo đợt e; Σ_e M_e − max_e M_e > 0.
- C5 số đợt vào DEV: TB 8 seed của (n_V / n_X14 − 1) ≥ −2 %.
Nhiều ứng viên ⇒ ít tham số đổi nhất (cả 4 đều đổi 1) ⇒ median ΔCalmar22 lớn hơn ⇒ DD22 seed tệ nhất tốt hơn. 0 ứng viên ⇒ giữ X14. Không thử thêm ô, không đổi ngưỡng sau khi thấy kết quả.
HO W9 (mô tả, không chấm): ΔPnL / ΔROI / ΔmaxDD vs `tsx-ho-x14-s*` theo seed, số cụm hoãn; không đổi shadow.

## 6. Xuất
`docs/result/TSX_V2_SIM.md` + `docs/result/tsx_v2_sim/` (JSON/CSV + script). Commit; không push.
