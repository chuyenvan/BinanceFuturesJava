# PREREG_KDOSE — liều–đáp ứng: nến phút lúc quyết định sai thì backtest↔live lệch bao nhiêu (agent KDOSE, 2026-10-10)

Câu hỏi owner: nếu live không lấy đúng nến phút hiện tại ở ≥ 99% ô thì lệch ra sao. Commit này TRƯỚC khi đo D2 (D1 được phép
chạy trước/sau, không ảnh hưởng lưới/thước). Không đổi lưới, thước, ngưỡng sau khi thấy số; lệch khỏi pre-reg ⇒ khai trong RESULT.
Ràng buộc: 0 chạm 242/shadow, 0 sửa .java, 0 build, 0 Java sim, 0 Kaggle, 0 Binance REST (chỉ data.binance.vision công khai),
Python logging, RAM ≤ 8G (lock `oracle_heavy.lock` khi > 4G), cache tự tạo ≤ 500 MB, xoá sau dùng.
Nền: `docs/audit/KLINE_242_DIVERGENCE.md` (bb43ce5b, KDIV), `KLINE_FIX_242_EVIDENCE.md` (origin/fix/live-ticker-reread).

## 1. Dữ liệu, cửa sổ
- **Nguồn "242" (sai)** = ticker HO26 `~/kaggle_data_hpo/ticker_2026MMDD.bin.gz` (≡ Aerospike 242 99,9996%, HO3 K1), ngày UTC
  2026-04-22 → 06-30. **Dữ liệu đúng T** = cùng universe (symbol, phút) HO26, giá trị O/H/L/C/Q thay bằng Binance Vision monthly
  (`futures/um/monthly/klines/<S>/1m`, 2026-04/05/06, tải trong RAM theo lô nhỏ); ô không có Vision giữ giá trị HO26 (như VisStore KDIV).
- **Cửa sổ chính W** = 2026-04-25 09:31 → 2026-06-30 23:59 +07 (sau điểm gãy KDIV). Lỗi chỉ được bơm trong W.
- **Cửa sổ chấm gate/kinh tế W_g** = 2026-05-01 00:00 → 2026-07-01 00:00 +07 (= cửa sổ KDIV D4a). Lịch sử r trước điểm gãy
  (01-31 → 04-25 09:30) lấy p15 từ CSV feature KDIV (`~/claude_master/1003/kdiv/kdiv_gate_{242,vis}_*.csv.gz`: 242 trước 04-01,
  vis từ 04-01) — trước gãy hai nhánh trùng (KDIV validate 99,84%).

## 2. D1 — kho lỗi thật
- Ô lỗi = ô (symbol, phút) ∈ W có cả HO26 và Vision mà ≥ 1 trong 5 trường O/H/L/C/Q khác nhau (feq KDIV: float32,
  |a − b| ≤ 1e-8·|b|). Lưu: symbol, phút, 5 giá trị 242, 5 giá trị Vision (npz cache, ≤ 500 MB).
- Phân phối theo biên độ phút Vision (H−L)/O, 7 bin KDIV: < 0,1 / 0,1–0,2 / 0,2–0,5 / 0,5–1 / 1–2 / 2–5 / > 5 %.
  Báo: tỉ lệ ô lỗi toàn W (ký hiệu ē), theo tháng, theo bin; trường lệch (close/H/L/O/Q); độ lớn close |Δ| p50/p99 (bps).
- **Kiểm khớp audit:** tỉ lệ ô lỗi T5–T6 trên universe HO26 so KDIV 21,05% — |Δ| ≤ 1,0 pp ⇒ PASS; ngoài ⇒ giải thích trước D2.
  Xu hướng theo bin phải tăng đơn điệu như KDIV (10,6% → 45,7% toàn kỳ).

## 3. Mô hình lỗi, lưới (D2)
- Lưới **e ∈ {0; 0,5; 1; 2; 5; 15}%** ô (symbol, phút) trong W bị sai, cộng điểm kiểm **ē** (toàn bộ kho = dữ liệu 242 thật, 1 lần,
  tất định). Nếu ē < 15% thì e = 15% thay bằng ē (khai).
- Lấy mẫu có điều kiện biên độ: trong mỗi bin b, chọn n_b = round(e/ē · |E_b|) ô **không lặp, đều** từ kho lỗi bin b; ô được chọn mang
  **đúng giá trị 242 của chính ô đó** (5 trường). ⇒ tỉ lệ toàn cục = e, phân phối theo biên độ = phân phối kho thật.
- 20 lần lặp mỗi e > 0, seed = 20261010 + 1000·i_e + rep (i_e = chỉ số trong lưới). Cùng tập ô cho R1 và R2 (ghép cặp).
- **R1 — chỉ nến quyết định sai** (trạng thái sau fix có đọc lại 3′): tại tick t, nến phút t của các ô lỗi ở phút t mang giá trị sai;
  mọi phút < t đúng. Thực thi: Engine (ring) và md_inline nạp nến sai ở t, tính feature/p15, rồi ghi đè ô đó bằng nến đúng.
  Xếp hạng rổ (CoinRankManager, mỗi 60′) tính tại tick dùng nến t như nó có lúc đó.
- **R2 — nến sai bám lịch sử** (bug cũ: cache giữ nến sai): dữ liệu = T với các ô lỗi thay bằng giá trị 242, dùng cho mọi tick sau.

## 4. Thước
**(a) Gate** — pipeline = KDIV D4a: 33 feature port `devexport_202609` (md INLINE, `DIED_SYMBOLS` từ `config.properties` repo), funding
từ bản sao Oracle-local (ns `test`, KHÔNG đọc 242; bản sao còn cập nhật tới 07-07 > W), p15 = ONNX `fold_20/Model_Regressor_Return15M`,
ứng viên = bins S1 HO26 `bins2026Ax` (sp = 1 − p0, ffill ≤ 15′), r = p15/(max(DYN_MIN, sp/0,15·1,2876)·1,55), q_h = phân vị
0,999950829 nearest-rank của r trong [h − 90 ngày, h), warm-up 7 ngày ⇒ 0,008; PASS ⇔ !(p15 < q·fac·1,55) (float32, như `gate_offline`).
Feature tính từ dữ liệu trong RAM (thay Aerospike). Ba cấu hình:
- **G0** = K24, không khoá, không skipFull (đúng KDIV; dùng cho D3).
- **G1** = K24 + khoá coin đang giữ + skipFull (printDone + `logs/sim.out` của `ho26-k24-s-s42`; `gate_offline.lock_mask`,
  `gate_skipfull_offline.full_mask`).
- **G2** = K16 + khoá (`ho26-b0-s-s42`), không skipFull (cấu hình live hiện tại K16).
Chỉ số trên W_g so với e = 0 cùng cấu hình: **flipPASS% = #cặp (phút, ứng viên) đổi PASS/REJECT / |PASS_0 ∪ PASS_e| × 100** (thước KDIV
~13%); flip/cặp hợp lệ; % phút có ≥ 1 đổi; |Δp15|/p15_0 p50/p99 trên phút M* (≈ % đổi r vì fac cố định); |Δq|/q p50/p99 theo giờ.
Tối ưu tính (chốt trước, có kiểm): feature chỉ tính tại **M\*** = {t ∈ W : max_k r_0(t,k) ≥ 0,5 · min_cfg q_0(h)} (r_0, q_0 từ chạy
e = 0 đầy đủ mọi phút, ứng viên không khoá); ngoài M* giữ p15_0. q tính bằng cây top-J chỉ trên r ≥ 0,25 · min q_0 với đếm m đầy đủ.
**Kiểm bắt buộc:** (i) chạy ē-R2 đầy đủ mọi phút ⇒ tập PASS của G0/G1/G2 trùng tuyệt đối bản M*; (ii) q bản sàn == q bản đầy đủ
(e = 0 và ē-R2). Hỏng ⇒ hạ 0,5 → 0,25 (và sàn 0,25 → 0,1), chạy lại TOÀN BỘ.

**(b) top-K S1** — đọc code `S1RankerLive` (origin/fix/live-ticker-reread): S1 CHỈ dùng chuỗi close 1h (close giờ t = close nến 1m
open t − 1′) + OI ⇒ thước = proxy close giờ (không chạy model S1, khai): mỗi mốc giờ t ∈ W_g, xếp hạng return 1h = close(t)/close(t−1h) − 1
trên universe có đủ 2 close (bỏ stable); top-K và đáy-K, K ∈ {16, 24}; chỉ số = % mốc giờ tập khác ≥ 1 symbol so e = 0, Jaccard TB.
R1: chỉ close(t) sai (close(t−1h) đúng — S1 đọc lại ≥ 2′ sau mốc); R2: cả hai có thể sai.

**(c) Giá vào** — chân leg0 `PREDICT_SYMBOL_TRADE` của 8 run `ho26-k24-s-s{42,7,13,21,99,123,777,2024}` có start ∈ W_g; nến quyết định =
phút start. Δ = (close_sai − close_đúng)/close_đúng (bps, có dấu). Báo TB trên mọi chân (0 nếu ô không lỗi) và trên chân dính lỗi,
CI95 qua 20 lặp (R1 ≡ R2 cho thước này). Kèm: với dữ liệu 242 thật (ē) — tỉ lệ chân dính lỗi và Δ TB (đo chọn lọc kiểu winner's curse,
so tỉ lệ nền ē).

**(d) Kinh tế proxy** — mỗi seed k24: gate G1 với khoá + full của CHÍNH seed đó. Mỗi cặp đổi trong W_g so e = 0:
PASS_0 → REJECT_e = bỏ lệnh (− notional × ret); REJECT_0 → PASS_e = thêm lệnh (+ notional × ret), một coin chỉ được thêm lại khi lệnh
proxy trước của nó đã thoát. ret = proxy thoát `qsleeve_q0` (như `ho26_luck_audit.proxy`: vào close ĐÚNG phút quyết định, đường giá ĐÚNG,
COST 0,000982 + 2·0,000067, phạt crash 0,01675 nếu nến vào ≤ −1%); dữ liệu kết thúc 06-30 ⇒ "mark". notional = margin chân thật nếu
(sym, phút) trùng chân PREDICT trong printDone, ngược lại median margin PREDICT của seed. **ΔΣPnL% = Σ_seed ΣΔ / |D| × 100**, D = Σ_seed
Σ notional × ret_proxy của mọi chân leg0 (mọi level) start ∈ W_g. Nếu |D| < 0,2 · Σ|notional × ret| ⇒ mẫu số dùng Σ|·| và cờ.
CI95 = phân vị 2,5/97,5 qua 20 lặp. KHÔNG mô phỏng: DCA, tương tác sổ lệnh (slot/margin/full thay đổi do lệnh thêm/bớt, coin được mở lại
sau khi bỏ lệnh), lệnh BIG_DOWN (md cũng phụ thuộc nến 1′ — không đo), phí funding.

## 5. D3 — kiểm chéo một điểm
ē-R2 (dữ liệu 242 thật bám lịch sử), G0: flipPASS% phải tái hiện KDIV 12,9% (97/752). |Δ| > 2 pp ⇒ giải thích trước khi báo.
Kiểm pipeline: p15 e = 0 vs CSV KDIV vis, ē-R2 vs CSV KDIV 242 trên W_g: % phút p15 trùng tuyệt đối báo kèm (kỳ vọng ≥ 95%;
thấp hơn ⇒ tìm nguyên nhân, ví dụ nguồn funding).

## 6. D4 — kết luận
- Đường cong e → (flipPASS% G0/G1/G2, flip top-K, Δgiá vào bps, ΔΣPnL% [CI]) cho R1 và R2.
- **e\*** (riêng R1, R2) = e lớn nhất trong lưới sao cho với MỌI e' ≤ e: |TB ΔΣPnL%| ≤ 3% VÀ TB flipPASS% ≤ 2% ở cả G1 và G2.
  Bản bảo thủ e\*_CI: dùng max(|CI lo|, |CI hi|) ≤ 3% và CI hi flipPASS ≤ 2%.
- Ngưỡng cảnh báo đề xuất: counter `[LIVE-KLINE]` (% nến lúc quyết định = final; chế độ sau fix ≈ R1): CẢNH BÁO khi 100 − %đúng > e\*_R1/2,
  NGHIÊM TRỌNG khi > e\*_R1; healthcheck REST/đối soát Vision (lỗi đã ghi vào store ≈ R2): cảnh báo khi % ô lệch > e\*_R2/2, nghiêm trọng > e\*_R2.
  Nếu e\* = 0 (0,5% đã vượt) ⇒ báo ngưỡng theo nội suy tuyến tính trong [0; 0,5]% và nói rõ là nội suy.
- Giá trị của "đọc lại 3′" = chênh R2 − R1 ở từng e (flip, ΔΣPnL%).

## 7. Phụ — lát DEV 2025 (thứ yếu; chạy nếu còn thời gian trong phiên, không chạy ⇒ khai KHÔNG CHẠY)
DEV 2025-06-01 → 06-30 (`ticker_2025*.bin.gz` ≡ Vision 100%), lịch sử q từ 2025-03-01 (sạch). Lỗi bơm: ô chọn có điều kiện bin biên độ
theo tỉ lệ bin của kho; giá trị sai = giá trị DEV × tỉ số (242/Vision) 5 trường của một ô kho cùng bin rút ngẫu nhiên. e ∈ {1; 5; 15}% ×
5 lặp, R1/R2, chỉ G0 (bins `predwf_map_s1a2_x1_2021`, p15 = ONNX fold_20 trên feature port — chỉ đo độ nhạy, không đo hiệu suất) và (c).

## 8. Giới hạn đã biết (khai trước)
- Cơ chế lỗi thứ hai của live (F1b: 12,5% phút trading đọc bản "nặn" TRƯỚC khi ingest chốt — lỗi cả phút, mọi symbol) KHÔNG có trong kho
  242 và không nằm trong mô hình i.i.d. theo ô; kết quả là cận dưới cho kiểu lỗi tương quan theo phút.
- Gate offline là xấp xỉ sim (khoá/full lấy từ sổ của chính run 242; `isTickerAvailable` không tái lập); S1 = proxy.

## 9. Sản phẩm
`research/analysis/kdose_*.py` (stage d1 | base | d2 | report), `docs/result/KDOSE_RESULT.md` + `KDOSE_RESULT.json`.
Thư mục Oracle tạm `~/claude_master/1010/kdose/` (tiền tố `kdose_`), xoá cache lớn sau khi xong.
