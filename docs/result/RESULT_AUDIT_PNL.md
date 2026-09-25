# RESULT_AUDIT_PNL — Audit độc lập **NHÃN (b)** + **MÔ HÌNH PHÍ** + **NGUỒN GIÁ TRỊ CỦA RỔ**

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_AUDIT_PNL.md` (commit `a331b80`) — chốt **TRƯỚC** khi đọc số.
**Đối tượng bị audit:** `docs/result/RESULT_PNL_RULER.md` (commit `acb88bd`) — kết luận
**"alpha xếp hạng trên 45 feature = 0 (0 chỉ số Δ ngoài CI)"** + **"mức của rổ = 1,27 %/vòng"**.
**Code:** `research/analysis/audit_pnl_lib.py` · `audit_pnl_label.py` · `audit_pnl_cost.py` · `audit_pnl_ro.py`.
**Số thô:** `/tmp/auditpnl/{label,cost,ro}.json`.
**Kỷ luật:** thuần Python offline · không `claude-run` · không train · không Java/sim hệ thống · không build lại
nhãn · **không nới ngưỡng** · không push.

---

## 0. TRẢ LỜI NGẮN

### (a) Nhãn (b) **ĐÚNG — tái lập CHÍNH XÁC 100 %**, không lệch, không hệ thống
- Tái lập **độc lập** (chạy lại `exit_engine` từ bins thô) trên **200 cặp `(t,sym)`** ngẫu nhiên (SEED `20260925`):
  `Δgross` = **0,000000** ở **mọi** phân vị (mean/med/p05/p25/p75/p95) · **100 %** khớp tuyệt đối `tp` **và**
  `exit_ts` · **100 %** khớp `status` · Spearman **1,000000** · không cặp nào lệch ≥ 1e-9
  (theo **cả 4 năm** 2022–2025 và **cả 2 loại** thoát) ⇒ **nhãn KHÔNG có sai số tái lập**.
- **6,87 % cặp bị bỏ** (chia khối 90 ngày) **không gây lệch đo được**: 200 cặp BỊ BỎ vs 200 cặp ĐƯỢC GIỮ
  → hiệu gross = **+1,20 pp**, CI khối-72h **[−1,80 pp ; +4,36 pp]** ⇒ **TRONG CI** (không hệ thống).
- `OPEN_AT_END` (113 dòng = **0,037 %**, **toàn bộ năm 2022**) được **mark-to-market tại nến CUỐI mảng**
  (KHÔNG bỏ dòng); chúng có gross **−58,9 %** (trung vị −94,8 % = coin "chết"). Ảnh hưởng lên mức của rổ:
  **0,022 pp** (1,2678 % có → 1,2898 % nếu bỏ) ⇒ **gồm vào là BẢO THỦ**, không đổi kết luận.

### (b) Phí thực **≥ 0,001/vòng (CHẮC)**, còn `0,008` là **giả định (slip chưa đo)** ⇒ **"alpha = 0" KHÔNG đổi ở BẤT KỲ mức phí nào**
- **Bất biến cấu trúc (đã kiểm bằng đo):** `Δglift8` **không đổi** theo phí — spread **0,0e+00** trên cả 6 mức
  `f ∈ {0,001 … 0,012}`; số cặp Δ **ngoài CI 1,21** = **0 ở MỌI mức phí**. `f` chỉ là **hằng số dịch** của `y`.
  ⇒ **Không có mức phí nào lật được kết luận "alpha xếp hạng = 0".** (Chấm lại từ bins: `glift8` khớp
  `RESULT_PNL_RULER` **chính xác 0,0e+00** ở cả 4 arm ⇒ harness chấm lại đúng.)
- **Phí thực (theo bằng chứng):** `fee` taker Binance USDⓈ-M VIP0 **0,05 %/chân ⇒ 0,001/vòng** (chắc chắn);
  mô hình dùng **0,002** = **2×** mức taker. `slip 0,003×2 = 0,006` là **GIẢ ĐỊNH** — **không có bằng chứng**
  (không có `commission`/`orderId`/`FILLED` ở bất kỳ log nào; proxy duy nhất là **biến động** RT trung vị
  1,91 % **không phải** slip). ⇒ chi phí thực biết chắc **0,001**, gồm phí mô hình **0,002**, còn `0,008` là mức
  **bảo thủ**.
- **Độ nhạy mức (không phải độ nhạy alpha):** `netm8(f)` — 45deploy `+1,227% / +1,127% / +0,927% / +0,727% /
  +0,527% / +0,127%` tại `f = 0,001/0,002/0,004/0,006/0,008/0,012`. **Rời 0 (chuẩn CHẶT 1,21) khi
  `f ≤ f* ≈ 0,0052–0,0064`** ⇒ ở mức phí **thật biết chắc (0,001–0,002)**, rổ **lãi NGOÀI CI** cả raw95 lẫn 1,21;
  ở `0,008` (mô hình) mean **vẫn dương** nhưng CI **chạm 0**; ở `0,012` ≈ 0. Nói cách khác: **câu "rổ có lãi" được
  CỦNG CỐ** khi sửa phí về mức thật, còn **câu "alpha = 0" thì đứng nguyên**.
- **Sửa câu chữ của tài liệu bị audit:** câu “0 chỉ số Δ nào ngoài CI” trong `RESULT_PNL_RULER` §0(1) là **SAI
  về mặt chữ** — JSON của chính nó có **38** mục Δ ngoài CI 1,21, **nhưng TẤT CẢ đều ÂM** và **KHÔNG có mục
  nào là chỉ số KINH TẾ** (chỉ `auc8/auc8c/lift8/ic/pacc` = kỹ năng hạng, ứng viên KÉM hơn). Kết luận “không có
  lift kinh tế” **giữ nguyên**; câu đúng phải là “0 chỉ số Δ **kinh tế dương** ngoài CI” (xem §3.3).

### (c) Giá trị của rổ đến từ **LUẬT THOÁT**, KHÔNG từ **S1** (chênh S1 là 0 trong CI)
Cùng luật thoát (P0: arm +7 % + ratchet + time-stop 168 h), cùng cửa sổ, **200 tick ngẫu nhiên** (SEED `20260927`):

| rổ | gross %/vòng | CI raw95 |
|---|---|---|
| **R1 = top-32 theo S1** (= pool của nhãn (b)) | **+1,814 %** | [+0,750 % ; +2,727 %] |
| **R2 = ngẫu nhiên 32 coin/tick** | **+1,742 %** | [+0,582 % ; +2,829 %] |
| **R3 = TOÀN THỊ TRƯỜNG** (282,7 coin/tick) | **+1,712 %** | [+0,539 % ; +2,789 %] |
| **R4 = bottom-32 theo S1** (đối chứng âm) | **+1,549 %** | [+0,334 % ; +2,733 %] |

- **Hiệu ghép cặp theo tick (đều TRONG CI):** `R1−R3` = **+0,102 pp** [−0,519 ; +0,683] ·
  `R1−R2` = +0,072 pp · `R1−R4` = **+0,265 pp** [−0,504 ; +1,056] · `R2−R3` = +0,030 pp (**cổng tự-kiểm ✓**).
- ⇒ **S1 không đóng góp đo được** (+0,10 pp, không kể được khỏi 0); cả **rổ ngẫu nhiên** lẫn **toàn thị trường**
  cho **cùng** mức gross ~**+1,7 %/vòng**; **bottom-32** (+1,55 %) gần bằng **top-32** ⇒ thứ hạng S1 **không có
  nội dung kinh tế**. Nguồn giá trị = **cấu trúc luật thoát** (win ~+7 % chiếm 62–78 % số lượt, thua bị chặn
  ~−8…−17 %) áp lên **cả thị trường** giai đoạn 2022–2025.
- **Cổng harness:** `R1resim − R1` (nhãn) = **0,00000 tuyệt đối** ⇒ sim độc lập của audit trùng nhãn trên đúng
  mẫu đó.

---

## 1. ĐỘC LẬP HOÁ NGUỒN DỮ LIỆU (cổng danh tính — chạy TRƯỚC mọi phép đo)

| Nguồn | Bằng chứng |
|---|---|
| bins 1m tick (local) | `zcat ticker_20220101.bin.gz \| md5sum` = `cf8f38ae65564187b5a19774c2c2d39f` = md5 file `ticker_20220101.bin` tải trực tiếp từ Kaggle `chuyendinh/wfo-ticker-2022` (đúng dataset kernel `mr-labelb-cpu` dùng) ⇒ **byte-identical** |
| tick size | `exchange_info_pin.json` md5 `5a815948d8909ea5b9615b28e28b53da` (local) = bản trong `ds_mr_inputs` |
| điểm S1 | `ds_mr_inputs/pred_s1a2x1.parquet` md5 `94d703a195e0d5b62ff9a3c7fac9cf87` = `ledger/pred_s1a2x1.parquet` |
| map symId→symbol | `symbol_map_20260806.csv` khớp **559/559** cặp `(symId,symbol)` có trong nhãn |
| nhãn | `/tmp/mrout/mrout/label_b_pnl.parquet` (309.024 dòng, 9.657 tick × đúng 32 coin) |

⇒ Replay local **chạy đúng trên dữ liệu mà nhãn (b) đã build** — không phải "dữ liệu khác".

## 2. VIỆC 1 — AUDIT NHÃN (b)

**Cách chạy lại:** `exitfit/exit_engine.simulate` + `make_p0()` + `pred=None`, entry `E = close(t)`, 1 leg —
đúng đường `mr_label_build.sim_one`; bars đọc TRỰC TIẾP từ bins thô (`jbin.iter_minutes`), cửa sổ
`[day(t) … day(t)+8]` **mở rộng dần** (2→4→6→8 ngày; chứng minh được: chỉ nhánh `OPEN_AT_END` phụ thuộc
cửa sổ — mọi status khác đã chốt trong cửa sổ ngắn, **đã kiểm chéo 0 lệch**).

### 2.1 V1a — 200 cặp ngẫu nhiên (SEED `20260925`)
| Đo | Kết quả |
|---|---|
| n tái lập được | **200/200** (no-entry = 0) |
| `Δgross` (replay − nhãn) | mean/med/p05/p25/p75/p95 = **0,000000 (toàn bộ)** |
| khớp tuyệt đối `tp` **và** `exit_ts` | **100 %** |
| khớp `status` | **100 %** (48 `STOP_LOSS_DONE` + 152 `STOP_MARKET_DONE`) |
| Spearman(gross_replay, gross_nhãn) | **1,000000** |
| theo năm | 2022 (n=65) · 2023 (15) · 2024 (41) · 2025 (79) → **mọi năm med Δ = 0** |
| **KẾT LUẬN** | **NHÃN ĐÚNG** (không lệch, không hệ thống) |

### 2.2 V1b — 6,87 % cặp bị bỏ có làm lệch không?
- **Cổng tự-kiểm cơ chế bỏ:** tái lập được **331.808** cặp ứng viên (top-32 S1, `ts < 2025-10-01`):
  **bỏ 22.784 = 6,867 %** (khai báo 22,8k ≈ 6,9 % ✔) và **tập GIỮ trùng KHÍT tập nhãn (309.024)** ⇒ cơ chế bỏ
  hiểu đúng, không phải "đoán".
- 200 cặp BỊ BỎ (SEED `20260926`) vs 200 cặp ĐƯỢC GIỮ (SEED `20260926`), chạy lại engine:

| | n | gross mean | gross med | tỉ lệ >0 | CI raw95 của mean |
|---|---|---|---|---|---|
| **BỊ BỎ** | 200 | **+2,086 %** | +5,497 % | 83,5 % | [−0,588 % ; +4,528 %] |
| **ĐƯỢC GIỮ** | 200 | **+0,944 %** | +5,000 % | 77,5 % | [−0,777 % ; +2,550 %] |

- **Hiệu BỎ − GIỮ = +1,199 pp · CI raw95 [−1,798 pp ; +4,361 pp] ⇒ TRONG CI** ⇒ **bỏ không gây lệch đo được**.
  (Điểm ước lượng *dương* ⇒ nếu có gì thì việc bỏ làm nhãn **bảo thủ hơn**, tức chống lại chiến lược.)
- Kiểm chéo lại: `med(replay_kept − nhãn)` = **0,000000**.

### 2.3 V1c — `OPEN_AT_END` xử lý thế nào (ghi RÕ)
- **113 dòng = 0,037 %** (toàn bộ **2022**). Theo code: `exit_ts is None` ⇒ `price_tp = close(nến CUỐI mảng)`,
  `status = "OPEN_AT_END"` ⇒ **mark-to-market tại nến cuối**, dòng **được GIỮ** trong pool (không bỏ, không
  NaN, không đánh dấu riêng) — tức **được tính vào mọi chỉ số** của `RESULT_PNL_RULER`.
- Hệ quả: các dòng này có gross **−58,9 %** (med −94,8 %; hold TB 6.122 phút) = coin **hết dữ liệu** (delist/gap
  ≤ 2 ngày nên không kích guard `DELIST`). Mức rổ: **1,2678 % (có)** vs **1,2898 % (bỏ)** ⇒ **0,022 pp**.
  ⇒ Xử lý hiện tại **an toàn và bảo thủ**; không cần sửa, nhưng nên ghi chú trong doc nhãn (hiện chưa ghi).

## 3. VIỆC 2 — AUDIT MÔ HÌNH PHÍ

### 3.1 Bằng chứng về phí/slip (đọc lại, không đo mới)
| Thành phần mô hình (`FEE_RT = 0,008`) | Giá trị | Bằng chứng / trạng thái |
|---|---|---|
| fee (`Configs.RATE_FEE`, comment "đã sửa thành 2 chân") | **0,002** | **2×** mốc taker thật (0,05 %/chân × 2 = **0,001**) — `RESULT_COST_REAL_AUDIT` §2.1 |
| slip (`SLIPPAGE_RATE 0,003` × 2 chân) | **0,006** | **GIẢ ĐỊNH — KHÔNG đo được** (§2.1/§2.2: không có `orderId`/`commission`/`FILLED` ở bất kỳ log nào; giá vào của sim = **close nến, sai số 0,0000 %** ⇒ sim **không** mô hoá spread/impact/độ trễ; `SLIPPAGE_RATE` là **hằng số cộng thêm**) |
| proxy duy nhất liên quan "khớp lệnh" | RT med **1,91 %** | là **BIẾN ĐỘNG** `0,5·(high−low)/close`, **KHÔNG phải** slippage (§2.2) |
| **KẾT LUẬN PHÍ** | **≥ 0,001/vòng (chắc: taker 100 %)**, mô hình **0,002 (fee)** + **0,006 (giả định)** | `0,008` là mức **BẢO THỦ**; "phí hoà vốn" của ruler (1,27–1,56 %) **không** bị ảnh hưởng (là `mean(gross)`, bất biến với phí) |
| **Lưu ý còn thiếu (chiều ngược lại):** nhãn (b) **KHÔNG có funding** (cả `gross` lẫn `0,008`). Đo funding THẬT trên 673 lệnh = **thu ròng ≈ +0,15…0,25 %/lệnh** ⇒ net thật **nhích lên**, không xuống. | | `RESULT_COST_REAL_AUDIT` §2.3 |

### 3.2 Độ nhạy: chấm LẠI từ bins ở 6 mức phí (thước `P32`, `y = gross − f`, `yb = (y>0)`)
Kiểm chéo harness: ở `f = 0,008`, `glift8` của 45deploy/MRA4/MRB8/MRB32 khớp `RESULT_PNL_RULER` **0,0e+00**.

**(i) `Δglift8` — BẤT BIẾN (spread = 0,0e+00 trên cả 6 mức phí):**

| cặp Δ (P32) | `Δglift8` ở mọi `f` | ngoài CI 1,21? |
|---|---|---|
| MRA4 − 45deploy / A45 / V5 | +0,00170 / +0,00135 / +0,00178 | **KHÔNG** ở mọi `f` |
| MRB8 − 45deploy / A45 / V5 | +0,00194 / +0,00159 / +0,00204 | **KHÔNG** ở mọi `f` |
| MRB32 − 45deploy / A45 / V5 | +0,00291 / +0,00256 / **+0,00301** | **KHÔNG** ở mọi `f` |
| V1 − 45deploy / A45 / V5 (kiểm hợp lệ) | +0,00011 / −0,00025 / +0,00018 | **KHÔNG** (≈0 ✔) |

Số cặp Δ có `glift8` **ngoài CI 1,21**: **0** tại `f = 0,001 · 0,002 · 0,004 · 0,006 · 0,008 · 0,012`.
⇒ **Không mức phí nào (kể cả 0) lật được kết luận "alpha xếp hạng = 0".**

**(ii) `netm8(f)` = MỨC của rổ (cái DUY NHẤT đổi theo phí):**

| `f`/vòng | 45deploy | MRA4 | MRB8 | MRB32 | ngoài CI 1,21? |
|---|---|---|---|---|---|
| **0,001** (taker thật) | **+1,227 %** | +1,397 % | +1,366 % | **+1,463 %** | **CÓ** (mọi arm) |
| **0,002** (phần fee của mô hình) | **+1,127 %** | +1,297 % | +1,266 % | **+1,363 %** | **CÓ** (mọi arm) |
| **0,004** | **+0,927 %** | +1,097 % | +1,066 % | **+1,163 %** | **CÓ** (mọi arm) |
| **0,006** | +0,727 % | +0,897 % | +0,866 % | +0,963 % | raw95: **CÓ** (cả 4); chuẩn 1,21: chỉ MRB32 |
| **0,008** (mô hình hiện hành) | +0,527 % | +0,697 % | +0,666 % | **+0,763 %** | KHÔNG (raw95 chạm 0) |

(`out` ở cột cuối = “ngoài CI **CHẶT 1,21**”; ở `f = 0,001/0,002/0,004` thì **cả raw95 lẫn 1,21** đều ngoài.)
| **0,012** | +0,127 % | +0,297 % | +0,266 % | +0,363 % | KHÔNG |

- **Ngưỡng `f*` (netm8 rời 0 ở chuẩn CHẶT 1,21): 45deploy ≈ 0,0052 · MRA4 ≈ 0,0064 · MRB8 ≈ 0,0052 ·
  MRB32 ≈ 0,0061.** ⇒ Ở mức phí **biết chắc** (0,001–0,002) rổ lãi **ngoài CI**; ở `0,008` chỉ *mean* dương.
- **Không đổi mô hình:** luật §8 của PREREG_PNL_RULER đòi **CẢ HAI** (`Δglift8` ngoài CI **VÀ** `netm8 > 0` ngoài CI).
  Điều kiện 1 **không đạt ở mọi `f`** ⇒ kết luận & quyết định giữ nguyên.
- **Ghi nhận trung thực:** các chỉ số **hạng** (`ic`, `pacc`, `dec_mono`, `glift8`, `gross8`) **bất biến** với `f`
  (chấm lại: spread **0,0e+00**; `pacc` = 0,5+0,5·Kendall trên `y` liên tục nên dịch hằng số không đổi). Chỉ
  `netbase` (dịch đúng −`f`) và `auc8c` (dùng `yb = (gross−f>0)`) đổi **rất nhẹ** theo `f`
  (MRB32: `auc8c` 0,59105 → 0,58983 khi `f` 0,001 → 0,012). **Tập Δ ngoài CI 1,21 giống hệt nhau ở cả 6 mức
  phí: 11 chỉ số, TẤT CẢ đều ÂM (ứng viên KÉM đối chứng) và KHÔNG có chỉ số KINH TẾ nào**
  (`auc8c` ×9 + `ic`/`pacc` của `MRB8−A45`) ⇒ **không mức phí nào đổi kết luận**, và các Δ ngoài CI đều **đi
  ngược** ứng viên (củng cố “không đổi model”).

### 3.3 SỬA LỖI VĂN BẢN của tài liệu bị audit (không đổi kết luận, nhưng câu chữ SAI)
- `RESULT_PNL_RULER` §0(1) viết: “**Toàn bộ JSON: 0 (không) chỉ số Δ nào ngoài CI ở chuẩn 1,21**”.
  **Đọc thẳng JSON của chính vòng đó** (`docs/result/mr_pnl_score.json`, thước `P32`): có **38** mục Δ
  `out_both = True` — **tất cả đều ÂM** (0 mục dương), thuộc **`auc8`, `auc8c`, `lift8`, `ic`, `pacc`** và
  **KHÔNG** có mục nào thuộc chỉ số kinh tế (`glift8`/`gross8`/`netm8`/`netbase`).
  Cùng nguồn: §0(1) còn viết `Δic −0,0096…−0,0227`, `Δpacc −0,0020…−0,0075` “**trong CI**” — nhưng hai giá
  trị **ở BIÊN của chính dải đó** (`MRB8−A45`: `Δic −0,02270`, `Δpacc −0,00752`) lại **ngoài CI** theo JSON.
- **Phát biểu ĐÚNG phải là:** “0 chỉ số Δ **KINH TẾ** *dương* ngoài CI; các chỉ số **kỹ năng** (`auc8`/`auc8c`/
  `lift8`/`ic`/`pacc`) của ứng viên **ÂM ngoài CI** ở 38 mục”. Kết luận §0(1) (“không có lift kinh tế”) **giữ
  nguyên**; chỉ câu chữ cần sửa (và §3.2 ở trên cho thấy nó giữ nguyên ở **mọi** mức phí).

## 4. VIỆC 3 — TÁCH NGUỒN GIÁ TRỊ CỦA RỔ

**Thiết kế:** 200 tick ngẫu nhiên (SEED `20260927`, 282,7 coin/tick trung bình, **0 coin bị loại** vì thiếu nến;
56.539 sim) — **cùng luật thoát P0 + cùng cửa sổ**, chỉ đổi cách chọn rổ. Kết quả ở §0(c). Bổ sung:

| rổ | % `STOP_MARKET_DONE` (TRAIL) | gross TB nhóm TRAIL | % thua (`STOP_LOSS_DONE`) | gross TB nhóm thua |
|---|---|---|---|---|
| R1 (S1 top-32) | 77,6 % | **+7,13 %** | 22,5 % | **−16,54 %** |
| R2 (ngẫu nhiên 32) | 69,0 % | +7,03 % | 31,0 % | −10,03 % |
| R3 (toàn thị trường) | 68,4 % | +7,03 % | 31,6 % | −10,05 % |
| R4 (S1 bottom-32) | 62,2 % | +7,02 % | 37,8 % | −7,48 % |

**Đọc:** nhóm thắng của **mọi** rổ đều bị **cắt ở đúng ngưỡng luật** (~+7 %, sàn arm/ratchet) — kể cả rổ ngẫu
nhiên và toàn thị trường. Chênh lệch giữa các rổ **không** đến từ chọn coin mà từ **tỉ lệ chạm arm** (77,6 %
ở S1 so với 62–69 % ở rổ khác) — chênh đó chỉ **+0,10 pp** giá trị (R1−R3), **trong CI** ⇒ **không kể được**.
⇒ **Giá trị của RO = LUẬT THOÁT** (P0: arm +7 % + ratchet + time-stop 168 h) trên **cả thị trường** giai đoạn
2021-12→2025-10; **S1 chỉ chọn được tick/coin "dễ chạm arm" hơn ~9 điểm % số lượt nhưng bù lại bằng nhóm thua
sâu hơn (−16,5 % vs −10,0 %), nên tổng bằng nhau.**

**Lưu ý phạm vi:** mẫu 200 tick cho mức +1,7…+1,8 %/vòng (mọi rổ) so với +1,27 % của toàn pool 9.657 tick —
chênh là **phân tán mẫu tick**, không phải mâu thuẫn (200 tick trong ~1.430 ngày, CI ±1 pp). Giá trị tuyệt đối
**không** phải bằng chứng về S1.

## 5. ĐIỀU **KHÔNG** KIỂM ĐƯỢC / GIỚI HẠN (nói rõ mức độ thiếu)

1. **Slip thật vẫn KHÔNG đo được** (không có fill/commission). Audit chỉ chứng minh: (i) `Δglift8` **bất biến**
   với mọi mức phí hằng số ⇒ kết luận alpha không phụ thuộc (ii); (ii) mức lãi của rổ phụ thuộc phí **rất mạnh**
   và chỉ còn ngoài-CI khi `f ≲ 0,005`. Nếu slip thật ≫ 0,005 thì câu "rổ có lãi" **cũng** mất — đây là rủi ro
   **còn nguyên**, chỉ giải được bằng dữ liệu khớp lệnh thật.
2. `V1a/V1b` là mẫu 200 (+200) cặp trên 309.024 dòng ⇒ **phát hiện được** sai số ≥ ~1 pp gross, **không** phát
   hiện được sai số cỡ 1e-4 (nhưng 100 % khớp tuyệt đối bit-level nên không còn chỗ cho sai số hệ thống).
3. Việc **bỏ 6,87 % cặp** được kiểm bằng so **phân bố** (200 vs 200) — không loại trừ được lệch cỡ <1,8 pp.
4. `OPEN_AT_END` toàn bộ ở 2022 ⇒ kiểm chế độ delist 2024–2025 bằng 0 dòng; không kết luận thêm.
5. Funding **không** nằm trong nhãn (b) (cả `gross` lẫn phí) ⇒ mọi số của audit cũng **không** có funding.

## 6. SẢN PHẨM + CHI PHÍ + KỶ LUẬT

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_AUDIT_PNL.md` | chốt trước (commit `a331b80`) |
| `docs/result/RESULT_AUDIT_PNL.md` | file này |
| `research/analysis/audit_pnl_lib.py` | hạ tầng: đọc bins thô + replay engine + tái lập cơ chế bỏ khối |
| `research/analysis/audit_pnl_label.py` | VIỆC 1 (V1a/V1b/V1c) |
| `research/analysis/audit_pnl_cost.py` | VIỆC 2 (chấm lại 6 mức phí, 7 arm × 16 fold) |
| `research/analysis/audit_pnl_ro.py` | VIỆC 3 (R1–R4, 56.539 sim) |
| `/tmp/auditpnl/{label,cost,ro}.json` | số thô (kèm `ro_ticks.pkl` resume) |

**Chi phí đo (thực tế):** V1a 449 s · V1b 1.017 s (bỏ) + ~1.600 s (giữ) · V2 545 s (bins đọc 1 lượt/arm) ·
V3 2.051 s → **~1,6 giờ** tổng, **4 lõi**, RAM đỉnh < 3 GB, **0** Java/sim hệ thống, **0** train.
Sự cố & cách chữa: 2 lần process bị session reaper giết (không phải lỗi code) → chuyển `setsid` + thêm
resume cache; 1 lỗi **của chính audit** (trừ phí 2 lần trong bảng `netm8`) đã bị **kiểm chéo với
`RESULT_PNL_RULER` phát hiện và sửa** trước khi báo cáo (giá trị sai đã bị chặn, có lưu `cost_buggy.json`).
**KHÔNG push.**
