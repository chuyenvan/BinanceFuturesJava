# RESULT_BD_CHAIN_CHAIN2 — xác minh "IC +50%" + dây chuyền đầy đủ cho biến thể `rateDown15MAvg` theo `f`

Chạy 2026-10-01 (subagent "BD-CHAIN 2"), nhánh `module`. Nền: `docs/result/RESULT_BD_CHAIN.md`
(commit `34695307`) + `docs/prereg/PREREG_BD_CHAIN.md`. **0-SIM THUẦN PYTHON** cho NHIỆM VỤ A
(KHÔNG Java, KHÔNG sim, KHÔNG xgboost, KHÔNG đọc/chạm 2026). **DEV ≤ 2025-12-31**; 2026 = HOLDOUT.
Script: `research/analysis/bd_chain2_ic.py`, `bd_chain2_ic72.py`, `bd_chain2_ic_ci.py`.
JSON kèm: `RESULT_BD_CHAIN_CHAIN2.json` (+ `research/analysis/out/bd_chain2_ic*.json`).

---

## 0. KẾT QUẢ CHỐT (đọc trước)

> ### ⛔ NHIỆM VỤ A = **NULL** — KHÔNG có nguồn "IC +50%", và đo lại IC **KHÔNG tăng +50%**.
> ### ⛔ NHIỆM VỤ B **KHÔNG CHẠY** (đúng luật task: "A = NULL ⇒ DỪNG nhiệm vụ B").
> ### ⇒ **NO-GO** — giữ `f = 0` (N=100). **Tiết kiệm trọn vòng Kaggle (0 kernel).**

| câu hỏi | trả lời |
|---|---|
| Nguồn "IC tăng 50 %" trong `docs/` + `research/analysis/out/` + `git log`? | **KHÔNG CÓ** cho biến thể `rateDown15MAvg`-theo-`f` (xem §1) |
| Đo lại rank-IC (0-sim)? | **CÓ** — 2 định nghĩa nhãn độc lập (§2) |
| IC có tăng +50 % không? | **KHÔNG.** vs nhãn GATE: **|IC| GIẢM 17–25 %** (ngoài CI). vs nhãn 72h: |IC| tăng **3–38 %** (CI chồng lấn) — không nhất quán, không +50 % |
| Dây chuyền đầy đủ (Kernel C/D) chạy được không? | **KHÔNG chạy** (luật: A=NULL ⇒ DỪNG B). Kernel C vẫn `CODE_READY_NOT_RUN`; Kernel D vẫn chưa viết |
| `f` nào qua 4 tầng? | **Không đo** (B NOT-RUN) ⇒ **không `f` nào được đề xuất** |

---

## 1. KIỂM CHỨNG NGUỒN "IC +50 %" (NHIỆM VỤ A.1)

**Phạm vi đã quét:** `docs/**/*.md`, `docs/prereg/*`, `research/analysis/out/*.json`, `git log --all`
(1 572 commit, cả `--grep`).

**(a) KHÔNG có nguồn nào phát biểu biến thể `rateDown15MAvg`-theo-tỷ-lệ-universe `f` làm IC tăng.**
- `RESULT_BD_DEEP` (dạo sâu `rateDown15MAvg`) **không** báo IC nào cho biến thể `N`/`cửa sổ`/`định nghĩa`
  — chỉ báo Jaccard/tần suất ON ⇒ **NO-GO, "chưa có bằng chứng PnL"**.
- `RESULT_BD_CHAIN` (commit `34695307`) **KHÔNG** đo IC; chỉ có bảng phụ lục **rule-path** (không đăng ký)
  và kết luận BLOCKED tại cổng parity.
- Commit `60b7c995` ("BD-FRACTION") **KHÔNG TỒN TẠI** (`git cat-file -t 60b7c995` ⇒ *Not a valid object*),
  đúng như `PREREG_BD_CHAIN` đã cảnh báo.
- Không có `*.json` nào trong `research/analysis/out/` chứa IC gắn với `rateDown15MAvg`/`momentum15M`
  (chỉ `bd_deep_dist.json` có phân bố, không có IC).

**(b) Nguồn duy nhất có cụm "+50 % IC" là một THÍ NGHIỆM KHÁC — dễ nhầm:**
| nguồn | nội dung | vì sao KHÁC |
|---|---|---|
| `docs/result/RESULT_SHORT_LABEL2.md:62` (commit `f6a5cba2`) | *"rank-IC 0,0519 → 0,0778…0,0824 (**tăng ~50–59 %**, ngoài CI)"* | Đây là **NHÃN PATH-AWARE của model SHORT** (`y=1[retEnd_72h≤−thr & maxFav_72h≤E]` trên 45 feature) — **không liên quan** `rateDown15MAvg` theo `f`. Kết luận của chính nó là **NO-GO/NULL** (net tụt 50–66 %, 2023/2024 âm hơn). |
| `RESULT_SHORT_MODEL` (`a3b59757`) | rank-IC nền **+0,0519** của nhãn short ngược | cùng gốc 0,0519 ⇒ xác nhận "0,0519→0,0778" là của **SHORT label**, không phải BD-CHAIN |

⇒ **KẾT LUẬN A.1: "không có nguồn".** Cụm "+50 % IC" bị gán nhầm từ `RESULT_SHORT_LABEL2`.

---

## 2. ĐO LẠI IC OFFLINE (0-SIM) — NHIỆM VỤ A.2

### 2.1 Phương pháp
- **Tín hiệu** `rateDown15MAvg` = `momentum15M` trong gate store = cột `down15` của `market.bin`.
  Baseline **`f=0` SINH LẠI** (cùng nguồn ticker với biến thể) — so sánh táo-với-táo; thêm mốc
  **`f=0` store gốc (live Aerospike)** để thấy sai lệch nguồn dữ liệu.
- `rateDown15MAvg` là **scalar market-level** (hằng số mọi coin trong 1 tick) ⇒ IC cross-section **suy biến**;
  dùng **rank-IC theo THỜI GIAN** (Spearman), **de-overlap 15 phút** (`ts % 900000 == 0`) — đúng như
  `research/pipeline/gate_feat_study/score_cycle.py`.
- **2 nhãn độc lập:**
  - **(a) nhãn GATE `label_oldbasket`** (realized 15′, chính là mục tiêu gate train) — n = 175 189.
  - **(b) nhãn 72h** `EW mean(retEnd_72h)` và `EW mean(pathq_72h=maxFav/|maxAdv|)` trên universe mỗi tick
    (từ `funding_label_15m_*.pb`) — n ≈ 166 410.
- **CI:** bootstrap **block 72h**, 2 000 rep, seed `20260905`, nới **×1,21**.

### 2.2 Bảng kết quả (IC trước/sau + "có +50 % không")

| nhãn | `f=0` (baseline, |IC|) | `f=0.5` | Δ vs f=0 | `f=1.0` | Δ vs f=0 | +50 %? |
|---|---|---|---|---|---|---|---|
| **GATE `label_oldbasket`** (a) | **0,4345** | **0,3600** | **−17 %** | **0,3271** | **−25 %** | **KHÔNG (GIẢM)** |
| `retEnd_72h` EW (b) | 0,0525 | 0,0725 | +38 % | 0,0685 | +30 % | không |
| `pathq_72h` EW (b) | 0,0755 | 0,0884 | +17 % | 0,0776 | +3 % | không |
| *(tham chiếu)* `f=0` store GỐC (live) | 0,4105 | — | — | — | — | — |

**CI block-72h ×1,21** (nhãn (a) — mốc so sánh chính):

| | `f=0` | `f=0.5` | `f=1.0` |
|---|---|---|---|
| IC điểm | −0,4345 | −0,3600 | −0,3271 |
| CI95 | [−0,4647 ; −0,4061] | [−0,3846 ; −0,3364] | [−0,3508 ; −0,3046] |
| chứa 0 | không | không | không |

⇒ **(a): 3 CI KHÔNG chồng lấn ⇒ |IC| của `f=0.5`/`f=1.0` GIẢM THẬT so với `f=0` (ngoài CI).**
⇒ **(b): CI cực rộng & chồng lấn nặng** — vd `retEnd` f=0 CI [−0,0963;−0,0088] vs f=0.5 [−0,1127;−0,0326]
⇒ **không phân biệt được**; và mức tăng lớn nhất (+38 % ở f=0.5) **vẫn < +50 %**.

### 2.3 Trôi theo NĂM
`|IC|` nhãn GATE theo năm (baseline `f=0` → `f=0.5` → `f=1.0`):

| năm | `f=0` | `f=0.5` | `f=1.0` |
|---|---|---|---|
| 2021 | 0,2484 | 0,2647 | 0,2490 |
| 2022 | 0,2947 | 0,3141 | 0,2976 |
| 2023 | 0,2836 | 0,2908 | 0,2637 |
| 2024 | 0,2583 | 0,2447 | 0,2219 |
| 2025 | **0,3653** | **0,2531** | **0,2052** |

`retEnd_72h` theo năm (f=0 / 0.5 / 1.0): 2021 `−0,078/−0,083/−0,079` · 2022 `−0,026/−0,025/−0,027` ·
2023 `−0,055/−0,053/−0,055` · 2024 `−0,070/−0,066/−0,060` · 2025 `−0,077/−0,049/−0,040`.
⇒ **Không** có xu hướng `f` "tốt dần theo năm"; mọi chênh lệch ≤ ~0,03 và dấu không nhất quán.

---

## 3. KẾT LUẬN NHIỆM VỤ A

**(1)** Không có nguồn nào trong repo phát biểu biến thể này làm IC tăng (cụm "+50 %" thuộc `RESULT_SHORT_LABEL2`).
**(2)** Đo lại **KHÔNG** cho IC +50 %: so với **nhãn chính của GATE** thì `|IC|` **giảm 17–25 %** (ngoài CI — xấu đi *thật*);
so với 2 nhãn 72h yếu (|IC| ≈ 0,05–0,09) thì `|IC|` đổi **+3…+38 %** nhưng **CI chồng lấn** (không phân biệt được).
**(3)** Không có dấu hiệu "edge thật" ⇒ **NHIỆM VỤ A = NULL.**

---

## 4. NHIỆM VỤ B — **KHÔNG CHẠY** (theo luật task)

Task quy định: *"Nếu A = NULL (IC không tăng) ⇒ DỪNG nhiệm vụ B + báo RÕ (tiết kiệm vòng Kaggle)."*
⇒ **Kernel C (gate retrain → `pred.bin`) và Kernel D (S1+bins) KHÔNG được chạy/viet.**
**0 vòng Kaggle tiêu.** Không có bảng `f × (n/T3/UW/maxDD/Calmar/T1–T4)` vì **B không chạy** — KHÔNG bịa số.

Vì sao điều này đúng về mặt khoa học: `rateDown15MAvg` là **input model** (gate idx 2 = `momentum15M`,
selector idx 5 — `PREREG_BD_CHAIN §1`), nên biến thể `f` **chỉ có thể** chạm PnL *qua* việc đổi feature —
mà feature đó (theo đo (a)) lại **kém tương quan HƠN** với chính nhãn mà gate học. Retrain gate trên
feature yếu hơn nhiều khả năng **không** tạo edge; đúng luật "đo IC trước, tiêu sim sau".

**Còn nợ (vòng sau, nếu owner muốn):** (i) dump Aerospike `market_data` read-only → dataset Kaggle (parity `f=0`);
(ii) Kernel D (S1+bins) chưa viết; (iii) nếu vẫn muốn thử B bất chấp A-NULL ⇒ cần pre-reg mới ghi rõ.

---

## 5. MỤC BỎ + LÝ DO

- **Bỏ NHIỆM VỤ B (4 arm + chấm 4 tầng + CI sim)**: luật task "A=NULL ⇒ DỪNG B". Không bịa số.
- **Bỏ chấm §9 `reset_rule_score.py`** (điều kiện B): B không chạy.
- **Giữ**: 3 script 0-sim + 3 JSON out + doc này + commit/push.
- **KHÔNG chạm**: 242 / ONNX / LIVE / đường SELL / 2026 / file dở-dang của job khác
  (`short_pathexit_sim.py`, `RESULT_SHORT_PATHEXIT.*`) — chỉ `git add <file của mình>`.

---

## 6. TRẢ LỜI 7 CÂU (báo cáo cuối)

1. **commit**: `bd_chain2` (xem `RESULT_BD_CHAIN_CHAIN2.json:commits`).
2. **IC trước/sau, nguồn?**: gốc `|IC|` 0,4345 (nhãn GATE) → `f=0.5` 0,3600 / `f=1.0` 0,3271; **nguồn "+50 %": KHÔNG có** (bị gán nhầm từ `RESULT_SHORT_LABEL2`).
3. **+50 %?**: **KHÔNG** (nhãn GATE giảm 17–25 %; nhãn 72h tăng ≤38 % & trong nhiễu).
4. **Dây chuyền đầy đủ chạy được?**: **không thử** (A=NULL ⇒ DỪNG B).
5. **Bảng `f × chỉ số` / `f` qua 4 tầng?**: **không có** (B not-run).
6. **Trôi theo năm?**: không xu hướng `f` tốt dần; chênh lệch ≤ ~0,03, dấu không nhất quán (§2.3).
7. **GO/NO-GO?**: **NO-GO** — giữ `f=0` (N=100).
