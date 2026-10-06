# BRIEF — GATE × K FRONTIER (nới gate / siết K và ngược lại; K theo độ mạnh gate)

Người viết: MASTER (2026-10-06). Người thực thi: claw. Trạng thái: **BRIEF**. Claw phải chuyển thành pre-reg (`docs/prereg/PREREG_GATE_K_FRONTIER.md`) và commit TRƯỚC khi chạy bất kỳ sim nào. Không được tune sau khi thấy số.

---

## 0. Câu hỏi của owner, viết lại cho đo được

Owner thấy với gate rolling hiện tại, K24 vẫn giữ chất lượng. Từ đó có hai giả thuyết:

- **H1 (đánh đổi tĩnh):** cùng một số lệnh/năm thì có thể (a) **nới gate** (mở nhiều phút hơn) và **siết K** (ít coin/phút), hoặc (b) **siết gate** và **nới K**. Một trong hai cách cho PnL/Calmar tốt hơn điểm hiện tại (K24, pct 0,999950829).
- **H2 (K thích ứng):** khi gate mạnh (phút sập sâu, r vượt q_t nhiều) thì cho vào sâu hơn trong bảng xếp hạng S1 (K lớn hơn). Khi gate vừa đủ mở thì giữ K chặt.

Mục tiêu cuối: tìm cấu hình đưa số lệnh từ ~740 lên ~1 000/năm mà không làm hỏng chất lượng, theo luật §9 A-20261003.

---

## 1. Cơ chế hiện tại (sự thật đã kiểm, có nguồn)

- **Công thức gate** (`EntryGate.java`, `GateRollingRatio.java:105-108`, `GateRatioBuffer.java`): pass ⇔ `r = p15 / (max(0,26787, sp/0,15·1,2876) · 1,55) ≥ q_t`.
  - q_t là phân vị `pct = 0,999950829` của r, tính trên **mọi symbol-phút trong top-K** của 90 ngày gần nhất. Tính lại mỗi giờ, warm-up 7 ngày.
  - Coin đang giữ bị loại trước (cap rồi mới skip).
- **p15 là market-level:** mọi coin trong cùng một phút có chung p15. Trong một phút, r chỉ khác nhau qua `dyn(sp)`.
  - Với C3, `sp_k = 1 − pwin_(k)`, và pwin giảm dần theo hạng S1 ⇒ **hạng càng thấp thì sp càng cao, dyn càng cao, r càng nhỏ**.
  - Nghĩa là trong một phút, hạng 1 qua gate trước. Hạng 20 chỉ qua khi p15 của phút đó rất cao.
  - Bằng chứng: pass rate theo decile sp giảm từ 43,7 xuống 0 (×1e-5) (GATE_QUOTA_DIAG §D3, 15d3e2d5).
- **Hệ quả quan trọng cho H2:** K **chỉ là trần** và trần này chỉ chạm ở các phút mạnh. Hệ thống đã có sẵn một phần "K thích ứng" ngầm. Nâng K có 2 tác dụng trộn vào nhau:
  - (i) cho hạng sâu hơn vào lệnh ở phút mạnh;
  - (ii) đưa thêm r của hạng sâu vào **buffer**, làm đổi q_t (quota = ρ × luồng ứng viên nên số pass tăng ∝ K, q_t hạ ⇒ mở thêm phút mới).

  Hai tác dụng này phải **tách riêng** (Phase 3).
- **Quota:** số pass ≈ ρ × luồng ứng viên. ρ ≈ 6,2–6,3e-5 và không đổi qua K16/24/32 (AUDIT_CHAIN_AND_N, c733467c). K và pct là **cùng một lever về số lệnh**. Khác nhau ở **phân bổ**: K chủ yếu thêm coin vào phút đã mạnh, pct thêm phút mới.
- **Sizing:** `TradeUtils.managerBudget` có `U = margin/equity`, `throttle = 1 − U/U_MAX` (U_MAX 0,60), F_BASE 0,015. Nhiều lệnh ⇒ mỗi lệnh nhỏ hơn. U ≥ U_MAX ⇒ chặn. `GATE_QUOTA_SKIP_WHEN_FULL=true` ⇒ không tiêu quota khi sổ đầy (merge 95d32a56). **Mọi arm vòng này bật skipFull.**

## 2. Bằng chứng đã có (đọc trước, không đo lại)

| Bằng chứng | Số | Ý nghĩa cho vòng này |
|---|---|---|
| N700 A1 K24 vs B0 K16 (9a62e1a0) | n 521→732, CAGR22 33,6→36,7, Calmar 1,90→1,65 | nới K: chất lượng giảm nhẹ |
| N700 A2 pct 0,99985 @K16 | n 1 242, Calmar 1,34 (0,71×), UW 284, 2022 âm, thay 73% sổ lệnh, % ΣPnL từ lệnh 0h 42→55% | **nới gate mạnh thì chất lượng sụt rõ** — bất lợi cho H1(a) |
| RANKBAND_K24 (96da8f82) | ROI/lệnh hạng 1–8/9–16/17–24 = 3,42/3,43/3,47%; PnL/lệnh hạng 17–24 ≈ ½ chỉ vì size | trong top-24 xếp hạng không phân biệt ROI ⇒ **siết K không mua thêm chất lượng/lệnh** — bất lợi cho H1(a) |
| R50 (b7fedef4) | random 16 trong top-50: Calmar 1,05 vs 3,43 | ở đâu đó sau hạng 24 chất lượng phải rơi mạnh — **chưa biết rơi từ hạng nào** |
| BD anatomy (7b17140a) | lệnh thứ >20 trong một episode (42% ΣPnL) và lúc >30 lệnh mở (23%) LÃI NHẤT | ủng hộ H2 / H1(b): phút/đợt mạnh chịu được nhiều lệnh hơn |
| GATE_SEEDBAND + SKIPFULL | K24 ON 8 seed: CAGR22 36,98 ± 1,37 (OFF 34,18 ± 3,58) | nhiễu theo seed gate là rất lớn ⇒ **bắt buộc đa seed** |
| COST_TRUTH (d059cc3) | lệnh vào trong nến ≤ −1%: trượt giá +1,675%/chân [+0,90;+2,67] | vào sâu hơn lúc sập ⇒ phải chấm thêm **stress cost** |

**Prior của MASTER (khai trước, không phải kết luận):**

- H1(a) nới gate + siết K: **khả năng thua cao**. N700 A2 cho thấy nới gate kéo chất lượng xuống, trong khi siết K không bù được vì ROI phẳng theo hạng.
- H1(b) siết gate + nới K: **chưa rõ**. Nó phụ thuộc chất lượng hạng 25–48 (chưa đo).
- H2 (K thích ứng tách khỏi buffer): **đáng thử nhất về cơ chế**, vì nhắm đúng chỗ BD anatomy nói là lãi.
- Kết cục khả dĩ nhất: các điểm trên frontier **không phân biệt được với nhiễu** (MDE sau inflate ~4–5pp CAGR22).

## 3. Thiết kế

### Phase 0 — chuẩn bị, chẩn đoán, không chọn gì (1 kernel)

**P0.a — Hiệu chuẩn iso-n bằng đếm offline** (không PnL, không phải "nhìn DEV").
- Mở rộng `research/analysis/gate_offline.py` thêm `--topk K --pct P`. Đếm số symbol-pass/năm, số phút mở/năm và số lệnh ước tính.
- **Validate trước khi dùng**, so offline với sim đã có:

  | Run tham chiếu | Cấu hình | Kỳ vọng |
  |---|---|---|
  | n700-a1 | K24 pct base | pass lệch ≤ 2% |
  | n700-a2 | K16 pct 0,99985 | pass lệch ≤ 2% |
  | gqsf seed 42 | K24 ON | pass lệch ≤ 2% |

  Lưu ý (GATE_QUOTA_DIAG §D1): offline không mô hình U_MAX/budget, nên số lệnh thật ≤ số pass ở tháng sập. Phải báo tỷ lệ lệnh/pass của sim tham chiếu và dùng tỷ lệ đó để quy đổi.
- Từ ρ ∝ 1/K cho iso-n: `ρ_base = 1 − 0,999950829 = 4,9171e-5` @K24. Ước lượng đầu: `pct(K) = 1 − ρ_base·24/K·(n_target/740)`. **Giá trị cuối cùng lấy theo đếm offline** (seed 42) sao cho số lệnh ước tính lệch ≤ 3% mục tiêu. Ghi pct vào pre-reg TRƯỚC Phase 1.

**P0.b — RANKBAND sâu** (1 kernel Kaggle, chẩn đoán, chỉ báo cáo).
- Cấu hình: K48, pct = pct iso-n tương ứng cho n ≈ 1 000 (từ P0.a), skipFull ON, seed 42.
- Báo cáo (dùng cách join rank của RANKBAND_K24 / R50):
  - ROI%/lệnh, SL%, ΣPnL, size TB theo dải hạng 1–8, 9–16, 17–24, 25–32, 33–40, 41–48;
  - theo năm;
  - theo **độ mạnh phút** `s = r/q_t` tại lúc vào lệnh (3 tercile **chia theo đếm**, không theo PnL).
- Mục đích: xác định chất lượng có rơi sau hạng 24 không, rơi ở đâu. **Không** dùng kết quả để chọn K cho Phase 1 (arm Phase 1 đã cố định ở §3 Phase 1). Kết quả chỉ dùng để quyết **có chạy Phase 3 hay không**, theo luật dưới.
- Luật chạy Phase 3 (khai trước): nếu ROI/lệnh dải 25–32 ≥ 0,8 × ROI/lệnh dải 1–24 thì chạy Phase 3 với K_entry ∈ {32, 48}; nếu chỉ dải 25–32 đạt mà 33–48 < 0,8× thì chỉ K_entry = 32; nếu dải 25–32 < 0,8× thì **dừng Phase 3**.

### Phase 1 — frontier tĩnh, sàng lọc 1 seed (8 kernel, seed 42)

- Arm (K, pct) với pct từ P0.a; mọi arm skipFull ON, jar dataset `sim-jar-shadow2` (code module 3a80ba91, P0 ff3ce513).
- **Đường iso-740** (cùng số lệnh với nền, so phân bổ): **K12, K16, K32, K40**. Nền = K24 pct base (đã có: `gqsf` seed 42, cost 0).
- **Đường iso-1000** (tăng số lệnh): **K16, K24, K32, K40**, mỗi điểm với pct cho n ≈ 1 000.
- Không thêm arm, không đổi pct sau khi thấy số.
- **Điểm sàng lọc (khai trước):** trên mỗi đường, xếp hạng arm theo Calmar22 MTM, hoà thì theo CAGR22. Lấy **top-2 mỗi đường** sang Phase 2. Nếu trên đường iso-740 không arm nào có Calmar22 ≥ nền thì vẫn lấy top-1 để có dải nhiễu.

### Phase 2 — xác nhận 3 seed (≤ 8 kernel)

- Arm được chọn ở Phase 1 × seed **7, 21**. pred.bin seed 7 lấy từ `~/claude_master/1004/gabl/ds_SEED7/pred.bin` (dataset `gate-abl-*`), seed 21 từ `~/claude_master/1004/gsb/pred_S21/pred.bin` (dataset `gate-sb-s21`), theo cách `gate_seedband_driver.py` / khối `pred_ds`.
- Nền K24 ON seed 7/21 đã có (`gqsf-*`), cost 0.
- So **ghép cặp theo seed**: arm(seed s) vs nền K24 ON(seed s), s ∈ {42, 7, 21}.

### Phase 3 — H2: tách K_entry khỏi K_buffer (cần Java; chỉ khi luật P0.b cho phép)

- Key mới `GATE_BUFFER_TOPK` (mặc định −1 = bằng `SELECTOR_RANK_TOPK` ⇒ byte-identical).
- Khi đặt `GATE_BUFFER_TOPK = 24` và `SELECTOR_RANK_TOPK = K_entry > 24`:
  - **chỉ r của hạng 1–24** được nạp vào buffer (q_t giữ đúng như nền);
  - hạng 25..K_entry vẫn được **kiểm** `r ≥ q_t` và vào lệnh nếu qua;
  - không nạp vào buffer.
- Hiệu ứng: phút mạnh mới cho hạng sâu vào (vì dyn(sp) lớn đòi p15 rất cao). Quota/q_t **không đổi**, nên tách được tác dụng (i) khỏi (ii) ở §1. **Không có ngưỡng mới nào để tune.**
- Áp cả sim lẫn live (cùng `EntryGate`/`GateRatioBuffer`).
- Quy ước code: JUnit ON/OFF, Cfg gateway (`tools/check_cfg_gateway.sh`), SLF4J, branch riêng, P0 B0@K16 md5 **ff3ce513** khi OFF.
- Arm: K_entry ∈ {32, 48} (theo luật P0.b) × seed {42, 7, 21}, vs nền K24 ON cùng seed. Tối đa 6 kernel + 1 P0.

## 4. Thước và luật (cố định trước)

- **Thước chính:** MTM ngày ghép cặp block-10d, NREP 2000, seed bootstrap 20260905, arm vs nền **cùng seed gate**. Báo CAGR22, ΔPnL, maxDD MTM phút, Calmar22, UW22, n/năm, phút vào/năm (đặc biệt 2022), skipFull count, U trung bình và p95.
  - Theo năm 2022–2025, theo quý, **bản bỏ 2022 (ex-2022)**, % ΣPnL từ top-10 ngày, % ΣPnL từ lệnh 0h (định nghĩa N700).
- **Stress cost bắt buộc:** chấm lại mỗi arm với phạt +1,675%/chân cho mọi chân vào trong nến 1m ≤ −1% (COST_TRUTH). Báo cả base và stress. GO phải đạt **cả hai**.
- **Inflate:** half-width × √(2 ln k), với k = tổng số arm đã nhìn trong vòng: Phase 1 = 8, cộng Phase 3 nếu chạy.
- **Đa seed:** báo mean ± sd qua 3 seed, CI paired t (df 2, ghi rõ là yếu), và số seed có Δ > 0.
- **Luật GO (§9 A.4/A.5):**
  - **Arm iso-740** (cùng n): GO nếu Calmar22 tăng ở **3/3 seed** VÀ mean ΔCAGR22 ≥ 0 VÀ maxDD ≤ 40% mọi seed VÀ ex-2022 không xấu đi (mean ΔCAGR23 ≥ −1,0pp) VÀ đạt cả base lẫn stress.
  - **Arm iso-1000** (lever n): GO nếu mean ΔPnL > 0 với CI MTM inflate (gộp 3 seed) loại 0 VÀ maxDD ≤ 40% mọi seed VÀ Calmar22 ≥ 0,90 × nền mỗi seed VÀ ≥ 3/4 năm ΔROI ≥ 0 VÀ đạt cả base lẫn stress.
  - **Phase 3:** cùng luật iso-1000 (vì tăng n).
  - **Không arm nào GO ⇒ giữ K24 pct base** (đang lên shadow #2). Không chọn "điểm ước lượng tốt nhất" khi nằm trong nhiễu.
- Win%/SL% chỉ báo cáo.

## 5. Ràng buộc thực thi (bắt buộc)

- **Pre-reg** commit + push TRƯỚC khi sim. Gồm câu hỏi, arm, pct cuối cùng (sau P0.a), luật Phase 3, thước, luật GO, kỳ vọng khai trước (điểm ước lượng ΔCAGR22 và Calmar từng đường), số kernel. Ghi hash. Mọi thứ ngoài pre-reg chỉ là "báo cáo".
- **Kernel** = `tools/kaggle_sim.py` HEAD (guard NOWRITE242) + khối `pred_ds` như các vòng gate. Tối đa 2 kernel song song.
- **Parity mỗi run:** jar sha, log override (`SELECTOR_RANK_TOPK`, `SIM_GATE_ROLLING_PCT`, `GATE_QUOTA_SKIP_WHEN_FULL=true`, `GATE_BUFFER_TOPK` nếu có), md5 pred.bin "md5 verified", n, eq, md5 printDone. Chạy lại nền K24 ON seed 42 qua đường mới (nếu đổi driver) phải trùng md5 `gqsf` seed 42.
- **KHÔNG** chạm 242 hay shadow. **KHÔNG** Java sim trên Oracle. **KHÔNG** sửa Java ngoài Phase 3 (branch riêng). DEV ≤ 2025-12-31, holdout 2026 niêm phong. Python logging, Java SLF4J.
- RAM ≤ 8G, lock `~/claude_master/1002/oracle_heavy.lock`. Kiểm `df` trước mỗi bước ghi; < 500 MB thì dừng.
- **Git:** fetch + kiểm fast-forward trước push. **Không** `pull --rebase` khi có merge commit. Chỉ add file của mình. Trailer commit theo quy định session.

## 6. Sản phẩm

- `docs/prereg/PREREG_GATE_K_FRONTIER.md`
- `research/analysis/gate_k_frontier_driver.py` + bản mở rộng `gate_offline.py` (`--topk --pct`)
- `docs/audit/GATE_OFFLINE_ISON_CALIB.md` (P0.a, kèm validate)
- `docs/audit/RANKBAND_K48.md` (P0.b)
- `docs/result/RESULT_GATE_K_FRONTIER.md` + `gate_k_frontier.json`
- Phase 3: branch `feat/gate-buffer-topk` + doc audit

**Bảng bắt buộc trong RESULT:**
1. Frontier mỗi đường: K, pct, n/năm, phút mở/năm, CAGR22, Calmar22, maxDD, UW, ex-2022 — mỗi ô mean ± sd qua seed.
2. Δ vs nền, CI raw và inflate, base và stress.
3. Theo năm/quý.
4. RANKBAND sâu.
5. Kết luận theo luật, từng arm.

## 7. Điều gì sẽ bác giả thuyết

- **H1(a) chết** nếu mọi arm iso-740 có K < 24 có Calmar22 ≤ nền: xét ở seed 42 với arm chỉ chạy Phase 1, và ở ≥ 2/3 seed với arm đã sang Phase 2.
- **H1(b) chết** nếu RANKBAND sâu cho ROI dải 25–32 < 0,8 × dải 1–24, HOẶC arm K32/K40 iso-740 có Calmar22 ≤ nền (cùng cách xét seed như H1(a)).
- **H2 chết** nếu Phase 3 không GO, hoặc không được chạy theo luật P0.b.
- **Cả ba chết** ⇒ ghi kết luận "trục K × gate trên DEV đóng". Hướng tăng n còn lại khi đó: chỉ forward/shadow, hoặc selector mới (S1_V2).

## 8. Chi phí ước tính

| Hạng mục | Chi phí |
|---|---|
| P0.a | ~1–2h Oracle |
| P0.b | 1 kernel |
| Phase 1 | 8 kernel |
| Phase 2 | ≤ 8 kernel |
| Phase 3 | ~½ ngày Java + ≤ 7 kernel |

Tổng ≤ 24 kernel, khoảng 10–14h wall (2 kernel song song). Đĩa ≤ 1 GB.
