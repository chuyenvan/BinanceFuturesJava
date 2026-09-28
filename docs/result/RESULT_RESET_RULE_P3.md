# RESULT_RESET_RULE_P3 — ĐỘ BỀN ỨNG VIÊN `R4` (D5, 4 test: jackknife · bootstrap · DSR · placebo)

Ngày: **2026-09-29** (`PLAN_OPENCLAW_BASELINE_RESET_20260928.md` §Phase 3 + `PLAN_OPENCLAW_ADDENDUM_20260928.md` §D5).
Pre-reg: **`docs/prereg/PREREG_RESET_RULE_P3.md`** (**commit `6119188`**, chốt **TRƯỚC**; sau đó **không sửa tiêu chí**).
Đối tượng: **`R4`** (`p2-r4-base` / `p2-r4-stress`) vs **`B*` = `R0`** (`p2-r0-base` / `p2-r0-stress`), theo `RESULT_RESET_RULE_P2.md` (`47a9d90`).
Công cụ: `research/analysis/reset_rule_p3.py` (dùng lại `reset_rule_score.py` + `research/exitfit/exit_engine.py`).
JSON: `docs/result/reset_rule_p3.json`.

**Tuân thủ:** **0 sim Java / 0 train** · thuần Python offline trên Oracle · **DEV ≤ 2025-12-31** · **KHÔNG chạm 2026** ·
không sửa Java · không chạm production/`242`/ONNX/LIVE · không push dữ liệu · `nice -n 10` · output tool nhỏ.

---

## 0. KẾT LUẬN (đọc trước)

| test | `R4` @base | @stress | số chính |
|---|---|---|---|
| **T1 episode jackknife** | **FAIL** | **FAIL** | bỏ top-3/top-5: `ΣPnL_còn` `46 502`/`40 958` (>0) **NHƯNG** `Calmar_còn(3)` **2,70** < `B*` **4,15** |
| **T2 bootstrap cụm episode** | PASS | PASS | CI `Calmar` `R4` **[2,28; 20,34]** (>0) · **CI chênh `R4−B*` `[−30,45; +3,95]` CHỨA 0** (điểm **−9,52**) |
| **T3 DSR** | PASS | PASS | `DSR(N_eff 1,27)=1,000` · `DSR(N=5)=0,999`; (tại `N=50` 0,935 · `N=200` 0,794) |
| **T4 placebo (cùng phút, coin ngẫu nhiên)** | PASS | (=) | THẬT **+3,29 %/leg** vs P1 **+1,72 %/leg**; chênh **+1,56 pp** CI95 **[+0,81; +2,39] pp** (ngoài 0) |

**`R4` KHÔNG xứng đáng lên Phase 4 ⇒ TRẢ VỀ GIỮ `B*`.** Lý do dứt khoát: theo **LUẬT KẾT LUẬN** đã chốt ("lên Phase 4 ⇔
PASS **CẢ 4** test @base"), `R4` **FAIL T1**; và ở T2 **CI chênh `R4−B*` chứa 0** trong khi **chênh `CAGR` = `−5,62 pp`,
CI `[−9,41; −2,34]` (âm, NGOÀI 0)** + **chênh `ΣPnL` = `−21 510`, CI `[−35 252; −8 499]`** ⇒ bằng chứng nói **`R4` ≤ `B*`**,
không phải "biên mỏng nhưng dương". `R4` vẫn **bền một mình** (T2/T3/T4) và **hơn placebo rõ** (T4), nhưng **không hơn `B*`**.

---

## 1. BƯỚC 0 — CỔNG HỢP LỆ (PASS hết)

| kiểm | kết quả |
|---|---|
| Artifact | `p2-r4-{base,stress}` n `2027`, eq `104 489`/`103 351`; `p2-r0-{base,stress}` n `1086`, eq `126 108`/`124 685` — **khớp `RESULT_RESET_RULE_P2`** |
| Cấu trúc leg `R4` base = stress | `PREDICT_SYMBOL_TRADE 1745 · BIG_DOWN 248 · DCA_LEVEL1 34` (**byte-giống**) |
| **Harness thoát (cho T4)** | `python3 research/exitfit/parity.py` → **`VERDICT: PASS`** (status 100 %, phút thoát 100 %, priceTP 99,82 %, \|ΔPnL\| ≤ 1 USDT 100 %) |
| 0 đọc 2026 | mọi ngày đọc ≤ `20251230`; placebo quét `first-seen` `2021-06-01..2025-12-01` |

---

## 2. T1 — EPISODE JACKKNIFE (FAIL)

Episode = ngày-vào liên tiếp cách **≤ 2 ngày trống**. Top-k = k episode PnL **lớn nhất**. `ΣPnL_còn`/`Calmar_còn`
theo đường equity dựng lại `35000 + cumΣPnL_còn` (maxDD ngày). Tiêu chí chốt: **PASS ⇔ bỏ top-3 & top-5 đều `ΣPnL_còn>0`
VÀ `Calmar_còn(3) ≥ B*`**.

| arm | n_ep | top-1 % | top-3 % | top-5 % | top-10 % | `ΣPnL_còn(3)` | `Calmar_còn(3)` | maxDD % | `ΣPnL_còn(5)` | `Calmar_còn(5)` |
|---|---|---|---|---|---|---|---|---|---|---|
| **R4** base | 93 | 17,3 | 33,1 | 41,1 | 57,3 | **46 502** | **2,70** | −7,67 | **40 958** | 2,30 |
| **R4** stress | 93 | 17,3 | 33,2 | 41,2 | 57,5 | 45 666 | 2,66 | −7,67 | 40 193 | 2,26 |
| **B*** base | 80 | 15,1 | 31,9 | 41,0 | 54,3 | **62 025** | **4,15** | −6,13 | 53 735 | 3,61 |
| **B*** stress | 80 | 15,1 | 32,0 | 41,1 | 54,5 | 60 987 | 4,07 | −6,17 | 52 799 | 3,54 |

**Đọc:** `R4` **bền một mình** — bỏ tới **top-5** (41 % lãi) vẫn còn `+40 958` (top-10 còn `+29 678`, Calmar 1,54); `@stress`
gần như y hệt. **NHƯNG** `Calmar_còn(3)` của `R4` **2,70 < `B*` 4,15** (và `Calmar_còn(1)` 3,54 < 5,13) ⇒ **FAIL** đúng
vế so `B*` của tiêu chí. `R4` rải đều hơn (`ne 93` vs `80`; `top-1 %` 17,3 vs 15,1) nhưng **kém hiệu quả trên Calmar còn lại**.

## 3. T2 — BOOTSTRAP CỤM EPISODE (5000 rep, seed `20260928`) — PASS, nhưng biên `R4−B*` là NHIỄU

**(a) Đơn đối tượng** (khối = episode + khoảng trống; `CAGR=(35000+ΣPnL)↑(365,25/Σngày)`; `Calmar=CAGR/|maxDD|` đường dựng lại):

| arm | `ΣPnL` CI95 | `CAGR` CI95 | `Calmar` CI95 | P(ΣPnL≤0) |
|---|---|---|---|---|
| **R4** base | [41 250; 103 261] | [18,4; 39,0] | **[2,28; 20,34]** (tb 7,75) | **0,000** |
| **R4** stress | [40 478; 101 686] | [18,1; 38,7] | [2,23; 19,82] (tb 7,58) | 0,000 |
| **B*** base | [59 477; 131 751] | [23,4; 46,6] | [4,84; 34,69] (tb 14,90) | 0,000 |
| **B*** stress | [58 490; 129 684] | [23,1; 46,2] | [4,77; 33,79] (tb 14,48) | 0,000 |

⇒ `R4` **CI `Calmar` KHÔNG chứa 0** ⇒ **PASS T2** (biên không phải 0).

**(b) Paired trên lưới khối CHUNG** (`K=93`, cùng chỉ số rút cho cả 2 arm):

| cost | chênh `Calmar` `R4−B*` | chứa 0? | chênh `CAGR` (pp) | chênh `ΣPnL` |
|---|---|---|---|---|
| base | **−9,52** CI **[−30,45; +3,95]** | **CÓ** | **−5,62** CI [−9,41; −2,34] | **−21 510** CI [−35 252; −8 499] |
| stress | −9,24 CI [−29,56; +3,76] | CÓ | −5,59 CI [−9,39; −2,31] | −21 154 CI [−34 632; −8 321] |

**AMENDMENT 1** (post-hoc, chỉ để đọc — phát hiện `Calmar`-theo-bootstrap bị **bất ổn định**: `maxDD→0` làm `Calmar` nổ):
dựng đường xếp theo **chỉ số khối GỐC** ⇒ chênh `Calmar` base `−2,30` CI `[−12,75; +4,58]` (vẫn **chứa 0**).
⇒ **Trả lời câu (2): biên `+0,7…0,95 %` KHÔNG sống qua bootstrap — CI chênh `R4−B*` CHỨA 0 và điểm ÂM ⇒ đây là NHIỄU
(không những thế, `CAGR` và `ΣPnL` của `R4` còn THẤP hơn `B*` NGOÀI CI).**

## 4. T3 — DSR (V[SR] từ 236 run DEV cùng cửa sổ) — PASS tại `N` khoá trước

Pool `236` run (`20210701..20251230`, ≥1640 điểm, gộp run trùng). `V[SR]=1,03e-3`; `ρ̄=0,785` ⇒ **`N_eff = 1,3`**
(các run DEV tương quan cao). `R4` `SR_ngày 0,1074` (≈ **2,05** năm).

| đối tượng | `N=5` | `N=10` | `N=50` | `N=200` | `N=448` | `N_eff 1,27` | PSR(SR0=0) |
|---|---|---|---|---|---|---|---|
| **R4** base | **0,999** | 0,994 | 0,935 | 0,794 | 0,678 | **1,000** | 1,000 |
| **B*** base | 0,999 | 0,997 | 0,950 | 0,820 | 0,704 | 1,000 | 1,000 |

**PASS T3** theo ngưỡng đã chốt (`DSR ≥ 0,95` ở **cả** `N_eff` và `N=5`). **Cảnh báo:** `N=5` là số arm **khoá trước**
của Phase 2; nếu tính đa dựng-giả của **toàn bộ không gian DEV** (`N≥50`) thì `DSR` **< 0,95** ⇒ kết luận T3 ĐÚNG trong
khung `k=5`, KHÔNG bảo chứng "đã chống dredging toàn cục".

## 5. T4 — PLACEBO "CÙNG PHÚT VÀO, COIN NGẪU NHIÊN" — PASS

`1745` leg `PREDICT_SYMBOL_TRADE` của `R4` @base; `227 339` lần replay `exit_engine.simulate` (parity PASS). Universe đủ
điều kiện tại `t0`: có nến đúng phút, niêm yết ≥30 ngày, không đang được `R4` giữ; `D=200` rút/leg, seed `20260928`.
Đo 1-leg: `entry=close(t0)`, `qty=margin/entry`, `net = (tp−entry)/entry − f`.

| mức | THẬT (net/leg) | P1 placebo | chênh | CI95 (block-72h, 2000 rep, `nb=89`) |
|---|---|---|---|---|
| **f=0,006** | **+3,29 %** (0,03286) | **+1,72 %** (0,01723) | **+1,56 pp** | **[+0,81; +2,39] pp** — **ngoài 0** |
| f=0,008 | +3,09 % | +1,52 % | +1,56 pp | (chênh KHÔNG đổi — cùng dịch phí) |

Phân bố trạng thái: THẬT **87,2 % `TRAIL`** / 12,7 % `TS168`; P1 **71,3 % `TRAIL`** / 27,4 % `TS168` / 0,6 % `OPEN_AT_END`.
⇒ **PASS T4**: chọn-coin-tại-phút-vào của `R4` có **giá trị thật** (+1,56 pp/leg net, ngoài CI) so với **cùng phút
nhưng coin ngẫu nhiên**. (Chỉ chạy `@base`; chênh bất biến phí nên `@stress` = cùng chênh.)

---

## 6. TRẢ LỜI CÂU HỎI (bắt buộc)

1. **`R4` có bền không?** **BỀN MỘT MÌNH, NHƯNG KHÔNG HƠN `B*`.** T1 **FAIL** (chỉ vế "Calmar_còn ≥ `B*`": 2,70 < 4,15;
   vế "ΣPnL_còn>0" thì PASS). T2 **PASS** (CI `Calmar` [2,28; 20,34] > 0). T3 **PASS** (DSR 0,999–1,000 ở `N=5`/`N_eff`).
   T4 **PASS** (+1,56 pp/leg so placebo).
2. **Biên `Calmar +0,7…0,95 %` có sống?** **KHÔNG — là NHIỄU.** CI chênh `R4−B*` `Calmar` **[−30,45; +3,95] CHỨA 0**,
   điểm **ÂM (−9,52)**; và chênh `CAGR` **−5,62 pp** CI **[−9,41; −2,34]** + chênh `ΣPnL` **−21 510** CI **[−35 252; −8 499]**
   đều **ÂM ngoài 0** ⇒ bootstrap không xác nhận `R4 > B*`; nếu có thì **`B* > R4`**.
3. **`R4` hơn placebo?** **CÓ.** THẬT +3,29 %/leg vs placebo +1,72 %/leg, chênh **+1,56 pp** CI **[+0,81; +2,39]** (ngoài 0).
4. **Có xứng đáng lên Phase 4 (holdout 2026)?** **KHÔNG — TRẢ VỀ GIỮ `B*`.** (a) LUẬT: lên Phase 4 ⇔ PASS cả 4 ⇒ `R4`
   FAIL T1; (b) biên `R4>B*` là nhiễu và **nghiêng về `B*`**; (c) `R4` còn gắn **`gate 1.55` nới nhẹ** (vùng D2 cảnh báo).
   `R4` không "tệ" (bền + hơn placebo) nhưng **không hơn incumbent** ⇒ **không đáng tiêu 1 slot holdout 2026 một lần**.

**MỤC NÀO BỎ + LÝ DO:**
- **BỎ `R4`** khỏi vị trí ứng viên Phase 4: T1 FAIL (Calmar_còn < `B*`) + T2 chênh vs `B*` chứa 0 / CAGR&ΣPnL âm ngoài CI.
- **BỎ thành phần `gate 1.55`** (nới nhẹ) của `R4`: không tạo được superiority đo được; giữ `gate 1.70` của `B*`.
- **GIỮ `B*`** (`R0`) làm incumbent; **KHÔNG tiêu `HOLDOUT_UNSEAL`** ở lượt này.
- **KHÔNG bỏ** kết luận T3 của T1/T2 (chúng đo đúng cái tên của chúng); **bỏ** việc dùng "Calmar-bootstrap" như thước
  chính (bất ổn định — xem AMENDMENT 1); dùng `CAGR`/`ΣPnL`/`Calmar`-đường-gốc thay thế khi cần chốt.
- **GIỮ** kết quả T4 (+1,56 pp/leg) làm bằng chứng **dương** rằng coin-selection có giá trị — hữu ích cho hướng khác
  (không liên quan `R4`).

## 7. HẠN CHẾ (khai rõ)

1. **T1/T2 dùng đường equity dựng lại theo NGÀY** (không MTM phút) ⇒ `Calmar` khác định nghĩa `Calmar_MTM` ở P2/P3-tầng-4;
   dùng nhất quán cho cả `R4` và `B*` nên so sánh vẫn công bằng, nhưng KHÔNG so ngang được với `1,676/1,661` của P2.
2. **`Calmar`-theo-bootstrap bất ổn định** (`maxDD→0` ⇒ `Calmar` nổ tới >1000). Vì vậy **câu (2) chốt bằng `CAGR`/`ΣPnL`**
   (ổn định) và bằng CI chênh; AMENDMENT 1 (khối theo chỉ số gốc) là bản đã sửa độ bất ổn, vẫn **chứa 0**.
3. **T4 chỉ `@base`** (chênh bất biến theo phí); đo **1 leg đơn** (bỏ DCA/merge/funding) cho **cả** THẬT và P1 nên cùng một thước;
   `entry=close(t0)` (không mô phỏng trượt giá vào). `OPEN_AT_END` 0,1 %.
4. **T3** `N_eff=1,3` vì các run DEV tương quan cao (`ρ̄=0,785`) ⇒ `DSR` ở `N_eff` ≈ `PSR`; chỉ đọc được trong khung `k=5`.
5. Mọi số là **mô tả quá khứ DEV (≤ 2025-12-30)**, không phải cam kết forward; **chưa chạm HOLDOUT 2026**.

## 8. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
python3 research/analysis/reset_rule_p3.py t123 --json /home/ubuntu/rr_p3_t123.json   # ~3-5 phut (doc 236 sim.out cho DSR)
python3 research/analysis/reset_rule_p3.py t4 --draws 200 --workers 4 --json /home/ubuntu/rr_p3_t4.json  # ~35 phut (checkpoint /home/ubuntu/rr_p3_cache)
# T4 resume tu checkpoint; first-seen cache /home/ubuntu/rr_p3_first_seen.npy; nen 1m /home/ubuntu/kaggle_data_hpo/ticker_*.bin.gz
```

## 9. COMMIT

- Pre-reg: **`6119188`** (`docs/prereg/PREREG_RESET_RULE_P3.md`).
- Kết quả: commit này (`RESULT_RESET_RULE_P3.md` + `reset_rule_p3.json` + `research/analysis/reset_rule_p3.py`).
