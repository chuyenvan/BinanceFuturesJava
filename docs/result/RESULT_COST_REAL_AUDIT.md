# RESULT_COST_REAL_AUDIT — Phase A (trích chi phí THẬT) + Phase B (đo phân bố chi phí)

Ngày: 2026-09-23. Kế hoạch: `docs/audit/PLAN_COST_AUDIT_REAUDIT.md` (viết **trước** khi đo).
Script: `research/analysis/cost_real_audit.py`. Trung gian: `/tmp/cost_real_audit/` (dọn sau commit).

**Tuân thủ:** thuần Python · **không** Java trên Oracle (shadow đang chạy) · **không** `claude-run`/Claude Code
· **không push** · 242 **CHỈ ĐỌC** (`ssh -p 2222`, không ghi/sửa/kill) · **không chạm 2026** (mốc dữ liệu ≤ 2025-12-31;
riêng `storage/data/order/` của 242 là log sản xuất sẵn có, chỉ đọc để kiểm kê, **không** đưa vào mô hình).

---

## 0. KẾT LUẬN NGẮN

1. **`printOrder.csv` KHÔNG TỒN TẠI** — không có trên Oracle (quét toàn máy) và không có trên 242. ⇒ Yêu cầu
   "check lại fundingfee THỰC theo các lệnh trong `printOrder.csv`" **không thực hiện được nguyên văn**;
   đã thay bằng nguồn tương đương gần nhất (mục §2).
2. **KHÔNG có dữ liệu khớp lệnh thật.** Toàn bộ log/file order đều **không** có `orderId` / `commission` /
   `executedQty` / giá khớp. ⇒ **fee/leg = KHÔNG ĐO ĐƯỢC**; **slip/leg = chỉ có proxy biến động**;
   **tỉ lệ khớp limit = KHÔNG ĐO ĐƯỢC**.
3. **Funding THẬT thì ĐO ĐƯỢC** (Aerospike `funding_data`): đa số lệnh **TRẢ** funding (68,2% trong số 673 lệnh
   có kỳ settle), nhưng **mean = −0,2518%/lệnh (âm = THU)**, median **+0,0109%** ⇒ **khoản thu ròng chỉ đến
   từ một thiểu số lệnh**, không phải "đa số được thu". Sim tính gần đúng tốt (corr **0,805**).
4. **Đối chiếu gross→net:** ở mức chi phí *chắc chắn* (phí thật + slip = 0) net **+0,73…+0,79pp/lệnh** so với sim
   ⇒ **thay đổi ĐỘ LỚN, không đổi dấu** (win% 88,0 → 88,3). Ở mức *proxy slip* net **GIẢM 2,61pp**.
5. **Có cơ sở để "lật" nhóm SIM-based không?** — **Không, ở mức chi phí biết chắc.** Mọi nhóm đang chạy đã
   dương đậm (`c*` = +1,77% … +52,9%); hạ phí chỉ làm chúng dương hơn. Muốn có "lật" thì phải **giảm slip rất
   mạnh** — mà mốc proxy (thứ duy nhất liên quan tới "khớp lệnh") lại **CAO** (RT median 1,91%), tức bằng chứng
   hiện có **đi ngược** hướng cần thiết.

---

## 1. PHASE A — KIỂM KÊ NGUỒN CHI PHÍ (file nào tồn tại · cột gì · bao nhiêu dòng · khoảng thời gian)

### 1.1 `printOrder.csv` — **KHÔNG TỒN TẠI**
| Nơi quét | Lệnh | Kết quả |
|---|---|---|
| Oracle, `/home/ubuntu` (độ sâu ≤ 5) | `find ... -name "printOrder*.csv"` | **0 file** |
| Oracle, toàn máy | `find / -name "printOrder*"` | **0 file** |
| 242, `/home/chuyennd` (độ sâu ≤ 5) | `find ... \( -name "*rder*.csv" -o -name "*rder*.data" -o -name "*.log" \)` | 12 file — **toàn `*.log`**, **không** có `printOrder*` |
| repo | `grep -rn "printOrder"` | chỉ là **tên hàm** `printOrderTestDone()` / `printOrderProduct()` (`TraceOrderDone.java:34,37,91`) — **không** có file dữ liệu nào tên `printOrder.csv` |

⇒ **Kết luận: không tồn tại; không bịa số.** Ghi nhận: tên gần nhất trong code là `printDone.csv` (do
`TraceOrderDone.printOrderTestDone("storage/printDone.csv", …)` sinh ra) — **đây là file sim**, không phải log lệnh thật.

### 1.2 Nguồn CÓ dữ liệu lệnh (và cột của nó)

| Nguồn | n | Cột chính | Khoảng thời gian | Có chi phí thật? |
|---|---|---|---|---|
| `java/devrun/*/storage/printDone.csv` (361 run; canonical `X1_GS_T170_2021`, md5 `efb793e2…`) | **1089** (canonical) | sym, side, entry, tp, profit, **status**, start, end, level, quantity, margin, **pnl**, time_order, **funding**, … | 2021-07-27 → 2025-12-01 (GMT+7) | **KHÔNG** (chỉ `pnl` + `funding` *suy ra*) |
| `java/devrun/*/storage/OrderTestDone.data` | 270 file | Java-serialized `TreeMap<Long,OrderTargetInfoTest>` | theo run | **KHÔNG** |
| `java/devrun/*/storage/BalanceIndex.data` | 270 file | ledger số dư nội bộ sim | theo run | **KHÔNG** |
| `/home/ubuntu/shadow_c3/ledger.csv` (paper) | **65** | sym, ts_entry, entry, qty, rank, symbol_pred, ts_exit, exit_price, reason, **pnl** | 2026-09 (ms) | **KHÔNG** (pnl = **GROSS**) |
| `/home/ubuntu/shadow_c3/open_positions.csv` | vài chục | sym, ts_first, avg_entry, qty, rank, …, leg_count | 2026-09 | **KHÔNG** |
| **242** `/home/chuyennd/java/v_t_m/storage/data/order/<YYYYMMDD>/<SYM>-<ts_ms>` | **2850 file / 83 ngày** | Java-serialized `OrderTargetInfo`: symbol, side, quantity, level, **status**, ticker snapshot (`maxPrice/minPrice/priceClose/priceOpen/totalUsdt/startTime`), marketRates | **2026-04-24 → 2026-09-12** | **KHÔNG** (xem §1.3) |

### 1.3 Bằng chứng "KHÔNG có khớp lệnh thật" (grep thực nghiệm)

| Log | Vị trí/ngày | n dòng | `orderId` | `commission` | `FILLED` | `executedQty` | `avgPrice` |
|---|---|---|---|---|---|---|---|
| Oracle `shadow_c3/app/logs/full.log` | → 2026-09-23 | 34 926 | **0** | **0** | **0** | **0** | **0** |
| Oracle `java/devrun/logs/*.log` (5 file) | — | — | **0** | **0** | **0** | **0** | **0** |
| 242 `v_t_m/logs/full.log` | 2026-08-12 → 2026-09-23 | 370 791 | **0** | **0** | **0** | **0** | **0** |
| 242 `v_t_m/logs/logt9.log` | 2026-09-01 → 2026-09-10 | 70 288 | **0** | **0** | **0** | **0** | **0** |

- **242 order store:** giải mã giải `strings` 2850 file ⇒ **status chỉ có duy nhất `REQUEST`** (2849/2850 khớp
  token), **0** `NEW`/`FILLED`/`CANCELED`/`FINISHED`/`STOP_MARKET_DONE` (enum `OrderTargetStatus.java`).
  ⇒ Đây là **hàng đợi request nội bộ**, **không** phải trạng thái order ở sàn.
- Log 242 có dòng `Create sl -> SELL <SYM> <qty> <entry> -> <sl> rate: x` (lệnh SL nội bộ) nhưng **không** có
  phản hồi khớp từ sàn. Có dòng `Error get position from binance!` ⇒ phiên bản này cũng **không** nhận được dữ liệu vị thế/khớp.

### 1.4 Nguồn funding THẬT (dùng được)
Aerospike `test.funding_data` @ `127.0.0.1:3222` (read-only) — key = symbol, bin `f_data` = Snappy(JSON `{ts_ms: rate}`),
cadence 4h/8h. **Coverage trên 358 symbol của 1089 lệnh = 358/358 (0 thiếu).**

---

## 2. PHASE B — ĐO PHÂN BỐ CHI PHÍ (trên 1089 lệnh T170)

**Cổng tự-kiểm (chạy trước mọi phép tính):** G1 md5 `efb793e2468ca3a7318da0f0ad23d4fc` ✔ n=1089 ✔ ·
G2 `|notional/margin−1|max = 1,52e−07` ✔ · G3 tái tạo `net_sim = gross − 0,80 − funding`: `|resid|max = 1,78e−15` ✔ ·
G4 **0 dòng ≥ 2026** ✔ · G5 funding coverage 358/358 ✔.

### 2.1 fee/leg — **KHÔNG ĐO ĐƯỢC** (nói rõ mức độ thiếu)
Không có trường `commission`/`makerCommission` ở bất kỳ log/file nào ⇒ **không có phí thật của sàn**.
Chỉ có thể nêu **mốc tham chiếu** (không phải đo): Binance USDⓈ-M VIP0 **maker 0,020%/chân · taker 0,050%/chân**.
Trong repo, config shadow dùng `RATE_FEE=0.0015` (1 chân) — cũng là **giả định**, không phải số đo.
**Không phân biệt được maker/taker** vì không có dữ liệu loại lệnh ở sàn.

### 2.2 slip/leg — chỉ có **PROXY BIẾN ĐỘNG** (không phải slip)
Proxy `0,5·(high−low)/close` tại **đúng phút khớp** (nguồn `kline_1m_opt`, xem §2.2b):

| Chân | mean | median |
|---|---|---|
| entry (phút vào) | **2,0476%** | 1,1006% |
| exit (phút ra) | **1,2973%** | 0,6338% |
| **round-trip** | **3,3449%** | **1,9099%** |

**2.2b Giá ý định vs giá khớp (dùng `kline_1m_opt` = `raw/*.f32`, cùng nguồn — đã chứng minh ở `RESULT_COST_LIQUIDITY.md` §2):**

| Đo | n | mean | median | p95\|.\| |
|---|---|---|---|---|
| `entry` (printDone) vs close nến @ phút vào | 1089 | −0,0000% | **−0,0000%** | **0,0000%** |
| `exit` (suy từ `entry + gross/qty`) vs close nến @ phút ra | 1089 | −2,4935% | −4,4295% | 31,2610% |

- **Entry của sim = CLOSE của nến đó, sai số 0,0000%** ⇒ sim **không** mô hình hoá spread/impact/độ trễ:
  "giá khớp" chính là giá nến. ⇒ **`SLIPPAGE_RATE` 0,30%/chân trong sim là HẰNG SỐ CỘNG THÊM, không phải
  một hiệu ứng được mô hình hoá.**
- Khác biệt ở **exit** là do sim thoát ở **giá trigger nội nến** (trailing/SL), không phải ở close — đây là
  **định nghĩa mức thoát**, **không phải** chi phí.

### 2.3 funding/leg — **THẬT, ĐO ĐƯỢC** (Aerospike, theo đúng cửa sổ giữ lệnh)
Cửa sổ = `(t_entry, t_exit]` (bản thể `[t_entry, t_exit)` cho kết quả gần như trùng: −0,2518 vs −0,2524%/lệnh).
Dấu quy ước **long**: `rate > 0` ⇒ **TRẢ**; `rate < 0` ⇒ **THU**.

| Tập | n | **THU** | **TRẢ** | = 0 | mean | median |
|---|---|---|---|---|---|---|
| Lệnh có ≥1 kỳ settle trong cửa sổ | **673 / 1089** | **31,8%** | **68,2%** | 0% | **−0,2518%/lệnh** | **+0,0109%** |
| Cả 1089 lệnh (không có kỳ settle ⇒ 0) | 1089 | **19,7%** | **42,1%** | 38,2% | **−0,1556%/lệnh** | — |
| **Sim** (cột funding suy từ `pnl`) | 1089 | 38,0% | 62,0% | 0% | **−0,1209%/lệnh** | +0,0000% |

- **Số kỳ settle/lệnh: mean 5,49 · max 169** (lệnh dài).
- **Lệch real − sim: mean −0,0562pp · median −0,0003pp · corr 0,805** ⇒ **sim tính funding gần đúng tốt**
  (tương quan mạnh, lệch trung vị ~0), hơi **bảo thủ** (real thu nhiều hơn sim ~0,06pp/lệnh).
- **Đọc đúng về DẤU:** funding **KHÔNG** phải "đa số lệnh được thu" — **68,2% lệnh TRẢ**. Nhưng **mean âm
  (thu ròng)** vì **một thiểu số lệnh dài được thu khoản lớn** (long ở coin có funding âm kéo dài). ⇒ Về
  *tổng*, funding là **+0,15…0,25%/lệnh thu ròng**; về *phần lớn lệnh*, funding là **chi phí nhỏ** (median ≈ 0).

### 2.4 Tỉ lệ khớp khi đặt LIMIT — **KHÔNG ĐO ĐƯỢC**
Không có trạng thái order ở sàn (242 store chỉ có `REQUEST`), không có `orderId`, không có `executedQty` ⇒
**không tính được** tỉ lệ khớp/hủy. Chỉ nêu **mốc lý thuyết đã công bố** từ `RESULT_EXECUTION_MAKER.md`:
hoà vốn `p*` = **0,47–0,99** (mô hình i.i.d., biên trên lạc quan) và **0,88–1,00** (adverse selection, biên dưới);
ở 2 mốc slip thực tế `p* = 0,96–0,99` ⇒ phải khớp **gần 100%** mới không mất gì so với taker.

### 2.5 Đối chiếu **gross → net** ở các mức chi phí (1089 lệnh, %/lệnh)

| Kịch bản | mean | median | win% |
|---|---|---|---|
| **S — sim hiện tại**: fee 0,80 + funding(sim) | **+4,5647** | +4,1758 | 88,0 |
| **E — fee sim 0,80 + funding(THẬT)** | **+4,5994** | +4,1774 | 88,0 |
| **D — fee taker 0,10 + slip 0 + funding(sim)** | +5,2647 | +4,8758 | 88,3 |
| **B — fee taker 0,10 + slip 0 + funding(THẬT)** | **+5,2994** | +4,8774 | 88,3 |
| **C — fee maker 0,04 + slip 0 + funding(THẬT)** | **+5,3594** | +4,9374 | 88,3 |
| **A — fee taker 0,10 + slip PROXY + funding(THẬT)** | **+1,9545** | +2,7232 | 77,7 |

- **Mức "biết chắc" (phí thật, slip = 0): Δ = +0,735pp (B−S) … +0,795pp (C−S)** ⇒ bằng đúng phần phí chênh
  (0,80 − 0,10 / 0,04). **win% gần như không đổi (88,0 → 88,3)** ⇒ **"chỉ đổi thang đo"**, không cải thiện chất
  lượng lệnh (khớp kết luận `RESULT_EXECUTION_MAKER.md` §0(3)).
- **Funding thật vs funding sim chỉ lệch +0,035pp/lệnh (E−S)** ⇒ **fix funding không tạo alpha**, chỉ sửa cho đúng dấu.
- **Nghịch lý quan trọng:** nếu thay slip phẳng 0,60% bằng **proxy biến động** (3,34% RT) thì net **GIẢM 2,61pp**
  (A−S). ⇒ Câu "sim đắt hơn thực" **chỉ đúng ở phần PHÍ** (0,20% → 0,04–0,10%). **Với SLIP thì chưa kết luận
  được chiều nào**: nếu slip thật ≈ proxy thì sim lại **rẻ hơn** thực tế.

**Theo nhóm `level`** (net %/lệnh — không nhóm nào đổi dấu ở 2 mức chi phí biết chắc):

| level | n | sim | fee thật, slip=0 | fee thật + slip proxy |
|---|---|---|---|---|
| `PREDICT_SYMBOL_TRADE` (selector) | 821 | +3,569 | **+4,264** | +2,072 |
| `BIG_DOWN` | 248 | +4,028 | **+4,733** | **−1,337** |
| `DCA_LEVEL1` | 20 | +52,088 | **+54,811** | +37,939 |

---

## 3. TRẢ LỜI CÂU HỎI OWNER + GIỚI HẠN

**"Dùng LIMIT thay MARKET + check funding THỰC ⇒ có thể lật nhiều hướng NULL thành alpha?"**
- **Funding thật:** đã đo (§2.3) — **sửa dấu đúng nhưng biên độ nhỏ** (+0,035pp/lệnh so với sim). **Không lật được gì.**
- **LIMIT thay MARKET:** **không đo được tỉ lệ khớp** (không có dữ liệu order ở sàn) ⇒ **không thể kết luận**.
  Mốc lý thuyết cho thấy cần khớp 0,96–1,00 mới trung tính ⇒ **chưa có cơ sở đề xuất chuyển sang limit**.
- **Hạ phí:** có cơ sở **về kỹ thuật thước đo** (sim đắt 2–4× ở phần phí), nhưng **KHÔNG có cơ sở để lật kết quả**:
  nhóm SIM-based đã dương đậm (`c*` +1,77…+52,9%); nhóm SCREENING âm vì **`c* < 0` do slip×turnover**, hạ phí vô nghiệm;
  và mốc slip proxy (bằng chứng duy nhất về khớp lệnh) lại **lớn**, tức đi **ngược** hướng cần.

**Giới hạn (nói rõ mức độ thiếu):**
1. **Không có fill thật** ⇒ `fee` và `slip` **không hiệu chỉnh được**. Cần: ghi `orderId` + `commission` +
   `executedQty` + `trạng thái order` từ sàn vào log (việc sửa code = **ngoài phạm vi** lần này, phải pre-reg riêng).
2. **Proxy slip là biến động, không phải tác động** — không được dùng làm "slip thực".
3. Mọi con số đo trên **1089 lệnh của MỘT run** (`X1_GS_T170_2021`) ⇒ có **selection bias**; không suy ra universe.
4. Đổi model chi phí = **đổi thước đo** ⇒ mọi "lật" (nếu có ở Phase D) là **POST-HOC**, phải **forward** mới tính là alpha.
5. **Phase C/D/E chưa làm** (đúng phạm vi: "LẬP KẾ HOẠCH + Phase A/B").

---

## 4. SẢN PHẨM

| File | Nội dung |
|---|---|
| `docs/audit/PLAN_COST_AUDIT_REAUDIT.md` | kế hoạch (viết trước khi đo) |
| `docs/result/RESULT_COST_REAL_AUDIT.md` | file này — Phase A + Phase B |
| `research/analysis/cost_real_audit.py` | script tái tạo (thuần Python, chỉ đọc) |
| `/tmp/cost_real_audit/` | `report_cost_real.txt`, `summary.json`, `legs_cost.csv`, `inventory_printdone.csv` — **dọn sau commit** |
