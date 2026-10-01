# RESULT_SHORT_LABEL2 — SHORT với NHÃN PATH-AWARE: có tránh được coin "pump rồi dump"?

Ngày: **2026-10-01**. Pre-reg: `docs/prereg/PREREG_SHORT_LABEL2.md` (**`8edf7c7b`**, amend **`ad2ee6b3`**, commit TRƯỚC đo).
Code: trainer **`a0438b84`** (`--label-mode pa/pw/pn`, `--label-e`, `sample_weight`) · kernel maker **`b8403282`** ·
analyzer **`d988aa2d`**. Số: `docs/result/RESULT_SHORT_LABEL2.json`. Nền: `RESULT_SHORT_MODEL`(`a3b59757`) / `RESULT_SHORT_DEEP`(`90c9480e`).

**Tuân thủ:** 0-sim · KHÔNG Java/sim trên Oracle · không sửa `.java` · không chạm production/242/ONNX/LIVE ·
không push dữ liệu · DEV ≤ 2025-12-31 · train CHỈ trên Kaggle (`sm-label2`, `sm-label2b`, `sm-label2c`).

---

## 0. KẾT LUẬN NGẮN

**`NO-GO/NULL`** theo luật §7 (commit TRƯỚC). **A PASS** (rank-IC tăng: `+0,0519 → +0,0778…+0,0824`, ngoài CI).
**B FAIL** ở MỌI cấu hình. Và **quan trọng hơn**: nhãn path-aware **KHÔNG tránh được coin pump-rồi-dump — nó làm
TỆ HƠN**: **cut-rate TĂNG**, **net GIẢM ~50 %**, **2023/2024 vẫn âm và âm hơn**.

> Cơ chế: mask `maxFav_72h > E` **xoá khỏi tập train chính các "âm bản" coin đã pump** ⇒ model **không còn
> mẫu để học né** đuôi pump ⇒ pick top-K lại càng dính coin tăng mạnh. IC tăng (xếp hạng `−retEnd` toàn cục
> đẹp hơn) nhưng **IC ≠ net**: tập top-8 đuôi trái xấu hơn.

---

## 1. ĐỊNH NGHĨA NHÃN (đã khóa) + DỮ LIỆU

```
MAE_nguoc_72h ≡ maxFav_72h = max( high/close(t) − 1 )  trên MỌI nến 15m trong (t, t+72h]
(tính bằng đường giá: ExportFundingLabel.updateAnchor, favR = hi/closeT − 1)
nhãn P-hard:  y = 1  ⇔  (retEnd_72h ≤ −thr)  VÀ  (maxFav_72h ≤ +E)
đối chứng:    E = +∞ ⇒ nhãn CŨ `ndown` y = 1[retEnd_72h ≤ −thr]
P-soft(pw):   y = 1[retEnd ≤ −thr], w = 1 nếu maxFav ≤ E, nếu không w = max(0, 1−(maxFav−E)/E)
P-noise(pn):  CÙNG mask như pa, y = Bernoulli(tỉ lệ gốc), seed 20260924
```
Nguồn: `funding_label_*.pb` — cột `retEnd_72h`, `maxFav_72h`, `nBars_72h ≥ 288`. (Không có chuỗi nến đầy đủ ⇒
chỉ dùng được cực trị đường đi; `tHitFav` không dùng.)

---

## 2. BẢNG KẾT QUẢ — `(thr,E) × seed`: IC · net · cut-rate · 2023/2024 (mean 3 seed, K=8/tick)

| cấu hình | rank-IC | cut% @+20 | cut% @+30 | net% @+20 | net% @+30 | net @+30 **sau funding** | 2023 @+30 | 2024 @+30 |
|---|---|---|---|---|---|---|---|---|
| **E=∞ (nhãn cũ)** | +0,0519 | 17,72 | 9,95 | **+0,420** | **+0,409** | −0,171 | −0,59 | −0,11 |
| PA thr1,5 % E=+3 % | +0,0824 | 24,94 | 14,78 | +0,183 | +0,151 | **−0,434** | −0,81 | −0,42 |
| PA thr1,5 % E=+10 % | +0,0778 | 24,90 | 14,87 | +0,213 | +0,173 | **−0,412** | −0,89 | −0,32 |
| PA thr7 % E=+3 % | +0,0811 | 24,99 | 14,85 | +0,176 | +0,138 | **−0,447** | −0,74 | −0,31 |
| PA thr7 % E=+10 % | +0,0824 | 25,19 | 15,06 | +0,195 | +0,159 | **−0,426** | −0,78 | −0,24 |
| *(control)* PW soft E=+10 (s42) | +0,0744 | 24,06 | 14,31 | +0,307 | +0,282 | −0,303 | −0,75 | −0,20 |
| *(control)* PN noise E=+10 (s42) | +0,0144 | 9,65 | 4,27 | +0,205 | +0,212 | −0,373 | −0,40 | −0,18 |

- **A PASS**: mọi cấu hình PA có rank-IC > 0 **ngoài CI** (raw & ×1,21), 3/3 seed (vd t15E10: 0,07741/0,07862/0,07738).
- **B FAIL**: không cấu hình nào net **ngoài CI** ở bất kỳ mức cắt nào (CI raw luôn chứa 0, vd +30 %: [−0,0045 ; +0,0076]);
  **sau funding** net **ÂM** toàn bộ; **≤2/4 năm dương** (2023+2024 âm mọi cấu hình).
- Thời lượng thật: **~14–29 phút/arm** (E=3 % nhanh hơn vì mask cắt nhiều dòng: pos 0,89 / 0,57; E=10 %: 0,67 / 0,38).

---

## 3. SO TRỰC TIẾP VỚI NHÃN CŨ (`E=∞`)

| so sánh | kết quả |
|---|---|
| **rank-IC** | 0,0519 → **0,0778…0,0824** (tăng ~50–59 %, ngoài CI) — *tốt lên* |
| **cut-rate** | +20 %: 0,177 → **0,249…0,252** (**TĂNG ~41 %**); +30 %: 0,0995 → **0,148…0,151** (**TĂNG ~49 %**) — *XẤU đi* |
| **net @+20/+30** | +0,42/+0,41 % → **+0,18…+0,21 / +0,14…+0,17 %** (**GIẢM ~50–66 %**) — *XẤU đi* |
| **2023** | −0,59 % → **−0,68…−0,89 %** — *âm HƠN* |
| **2024** | −0,11 % → **−0,24…−0,42 %** — *âm HƠN* |
| **3/4 năm dương** | nhãn cũ 2/4 → path-aware **1–2/4** — *không cải thiện* |

⇒ Nhãn path-aware **không** biến "CI chứa 0 → ngoài CI", **không** làm 2023/2024 hết âm — **ngược lại**.

---

## 4. FUNDING ẢNH HƯỞNG

Theo `RESULT_SHORT_DEEP`: short **TRẢ** funding, mean **−0,585 %/72h** (raw) / −0,452 % (clip) ⇒ trừ phẳng.
Sau funding **mọi** cấu hình path-aware thành **ÂM** (−0,39…−0,45 % @+20 %; −0,41…−0,45 % @+30 %), **âm sâu hơn**
nhãn cũ (−0,16/−0,17 %). Kết luận **không đổi dấu**: funding là CHI PHÍ cấu trúc của short-theo-đà.

---

## 5. TRẢ LỜI 4 CÂU

1. **Nhãn path-aware có tránh được coin pump-rồi-dump không (cut-rate giảm bao nhiêu %)?**
   **KHÔNG — cut-rate TĂNG**, không giảm: @+20 % `17,72 % → 24,90–25,19 %` (**+41 %**), @+30 %
   `9,95 % → 14,78–15,06 %` (**+49 %**). Đối chiếu **noise** (`pn`) có cut@+20 % chỉ **9,65 %** ⇒ tín hiệu
   path-aware **còn chọn coin dễ pump hơn cả chọn ngẫu nhiên**.
2. **Net sau cắt cứng + funding có ngoài CI & ≥3/4 năm dương không?** **KHÔNG.** (i) net chưa funding **dương**
   (+0,14…+0,21 %) nhưng **CI chứa 0**; (ii) **sau funding ÂM** toàn bộ; (iii) **≤2/4 năm dương** (2023, 2024 âm).
3. **2023/2024 hết âm chưa? Vì gì?** **CHƯA — còn âm và âm hơn nhãn cũ.** Vì cùng **regime** (Q1 âm, thị trường
   tăng thì short thua − theo `RESULT_SHORT_DEEP §2`) **cộng** đuôi `maxFav≥10 %` — và mask path-aware **không sửa**
   được regime, chỉ **dịch** lựa chọn sang nhóm coin biến động mạnh hơn.
4. **Kết luận dứt khoát:** **`NO-GO/NULL`.** Không có cấu hình SHORT nào (thr, E) trong lưới đạt net > 0 ngoài CI
   & ≥3/4 năm dương sau funding ⇒ **KHÔNG dựng đường SELL**. **Còn thiếu gì cụ thể:** để short có cửa cần (a) **thoát
   theo ĐƯỜNG GIÁ** (trailing/time-stop thật — cần sim Java, `.pb` aggregate không đủ), hoặc (b) **bộ feature/tín hiệu
   regime** (chặn vào lệnh khi regime up) — vòng này đã chứng minh **đổi NHÃN một mình là vô ích, thậm chí hại**.

---

## 6. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | `E ∈ {+5 %, +20 %}` | ⛔ BỎ (vòng này) | ngân sách (~14–29 ph/arm; xem pre-reg amend `ad2ee6b3`) |
| 2 | Gate-33 / S1-9 | ⛔ BỎ | dataset không có sẵn trên Kaggle |
| 3 | Time-stop/trailing đường giá/liquidation | ⛔ BỎ | `.pb` aggregate chỉ có cực trị đường đi |
| 4 | Dựng đường SELL / production | ⛔ BỎ | theo luật §7: verdict NO-GO |
| 5 | `sm-thr-sweep` (9 arm quét ngưỡng cũ) | ✅ đã xong (ngoài phạm vi vòng này) | thuộc `RESULT_SHORT_DEEP §5/§7`; JSON sẵn trên Kaggle, không tải trong vòng này |
