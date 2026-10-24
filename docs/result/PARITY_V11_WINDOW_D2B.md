# PARITY v1.1 — lượt D2B: 10-23 phần offline, sửa CTL, nhãn ADDENDUM 2 cho 3 ngày

- **Thước:**
  - prereg `481701b2`;
  - ADDENDUM 1 `fea9fb97`;
  - **ADDENDUM 2 `4eef2788`**: chính thức cho 10-23, chỉ để relabel cho 10-21 và 10-22;
  - ADDENDUM 3 `67ce404a`: áp từ 10-24, ở đây chỉ báo kèm.
- **Dữ liệu:** `pull242/2026-10-23` (COMPLETE) và Vision daily 10-23. Lượt chấm do MASTER chạy (`run_day.sh 2026-10-23`, xong 2026-10-24T14:41Z).
- **Code:**
  - sửa CTL: `fe35f218` (commit A);
  - nhãn ADD2: `py/day_kpp.py`;
  - kiểm lại S1-I D1: `py/s1i_legacy_d1.py`;
  - kiểm ngoài parity: `py/died_bt_check.py`.
- **An toàn:** không chạm 242, không gọi Aerospike, không gọi Binance REST.

## 0. Kết luận (risk-first)

| ngày UTC | verdict trong sổ | căn cứ |
|---|---|---|
| **2026-10-23** | **XÁM** (bản gốc d2b ghi TRƯỢT, đã sửa vì lỗi chấm CTL ở §1) | P1, P2, P3, TSX, S1-I, GV-I, CTL **đều ĐẠT**. **K5″ = 3 phút** (ADD2 chính thức): 07:59, 12:48, 22:14 (+07) |
| 2026-10-22 | **XÁM** (giữ nguyên theo ADD2) | relabel hậu kiểm theo ADD2 cho K5″ = 164 |
| 2026-10-21 | **ĐẠT** (giữ nguyên theo D1 ADD1) | relabel hậu kiểm theo ADD2 cho K5″ = 67 |

Rủi ro, xếp theo mức độ:

1. **P2 lần đầu bị thử thật ở 10-23, và đạt.**
   - Có 25 cặp pass live và 25 cặp pass offline, **0 lật, 0 lật nặng**.
   - 28 cặp r/q ≥ 0,9 ở live và 28 ở offline. Max r/q 1,6572306 (live) / 1,6572309 (offline).
   - `[GATE] n_pass` khớp 1440/1440 phút (Σ 25 = 25).
2. **CTL "TRƯỢT" trong bản d2b gốc là lỗi của code chấm** (§1). Sau khi sửa, CTL ĐẠT; số của D1 và 10-22 **không đổi**.
3. **K5″ = 3 ở 10-23.** Cả ba là phút lệch 12 feature ở mức thị trường, nằm trong cửa sổ `[LIVE-KLINE]` có ghi đè (226 / 67 / 241). Ứng viên trực tiếp là nến chưa settle tại thời điểm quyết định; cơ chế cụ thể **CHƯA GIẢI THÍCH**, vì phép thay nến (b) không tái lập được (xem §3).
   - 07:59 rơi đúng 3′ sau restart 07:55:42.
   - Cần log theo từng symbol (ADD2 mục 3, việc C14 của v1.2) thì mới kiểm được.
4. **K1″ được gán nhưng bằng chứng yếu (không duy nhất).** Mọi phút K1″ đều có từ 14 đến 98 phương án "bỏ 1 nến" cùng tái lập được giá trị live trong dung sai. ADD2 không đòi tính duy nhất, nên nhãn hợp lệ theo chữ, nhưng **không định danh được symbol**.
5. **Mâu thuẫn trong chữ của ADD2, đã xử bằng ADD3 cho các ngày sau.** Đọc đúng chữ, nhánh score-only của K6′ không thể đạt, nên:
   - 10-21 còn 60 phút K5″ ở S1-V, 10-22 còn 161 phút;
   - đọc theo ADD3 thì cả hai ngày về 0 ở S1-V.
6. **Ngoài parity (§5): sim X14 giao dịch trên symbol mà live coi là DIED.**
   - Chiếm 20,3 % số leg và 17,7 % PnL của DEV 2022–25.
   - Gần như toàn bộ là coin đã bị huỷ niêm yết từ trước, nên không phải lệch live/BT ở hiện tại.
   - Chỉ **POWRUSDT** vẫn còn giao dịch: live không bao giờ vào lệnh, sim có 3–4 leg (PnL ≈ 0).

## 1. Nguyên nhân CTL TRƯỢT ở 10-23 (gốc) và cách sửa (commit A `fe35f218`)

| | gốc (d2b MASTER) | sửa |
|---|---|---|
| gate 33 cột (OFF-NEW2 vs OFF-BT) | 1440/1440 bit | không đổi |
| Tool1 nonfund `rows_tol_nonfund` | **0,99750** (123 dòng lệch) | **1,0** |
| cột lệch | `cand` 123 dòng; `f3` 2664 dòng (chỉ bit cuối, như D1 và 10-22) | `f3` 2664 dòng (bit); `cand_flag_diff`: 123 dòng, 1 symbol, 123 phút (báo riêng) |
| CTL | TRƯỢT | **ĐẠT** |

**Bằng chứng:**
- **Phạm vi lệch:**
  - Chỉ có POWRUSDT, đúng 1 dòng/phút trong 123 phút, từ 10-23 21:06 đến 10-24 06:54 (+07).
  - BT ghi `cand=1`, NEW2 ghi `cand=0`.
  - Trên chính 123 dòng này, **f0..f44 đều khớp dung sai**.
- **Cơ chế:**
  - POWRUSDT nằm trong `DIED_SYMBOLS` (143 symbol) của config harness.
  - Đường BT (`fund(ts, null, …)`) lấy tập ứng viên từ `EntrySignalFilter.selectCoins`, và hàm này **không lọc DIED**.
  - Đường NEW2 = đường live (`fin`) **có lọc DIED**, nên POWR được tính qua nhánh "extra": cùng nến, cùng feature, nhưng `cand=0`.
  - POWR qua `selectCoins` 123 phút ở 10-23, 0 phút ở 10-22 và D1, vì vậy lỗi chỉ lộ ra hôm nay.
- **Vì sao là lỗi chấm:** `cand` là cột ghi chú, không thuộc "Tool1 #1–40" mà prereg dùng cho CTL. `cmp_runs.py` đã tính nhầm cột này vào phép kiểm nonfund.
- **Đã loại trừ:**
  - Sai jar: không thể, vì CTL so offline với offline, cùng jar `eea5adec`.
  - Restart 07:55:42 và 09:37:31: lệch bắt đầu từ 21:06 và chỉ dính 1 symbol.
  - Buffer chụp ngày 10-24: buffer không tham gia CTL.
- **Ảnh hưởng tới quyết định: không có.** Live psym 10-23 có 0 dòng POWR; `join_fund` (live vs BT) có 0 dòng POWR; FUND/NET/GV-O/P2 không bị chạm. Không có lệnh hay paper leg nào khác.
- **Regression:** chạy lại cmp cho D1 và 10-22, mọi giá trị **trùng hệt**. D1 chỉ khác chuỗi đường dẫn `ref/new`; file D1 gốc đã khôi phục. `cand_flag_diff` = 0 ở cả hai ngày. Mọi số P* của D1/D2 không đổi.

## 2. Bảng chính 10-23 (sau sửa)

| mã | ngưỡng | 10-23 |
|---|---|---|
| **P1** | median ≤ 1e-4 **và** ≥ 98 % ≤ 1e-3 | median 7,11e-10; 99,861 %; max 7,41e-3 ⇒ **ĐẠT** |
| P1-m | 100 % | 100 % (max 5,21e-7) |
| P1-F / MD | báo cáo | 1435/1440 / 99,79 · 99,79 · 99,65 % |
| FUND / NET | báo cáo | 99,639 % dòng (49 080) / 99,969 %, max \|Δ\| 0,0123 |
| **S1-I** / S1-m | 100 % | 1440/1440 / max 0 |
| S1-V | báo cáo | f2 99,918 %, f5 99,883 %, score 99,998 %; top-24 trùng thứ tự 1440/1440 |
| **GV-I** / GV-O | 100 % / báo cáo | 34 560/34 560 / 99,974 % (9 dòng) |
| **P2** | lật nặng = 0 | 34 560 cặp; pass 25 / 25; **0 lật**; 28 / 28 cặp ≥ 0,9; 41 cặp ≥ 0,8; q_live: log 1350 phút + replay trước restart 90 phút ⇒ **ĐẠT** (thử thật) |
| `[GATE] n_pass` | báo cáo | 1440/1440 (Σ 25 = 25) |
| **P3** | mọi giờ ≤ 1e-6 | 24/24 (max 6,35e-10) ⇒ **ĐẠT** |
| **TSX** | cờ trùng | OFF = OFF; ΔS_10-23 6,3e-9 (days64) / 1,1e-16 (days32) ⇒ **ĐẠT** |
| **CTL** | 100 % | **ĐẠT** (sau sửa) |

## 3. Nhãn ADDENDUM 2 (`kpp_<ngày>.json`)

### 3.1 Cách thực thi

**K1″ cần hai điều kiện:**
- (a) Phút nằm trong [W_start − 20′, W_end + 10′] của một cửa sổ `[LIVE-KLINE]` có `reread_overwritten > 0`.
- (b) Phép thay nến tái lập được giá trị live. Oracle không có nến live, nên họ phép thay nến làm được là: **bỏ đúng 1 nến khả dụng (s, X)** với X trong khoảng (a) và X ≤ M. Đây là cơ chế H2 của D1 ADD1 §7.1.
  - Tính lại `rateDown15MAvg` **độc lập** bằng float32, theo đúng logic của jar.
  - Kiểm hợp lệ trước: bản tính lại khớp bit với OFF-BT trên **1386/1386** (D1), **1440/1440** (10-22), **1440/1440** (10-23).
  - Đạt khi khớp live trong `1e-6·(1+|b|)` **và** `momentumAcceleration` cũng khớp.
  - Chỉ áp được cho phút mà mọi lệch đều đi qua kênh momentum15M, gồm: gate `momentum15M` / `momentumAcceleration`; MD `rateDown15MAvg`; FUND cột `f5` (bản sao mức thị trường); NET / GV-O / P1 là hệ quả.

**K6′:** top-24 phải trùng **tập và thứ tự** (thực tế 100 % mọi giờ ở cả 3 ngày). Thêm một trong ba điều kiện:
- hoán đổi kề (|Δhạng| = 1/n);
- tie-split (|Δhạng| = 0,5/n) với đối tác có |Δv| ≤ max(1e-6·|v|, 1e-7);
- score-only: đọc **đúng chữ** ADD2 là |Δscore| ≤ max(1e-6·|score|, 1e-7).

K2 và K3′ giữ nguyên kết quả của ADD1.

### 3.2 Kết quả

| | **10-23 (chính thức ADD2)** | 10-22 (relabel hậu kiểm) | 10-21 (relabel hậu kiểm) |
|---|---|---|---|
| phút lệch | 704 | 572 | 604 |
| K1″ | 2 phút (22:23, 22:25; 70 / 14 phương án tái lập) | 6 phút (08:16, 08:28, 05:26, 05:28, 05:29, 05:30; 14–98 phương án mỗi phút) | 2 phút (17:16, 17:18; 14 / 42 phương án) |
| K6′ (S1-V) | 704 / 704 | 404 / 565 | 541 / 601 |
| **K5″ (ADD2 đúng chữ)** | **3** (07:59, 12:48, 22:14) | **164** = 3 phút mức thị trường (08:10, 05:14, 05:32) + 161 phút S1-V score-only | **67** = 7 phút mức thị trường (07:53, 11:59, 17:04, 17:37, 17:38, 17:40, 23:59) + 60 phút S1-V score-only |
| K5 nếu đọc theo ADD3 (mô tả) | 3 | 3 | 7 |
| \|Δscore\| score-only lớn nhất | 0 (không có dòng nào) | 0,00769 | 0,00403 |

**Lý do phút mức thị trường vẫn là K5:**
- Phút lệch **12 feature** (07:59, 12:48, 22:14 ở 10-23; 08:10, 05:14 ở 10-22; 11:59, 17:04, 23:59 ở 10-21): không có phép bỏ 1 nến nào tái lập được, nên (b) chưa được chứng minh.
- Phút chỉ lệch 15′ nhưng **ngoài khoảng (a)**: 05:32 ở 10-22 (cửa sổ kết thúc 05:21, 05:32 > 05:31); 17:37–17:40 ở 10-21.
- 10-21 07:53 là phút warm-up sau restart, không có cửa sổ.

## 4. Kiểm lại S1-I D1 với LEGACY đúng (ADD2 mục 4)

- LEGACY đọc từ log: `[LEGACY] managed 44` (8681 dòng log; dùng dòng gần nhất ≤ ts + 2′). Kết quả S1-I: **1387/1387**.
- Có 0 phút mà symbol legacy lọt top-24 thô. Vì vậy tập LEGACY rỗng trong D1 gốc **không làm đổi** kết quả S1-I của D1.
- Artefact: `s1i_legacy_d1.json`.

## 5. Ngoài parity: sim X14 có lọc `DIED_SYMBOLS` không? (`died_bt_check.json`)

**Code:**
- `SimulatorMarketLevelTicker1MStopLoss` chọn ứng viên qua `MarketBigChangeDetector.getTopSymbolArray` / `BdSelection`; các hàm này không kiểm `diedSymbol`.
- `MarketBigChangeDetector.calMarketData` có lọc `diedSymbol`, nhưng chỉ khi tính số đo thị trường.
- Tool1 / `EntrySignalFilter.selectCoins` không lọc.
- Live (`DetectEntrySignal2TradeNormal`) có lọc.

**Cấu hình:**
- Mọi sim (`~/kaggle_sim/out/*`, cùng `src/config.properties`) dùng `DIED_SYMBOLS=BTCDOM,USDC`. Đây là chủ ý: comment config ghi "đổi = skip ~100 coin có data = survivorship bias".
- Live (theo config harness) dùng danh sách **143 symbol**.

**Mẫu 10-23:** POWRUSDT qua `selectCoins` 123 phút ở BT, nhưng có 0 dòng trong psym live.

**Định lượng DEV 2022–25 (7 seed `tsx-x14-s*`):**

| chỉ số | giá trị |
|---|---|
| leg trên symbol thuộc DIED của live | trung bình **20,3 %** số leg (586–618 trên 2900–3034 leg mỗi seed; 104–107 symbol) |
| PnL trên symbol thuộc DIED của live | **17,7 %** PnL |
| symbol DIED của live **vẫn còn giao dịch** ngày 10-23 | chỉ POWRUSDT |
| leg / PnL trên POWRUSDT | 3–4 leg mỗi seed (0,13 %); PnL ≈ 0 (−0,01 %) |

**Diễn giải:** gần như toàn bộ 20 % là coin đã bị huỷ niêm yết sau khi được giao dịch hợp lệ. Sim đưa chúng vào là đúng mục đích chống survivorship bias, và live hiện cũng không thể giao dịch chúng. Lệch thực tế giữa live và BT ở hiện tại chỉ còn POWR, ảnh hưởng không đáng kể.

**Rủi ro cần MASTER cân nhắc:** danh sách DIED của live có thể chứa symbol **vẫn còn giao dịch** (như POWR). Live sẽ bỏ qua những symbol này, còn BT thì không. Hiện tại ảnh hưởng ≈ 0, nhưng nên rà lại danh sách định kỳ. Báo cáo, không sửa.

## 6. Tích luỹ cửa sổ (10-21 → 10-23)

| | 10-21 | 10-22 | 10-23 | tổng |
|---|---|---|---|---|
| verdict trong sổ | ĐẠT | XÁM | **XÁM** | 0 ngày TRƯỢT |
| P2 cặp (đủ hai phía) | 33 264 | 34 560 | 34 560 | **102 384** |
| cặp r/q ≥ 0,9 (live / off) | 0 / 0 | 0 / 0 | 28 / 28 | **28 / 28** |
| cặp r/q ≥ 0,8 (live / off) | 6 / 6 | 0 / 0 | 41 / 41 | **47 / 47** |
| lật / lật nặng | 0 / 0 | 0 / 0 | 0 / 0 | **0 / 0** |
| P3 giờ ĐẠT | 24/24 | 24/24 | 24/24 | 72/72 |
| CTL | ĐẠT | ĐẠT | ĐẠT (sau sửa) | |
| K5″ (ADD2 đúng chữ) | 67 (hậu kiểm) | 164 (hậu kiểm) | **3** | |

## 7. Artefact

- `docs/result/parity_v11_d2b/parity_v11_d2b.json`: verdict sau sửa. Bản gốc của MASTER giữ ở `parity_v11_d2b_orig_truot.json`.
- `docs/result/parity_v11_d2b/2026-10-23/`: các JSON của ngày; `orig_d2b/cmp_ctl_*` là bản gốc trước sửa.
- `docs/result/parity_v11_d2b/kpp/`: `kpp_d1.json`, `kpp_20261022.json`, `kpp_20261023.json`.
- `docs/result/parity_v11_d2b/s1i_legacy_d1.json`, `docs/result/parity_v11_d2b/died_bt_check.json`.
