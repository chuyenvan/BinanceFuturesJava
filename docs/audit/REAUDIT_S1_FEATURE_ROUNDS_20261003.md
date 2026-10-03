# REAUDIT_S1_FEATURE_ROUNDS — chấm lại mọi vòng feature/label trên S1 bằng thước §9 A-20261003

- **Ngày:** 2026-10-03 · **Loại:** audit đối kháng + chấm lại từ artifact CÓ SẴN (**0 train · 0 sim · 0 Kaggle · 0 Java · 0 chạm 242/shadow**), DEV ≤ 2025.
- **Câu hỏi owner:** "selector đã thử cắt/thêm feature nhưng claw làm không ổn — review kỹ rồi tìm hướng làm S1 tốt hơn, theo bản S1 KEEP9 tốt nhất hiện tại".
- **Luật dùng để chấm lại:** `docs/runbooks/RISK_APPETITE.md` §9-AMENDMENT A-20261003 (PnL ròng là mục tiêu chính; T3 win%/TSloss% chỉ thông tin; maxDD MTM ≤ 40 %; Calmar_MTM ≥ 0,90× nền (mặc định tới khi owner chốt X); ≥ 3/4 năm không âm hơn nền; thước = MTM ngày ghép cặp block-10d, inflate √(2 ln k)). Amendment ghi "không hồi tố" ⇒ mọi verdict MỚI dưới đây là **đánh giá thông tin**, không tự đảo verdict đã chốt.
- **Script:** `research/analysis/reaudit_s1_feat_rounds.py` (`oi12` · `geom` · `offline` · `devpair`). **JSON:** `docs/audit/reaudit_s1_feat_rounds.json`. Bootstrap MTM: `SAD.daily_boot` (block 10 ngày, NREP 2000, seed 20260905); offline: `HBF.block_ci_diff` (block 72h, NREP 2000, seed 20260919 — đúng seed vòng gốc).
- **Tác giả từng vòng** lấy từ git (`git log --follow`) + dòng Co-Authored/Session trong file. "claw" = OpenClaw (commit `oracle@local`/`openclaw@local`, đợt 09-04 → 09-29). Trong các vòng S1 feature, **chỉ FS_RESULT** mang chữ ký `oracle@local` (đợt OpenClaw); các vòng còn lại là Claude (Opus 4.8 / Sonnet 5 / Opus 5) — "claw làm không ổn" chỉ đúng nguyên văn cho FS, nhưng lỗi THƯỚC lặp lại ở hầu hết các vòng (xem §1).

## 0. KẾT LUẬN THẲNG

1. **Không có vòng nào bị "bác oan" rõ ràng** theo nghĩa: có PnL dương ngoài CI mà luật cũ bỏ đi. Thứ luật cũ làm sai là **dùng thước không đo được PnL** (rate kiểu T3, rank-IC, money-proxy không qua gate) ⇒ nhiều verdict là **CHƯA ĐỦ BẰNG CHỨNG**, không phải "đã chứng minh vô dụng".
2. **GEOM (cf5c90e4)** là trường hợp sát nhất: dưới luật mới với **k = 1** (GN là đối chứng nhiễu, không phải lever) G − CTRL ΔCAGR **+2,46 pp CI raw [+0,21; +4,69]**, Calmar +0,83 [+0,09; +1,64], 4/4 năm ⇒ *sẽ qua* điều kiện 1. **Nhưng** chấm lại đối kháng: CTRL (K42+S7) là cặp seed **xui** (CTRL − CTRL4 = −0,64 pp); 4 run có GEOM {G42,G7,GN42,GN7} vs 4 seed CTRL {K42,S7,S13,S21} ⇒ **ΔCAGR +1,82 [−0,09; +3,81]**, Calmar +0,59 [+0,07; +1,28], năm 2022 +1,8 / 2023 +0,0 / 2024 −0,2 / 2025 **+5,3** ⇒ CI chứa 0, lợi ích dồn 2025 ⇒ **CHƯA ĐỦ BẰNG CHỨNG** (không phải bác oan; dấu dương nhất quán).
3. **Ứng viên cứu #1 = G2 funding/carry** (FEATGRP, 6 cột). Vòng gốc so với baseline seed-42 đơn: +2,62 pp edge5 CONFIRM — nhưng đo lại thấy **chính 5 cột NHIỄU cũng cho +0,61 pp (sd 0,36)** ⇒ so chuẩn đúng là trừ nhiễu: **G2 − TB nhiễu = +2,01 pp [raw −0,76; +5,39]**, dương 4/5 năm (2021 +1,3 · 2022 −0,3 · 2023 +0,7 · 2024 +0,7 · 2025 +2,3). Là nhóm DUY NHẤT trong 10 ứng viên FEATGRP/HPO/BAG tách khỏi phân phối nhiễu (z ≈ 5,6 theo sd 5 cột nhiễu; z ≈ 2,9 nếu dùng sd seed GPU 0,49 × √2). Chưa từng sim.
4. **Ứng viên cứu #2 = OFI** (`ofi_1h`, `aggr_buy_ratio_1h`): offline THẮNG multi-seed (+1,76 pp, noise +0,26 ⇒ ròng ~+1,5); vòng "tiền" (OFI_MONEY/REORIENT) dùng **thước sai tầng** (top-8 mọi tick trên pool nhãn exit Python, không gate quota/sizing/MTM; bản đầu còn **lỗi dấu** chọn 8 coin tệ nhất) và **chưa từng hiệu chuẩn trên một dương tính đã biết** (GEOM) ⇒ **CHƯA ĐỦ BẰNG CHỨNG**, không phải "không ra tiền". Chi phí LIVE cao (aggTrades realtime, 47 cột ONNX).
5. **Chết hẳn (bác đúng, cả luật mới):** đổi NHÃN S1 (FIRSTHIT_RANK −15 pp; MAXFAV tiền âm), lưới 5m (MTM −12,95 pp [−24,4; −2,9]), OI12 (MTM −1,79 pp [−5,20; +1,30], năm 2025 −6,7), HPO sâu/nhiều cây (H2 max_depth 6, H4 600 cây: **hại ngoài CI** sau trừ nhiễu), BAG5, G1 rel-strength, G3 long-horizon, LS_TAKER (factor độc lập).
6. **Lỗi phương pháp xuyên suốt (để không lặp lại):** (a) so với **một** seed baseline ⇒ thiên lệch ~+0,6 pp edge5 cho mọi biến thể; (b) rank-IC toàn cục không thấy thay đổi ở ĐỈNH top-K (GEOM: ΔIC +0,0006 nhưng Δedge5 +2,3, ΔCAGR +2,5); (c) cửa sổ SELECT 2022–23 là nơi MỌI hiệu ứng ≈ 0 — GEOM, G2, OFI đều chỉ hiện ở 2024–25 ⇒ FS (chỉ có dữ liệu tới 2024-06, quyết định trên SELECT) **mù đúng chỗ có tín hiệu**; (d) money-proxy bỏ qua gate quota (chuỗi thật vào lệnh theo cụm); (e) nền T170 chi phí cũ ≠ chuỗi B0.

## 1. BẢNG VÒNG — thước cũ vs thước mới, verdict cũ/mới

Quy ước verdict mới: **BÁC ĐÚNG** (luật mới cũng NO-GO, có số) · **BÁC OAN** (luật mới GO) · **CHƯA ĐỦ** (thước cũ không đo PnL chuỗi, hoặc PnL dương nhưng CI chứa 0) · "không chấm lại được" = thiếu artifact sim.

| # | vòng (commit) | tác giả | thước/luật cũ | lỗi thước theo A.3 | chấm lại (thước đúng) | verdict cũ → mới |
|---|---|---|---|---|---|---|
| 1 | **FS_RESULT** (`c14107a2`/`3257d753`, 09-04) | `oracle@local` (đợt OpenClaw) | ΔrankIC `g1_replay` khi thêm 1 cột vào BASE7 (bỏ OI), SELECT 2022–23, ngưỡng √(2 ln 16)·sd; CONFIRM 2024H1 tự khai "không phân biệt" | rank-IC ≠ đỉnh top-K; dữ liệu chỉ tới 2024-06 ⇒ thiếu 2024H2–2025; không edge5, không sim | **không chấm lại được** (không có pred/sim theo thước mới). Điểm: `fs_wick_up_7d` +0,0043 (cao nhất, họ hình học ⊂ GEOM), `fs_dd_speed`, `fs_dvol_*` dương nhỏ; `fs_taker_buy_7d`, `fs_body_ratio_7d`, `fs_fund_persist` **âm ngoài CI** trên g1lite | 0/15 → **CHƯA ĐỦ** cho nhóm dương (thực chất hình học đã được GEOM đo lại); **BÁC ĐÚNG** cho 3 cột hại |
| 2 | **S1_OI12** (`422b23e8`, 09-13) | Claude Opus 4.8 (session 011zpg…) | ≥ 2 rate chất lượng (win%, TSloss%, meanP, mP\|SL) ngoài CI block-72h + ràng buộc cứng; nền **T170** gate cố định, chi phí cũ | luật rate = T3 (nay chỉ thông tin); 1 seed; nền ≠ B0 | MTM ngày ghép cặp (devrun `X1_GS_T170_OI12_2021` vs `X1_GS_T170_2021`): **ΔCAGR −1,79 pp [−5,20; +1,30]** (2022+: −1,71 [−5,47; +1,59]); ΔCalmar −0,10 [−1,84; +0,14]; ΔROI năm 2022 +0,1 / 2023 +0,6 / 2024 −0,9 / **2025 −6,7**; ΣPnL −6,76k (2025 −5,85k). Tầng model: Δedge5 +0,50 pp ≈ sàn seed (sd 0,32–0,49) | NULL → **BÁC ĐÚNG** (PnL âm; "0/2 rate" là T3 nhưng tiền cũng không có). Chưa đo trên chuỗi B0 — không đáng đo: không có tín hiệu model |
| 3 | **S1_HPO_BAG_FEATGRP** + NOISE_CAL (`a9f5f423`, 09-19) | Claude Sonnet 5 (session 01UoV…) | Δedge5 g1lite CONFIRM 2024–25 vs baseline seed 42 CPU, inflate(k) | baseline 1 seed ⇒ **mọi** biến thể hưởng ~+0,6 pp (5 cột nhiễu: +0,13/+0,66/+0,43/+0,76/+1,09); offline, không sim | **trừ TB 5 cột nhiễu** (bảng §2): G2 **+2,01** [raw −0,76; +5,39]; H2 −1,88 [raw −3,66; **−0,46**]; H4 −1,11 [raw −2,05; **−0,23**]; còn lại |Δ| ≤ 0,33 | NULL ×10 → G2 **CHƯA ĐỦ (cứu #1)**; H2, H4 **BÁC ĐÚNG (hại)**; H1/H3/H5/H6/BAG5/G1/G3 **BÁC ĐÚNG (≈ 0)** |
| 4 | **RESULT_LS_TAKER** (`19b4c021`, 09-24) | Claude Opus 5 | factor độc lập: decile net/lệnh, Q9−EW, CI72h ×1,21, MDE | đúng cho câu hỏi "factor độc lập long-only"; KHÔNG phải phép thử feature S1 | không cần: `ls_toptrader`/`taker_buy` đã vào S1 ở OI12 (bác đúng); `ls_global` đã trong KEEP9 | NO-GO/NULL → **BÁC ĐÚNG** (đúng câu hỏi của nó) |
| 5 | **S1_FREE_OFI** v1 (`88b7dc42`, 09-20) | Claude Opus 5 | edge5 offline, 15 symbol | subset thanh khoản | — (thay bởi V3) | HARNESS_NGHI_NGO → **thay thế** |
| 6 | **OFI_V3 UNIVERSE + MULTISEED** (`c5c9faf`, `34d50c7e`, 09-26) | Claude Opus 5 | Δedge5 CONFIRM vs `baseline_fresh` CÙNG seed, 3 seed mới, k=3, noise | đúng ở tầng model (so cùng seed, có noise) | dùng nguyên: **+1,76 pp [+0,50; +3,15]**, noise +0,26 [−0,53; +1,08] ⇒ ròng ~+1,5 | THẮNG (model) → giữ nguyên |
| 7 | **OFI_MONEY** (`96a08e57`, 09-26) → **REORIENT** (`1ec07fc2`, 09-28) | Claude Opus 5 | Δ`net_gr1dv` (net/1 đv gross) top-K=8 mọi tick trên pool nhãn luật thoát Python (P32/B2), phí 0,6 %, trần 70 % | **sai tầng**: không gate quota, không sizing/DCA, không MTM chuỗi (chuỗi thật vào lệnh theo cụm khi gate mở); bản đầu **lỗi DẤU** (`score=−pred`, chọn 8 coin tệ nhất, B1 100 % ngoài pool); chưa hiệu chuẩn trên GEOM | **không chấm lại được bằng MTM** (không có sim OFI). Điểm sau sửa dấu: Δ ≈ −1e−6 [−2,7e−5; +2,4e−5] (≈ 0 — bằng chứng YẾU chống) | NULL → **CHƯA ĐỦ (cứu #2)** |
| 8 | **OFI_GAINSHARE** (`9a89a1d6`) | Claude Opus 5 | gain share | chẩn đoán | 2 cột OFI ~9,9 % gain, không áp đảo | thông tin |
| 9 | **S1_MAXFAV** (`1d303f22`…, 09-25) | Claude Opus 5 | thước nhãn + thước tiền (`glift8`, `netm8` luật thoát), offline | offline, trainer 45 cột | không có sim; `netm8` cả 3 arm ÂM, MFC4 âm ngoài CI ở 5/5 chỉ số tiền; trục nhãn đã bị FIRSTHIT_RANK bác bằng sim | 0/3 → **BÁC ĐÚNG** |
| 10 | **5MGRID** (09-2x) | (chuyển docs `37fd5024`) | rate (`x1_rates`) trên nền X1_C3 | rate = T3 | MTM ghép cặp `X1_C3_5M` vs `X1_C3_FULL_PARITY`: **ΔCAGR −12,95 pp [−24,45; −2,89]**, ΔCalmar −1,79 [−3,34; −0,27], âm 4/4 năm | tệ hơn → **BÁC ĐÚNG** (mạnh) |
| 11 | **S1_FIRSTHIT_RANK** (`06818fa6`, 10-03) | Claude Opus 5 | MTM sim vs CTRL K42+S7, inflate 1,18 | đúng thước | ΔCAGR −15,3/−15,5 pp, CI < 0, 4/4 năm âm | NO-GO → **BÁC ĐÚNG** |
| 12 | **S1_FEAT_GEOM** (`cf5c90e4`, 10-03) | Claude Opus 5 | MTM sim; GO ⟺ ΔCAGR ≥ +3,3 pp **và** ΔCalmar CI inflate(2) > 0 … | ngưỡng tuyệt đối +3,3 pp + Calmar (A.3 bỏ Calmar làm tiêu chí chọn); k=2 tính cả đối chứng nhiễu GN | k=1: **+2,46 [+0,21; +4,69]** (qua đ.k.1); 4 vs 4 seed: **+1,82 [−0,09; +3,81]**, Calmar +0,59 [+0,07; +1,28], 3/4 năm không âm (2024 −0,18); vs B0 +1,81 [−0,58; +4,49] | NO-GO → **CHƯA ĐỦ** (biên; không bác oan) |
| 13 | **S1_RETRAIN_NOISE** (`f0b9d8e6`) | Claude Opus 5 | hiệu chuẩn | — | dùng làm sàn: CAGR sd 0,83 pp (3 seed), edge5 CONFIRM sd 0,49 pp (4 seed GPU) | hợp lệ |
| 14 | **SELECTOR_ABLATION (+R50)** (`33d8fc17`, `b7fedef4`) | Claude Opus 5 | MTM vs random | đúng thước | selector = lever (+24 pp CAGR vs random; gap R50 14,7 pp) | hợp lệ — trần dư địa xếp hạng còn lớn |

## 2. Offline FEATGRP/HPO/BAG — chấm lại có trừ nhiễu (CONFIRM fold 10–17 = 2024–25, Δedge5 pp)

Nguồn pred: `~/s1hpo/pred_*.parquet` (CPU, seed 42, 18 fold, 6 685 957 dòng, 18 283 tick; join 100 %). "vs TB nhiễu" = Δ so với trung bình edge5 của 5 cột nhiễu (noise_0..4), tức so với "một lần nhiễu loạn vô thông tin" thay vì so với đúng 1 seed baseline.

| ứng viên | k | vs baseline (vòng gốc, CI inflate) | **vs TB nhiễu** (CI inflate k) | CI raw (k=1) | theo năm vs TB nhiễu 2021/22/23/24/25 |
|---|---|---|---|---|---|
| **G2 funding** | 3 | +2,62 [−1,31; +7,16] | **+2,01 [−2,24; +6,88]** | [−0,76; +5,39] | +1,3 / −0,3 / +0,7 / +0,7 / **+2,3** |
| G1 rel-strength | 3 | +0,41 | −0,21 [−1,88; +1,47] | [−1,34; +0,93] | +1,0 / +0,2 / −0,6 / −0,5 / −0,2 |
| G3 long-horizon | 3 | +0,51 | −0,10 [−2,75; +2,67] | [−1,87; +1,79] | +2,4 / −0,5 / +1,3 / +0,6 / −0,2 |
| H1 depth 3 | 6 | +0,82 | +0,21 | [−0,92; +1,28] | ≈ 0 |
| **H2 depth 6** | 6 | −1,27 | **−1,88** [−5,09; +0,97] | **[−3,66; −0,46]** | 2025 −2,1 |
| H3 150 cây | 6 | +0,71 | +0,10 | [−1,21; +1,38] | ≈ 0 |
| **H4 600 cây** | 6 | −0,50 | **−1,11** [−2,86; +0,58] | **[−2,05; −0,23]** | 2025 −1,3 |
| H5 mcw 200 | 6 | +0,62 | +0,01 | [−0,92; +0,89] | ≈ 0 |
| H6 pairs 16 | 6 | +0,29 | −0,33 | [−1,28; +0,50] | ≈ 0 |
| BAG5 | 1 | +0,48 [−0,14; +1,06] | −0,13 [−0,79; +0,49] | = | ≈ 0 |

Sàn nhiễu: 5 cột nhiễu Δ vs baseline = +0,13/+0,66/+0,43/+0,76/+1,09 (TB **+0,61**, sd 0,36). Sàn seed GPU (K42/S7/S13/S21, 2024–25): edge5 17,13/18,09/18,18/17,58, sd **0,49**; ORIG (deploy, seed 42 CPU) thấp hơn TB 4 seed 0,16 pp ⇒ baseline seed 42 hơi "thấp" ở CONFIRM — một phần giải thích thiên lệch +0,6.
**Đọc:** (i) BAG5 +0,48 của vòng gốc chỉ là thiên lệch baseline (−0,13 sau trừ nhiễu) ⇒ bác đúng. (ii) Model phức tạp hơn (H2, H4) **hại** có ý nghĩa raw ⇒ KHÔNG đi hướng HPO. (iii) G2 là ngoại lệ duy nhất — nhưng CI rộng (G2 đổi nhiều pick), SELECT 2022–23 ≈ 0 (−0,04), và lợi ích nặng 2025 giống GEOM ⇒ rủi ro hai nhóm cùng ăn một "hiệu ứng 2025".

## 3. GEOM — chấm lại dưới A-20261003 (MTM ngày ghép cặp, 2022-01-01..2025-12-30)

| tương phản | ΔCAGR pp [CI] | ΔCalmar [CI] | ghi chú |
|---|---|---|---|
| G − CTRL, k=2 (pre-reg) | +2,46 [−0,19; +5,09] | +0,83 [−0,05; +1,78] | tái lập đúng số RESULT |
| G − CTRL, **k=1** (GN = đối chứng, không phải lever) | +2,46 **[+0,21; +4,69]** | +0,83 [+0,09; +1,64] | qua đ.k.1 luật mới |
| **GEO4 − CTRL4** (post-hoc thông tin: 4 run có GEOM vs 4 seed CTRL sẵn có S13/S21) | **+1,82 [−0,09; +3,81]** | +0,59 [+0,07; +1,28] | CI chứa 0; năm +1,8/+0,0/−0,2/+5,3 |
| CTRL(K42,S7) − CTRL4 | −0,64 [−1,38; +0,03] | −0,16 | CTRL vòng gốc là cặp seed xui |
| GEO4 − B0 / G − B0 | +1,81 [−0,58; +4,49] / +1,80 [−0,53; +4,24] | +0,11 / +0,20 | chưa vượt deploy |
| CTRL4 − B0 | −0,02 [−2,13; +2,25] | −0,48 [−0,89; +0,27] | B0 = realization bình thường về CAGR, đỉnh về Calmar |

sd CAGR theo seed: GEO4 0,62 pp, CTRL4 0,94 pp. maxDD mọi arm ≪ 40 %. **Kết luận:** GEOM dương nhất quán (mọi điểm ước lượng > 0, 6/6 tương phản), cỡ thật ~**+1,8 pp** (không phải +2,5), lợi ích tập trung 2025 ⇒ **CHƯA ĐỦ**. Không phải bác oan: chọn k=1 + CTRL 2 seed xui mới cho "GO" — đó chính là kiểu đọc lạc quan cần tránh.

## 4. Câu hỏi soi riêng

- **OI12 "0/2 rate ngoài CI":** rate = win%, TSloss%, mP|SL, meanP (≡ T3 + rate phụ). Dưới luật mới T3 chỉ thông tin, nhưng PnL cũng âm (ΔCAGR −1,79, ΣPnL −6,8k, 2025 −6,7 pp) ⇒ NO-GO cả luật mới. Không phải "chỉ fail T3".
- **FEATGRP funding +2,62 CI rộng:** đúng là rộng ([−1,31; +7,16] k=3); sau trừ thiên lệch nhiễu còn +2,01, raw [−0,76; +5,39]. Đây là bằng chứng YẾU nhưng là tín hiệu offline mạnh thứ 2 sau GEOM (+2,91 CONFIRM) ⇒ đáng 1 vòng sim end-to-end.
- **OFI offline thắng / money NULL:** money đo bằng `net_gr1dv` top-8 **mọi tick** trên pool nhãn exit Python, phí 0,6 %; **không** có gate quota (chuỗi B0 chỉ vào ~16 lệnh/ngày lúc gate mở, đóng ~56 % số tuần), không sizing, không MTM ⇒ **lỗi TẦNG** cùng họ FULLCHAIN. **Lỗi DẤU có thật** ở bản 09-26 (`ofi_money_score.py:149,165`, `ofi_money_ext.py:106` lấy `argsort(−score)` trong khi `score = −pred`) — đã sửa ở REORIENT; sau sửa Δ ≈ 0. Thước money chưa từng chạy trên GEOM (dương tính đã biết) ⇒ không biết nó có lực hay không.
- **"Quy đổi" offline → CAGR (ghi rõ là QUY ĐỔI, không phải đo):** GEOM cho ΔCAGR(sim 2022–25)/Δedge5(CONFIRM): 2,46/2,91 = **0,85** (G vs CTRL); dùng ΔCAGR 4v4 1,82 ⇒ ~**0,63**. OI12: Δedge5 +0,50 ↔ ΔCAGR −1,79 (nền T170, 1 run) — nằm trong nhiễu, không mâu thuẫn hệ số nhưng cho thấy hệ số rất bất định.

## 5. Tổng hợp — nhóm được cứu / đáng thử lại vs chết hẳn

| nhóm | trạng thái | bằng chứng tốt nhất | kỳ vọng ΔCAGR (quy đổi ×0,63–0,85) | dữ liệu / chi phí |
|---|---|---|---|---|
| **GEOM** (9 cột HIGH/LOW) | CHƯA ĐỦ — nền của S1 v2 | sim 4v4 +1,82 pp [−0,09; +3,81] | **+1,8** (đo) | store `OHLCV_1H_v2.bin` + `geom_x1.parquet` có sẵn; live đã dựng nhánh `feat/geom-live` |
| **G2 funding/carry** (6 cột) | **CỨU #1** | offline +2,01 pp sau trừ nhiễu, 4/5 năm | **+1,3 … +1,7** (cộng dồn với GEOM: không chắc, cùng nặng 2025) | builder `x1_feat_v2_build.py` có `fund_*` (dòng 93/106); gốc 40 cột đã mất ⇒ build lại TỪNG cột (bản stack-tất-cả OOM 23 GB); live: funding đã có trong đường dữ liệu, phải thêm extractor như GEOM |
| **OFI** (`ofi_1h`, `aggr_buy_ratio_1h`) | **CỨU #2** (ưu tiên sau G2) | offline multi-seed +1,76 (ròng nhiễu ~+1,5), CI ngoài 0 | **+0,9 … +1,3** | feature 630 sym đã build (Kaggle `ofi-v3-build-s0..s9`, ~25 h CPU, coverage 0,951); **LIVE đắt**: stream aggTrades realtime + ONNX đổi input |
| hình học FS (`wick_up`, `dd_speed`) | gộp vào GEOM | rank-IC dương nhỏ | ⊂ GEOM | — |
| dollar-volume FS (`dvol_7d`, `dvol_ratio`) | để sau (bằng chứng yếu) | rank-IC +0,0026, CI chứa 0; arm thanh khoản thay selector thua B0 −17,9 pp | ~0 | rẻ (kline) |
| OI mở rộng (`oi_z`, `ls_toptrader`, `taker_buy`) | **CHẾT** | MTM −1,79 pp; Δedge5 ≈ sàn seed | ≤ 0 | — |
| `taker_buy_7d`, `body_ratio_7d`, `fund_persist` | **CHẾT** (hại trên g1lite) | ΔrankIC âm ngoài CI | < 0 | — |
| G1 rel-strength, G3 long-horizon | **CHẾT** | ≈ 0 sau trừ nhiễu | 0 | — |
| HPO (depth/cây/mcw/pairs), BAG5 | **CHẾT** (H2/H4 hại) | ≈ 0 hoặc âm ngoài CI raw | ≤ 0 | — |
| đổi nhãn S1 (first-hit, maxFav) | **CHẾT** | sim −15 pp; tiền âm | ≪ 0 | — |
| lưới 5m | **CHẾT** | MTM −12,95 pp CI < 0 | ≪ 0 | — |

**Hướng làm S1 tốt hơn (đề xuất):** không mở rộng tìm kiếm feature; **xếp chồng 2 nhóm đã có bằng chứng dương** (GEOM + funding, rồi OFI) và chấm **end-to-end** với CTRL 4 seed (đã có sẵn, 0 chi phí) — pre-reg nháp `docs/prereg/PREREG_S1_V2_DRAFT.md`. Kỳ vọng trung thực: mỗi bước +1–2 pp, tổng có thể +2,5–4 pp nếu cộng dồn được; rủi ro chính là cả 3 nhóm cùng ăn "hiệu ứng 2025" ⇒ pre-reg bắt buộc điều kiện năm và báo cáo 2022–24 riêng.

## 6. Giới hạn

- Amendment A-20261003 không hồi tố ⇒ bảng §1 là verdict THÔNG TIN; không promote gì.
- GEO4 vs CTRL4 là post-hoc (gộp GN vào họ GEOM vì GN − G = +0,01 pp; thêm S13/S21 vì có sẵn) — dùng để hiệu chỉnh kỳ vọng, không phải để GO.
- "z vs nhiễu" của G2 dựa trên sd của 5 cột nhiễu (n nhỏ) ⇒ chỉ định cỡ.
- OI12/5MGRID chấm trên nền cũ (T170 / X1_C3, chi phí cũ), 1 run/arm; CI không gồm nhiễu seed.
- FS, MAXFAV, OFI không có sim ⇒ không chấm MTM được; verdict dựa trên thước offline + lập luận tầng.
- 0 train · 0 sim · 0 Kaggle · 0 .java · 0 chạm 242/shadow; RAM đỉnh 4,3 GB (offline), lock `oracle_heavy.lock` giữ trong lúc chạy.
