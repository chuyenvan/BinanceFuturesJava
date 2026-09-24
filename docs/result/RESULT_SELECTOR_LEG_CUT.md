# RESULT_SELECTOR_LEG_CUT — căt/giới hạn leg SELECTOR: NULL (giữ T170)

Ngày: 2026-09-23. Pre-reg: `docs/prereg/PREREG_SELECTOR_LEG_CUT.md` (**commit `e566354`**, chốt TRƯỚC khi chạy
biến thể; sau đó **không sửa thiết kế**). Script: `research/analysis/selcut_run.py` (đẩy 4 chân lên Kaggle),
`research/analysis/selcut_score.py` (chấm điểm). Toàn bộ sim chạy **trên Kaggle CPU kernel** — **không**
chạy Java sim trên Oracle (job `shadow-c3` vẫn `active`), **không** `claude-run`/Claude Code, **không push**,
**không chạm HOLDOUT 2026** (dữ liệu ≤ 2025-12-31). Trung gian `/tmp/selcut_*`.

---

## 0. KẾT LUẬN (một dòng)

> **NULL / NO-GO — giữ nguyên T170.** Cắt hẳn (V1 `CUT`) hay giới hạn độ phủ (V2 `TOPK3=3`) leg selector
> **KHÔNG** làm tăng số lệnh hay PnL của `BIG_DOWN`/`DCA_LEVEL1`, và **KHÔNG** sinh ra rate chất lượng nào
> ngoài CI theo hướng tốt (0/5 rate ở cả hai biến thể). Cơ chế "giải phóng khóa symbol" **CÓ** xảy ra thật
> (125/248 lệnh `BIG_DOWN` đổi sang coin khác) — nhưng **coin được giải phóng không tốt hơn**: chất lượng
> `BIG_DOWN` đi ngang đến xấu hơn (`mean(profit)` +0,026 CI `[-2,276; +0,358]`; `PnL/leg` **giảm** 65,54 → 52,06;
> `TSloss%` 8,47 → 9,68). V2 còn **FAIL ràng buộc cứng** (UW 203 > 200, tập trung 16,55% > 15%) và có 1 rate
> **XẤU ngoài CI** (`mP|SL` −3,728, CI `[-7,036; −0,310]`). Không áp dụng biến thể nào.

---

## 1. CỔNG BƯỚC 0 — Kaggle có tái lập được PARITY của T170 không? **CÓ (PASS)**

| hạng mục | giá trị |
|---|---|
| Bundle | `chuyendinh/sim-x1-2021-bundle` (private, dataset `wfo_ds_x1_2021` — 18 fold, `leakFreeFrom=2021-07-01`) |
| Ticker | 7 dataset `wfo-ticker-2021..2025h2`, **1.826 ngày** 2021-01-01..2025-12-31, không thiếu ngày |
| Chân parity mới (`selcut-par0`, 2026-09-23) | `equity=111070`, `n=1089`, mapper 863, **JVM 970,4s** |
| md5 `printDone.csv` Kaggle | **`efb793e2468ca3a7318da0f0ad23d4fc`** |
| md5 `printDone.csv` Oracle (`X1_GS_T170_2021`) | **`efb793e2468ca3a7318da0f0ad23d4fc`** |
| `diff` | **0 dòng** ⇒ **byte-identical** |

⇒ Dataset/bundle trên Kaggle **đúng là `wfo_ds_x1_2021`** (18 fold, 2021-07-01), **không** còn là
`wfo_ds_clean` (10 fold, leakFreeFrom 2022-01-01). Bins không đi qua đường Kaggle (`docs/runbooks/KAGGLE_SIM.md` §6)
— điều đó **không cản** vòng này vì biến thể là biến thể **CODE/PROFILE**, không phải biến thể bins
(selector được đọc từ `funding.bin` qua `time2SymbolPred = ds.funding`, `Simulator:882`).

### 1.1 🔴 Vật cản thật của Bước 0 — KHÔNG phải dữ liệu, mà là TOOL hỏng

`tools/kaggle_sim.py` **chứa marker merge-conflict CHƯA GIẢI đã được commit** (`68feced`, 2026-09-22 11:47)
⇒ `SyntaxError` khi import ⇒ **mọi phiên chạy sim Kaggle từ 11:47 ngày 22/09 đều không đẩy được chân nào**
(4 chân `brct50`/`brc-cont` cuối cùng đều trước mốc đó). Đã sửa bằng cách **gộp CẢ HAI nhánh** của merge
(`bundle_ds` + `extra_ds`), **không bỏ tính năng nào**; thêm `jar_ds` + in `JAR_SHA256=` (xem §5.3).
Vẫn còn 1 file khác có marker y hệt nhưng **ngoài phạm vi vòng này**: `docs/analysis/RECON_EVENT_ALPHA.md`.

---

## 2. Commit

| commit | nội dung |
|---|---|
| `e566354` | **PREREG_SELECTOR_LEG_CUT** + sửa `tools/kaggle_sim.py` (gộp conflict + `jar_ds` + `JAR_SHA256`) |
| `2cb7f78` | Cờ `SELECTOR_LEG_CUT` (V1) + `selcut_score.py` + `selcut_run.py` |

Bản đồ chạy: cổng parity (Bước 0) chạy **trước** — đúng thứ tự brief giao; **cả 3 biến thể** (`cutpar`, `cut`,
`topk3`) chạy **sau** `e566354`.

### 2.1 Đính chính cơ chế (ghi trong pre-reg §1.1, đo lại lần nữa ở đây)

- **`SELECTOR_ONLY_ENTRY=1` TẮT leg `BIG_DOWN`** (`Simulator:346`), **KHÔNG** phải leg selector. Nếu dùng
  nhầm cờ này cho V1 sẽ ra **đúng cái ngược lại** giả thuyết. Trong code **không tồn tại** cờ cắt leg selector
  (`DISABLE_PREDICT_SYMBOL` chỉ còn trong file backup `Configs.java.bak_cfg`).
- V1 vì vậy dùng **cờ MỚI `SELECTOR_LEG_CUT`** (default `false` ⇒ byte-identical) chặn khối
  `Simulator:388` (`if (symbol2Pred != null && !Configs.SELECTOR_LEG_CUT)`).
- **Tự-kiểm cờ đúng**: chân `cut` có `n PREDICT_SYMBOL_TRADE = 0` ✔ (yêu cầu pre-reg §5) và log
  `[SELECTOR-CFG] … SELECTOR_LEG_CUT=true`.

---

## 3. Cổng parity cho jar mới (pre-reg §3.1) — **PASS**

| chân | jar `JAR_SHA256` | equity | n | md5 `printDone` |
|---|---|---|---|---|
| `selcut-par0` (gate Bước 0) | `2c2f8aef78c98470…` (jar trong bundle) | 111070 | 1089 | `efb793e2468ca3a7318da0f0ad23d4fc` |
| `selcut-cutpar` (jar MỚI, cờ OFF) | `b4caa81d7b936e04…` (= jar build 2026-09-23) | 111070 | 1089 | **`efb793e2468ca3a7318da0f0ad23d4fc`** |

`diff` = 0 dòng; log `SELECTOR_LEG_CUT=false`. ⇒ Code mới **trơ** khi cờ OFF, jar mới tái lập T170
**byte-identical**. Chỉ sau cổng này chân `cut` mới được chạy (pre-reg §3.1 tuân thủ **tuần tự**).

### 3.1 Vật cản kỹ thuật nhỏ đã xử lý

`kernels_status()` trả **403 "Permission 'kernels.get' was denied"** tạm thời (rate-limit phía Kaggle) —
nhiều lần liên tiếp rồi tự khỏi; `kernels_list`/`dataset_list_files`/`kernels_output` vẫn OK. Không ảnh
hưởng kết quả (đã đối chiếu bằng `kernels_list` + `fetch`).

---

## 4. Bảng biến thể vs PARITY

`k = 2` ⇒ nở rộng CI chuẩn hoá `inflate(2) = 1,1774`; báo **cả** hệ số cũ `x1.21` (rộng hơn ⇒ chặt hơn).
"Ngoài CI" chỉ được tính khi ngoài ở **cả hai** độ rộng. Bootstrap block-72h, 2000 rep, seed `20260905`.
Mốc neo block **cố định 2021-07-01** cho mọi arm (khác `c3_rates` neo theo `ts.min()` của từng bảng —
nếu 2 arm có lệnh đầu tiên lệch giờ thì block lệch nhau ⇒ ghép cặp "paired" sai).

### 4.1 5 rate chất lượng (toàn bộ leg)

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP |
|---|---:|---:|---:|---:|---:|---:|
| PARITY | 1089 | 88,25 | 9,73 | 7,642 | −16,992 | 5,244 |
| **CUT** (V1) | **248** | 88,71 | 9,68 | 6,669 | −12,514 | 4,812 |
| **TOPK3** (V2) | **615** | 88,78 | 9,59 | 7,040 | −20,720 | 4,377 |

### 4.2 Hiệu (biến thể − parity) + CI **cả hai** độ rộng

| tag | rate | hiệu | CI @1,21 | CI @1,1774 | ngoài CI | hướng |
|---|---|---:|---|---|---|---|
| CUT | win% | +0,464 | [−4,314; +6,088] | [−4,174; +5,948] | – | |
| CUT | TSloss% | −0,056 | [−4,462; +5,880] | [−4,322; +5,741] | – | |
| CUT | mP\|SM | −0,973 | [−2,276; +0,358] | [−2,241; +0,323] | – | |
| CUT | mP\|SL | +4,478 | [−1,940; +10,105] | [−1,777; +9,943] | – | |
| CUT | meanP | −0,431 | [−2,137; +1,326] | [−2,090; +1,280] | – | |
| TOPK3 | win% | +0,534 | [−1,539; +2,754] | [−1,481; +2,696] | – | |
| TOPK3 | TSloss% | −0,140 | [−2,593; +2,144] | [−2,529; +2,080] | – | |
| TOPK3 | mP\|SM | −0,601 | [−1,428; +0,290] | [−1,404; +0,267] | – | |
| TOPK3 | **mP\|SL** | **−3,728** | **[−7,036; −0,310]** | **[−6,945; −0,401]** | **CÓ** | **XẤU** |
| TOPK3 | meanP | −0,867 | [−2,021; +0,290] | [−1,990; +0,259] | – | |

- **CUT: 0/5 rate ngoài CI (tốt) và 0/5 XẤU ngoài CI** ⇒ không có bằng chứng cải thiện chất lượng.
- **TOPK3: 0/5 rate ngoài CI (tốt), 1/5 XẤU ngoài CI** (`mP|SL`) ⇒ vừa không tốt hơn, vừa **xấu đi có ý nghĩa**.

### 4.3 Ràng buộc CỨNG (`docs/runbooks/RISK_APPETITE.md`)

| tag | equity cuối | CAGR% | maxDD% | UW ngày | quý xấu nhất | tập trung 1 coin | PASS |
|---|---:|---:|---:|---:|---:|---:|---|
| PARITY | 111 070 | 29,27 | −11,84 | 92 | −0,92 | 9,77% | ✔ |
| CUT | 47 911 | 7,23 | **−3,23** | **184** | −0,37 | 4,51% | ✔ (UW 184 < 200, sát trần) |
| TOPK3 | 72 313 | 17,51 | −10,00 | **203** | −0,37 | **16,55%** | ❌ **FAIL 2 chặn** |

Theo năm (maxDD% / UW ngày / return%):

| năm | PARITY | CUT | TOPK3 |
|---|---|---|---|
| 2021 | −2,46 / 37 / +12,21 | −1,05 / 47 / +3,61 | −1,65 / 30 / +8,45 |
| 2022 | −11,84 / 72 / +19,58 | −0,05 / 1 / +4,25 | −10,00 / 95 / +16,99 |
| 2023 | −2,73 / 63 / +34,96 | −3,23 / 166 / +3,11 | −2,53 / 63 / +17,06 |
| 2024 | −6,60 / 92 / +32,14 | −2,68 / 184 / +12,68 | −3,82 / 87 / +23,48 |
| 2025 | −4,23 / 52 / +32,71 | −0,56 / 2 / +9,15 | −4,97 / **203** / +12,73 |

Không năm nào âm ở cả 3 chân. CUT **giảm** maxDD/tập trung (vì bỏ hẳn 841 lệnh) nhưng **kéo dài UW**
92 → 184 ngày (gần trần 200). V2 vượt trần UW (203) và trần tập trung (16,55%).

---

## 5. CÂU HỎI CHÍNH — số lệnh + PnL của `BIG_DOWN` và `DCA_LEVEL1` trước–sau

### 5.1 Bảng theo LEVEL

| tag | level | n | SumPnL (USDT) | **PnL/leg (USDT)** | mean(profit) | win% | TSloss% |
|---|---|---:|---:|---:|---:|---:|---:|
| PARITY | PREDICT_SYMBOL_TRADE | 821 | 47 114,5 | 57,39 | 4,221 | 88,31 | 10,11 |
| PARITY | BIG_DOWN | 248 | 16 254,4 | **65,54** | 4,786 | 88,71 | 8,47 |
| PARITY | DCA_LEVEL1 | 20 | 12 701,3 | **635,06** | 52,888 | 80,00 | 10,00 |
| PARITY | ALL | 1089 | 76 070,2 | 69,85 | 5,244 | 88,25 | 9,73 |
| CUT | PREDICT_SYMBOL_TRADE | **0** | – | – | – | – | – |
| CUT | BIG_DOWN | **248** | 12 911,4 | **52,06** | 4,812 | 88,71 | 9,68 |
| CUT | DCA_LEVEL1 | **0** | 0,0 | – | – | – | – |
| CUT | ALL | 248 | 12 911,4 | 52,06 | 4,812 | 88,71 | 9,68 |
| TOPK3 | PREDICT_SYMBOL_TRADE | 359 | 18 991,6 | 52,90 | 3,785 | 89,42 | 8,91 |
| TOPK3 | BIG_DOWN | **248** | 13 979,4 | **56,37** | 4,524 | 88,71 | 10,48 |
| TOPK3 | DCA_LEVEL1 | **8** | 4 342,6 | 542,83 | 26,367 | 62,50 | 12,50 |
| TOPK3 | ALL | 615 | 37 313,6 | 60,67 | 4,377 | 88,78 | 9,59 |

Delta:

| | `BIG_DOWN` Δn | ΔSumPnL | ΔPnL/leg | Δmean(profit) | `DCA_LEVEL1` Δn | ΔSumPnL |
|---|---:|---:|---:|---:|---:|---:|
| CUT | **+0** | −3 343,0 | **−13,48** | +0,026 | **−20** | −12 701,3 |
| TOPK3 | **+0** | −2 275,0 | **−9,17** | −0,262 | **−12** | −8 358,6 |

### 5.2 Trả lời thẳng: **KHÔNG tăng — mà GIẢM**

1. **`BIG_DOWN`: số lệnh KHÔNG đổi (248 ở cả 3 chân).** Điều này **không** phải vì khóa không tác động —
   `BIG_DOWN` chọn tối đa `NUMBER_ENTRY_EACH_SIGNAL = 2` coin/tick, nên **khóa ảnh hưởng tới *coin nào* được
   chọn, không tới *bao nhiêu* lệnh**. PnL thì **giảm**: `SumPnL` 16 254 → 12 911 (CUT) / 13 979 (TOPK3);
   `PnL/leg` 65,54 → 52,06 / 56,37. Chất lượng `mean(profit)` đi ngang (CUT, CI chứa 0) hoặc xấu hơn (TOPK3).
2. **`DCA_LEVEL1`: số lệnh GIẢM MẠNH (20 → 0 ở CUT; 20 → 8 ở TOPK3).**
3. **Cơ chế khóa CÓ thật và đã được chứng minh**: so `(start, sym)` của 248 lệnh `BIG_DOWN`, chỉ **123/248
   trùng** giữa PARITY và CUT ⇒ **125 lệnh (50%) đổi sang coin khác** sau khi giải phóng khóa. Nhưng
   "coin được giải phóng" **không tốt hơn** — đo ra là đi ngang/xấu hơn. **Giả thuyết bị bác bỏ ở đúng chỗ
   nó định đứng.**

### 5.3 🔴 Phát hiện cấu trúc: `DCA_LEVEL1` KHÔNG phải một nhóm vào lệnh độc lập

Kiểm trực tiếp `printDone.csv` của PARITY: **cả 20 lệnh `DCA_LEVEL1` đều là leg THỨ 2/3 của một cụm
(`leg > 0`), không có leg nào là leg đầu**. 1089 leg = 1069 cụm; 16 cụm nhiều leg (đúng bằng 20 leg dư):

| cụm host | leg đầu (level) | leg DCA |
|---|---|---|
| 13 coin: AIA, ANC, DAR, EVAA(×2), FTT, GAL, JELLYJELLY, SOL, SRM, STBL, XAN, XPL | `PREDICT_SYMBOL_TRADE` | 1–2 leg `DCA_LEVEL1` |
| 3 coin: ALPINE, EDEN, MYX | `BIG_DOWN` | 1 leg `DCA_LEVEL1` |

⇒ `DCA_LEVEL1` là **leg nhồi grid lên một vị thế đang lỗ** (leg đầu luôn âm −12…−68 profit, leg DCA +12…+167),
**không thể "được giải phóng khóa"** như brief hình dung: bỏ selector thì **13/16 cụm host biến mất**, nên
leg DCA của chúng cũng biến mất. Đây là hệ quả **bắt buộc về cơ chế**, không phải nhiễu.
(3 cụm host `BIG_DOWN` cũng mất leg DCA vì khi giải phóng khóa, coin được chọn ở các tick đó **khác đi**.)

### 5.4 Đính chính đơn vị: "meanP +57,39 / +65,54 / +635,06"

Ba số này trong brief là **PnL/leg (USDT)** = `SumPnL/n`, **không** phải `meanP` theo quy ước repo
(`meanP = mean(profit)`, `c3_rates.rates()`). Đối chiếu: 47 114,5/821 = **57,39**; 16 254,4/248 = **65,54**;
12 701,3/20 = **635,07** — khớp. Theo đúng đơn vị PnL/leg thì **vẫn đúng** thứ tự "DCA ≫ BIG_DOWN >
selector". Nhưng `+635/leg` của DCA là **hiện tượng chọn mẫu**: chỉ 20 leg nhồi sâu vào 16 vị thế đã lỗ rồi
hồi — không phải một nhóm 20 lệnh độc lập để nhân bản.

---

## 6. Kết luận theo luật pre-reg §5

| biến thể | rate ngoài CI hướng TỐT | rate XẤU ngoài CI | ràng buộc cứng | verdict |
|---|---:|---:|---|---|
| `CUT` (V1) | **0/5** | 0/5 | PASS (UW 184 sát trần) | **NULL** |
| `TOPK3` (V2) | **0/5** | 1/5 (`mP|SL`) | **FAIL** (UW 203; tập trung 16,55%) | **NO-GO** |

- Không biến thể nào đạt **≥2 rate ngoài CI cùng hướng tốt** ⇒ **NULL**.
- Không biến thể nào **đơn lẻ** đạt ⇒ không có chuyện "phụ thuộc 1 biến thể" ⇒ **không UNCONFIRMED**,
  mà là **bác bỏ** theo cả hai cách cắt (cắt hẳn và giới hạn).
- **Không chọn theo equity** (pre-reg §4.5): cả hai biến thể đều **giảm** equity cuối
  (111 070 → 47 911 / 72 313) — và dù có tăng thì cũng không được dùng để chọn.
- Equality: hệ số multiplicity `x1.21` đã **rộng hơn** `inflate(2)=1,1774` nên nguồn chung đã siết; kết luận
  NULL không phụ thuộc hệ số.
- **Cơ chế được làm rõ**: alpha của T170 nằm ở **cả hai** luồng (selector 821 lệnh PnL/leg 57,39 và BIG_DOWN
  248 lệnh 65,54) nhưng **không** có chuyện nhóm này đang chặn nhóm kia. `BIG_DOWN` bị trần 2 lệnh/tick
  (không bị khóa chặn số lượng), còn `DCA_LEVEL1` là **leg phụ thuộc** chứ không phải nhóm bị chặn.
  ⇒ "phân bổ vốn/khóa" **không** phải nút thắt cần vặn.

## 7. Tài nguyên Kaggle đã dùng (chi phí 0 — CPU kernel không tính quota)

| chân | tag kernel | JVM | tổng kernel (push→fetch) |
|---|---|---:|---|
| cổng Bước 0 | `chuyendinh/sim-selcut-par0` | 970,4s | ~35′ |
| cổng jar mới | `chuyendinh/sim-selcut-cutpar` | 1210,0s | ~27′ |
| V1 | `chuyendinh/sim-selcut-cut` | 749,8s | ~25′ |
| V2 | `chuyendinh/sim-selcut-topk3` | 1279,1s | ~27′ |
| **tổng** | **4 chân**, tối đa 2 slot đồng thời / 5 | – | **~1h55′ wall** |

Dataset mới: `chuyendinh/sim-jar-selcut` (95MB, chỉ chứa `sim.jar` — để đổi CODE mà **không** phải tạo lại
bundle 5,3GB; kernel in `JAR_SHA256=` và ghi vào `result.json` để **không bao giờ** dùng nhầm jar cũ âm thầm).

## 8. File liên quan + vệ sinh

- `docs/prereg/PREREG_SELECTOR_LEG_CUT.md` (thiết kế chốt trước), `research/analysis/selcut_run.py`,
  `research/analysis/selcut_score.py`, `tools/kaggle_sim.py` (sửa conflict + `jar_ds` + `JAR_SHA256`).
- Bằng chứng số: `/home/ubuntu/kaggle_sim/out/{selcut-par0,selcut-cutpar,selcut-cut,selcut-topk3}/`
  (`printDone.csv`, `sim.out`, `result.json`) + `/home/ubuntu/kaggle_sim/out/selcut_score_all.json` (raw của script chấm) — giữ lại.
- Thư mục stage jar để tạo version dataset sau này: `/home/ubuntu/selcut_jar/` (hardlink `sim.jar`, 95MB).
- **Không** đụng `shadow-c3` (vẫn `active`), **không** systemctl/kill, **không push**.
- Cờ `SELECTOR_LEG_CUT` để lại trong code (default `false` = byte-identical) làm công cụ cho vòng sau;
  **không** bật ở đâu.
- Còn treo (ngoài phạm vi): `docs/analysis/RECON_EVENT_ALPHA.md` còn marker merge-conflict y hệt `kaggle_sim.py`.
