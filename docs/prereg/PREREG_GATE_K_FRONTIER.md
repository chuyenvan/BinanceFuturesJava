# PREREG_GATE_K_FRONTIER — frontier K × gate (nới gate/siết K và ngược lại; K theo độ mạnh gate)

Ngày 2026-10-06 (GMT+7). Chốt TRƯỚC mọi số của vòng này. MASTER chốt thiết kế (brief `Claude outputs/BRIEF_GATE_K_FRONTIER_20261006.md`, commit `46a1dc36`); agent không đổi sau khi thấy số. Nghiên cứu thay thế nhánh held-rerank đã NO-GO (commit `4ff24c1a`, `feat/rank-margin`).
Bối cảnh: gate "đều lệnh" rolling ratio đang chạy (K24, ρ ≈ 6,2–6,3e-5, pct 0,999950829). Owner thấy K24 vẫn giữ chất lượng ⇒ muốn biết có thể đẩy số lệnh ~740 → ~1 000/năm mà không hỏng chất lượng bằng cách đổi trục K × gate, có "cái gì đó kiểm soát tránh vào ồ ạt".
Ràng buộc: 0 Java sim trên Oracle (chỉ `mvn -o test` + build, riêng Phase 3 branch), 0 chạm 242/shadow_c3, 0 merge/promote, DEV ≤ 2025-12-31 (2026 niêm phong), Kaggle ≤ 2 kernel song song, RAM ≤ 8G, lock `~/claude_master/1002/oracle_heavy.lock`, df < 500 MB ⇒ dừng.

## 1. Câu hỏi + giả thuyết (CỐ ĐỊNH)
- **H1 (đánh đổi tĩnh):** cùng số lệnh/năm thì (a) **nới gate** + **siết K**, hoặc (b) **siết gate** + **nới K**, một trong hai cho PnL/Calmar tốt hơn điểm hiện tại (K24, pct 0,999950829).
- **H2 (K thích ứng):** khi gate mạnh (phút sập sâu, r vượt q_t nhiều) cho vào sâu hơn bảng xếp hạng S1 (K lớn hơn); khi gate vừa đủ mở thì giữ K chặt.

## 2. Cơ chế hiện tại (sự thật đã kiểm, có nguồn)
- Gate pass ⇔ `r = p15 / (max(0,26787, sp/0,15·1,2876) · 1,55) ≥ q_t` (`EntryGate.java`, `GateRollingRatio.java:105-108`, `GateRatioBuffer.java`). q_t = phân vị `pct` của r trên **mọi symbol-phút trong top-K** của 90 ngày gần nhất; tính lại mỗi giờ, warm-up 7 ngày. Coin đang giữ bị loại trước (cap-then-skip).
- p15 là market-level (chung mọi coin trong 1 phút); r chỉ khác qua `dyn(sp)` với `sp_k = 1 − pwin_(k)` ⇒ hạng càng sâu sp càng cao, r càng nhỏ ⇒ hạng 1 qua trước, hạng 20 chỉ qua khi p15 rất cao.
- **K chỉ là trần** và trần chỉ chạm ở phút mạnh. Nâng K trộn 2 tác dụng: (i) cho hạng sâu vào lệnh ở phút mạnh; (ii) đưa thêm r hạng sâu vào buffer ⇒ đổi q_t ⇒ mở thêm phút. **Phải tách riêng** (Phase 3).
- Quota ≈ ρ × luồng ứng viên; ρ ≈ 6,2–6,3e-5 không đổi qua K16/24/32. K và pct **cùng lever về số lệnh**, khác **phân bổ** (K thêm coin vào phút đã mạnh, pct thêm phút mới).
- Sizing: `managerBudget` U = margin/equity, throttle = 1 − U/U_MAX (0,60), F_BASE 0,015. `GATE_QUOTA_SKIP_WHEN_FULL=true` ⇒ không tiêu quota khi sổ đầy. **Mọi arm vòng này bật skipFull.**

## 3. Bằng chứng đã có (đọc trước, KHÔNG đo lại)
| Bằng chứng | Số | Ý nghĩa |
|---|---|---|
| N700 A1 K24 vs B0 K16 (9a62e1a0) | n 521→732, CAGR22 33,6→36,7, Calmar 1,90→1,65 | nới K: chất lượng giảm nhẹ |
| N700 A2 pct 0,99985 @K16 | n 1 242, Calmar 1,34 (0,71×), UW 284, 2022 âm, %ΣPnL lệnh 0h 42→55% | nới gate mạnh ⇒ chất lượng sụt rõ — bất lợi H1(a) |
| RANKBAND_K24 (96da8f82) | ROI/lệnh hạng 1–8/9–16/17–24 = 3,42/3,43/3,47%; PnL hạng 17–24 ≈ ½ do size | siết K không mua thêm chất lượng/lệnh — bất lợi H1(a) |
| R50 (b7fedef4) | random 16 trong top-50: Calmar 1,05 vs 3,43 | sau hạng 24 chất lượng phải rơi mạnh — chưa biết rơi từ hạng nào |
| BD anatomy (7b17140a) | lệnh >20 trong episode (42% ΣPnL) và lúc >30 lệnh mở (23%) LÃI NHẤT | ủng hộ H2 / H1(b): phút mạnh chịu nhiều lệnh hơn |
| GATE_SEEDBAND + SKIPFULL | K24 ON 8 seed CAGR22 36,98 ± 1,37 (OFF 34,18 ± 3,58) | nhiễu theo seed gate rất lớn ⇒ bắt buộc đa seed |
| COST_TRUTH (d059cc3) | lệnh vào nến ≤ −1%: trượt giá +1,675%/chân [+0,90;+2,67] | vào sâu lúc sập ⇒ chấm thêm stress cost |

**Prior của MASTER (khai trước, không phải kết luận):** H1(a) khả năng thua cao; H1(b) chưa rõ (phụ thuộc chất lượng hạng 25–48, chưa đo); H2 đáng thử nhất về cơ chế; khả dĩ nhất là các điểm frontier **không phân biệt được với nhiễu** (MDE ~4–5pp CAGR22).

## 4. Thiết kế (CỐ ĐỊNH)
### Phase 0.a — Hiệu chuẩn iso-n bằng đếm offline (không PnL, 1 bước Oracle)
- Mở rộng `research/analysis/gate_offline.py` thêm `--topk K --pct P`: đếm symbol-pass/năm, phút mở/năm, lệnh ước tính.
- Validate trước khi dùng: n700-a1 (K24 base) · n700-a2 (K16 pct 0,99985) · gqsf seed 42 (K24 ON) — pass lệch ≤ 2%.
- Offline không mô hình U_MAX/budget ⇒ lệnh thật ≤ pass tháng sập; báo tỷ lệ lệnh/pass tham chiếu và dùng để quy đổi.
- Công thức iso-n: `pct(K) = 1 − ρ_base·24/K·(n_target/740)` với ρ_base = 4,9171e-5 @K24. **Giá trị cuối cùng lấy theo đếm offline seed 42** sao cho lệnh ước tính lệch ≤ 3% mục tiêu. Ghi pct vào pre-reg (amendment) TRƯỚC Phase 1.

### Phase 0.b — RANKBAND sâu (1 kernel Kaggle, chẩn đoán, chỉ báo cáo)
- K48, pct = iso-n cho n ≈ 1 000 (từ P0.a), skipFull ON, seed 42.
- Báo: ROI%/lệnh, SL%, ΣPnL, size TB theo dải hạng 1–8/9–16/17–24/25–32/33–40/41–48; theo năm; theo **độ mạnh phút** `s = r/q_t` lúc vào lệnh (3 tercile chia theo đếm, không theo PnL).
- Mục đích: xác định chất lượng có rơi sau hạng 24 không, rơi ở đâu. KHÔNG dùng để chọn K cho Phase 1 (arm Phase 1 đã cố định).
- **Luật chạy Phase 3 (khai trước):** nếu ROI/lệnh dải 25–32 ≥ 0,8 × dải 1–24 ⇒ chạy Phase 3 với K_entry ∈ {32, 48}; nếu chỉ dải 25–32 đạt mà 33–48 < 0,8× ⇒ chỉ K_entry = 32; nếu dải 25–32 < 0,8× ⇒ **dừng Phase 3**.

### Phase 1 — frontier tĩnh, sàng lọc 1 seed (8 kernel, seed 42)
- Mọi arm skipFull ON, jar `sim-jar-shadow2` (code module `3a80ba91`, P0 `ff3ce513`).
- **Đường iso-740** (cùng n, so phân bổ): K12, K16, K32, K40. Nền = K24 pct base (`gqsf` seed 42, cost 0).
- **Đường iso-1000** (tăng n): K16, K24, K32, K40 (mỗi điểm pct cho n ≈ 1 000).
- Không thêm arm, không đổi pct sau khi thấy số.
- **Sàng lọc (khai trước):** mỗi đường xếp theo Calmar22 MTM, hoà thì CAGR22. Lấy top-2 mỗi đường sang Phase 2. Nếu iso-740 không arm nào Calmar22 ≥ nền ⇒ vẫn lấy top-1 để có dải nhiễu.

### Phase 2 — xác nhận 3 seed (≤ 8 kernel)
- Arm chọn ở Phase 1 × seed {7, 21}. pred.bin seed 7 từ `~/claude_master/1004/gabl/ds_SEED7/pred.bin` (dataset `gate-abl-*`), seed 21 từ `~/claude_master/1004/gsb/pred_S21/pred.bin` (dataset `gate-sb-s21`).
- Nền K24 ON seed 7/21 đã có (`gqsf-*`), cost 0. So ghép cặp theo seed.

### Phase 3 — H2: tách K_entry khỏi K_buffer (cần Java; chỉ khi luật P0.b cho phép)
- Key mới `GATE_BUFFER_TOPK` (mặc định −1 = bằng `SELECTOR_RANK_TOPK` ⇒ byte-identical).
- `GATE_BUFFER_TOPK = 24` và `SELECTOR_RANK_TOPK = K_entry > 24`: chỉ r hạng 1–24 nạp buffer (q_t giữ đúng nền); hạng 25..K_entry vẫn được kiểm `r ≥ q_t` và vào lệnh nếu qua, không nạp buffer.
- Tách tác dụng (i) khỏi (ii) ở §2. **Không có ngưỡng mới nào để tune.** Áp cả sim lẫn live (cùng `EntryGate`/`GateRatioBuffer`).
- Quy ước code: JUnit ON/OFF, Cfg gateway (`tools/check_cfg_gateway.sh`), SLF4J, branch riêng `feat/gate-buffer-topk`, P0 B0@K16 md5 `ff3ce513` khi OFF.
- Arm: K_entry ∈ {32, 48} (theo luật P0.b) × seed {42, 7, 21}, vs nền K24 ON cùng seed. Tối đa 6 kernel + 1 P0.

## 5. Thước + luật GO (CỐ ĐỊNH)
- **Thước chính:** MTM ngày ghép cặp block-10d, NREP 2000, seed bootstrap 20260905, arm vs nền **cùng seed gate**. Báo CAGR22, ΔPnL, maxDD MTM phút, Calmar22, UW22, n/năm, phút vào/năm (đặc biệt 2022), skipFull count, U TB và p95. Theo năm 2022–2025, theo quý, ex-2022, %ΣPnL top-10 ngày, %ΣPnL lệnh 0h.
- **Stress cost bắt buộc:** +1,675%/chân cho chân vào nến 1m ≤ −1% (COST_TRUTH). Báo cả base và stress. GO phải đạt **cả hai**.
- **Inflate:** half-width × √(2 ln k), k = tổng arm đã nhìn (Phase 1 = 8, +Phase 3 nếu chạy).
- **Đa seed:** mean ± sd qua 3 seed, CI paired t (df 2, yếu, ghi rõ), số seed có Δ > 0.
- **Luật GO (§9 A.4/A.5):**
  - **iso-740:** Calmar22 tăng ở **3/3 seed** VÀ mean ΔCAGR22 ≥ 0 VÀ maxDD ≤ 40% mọi seed VÀ mean ΔCAGR23 ≥ −1,0pp VÀ đạt cả base lẫn stress.
  - **iso-1000:** mean ΔPnL > 0 với CI MTM inflate (gộp 3 seed) loại 0 VÀ maxDD ≤ 40% mọi seed VÀ Calmar22 ≥ 0,90 × nền mỗi seed VÀ ≥ 3/4 năm ΔROI ≥ 0 VÀ đạt cả base lẫn stress.
  - **Phase 3:** cùng luật iso-1000.
  - **Không arm nào GO ⇒ giữ K24 pct base.** Không chọn "điểm ước lượng tốt nhất" khi nằm trong nhiễu.
- Win%/SL% chỉ báo cáo.

## 6. Điều gì sẽ bác giả thuyết (CỐ ĐỊNH)
- **H1(a) chết:** mọi arm iso-740 có K < 24 có Calmar22 ≤ nền (seed 42 ở Phase 1; ≥ 2/3 seed ở Phase 2).
- **H1(b) chết:** RANKBAND sâu cho ROI dải 25–32 < 0,8 × dải 1–24, HOẶC arm K32/K40 iso-740 Calmar22 ≤ nền.
- **H2 chết:** Phase 3 không GO, hoặc không được chạy theo luật P0.b.
- **Cả ba chết** ⇒ ghi "trục K × gate trên DEV đóng"; hướng tăng n còn lại: chỉ forward/shadow, hoặc selector mới (S1_V2).

## 7. Kỳ vọng khai trước (điểm ước lượng, sẽ so với thực tế)
- MDE sau inflate ~4–5pp CAGR22 ⇒ phần lớn chênh lệch frontier khả năng nằm trong nhiễu.
- H1(a) nới gate + siết K: kỳ vọng Calmar thấp hơn nền.
- H2 (K thích ứng tách buffer): kỳ vọng đáng thử nhất, nhắm đúng BD anatomy.
- Ràng buộc: điểm số cụ thể từng đường ghi vào RESULT sau khi chạy, đối chiếu với prior ở §3.

## 8. Ràng buộc thực thi (bắt buộc)
- Pre-reg commit + push TRƯỚC sim. Gồm câu hỏi, arm, pct cuối cùng (sau P0.a), luật Phase 3, thước, luật GO, kỳ vọng khai trước, số kernel. Ghi hash. Mọi thứ ngoài pre-reg chỉ là "báo cáo".
- Kernel = `tools/kaggle_sim.py` HEAD (guard NOWRITE242) + khối `pred_ds` như các vòng gate. Tối đa 2 kernel song song.
- Parity mỗi run: jar sha, log override (`SELECTOR_RANK_TOPK`, `SIM_GATE_ROLLING_PCT`, `GATE_QUOTA_SKIP_WHEN_FULL=true`, `GATE_BUFFER_TOPK` nếu có), md5 pred.bin "md5 verified", n, eq, md5 printDone. Chạy lại nền K24 ON seed 42 qua đường mới (nếu đổi driver) phải trùng md5 `gqsf` seed 42.
- KHÔNG chạm 242/shadow. KHÔNG Java sim trên Oracle. KHÔNG sửa Java ngoài Phase 3 (branch riêng). DEV ≤ 2025-12-31, holdout 2026 niêm phong. Python logging, Java SLF4J.
- Git: fetch + kiểm fast-forward trước push. Không `pull --rebase` khi có merge commit. Chỉ add file của mình.

## 9. Sản phẩm
- `docs/prereg/PREREG_GATE_K_FRONTIER.md` (file này)
- `research/analysis/gate_k_frontier_driver.py` + `gate_offline.py` (`--topk --pct`)
- `docs/audit/GATE_OFFLINE_ISON_CALIB.md` (P0.a) · `docs/audit/RANKBAND_K48.md` (P0.b)
- `docs/result/RESULT_GATE_K_FRONTIER.md` + `gate_k_frontier.json`
- Phase 3: branch `feat/gate-buffer-topk` + doc audit

## 10. Chi phí ước tính
P0.a ~1–2h Oracle · P0.b 1 kernel · Phase 1 8 kernel · Phase 2 ≤ 8 kernel · Phase 3 ~½ ngày Java + ≤ 7 kernel. Tổng ≤ 24 kernel, ~10–14h wall (2 kernel song song). Đĩa ≤ 1 GB.
