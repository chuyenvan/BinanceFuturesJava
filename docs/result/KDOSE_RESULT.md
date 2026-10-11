# KDOSE_RESULT — nến phút lúc quyết định sai thì backtest↔live lệch bao nhiêu (agent KDOSE, 2026-10-10)

Pre-reg `docs/prereg/PREREG_KDOSE.md` (**403f3302**, commit TRƯỚC D2). Script `research/analysis/kdose_data.py` (D1, funding),
`kdose_run.py` (base | d2 | post), `kdose_chk170.py` (kiểm D1 trên mẫu KDIV), `kdose_report.py` (e*, bảng). JSON `docs/result/KDOSE_RESULT.json`.
0 chạm 242/shadow (funding + symbol_mapper đọc Aerospike Oracle-LOCAL ns `test`), 0 Binance REST (Vision công khai, trong RAM),
0 Java/sim/Kaggle, 0 sửa `.java`. Thư mục tạm Oracle `~/claude_master/1010/kdose/` (cache ≤ 200 MB, xoá sau khi xong).

## KẾT LUẬN (rủi ro trước)

1. **"≥ 99% nến đúng" là CHƯA đủ theo ngưỡng chốt trước.** Ở e = 1% ô sai, gate đổi **2,6–2,8%** quyết định PASS (G1 K24 / G2 K16 trung
   bình 20 lặp; CI95 tới ~9,7%) ⇒ vượt ngưỡng 2%. ΔΣPnL proxy +1,1…+1,5% (CI −9,0…+6,5%), Δgiá vào TB +0,18 bps/chân.
   **e\* = 0,5% cho cả R1 lẫn R2** (TB: flip G1 1,5–1,6%, G2 1,5–1,6%, ΔΣPnL +1,1…+1,3%). Bản bảo thủ theo CI: **e\*_CI = 0** — ngay ở 0,5%
   có lần lặp đổi ~9% PASS (CI hi 8,3–9,6%) ⇒ dưới 0,5% chưa đo, không khẳng định an toàn.
2. **Flip gate có đuôi nặng, không tuyến tính:** phần lớn lần lặp ở e nhỏ đổi 0 PASS, vài lần đổi 8–10%. Cơ chế: q_h là phân vị cực trị
   (top ~150 giá trị r / 90 ngày); một phút nhiễu lọt vào top dịch q (|Δq| p99 0,8% → 3,3% khi e 0,5% → 5%) ⇒ cả loạt cặp sát ngưỡng đổi.
   PASS hiếm (0,03% cặp) nên % trên toàn cặp chỉ 0,0003–0,005%.
3. **R1 ≈ R2 ở tầng gate** (R2 cao hơn 0,1–1,0 pp): gate nhạy chủ yếu với **nến quyết định** (momentum1M/md, breadth của nến hiện tại,
   nến BTC), ít với lịch sử ⇒ fix "đọc lại 3′" **không** làm gate an toàn hơn; chỉ có nến đúng ngay lúc quyết định mới giúp (WS x=true).
   R1 vs R2 khác rõ ở **S1 (close giờ)**: top-24 đổi 6% vs 11% (e 5%), 16% vs 26% (ē) ⇒ giá trị của đọc lại nằm ở S1/lịch sử.
4. **Giá vào:** dữ liệu 242 thật làm **35,5%** chân PREDICT dính nến lỗi (gấp 2,5 lần ē = 14,3%: lệnh được chọn đúng ở phút biến động/ô lệch
   — chọn lọc), Δ TB **+1,9 bps/chân**, +5,4 bps trên chân dính (|Δ| 12,8 bps). Trên kho toàn bộ Δ có dấu ≈ 0 ⇒ thiên lệch dương là do chọn lọc.
5. **Kinh tế proxy** không có hướng rõ ở e ≤ 2% (TB +0,3…+1,5%, CI rộng ±5–12%); e = 5%: −7,6% (R1) / −4,3% (R2), CI vẫn chứa 0;
   ē: −13,0% (R1) / −3,8% (R2) (1 lần, tất định). Mẫu số D = +29 685 USD (8 seed, chân leg0 05-01→06-30).
6. **D3 PASS:** ē-R2 (242 thật bám lịch sử), G0: flipPASS **12,71%** (97/763; thêm 64 / bỏ 33) vs KDIV 12,9% (97/752).

## D1 — kho lỗi thật (HO26 = 242 vs Binance Vision, W = 2026-04-25 09:31 → 06-30 +07)

Universe = 717 symbol HO26 (1 symbol không có Vision: BDXNUSDT; ô HO26 không có Vision trong W: 1). 57 169 632 ô trong W,
**8 173 353 ô lỗi ⇒ ē = 14,30%** (≥ 1 trong O/H/L/C/Q khác, float32). Trường: Q 14,30%, C 9,44%, H 1,23%, L 1,21%, O 0,053%.
Tháng: T4 (từ 25/4 09:31) 12,16% · T5 15,72% · T6 13,29%. 4 ngày trước gãy: 1 142/2 694 865 = 0,042%.
Độ lớn close trên ô lệch close: |Δ| p50 3,5 bps · p90 10,6 · p99 25,6; **Δ có dấu TB +0,006 bps** (đối xứng, không thiên lệch).

| Biên độ phút Vision (H−L)/O | < 0,1% | 0,1–0,2 | 0,2–0,5 | 0,5–1 | 1–2 | 2–5 | > 5% |
|---|---|---|---|---|---|---|---|
| ô trong W | 25 276 404 | 16 340 585 | 12 376 595 | 2 432 743 | 595 928 | 135 075 | 12 302 |
| % ô lỗi | 8,3 | 14,8 | 20,8 | 31,6 | 40,8 | 46,5 | 50,9 |
| tỉ trọng trong kho | 25,7 | 29,5 | 31,5 | 9,4 | 3,0 | 0,8 | 0,08 |

**Kiểm khớp audit:** pre-reg so tỉ lệ T5–T6 *toàn universe* (14,48%) với KDIV 21,05% ⇒ theo chữ là FAIL (|Δ| 6,6 pp). Nguyên nhân: số
21,05% của KDIV đo trên **mẫu 170 symbol** (top-50 volume ∪ symbol có lệnh HO26), không phải toàn universe; symbol ít giao dịch ít lỗi
(ít trade giây cuối). Đo lại trên đúng mẫu đó (`kdose_chk170.py`): **21,05%** (KDIV 21,05%), close 14,78% (KDIV 14,78%), tập HO26
18,68% (18,65%), top-50 27,77% (27,71%) ⇒ kho lỗi khớp audit; ē toàn universe = 14,30% là thước đúng cho lưới (sai sót viết pre-reg,
không đổi lưới/thước). Xu hướng theo biên độ tăng đơn điệu như KDIV.

## Kiểm pipeline (trước khi đọc số D2)

- **md INLINE vector hoá** (`VecMD`) so `md_inline.InlineMD`: 3 500 + 3 000 phút, lệch **0** (bit-exact).
- **p15 so CSV KDIV trên W_g (87 802 phút):** e = 0 vs KDIV vis: trùng tuyệt đối **97,37%**, |Δ| p99 0,005 pp, max 0,39 pp; ē-R2 vs
  KDIV 242: 97,31%, cùng p99/max (khác biệt trạng thái Engine lúc khởi động chunk + nguồn funding Oracle-local thay vì 242; không ảnh hưởng
  so sánh trong-thí-nghiệm vì mọi nhánh dùng chung).
- **Sàn cây q** (r ≥ 0,25·min q₀ = 0,001378): q và PASS trùng tuyệt đối bản đầy đủ ở e = 0 và ē-R2, cả 10 cấu hình ⇒ PASS.
- **M\*** (max_k r₀ ≥ 0,5·min q₀): 6 534 phút = 6,8% cửa sổ. ē-R2 chỉ thay p15 tại M* ⇒ PASS/q trùng tuyệt đối bản đầy đủ, 10/10 ⇒ PASS.
- **Lỗi phát hiện và sửa trong lúc chạy (khai thật):** lượt D2 đầu (4 task, bỏ: `kdose_d2_raw_bug1.jsonl`) cho ē-R2 G0 14,29% ≠ 12,71%
  của bản đầy đủ ⇒ p15 phụ thuộc tập phút xuất: `Engine.fund_feats` cache funding theo (symbol, giờ) tại lần gọi ĐẦU trong giờ; bản đầy đủ
  gọi ở phút đầu giờ, bản M* gọi ở phút M* đầu tiên ⇒ funding khác. Sửa: gọi `fund_feats` ở phút có dữ liệu đầu tiên của mỗi giờ (như bản
  đầy đủ). Kiểm thêm trong D2: e = 0 và ē-R2 chạy kiểu M* trùng p15 bản đầy đủ **100,000%**, e = 0 cho 0 cặp đổi. Kiểm (i) của pre-reg chỉ
  thay giá trị p15 nên không bắt được lỗi này — đã bổ sung kiểm path-independence.
- skipFull: `full_mask` (sim.out 1 825 snapshot) cho **0 phút full** trong cửa sổ ở cả 8 seed ⇒ G1 trong W_g ≡ K24 + khoá.

## D2 — liều–đáp ứng (20 lặp mỗi e, seed 20261010+1000*i_e+rep)

### R1
| e | flipPASS G0 | G1 (K24+SF s42) | G2 (K16) | phút có đổi G1 | Δp15 p50/p99 | Δq p99 G1 | S1 top24/đáy24 đổi | Δgiá vào bps (mọi chân / chân lỗi) | ΔΣPnL% [CI] |
|---|---|---|---|---|---|---|---|---|---|
| 0.5% | 1.7 [0.0; 9.1] | 1.5 [0.0; 8.9] | 1.5 [0.0; 7.7] | 0.002 [0.000; 0.007] | 0.00% / 1.0% | 0.83% | 1% / 1% | +0.02 / +1.95 | 1.12 [-5.15; 4.63] |
| 1.0% | 2.8 [0.2; 9.7] | 2.6 [0.1; 9.2] | 2.3 [0.0; 7.9] | 0.003 [0.001; 0.008] | 0.00% / 1.4% | 1.38% | 1% / 1% | +0.18 / +7.56 | 1.46 [-6.59; 6.54] |
| 2.0% | 3.2 [0.1; 9.2] | 3.1 [0.1; 9.6] | 2.7 [0.0; 8.0] | 0.004 [0.001; 0.010] | 0.00% / 1.7% | 1.53% | 3% / 2% | +0.26 / +5.52 | 0.29 [-12.26; 6.68] |
| 5.0% | 8.0 [0.6; 10.4] | 7.7 [0.7; 9.7] | 6.6 [0.8; 8.6] | 0.008 [0.003; 0.010] | 0.00% / 2.4% | 3.21% | 6% / 6% | +0.72 / +5.63 | -7.59 [-16.87; 5.20] |
| ē=14.3% | 13.4 | 9.8 | 7.7 | 0.010 | 0.13% / 4.0% | 3.97% | 16% / 15% | +1.90 / +5.35 | -13.03 |

### R2
| e | flipPASS G0 | G1 (K24+SF s42) | G2 (K16) | phút có đổi G1 | Δp15 p50/p99 | Δq p99 G1 | S1 top24/đáy24 đổi | Δgiá vào bps (mọi chân / chân lỗi) | ΔΣPnL% [CI] |
|---|---|---|---|---|---|---|---|---|---|
| 0.5% | 2.3 [0.0; 9.6] | 1.6 [0.0; 9.3] | 1.6 [0.0; 8.3] | 0.002 [0.000; 0.008] | 0.00% / 1.3% | 0.86% | 1% / 1% | +0.02 / +1.95 | 1.25 [-5.57; 4.73] |
| 1.0% | 3.5 [0.4; 9.9] | 2.8 [0.1; 9.7] | 2.5 [0.0; 7.9] | 0.004 [0.001; 0.010] | 0.00% / 1.6% | 1.39% | 2% / 3% | +0.18 / +7.56 | 1.13 [-8.98; 6.54] |
| 2.0% | 4.2 [1.1; 9.7] | 3.2 [0.3; 9.4] | 2.9 [0.2; 8.0] | 0.004 [0.001; 0.009] | 0.00% / 2.0% | 1.52% | 5% / 5% | +0.26 / +5.52 | -0.07 [-11.78; 6.75] |
| 5.0% | 8.6 [1.6; 11.2] | 7.9 [0.8; 10.3] | 7.4 [1.4; 9.7] | 0.009 [0.003; 0.011] | 0.00% / 2.9% | 3.27% | 11% / 13% | +0.72 / +5.63 | -4.32 [-18.60; 6.11] |
| ē=14.3% | 12.7 | 10.1 | 8.8 | 0.010 | 0.25% / 4.5% | 3.74% | 26% / 29% | +1.90 / +5.35 | -3.83 |

Đọc bảng: flipPASS = #cặp (phút, ứng viên) đổi / |PASS₀ ∪ PASS_e| trên 05-01→06-30, TB [CI95 qua 20 lặp]; ē = 1 lần tất định
(e = 15% > ē ⇒ thay bằng ē theo pre-reg §3). G1 = K24 + khoá (+ skipFull, 0 phút full) seed 42; trung bình 8 seed G1 thấp hơn
(e 1%: 1,8% R1 / 2,0% R2). S1 = proxy return 1h, % mốc giờ tập top-24/đáy-24 khác (K16 thấp hơn ~30%). Δgiá vào = chân leg0 PREDICT
k24 8 seed (951 chân), (close sai − đúng)/đúng. ΔΣPnL% = Σ 8 seed ΔPnL proxy / D.

## D4 — e\* và ngưỡng cảnh báo (pre-reg §6, không đổi)

| | e\* (TB) | e\*_CI | ràng buộc gãy ở e kế tiếp (1%) |
|---|---|---|---|
| R1 (sau fix, đọc lại) | **0,5%** | 0 | flip G1 2,64% > 2% (G2 2,34%) |
| R2 (bug cũ, bám lịch sử) | **0,5%** | 0 | flip G1 2,81% > 2% (G2 2,52%) |

ΔΣPnL% không phải ràng buộc gãy (|TB| ≤ 1,5% tới e = 2%); gate là ràng buộc gãy.

**Ngưỡng đề xuất** (theo §6: cảnh báo = e\*/2, nghiêm trọng = e\*; e = % ô (symbol, phút) nến lúc quyết định ≠ final):
- `[LIVE-KLINE]` (đo đúng chế độ R1): **CẢNH BÁO khi %đúng < 99,75%**, **NGHIÊM TRỌNG khi < 99,5%**, cửa sổ ≥ 1 ngày (ở 0,25% cần
  ~3 600 ô/ngày mới phân biệt — đủ với ~700 symbol × 1 440 phút).
- **Tách nhóm (đề xuất bảo thủ, KHÔNG đo trực tiếp):** e\* đo trên ô universe với phân phối biên độ của kho thật; nhưng feature gate
  dồn vào **BTC** (momentum 5M–24H, volatility, RSI, MA20, volumeSpike — 1 symbol) và **rổ top-50% volume** (breadth, basket*), nơi tỉ lệ
  lỗi thật gấp ~2 lần universe (top-50: 27,8% vs 14,5%). ⇒ áp CÙNG ngưỡng 99,75/99,5% **riêng cho từng nhóm**: (a) BTC (tính theo tick:
  ≥ 4/1 440 tick/ngày nến BTC chưa final ⇒ cảnh báo, ≥ 8 ⇒ nghiêm trọng), (b) rổ volume cao, (c) toàn universe; báo động khi nhóm nào vượt.
  Với nhóm BTC đây là suy rộng (lỗi tập trung 1 symbol có thể nặng hơn i.i.d.), cần kiểm riêng nếu muốn nới.
- Healthcheck REST / đối soát Vision (lỗi đã ghi vào store ≈ R2): cảnh báo khi % ô lệch > 0,25%, nghiêm trọng > 0,5%
  (REST check 100 ô ⇒ 1 ô lệch đã > 0,5%: dùng cộng dồn ≥ 2 000 ô trước khi kết luận).
- Dưới 0,5% chưa đo (e\*_CI = 0): mục tiêu vận hành nên là **0 ô lệch** (WS x=true cho phép), không coi 0,25–0,5% là "an toàn đã chứng minh".

## Áp dụng (bối cảnh 2026-10-11, không đổi thước)
- 10-11 08:53: ingest 242 chạy ws_settle; REST check 0/100 lệch. 09:01–09:05: trading live + 2 shadow chạy jar có `[LIVE-KLINE]`.
  ⇒ đọc counter theo ngưỡng trên sau ≥ 24 h, tách BTC / rổ volume cao / universe.
- **Backfill lịch sử CHƯA chạy** ⇒ store 242 04-25→10-10 vẫn mang ~12–16% ô lỗi (universe T4–T6 đo ở đây; mẫu KDIV T7–T10 11–13%) — ≫ 0,5%: buffer r 90 ngày của gate (q) và lịch sử S1
  đang đúng chế độ R2 ở mức ē ⇒ theo bảng, so với dữ liệu chuẩn ~10% (G1) / ~9% (K16) quyết định PASS khác và S1 top-24 đổi ~26% mốc giờ,
  cho tới khi backfill + khởi tạo lại buffer (theo runbook KLINE_FIX_242). Fix live chỉ đưa nến MỚI về R1 ≈ 0.

## Giới hạn / lệch pre-reg (khai thật)
- Kiểm D1 ghi sai thước so sánh trong pre-reg (21,05% là mẫu 170 symbol) — đã đối chiếu đúng mẫu: khớp. Không đổi lưới/thước.
- Lỗi cache funding (path-dependence) tìm thấy khi chạy D2, sửa, chạy lại toàn bộ D2; bổ sung kiểm M\* độc lập tập phút (100%).
- e = 15% > ē ⇒ thay bằng ē (đúng §3); lưới thực tế 0,5/1/2/5% × 20 lặp + ē.
- Lát DEV 2025 (§7, phụ): **KHÔNG CHẠY** (hết thời gian phiên).
- Mô hình lỗi i.i.d. theo ô có điều kiện biên độ; **không** gồm lỗi live đọc bản "nặn" (F1b, 12,5% phút, cả phút, mọi symbol) — kiểu
  tương quan theo phút, có thể nặng hơn với gate (BTC + breadth cùng sai). Kết quả là cận dưới cho kiểu lỗi đó.
- Gate offline: khoá/full lấy từ sổ run 242; S1 = proxy close giờ (không chạy model); kinh tế bỏ qua DCA, BIG_DOWN (md cũng phụ thuộc
  nến 1′), slot/margin, mở lại coin sau khi bỏ lệnh, funding. p15 = ONNX fold_20 (= live). G1 skipFull không kích hoạt trong cửa sổ.
- ΔΣPnL ở ē là 1 lần tất định; chênh R1 (−13,0%) vs R2 (−3,8%) nằm trong độ rộng CI quan sát ở e = 5% ⇒ không diễn giải R1 xấu hơn R2.

Cache tu tao da xoa sau khi xong (207 MB), md5 truoc khi xoa:
```
59402b5d614bc5f11b9829f88a65638c  kdose_err.npz
6b12cd4457342af7967fb8d66089e2b4  kdose_fund.pkl
d10dfbc2e424c91afd8b028e94d10745  kdose_rel_close.npy
e0b9207e1da8bde3dbeeda5ac26e3b44  kdose_base.npz
```
