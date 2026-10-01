# RESULT_SHORT_V3B / V3C — STEER OWNER: CHỌN COIN "MẤT THANH KHOẢN" + GIỮ ĐỦ LÂU

> **NGUỒN:** STEER của **OWNER lúc 2026-10-01 06:32** (không phải thiết kế tự chọn):
> *"Chú ý cái rút ngắn giữ lệnh vì lý thuyết là chọn coin đã vào chu kì mất thanh khoản nó sẽ giảm đều"*.
Prereg: `PREREG_SHORT_V3B.md` (`bc531673`) · `PREREG_SHORT_V3C.md` (`5062f5bf`) — đều commit **TRƯỚC đo**.
Chấm 0-sim, **không train lại**, DEV ≤ 2025-12-31. 3 seed {42,7,13}, K=8, cắt +30 %, CI block-72h ×1,21.

## 0. VERDICT: **NO-GO/NULL** (luật V3 §6: A ∧ B ∧ C đều phải đạt)

## 1. (a) Lọc "MẤT THANH KHOẢN" vào bước CHỌN COIN (causal)

- **V3B L1a/L1b/L1c = VOID (chọn 0 dòng)** — ngưỡng sai dấu: `volumeTrend = avgVol5/avgVol60` là **TỈ SỐ ~1**
  (không phải dấu), `atrSqueeze = atr5/atr60` cũng vậy (`FundingDataCollectionManager.java:433,458`).
  ⇒ **V3C** sửa ngưỡng theo **định nghĩa** (không sửa theo kết quả).

| cấu hình (T=72h, cắt +30 %) | n lệnh | net TRƯỚC funding | net SAU funding | fund mean | winrate | năm dương |
|---|---|---|---|---|---|---|
| baseline (không lọc) | 1.114.016 | +0,409 | **−0,171** | −0,580 % | 0,558 | 1/4 |
| L1b′ `vtrend<1` | 380.700 | +0,500 | −0,111 | −0,619 % | 0,560 | 1/4 |
| **L1b′ + N1b** (teo + dấu funding) | 251.713 | +0,532 | **+0,547** | +0,004 % | 0,570 | 2,7/4 |
| **L1b′ + N1b + K3** (chọn tinh) | 87.951 | +0,768 | **+0,754** | +0,001 % | 0,578 | 3,7/4 |
| L1a′+N1b · L1c′+N1b | ~489 k | +0,414 / +0,423 | +0,424 / +0,437 | ~0 | 0,569 | 2,7/4 |

- Lọc "mất thanh khoản" **một mình cải thiện gross** (+0,409 → +0,500) nhưng funding vẫn ăn hết.
- Ghép **dấu funding causal (N1b)** ⇒ net **−0,171 % → +0,547 %** (**+0,72 pp/lệnh**), nhưng
  **CI raw [−0,0005, +0,0115] CHỨA 0** (bản ×1,21 càng chứa 0) ⇒ **A FAIL**.
- K3 siết thêm: net +0,754 %, CI raw **[+0,0005, +0,0145] (ngoài raw)** nhưng **×1,21 chưa ngoài** ⇒ A FAIL.

## 2. (b) ĐỘ ĐỀU CỦA NHỊP GIẢM (đường đi) — **XÁC NHẬN luận điểm owner** (nhưng là LOOKAHEAD)

Đo trên `.pb` (`ratio = retEnd_72h / maxAdv_72h` ∈ [0,1]; `hoi = maxFav_72h`):

| nhóm | ratio (median) | hồi (median) | net SAU funding | winrate | năm dương |
|---|---|---|---|---|---|
| chọn baseline | 0,269 | 0,070 | −0,171 % | 0,558 | 1/4 |
| chọn + L1b′+N1b | 0,260 | 0,067 | +0,547 % | 0,570 | 2,7/4 |
| **`ratio ≥ 0,5`** (giảm đều) | 0,772 | 0,034 | **+10,58 %** | **0,974** | **4/4** |
| **`ratio ≥ 0,5` & hồi ≤ 3 %** | 0,767 | 0,013 | **+12,38 %** | **0,9995** | **4/4** |

⇒ Luận điểm owner **ĐÚNG về cơ chế**: gần như **toàn bộ lãi** nằm ở các lệnh **giảm ĐỀU** (ít hồi).
⇒ NHƯNG `maxAdv/maxFav` là **thông tin TƯƠNG LAI** ⇒ đây là **chẩn đoán**, **KHÔNG tradeable**, **không tính GO**.

## 3. (c) GIỮ NGẮN vs GIỮ ĐỦ — rút ngắn **PHÁ EDGE** (đúng steer owner)

| T (giữ) | baseline net_post | L1b′+N1b net_post | winrate |
|---|---|---|---|
| 4h | −0,111 % | **+0,010 %** | 0,506 |
| 12h | −0,123 % | — | 0,533 |
| 24h | −0,162 % | +0,178 % | 0,552 |
| **72h (giữ đủ)** | −0,171 % | **+0,547 %** | **0,570** |

⇒ Càng giữ lâu càng lãi (đúng "giảm đều" cần thời gian); **rút ngắn để né funding là SAI** ⇒ bỏ khỏi
vai trò biện pháp chính (đúng yêu cầu steer).

## 4. Trả lời 4 câu

1. **Nề funding giúp bao nhiêu?** Causal tối đa: **−0,171 % → +0,547 %** (+0,72 pp/lệnh) khi ghép
   *dấu funding kỳ settle kế tiếp* + *lọc thanh khoản teo*; K3 → +0,754 %. Nhưng **CI chưa ra ngoài 0**.
2. **Winrate tăng bao nhiêu / bằng cách nào?** 0,558 → **0,570** (L1b′+N1b) → **0,578** (K3) = **+1,2..+2,0 pp**.
   Cách hiệu quả nhất = **lọc thanh khoản teo + dấu funding + chọn tinh**. Vẫn **< +5 pp** ⇒ **C FAIL**.
3. **2023/2024 hết âm?** L1b′+N1b: 2023 −0,23 %, 2024 **+0,07 %**; K3: 2023 **+0,03 %**, 2024 **+0,26 %**
   ⇒ **2024 hết âm, 2023 gần hết** (K3 hết).
4. **Kết luận: NO-GO.** Còn thiếu **CỤ THỂ**: **một model DỰ BÁO được "giảm đều"/"mất thanh khoản"**
   (nhãn phụ `ratio`/hồi + feature thanh khoản tại `t`) — mới biến được +10,6 % (lookahead) thành
   tradeable. Đây là việc **train lại trên Kaggle** ⇒ vòng sau.

## 5. Deviations & BLOCKED (khai báo)

1. **V3B L1 = VOID** do sai dấu ngưỡng; sửa ở **V3C** theo định nghĩa Java (không theo kết quả).
2. **(c) path-aware label + "mất thanh khoản" (train lại) = BLOCKED** — bins `pa` đã bị kernel
   `sm-label2` xoá; cần GPU Kaggle ⇒ vòng sau.
3. Bỏ **feature OI** (`oi_delta24h`) khỏi lọc (ghép `merge_asof` local nặng).
4. `kept_frac` trong JSON tính trên **tập top-8/tick** (không phải toàn universe).
5. Chân BTC của gate regime vẫn không đo được (universe nhãn không chứa BTCUSDT) — như V3.

## 6. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_V3B.md` · `PREREG_SHORT_V3C.md` | 2 prereg (steer + sửa ngưỡng) |
| `research/analysis/short_v3b_score.py` | chấm 0-sim (ghép nhãn/feature/funding chỉ cho dòng chọn) |
| `research/analysis/short_v3bc_analyze.py` | gộp 3 seed + luật GO |
| `docs/result/RESULT_SHORT_V3B.json` | số đầy đủ 21 cấu hình |
