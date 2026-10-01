# RESULT_SHORT_V4 — SHORT: CHỌN COIN **MẤT THANH KHOẢN** ⇒ GIẢM ĐỀU ⇒ GIỮ ĐỦ LÂU

Prereg: `docs/prereg/PREREG_SHORT_V4.md` (`d32ff529`, commit TRƯỚC đo).
Chấm: **0-sim, KHÔNG train lại** (bins SHORT Kaggle `sm-train-gpu`), DEV ≤ 2025-12-31, không chạm 2026.
Script: `research/analysis/short_v4_score.py` (`de6315e9`, `c10eef85`).
Dữ liệu: bins `SHORT{42,7,13}` (nhãn `ndown 1,5 %`) · nhãn `.pb` (4/12/24/72h) · funding **exact từng
lệnh** `/tmp/fund_cache.npz` · **OI per-coin** `oi_percoin_full.bin` (khớp **91,4 %**).
OOS: 16 fold, **35.450.551 dòng/arm**, panel nhãn **39.266.404**. CI block-72h, NREP=2000, SEED=20260905, ×1,21.

## 0. VERDICT: **NO-GO/NULL** (theo luật §7 khoá)

Không cấu hình **tradeable** nào đạt A (net>0 ngoài CI raw ×1,21) **và** B (≥3/4 năm) **và** C
(winrate ≥ 55 % **và** ≥ baseline +5 pp). Baseline winrate = **0,5581** (ngưỡng C = **0,6081**);
winrate tradeable cao nhất = **0,582** ⇒ **C FAIL ở mọi cấu hình**.

---

## 1. (Q1) Feature **"MẤT THANH KHOẢN"** (LIQ từ OI) có giúp chọn coin không? ⇒ **KHÔNG**

`LIQ = 0,5·z_CS(−oi_delta24h) + 0,5·z_CS(−oi_z)` (cao = OI co & cạn = "đang mất thanh khoản").

| chỉ số | giá trị |
|---|---|
| **IC(LIQ, −retEnd_72h)** panel | **−0,0254** (mỗi arm: −0,0252 → nhất quán) |
| IC(score, −retEnd_72h) | +0,058…+0,061 |
| **X1_liq100** (gate z≥1,0) net_post | **+0,00170**, win 0,563, **giữ 1,1 %** đơn, CI **chứa 0** (raw [−0,013; +0,018]) |
| X1_liq050 (gate z≥0,5) net_post | −0,00071 (kém baseline) |
| X2 ranker (rank score+LIQ) k3/k1 | −0,00141 / −0,00073 ⇒ **kém hơn** baseline |

**Decile net theo LIQ (K8/T72, mean-seed)** — **KHÔNG đơn điệu**:
`d0(−6,4)→−0,0006 · d3(−1,1)→+0,0063 · d6(−0,2)→+0,0086 · d9(+0,7)→+0,0004`.
⇒ Đuôi "mất thanh khoản mạnh" (d9) ≈ 0; **không có edge chọn-coin**.

**Phát hiện NGƯỢC luận điểm owner:** IC **ÂM & lớn hơn** IC của chính model ⇒ coin **OI ĐANG CO**
(`LIQ` cao) có xu hướng **giảm ÍT hơn / tăng** — tức "đang mất thanh khoản" **KHÔNG** báo trước
nhịp giảm; nếu có thì là dấu **ngược lại** (OI đang TĂNG thì coin giảm nhiều hơn). Bác bỏ giả thuyết
"chọn coin đã vào chu kì mất thanh khoản ⇒ nó giảm đều" **qua proxy OI**.

## 2. (Q2) **GIỮ ĐỦ LÂU** (T=72h) vs **GIỮ NGẮN** (4/12/24h) — báo CẢ HAI

| T | net_pre | net_post (funding exact) | winrate |
|---|---|---|---|
| 4h | −0,00052 | **−0,00111** | 0,505 |
| 12h | +0,00033 | −0,00123 | 0,533 |
| 24h | +0,00115 | −0,00162 | 0,546 |
| **72h** | **+0,00409** | **−0,00171** | **0,558** |

- **Giữ đủ lâu (72h) THẮNG về GROSS (+0,409 %/lệnh) và WINRATE (0,558)** — đúng phần "alpha giảm"
  tích luỹ theo horizon.
- **NHƯNG giữ đủ lâu THUA về NET sau funding (−0,171 %)** — funding trả theo thời gian (≈ −0,585 %/72h)
  ăn hết alpha; giữ ngắn giảm được funding drag (−0,111 % ở 4h) nhưng mất alpha nhiều hơn.
- **Kết luận trung thực:** "giữ đủ lâu" **đúng về cơ chế alpha** nhưng **một mình không tạo net>0**;
  và **rút ngắn để nề funding cũng không cứu được** (khớp V3 N2a). ⇒ Nghẽn là **FUNDING**, không phải
  độ dài giữ.

## 3. (Q3) Coin **"giảm ĐỀU"** vs **"giảm GIẬT"** (Q3a ex-post + Q3b causal)

**Q3a (mô tả, dùng path TƯƠNG LAI — KHÔNG tradeable):** chia lệnh K8/T72 theo `bounce = maxFav_72h`
≤ median tick (= đều) vs phần còn lại (= giật):

| nhóm | n | net_post | winrate | bounce_mean |
|---|---|---|---|---|
| **đều** (ít nhúng lên) | 557.067 | **+0,05791** | **0,733** | 0,049 |
| **giật** | 556.949 | **−0,06182** | 0,381 | 0,229 |

⇒ Khoảng cách **CỰC LỚN (~12 pp/lệnh), ngoài CI cả hai phía**. "Giảm đều" đúng là điều kiện của
net tốt — **giả thuyết owner ĐÚNG ở mức mô tả**.

**Q3b (CAUSAL — dùng path QUÁ KHỨ `Shist` = z_CS(−bounce tại t−72h)):** gate "đều quá khứ":
net_post **+0,00195**, win 0,540, yrs+ 2, CI **chứa 0** (raw [−0,0044; +0,0074]).
IC(Shist, −retEnd_72h) = **−0,0330** (âm).

⇒ **ĐỘ ĐỀU tương lai KHÔNG dự báo được từ độ đều quá khứ** (thậm chí ngược dấu). Đây là **còn thiếu
CỤ THỂ #1**: cần một **predictor của path tương lai** (không phải path quá khứ).

## 4. (Q4) **Dự báo FUNDING CẢ CỬA SỔ** (F1) tại `t`

`F̂_72h = 9 × mean(rate của 8 settle gần nhất TRƯỚC t)` (causal, không lookahead).

| | mean-seed net_post | winrate | yrs+ | out CI (raw ×1,21) |
|---|---|---|---|---|
| **F1** gate `F̂_72h ≥ 0` (giữ 62 %) | **+0,00312** | 0,566 | **2/4** | **KHÔNG** (raw ∋ 0) |
| **N1b** (dấu 1 settle — như V3) | +0,00374 | 0,569 | 2/4 | KHÔNG |
| **N1a** (`f_72h≥0` LOOKAHEAD — cận trên) | +0,00725 | 0,559 | **4/4** | **CÓ (raw & ×1,21)** |
| F1 + k3 (chọn tinh) | +0,00625 | 0,574 | 2/4 | KHÔNG (1/3 seed ra ngoài raw) |
| F1 + X1_liq100 (giữ 0,6 %) | +0,01202 | **0,582** | **3/4** | KHÔNG |

- **Dự báo cả cửa sổ TỐT:** `IC(F̂_72h, f_72h) = **0,678**` ⇒ lấp được "thiếu sót (a) của V3".
- **NHƯNG net vẫn KHÔNG ra ngoài CI** và **chỉ 2/4 năm** ⇒ **A & B vẫn FAIL**. Dự báo funding đúng
  ≠ lọc funding có lãi: lọc vẫn **cắt mất alpha** tương đương phần tiết kiệm (F1 ≈ N1b).
- Chỉ **lookahead N1a** (không tradeable) mới ra ngoài CI & 4/4 năm ⇒ xác nhận lại V3: *chi phí
  funding đủ lớn nhưng KHÔNG dự báo được ở mức cần*.

## 5. (Q5) KẾT LUẬN DỨT KHOÁT

**NO-GO** cho đường SELL theo luận điểm owner. **A/B/C đều FAIL** ở mọi cấu hình tradeable
(chi tiết per-seed trong `RESULT_SHORT_V4.json`).

**CÒN THIẾU gì CỤ THỂ (theo thứ tự ưu tiên):**
1. **Predictor của PATH tương lai** (độ đều nhịp giảm). Q3a cho thấy payoff khổng lồ (+5,79 % vs
   −6,18 %/lệnh) nhưng **mọi thước đo quá khứ (OI, đường giá quá khứ) đều KHÔNG dự báo được**.
   Đây là hướng đáng đầu tư nhất — cần **feature path/microstructure mới** (orderbook, CVD, tốc độ
   cạn depth), train lại trên Kaggle.
2. **Alpha short TRỰC GIAO funding**: chọn tinh làm gross tăng nhưng net giảm (V3); V4 xác nhận
   `IC(LIQ)` **âm** ⇒ các tín hiệu "giảm" hiện có đều trùng với coin phải trả funding.
3. **Bins PATH-AWARE per-lệnh**: nhãn `pa/pw/pn` có prereg+code nhưng **bins bị kernel Kaggle xoá**
   ⇒ cần 1 vòng Kaggle train lại (~4 h GPU) để ghép path + nề funding per-lệnh.

---

## 6. Deviations & giới hạn (khai báo)

1. **IC tính Spearman TOÀN CỤC** (không phải per-tick rồi mean như §6.1) ⇒ số IC hơi khác V3
   (V3 rank-IC per-tick = +0,0519; V4 global = +0,058…+0,061). CI/net/cut/winrate vẫn đúng khoá.
2. **LIQ = proxy OI** (không có volume THÔ); `oi_delta24h/oi_z` khớp nhãn **91,4 %** (8,6 % NaN/thiếu).
3. **"Giữ đủ lâu" chỉ tới 72h** — `.pb` không có horizon > 72h (§3 prereg).
4. **Q3a là EX-POST** (dùng path tương lai) ⇒ **cận trên**, KHÔNG dùng để tuyên bố GO.
5. `RESULT_SHORT_LABEL2.md` **KHÔNG tồn tại** trong repo (đã `find`; chỉ có prereg `8edf7c7b` + code)
   ⇒ không dùng làm nền; nhãn path-aware per-lệnh **không đo được**.
6. Không mô hình liquidation/borrow (PERP, borrow = 0); chi phí base 0,112 %/vòng.

## 7. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_V4.md` | prereg (`d32ff529`, TRƯỚC đo) |
| `research/analysis/short_v4_score.py` | chấm 0-sim 17 cấu hình × 3 seed |
| `docs/result/RESULT_SHORT_V4.md` (+`.json`) | kết quả + trả lời 5 câu |
