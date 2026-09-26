# PREREG_GATE_RECAL — hieu chuan lai nguong gate: nguong theo PHAN VI CUON cua chinh nguon p15 (fit <= 2025-12-31)

**Trang thai: DE XUAT — CHUA CODE, CHUA CHAY, CHUA AP DUNG VAO PRODUCTION.** Can **owner duyet** truoc khi lam bat cu buoc nao.
Chot (du kien): 2026-09-26, **TRUOC** khi viet code/chay. Nguon chan doan: `docs/audit/DIAG_GATE_FROZEN_20260926.md`
(+ `.json`). Bai nay **KHONG** mo lai `GATESCALE` / `GATE_CALIB` / `FLATGATE`; chi tra loi mot cau moi ma chan doan 26/09 dat ra.

## 0. Cau hoi + vi sao KHONG phai open-search

Chan doan 26/09/2026 (so, khong suy dien): nguong gate dang chay `thr = 0.008 * max(0.26787, sp/0.15*1.2876) * 1.70`
= **2,947-3,760%**, trong khi:
- phan bo `predReturn15M` cua **model live 2026** (8.929 mau, 12/08-26/09, do tren 242) co **max 2,30%**;
- nguong do = **p99,910-p99,949** cua bo pred DEV (`wfo_ds_x1_2021/pred.bin`) nhung **> p100** cua 2026;
- sim danh gia entry **1.440 lan/ngay** con live **96 lan/ngay** (15x) => ty le entry DEV (0,5-1,4/ngay) **khong chuyen duoc**
  sang live; ky vong live ~**0,086 lan/ngay ~ 2,6 entry/thang** => kenh shadow khong the giao dich.

Cau hoi hop le duy nhat: **nguong gate nen duoc bieu dien theo PHAN VI CUON cua chinh chuoi p15 cua nguon dang dung
(thay vi hang so tuyet doi hieu chuan tren bo pred DEV), de ty le entry la mot muc tieu chu dong va chuyen duoc giua sim/live?**
KHONG lam open-search "tim config thang baseline" (truong phai biet L2; `CI_REAUDIT`: DEV khong phan biet duoc delta gate ~3pp).
**Ky vong ghi truoc: NULL** (khuon B4/GATESCALE) hoac hieu qua tuong duong nhung **ty le entry doi duoc va on dinh hon**.

## 1. Co che — chot cung (phai byte-identical khi TAT)

- Them **1 key** `SIM_GATE_P15_Q` (float, doc 1 lan o `Configs`, khong khai/<=0 => TAT => hanh vi cu y nguyen):
  `PASS <=> !(predReturn15M < thr)`, `thr = max(MIN_MOMENTUM_15M, quantile_W(p15_past, Q))`
  voi `quantile_W` = phan vi `Q` tren cua so truot `W` ngay cua chinh chuoi p15 **cua nguon dang chay**
  (sim: `predictionMap`; live: model live), **chi dung du lieu QUA KHU** (causal, khong nhin tuong lai, khong forward-fill nguoc).
- `W` co dinh trong profile (khong fit trong bai nay): **W = 30 ngay**. `Q` nhan **3 diem chot**: **0.995 / 0.998 / 0.999**.
- **San an toan** `max(MIN_MOMENTUM_15M, ...)`: khong bao gio ha nguong duoi `base` (chong vao lenh tren nhieu khi duoi phan bo bi nen).
- Giu nguyen `EntryGate` cho nhanh `symbolPred != null`: `thr_final = max(rolling_thr, EntryGate.threshold(sp))`
  — tuc **KHONG noi long** hanh vi dang co; chi **ha tran** khi rolling_thr thap hon. (Neu owner muon chieu nguoc lai — thay han —
  phai la pre-reg KHAC.)
- Ap o CA sim va live (cung mot ham), va **cung nguon p15** o ca hai phia. Neu nguon p15 sim != nguon live thi ket qua VO NGHIA
  (day chinh la nguyen nhan dong bang: xem `DIAG_...` §3.3).
- Log: them 1 dong `[GATE-RECAL] W Q thr_rolling thr_final n_cand n_pass` (thuan LOG).

## 2. Bien the — DUNG 3, KHOA (khac nhau CHI o Q)

| tag | profile | Q | y nghia |
|---|---|---|---|
| `X1_GR_Q995` | `profiles/x1_gr_q995.properties` | 0.995 | nguong ~ p99,5 cua 30 ngay => ty le entry cao nhat trong 3 diem |
| `X1_GR_Q998` | `profiles/x1_gr_q998.properties` | 0.998 | trung binh |
| `X1_GR_Q999` | `profiles/x1_gr_q999.properties` | 0.999 | chat nhat |

Moi key khac y `x1_gs_t170.properties`. **Khong them diem, khong doi Q sau khi thay so.** `SIM_GATE_P15_Q` khong khai = TAT = parity.

## 3. Thu tu — bat buoc

1. **Owner duyet** ban pre-reg nay (chua duyet thi khong lam gi).
2. Commit pre-reg >>> roi moi viet code + 3 profile.
3. **Cong nghiem thu TAT:** jar moi + `x1_gs_t170.properties` (khong khai key) => `printDone.csv` md5
   `efb793e2468ca3a7318da0f0ad23d4fc` (n=1.089, equity 111.070) **byte-identical**. FAIL => sua code, KHONG chay bien the.
4. **Do phan bo nguon p15 truoc khi chay** (chi doc, khong fit): xac nhan thang do p15 cua nguon SIM va nguon LIVE.
   Neu hai thang do khac nhau (nhu chan doan 26/09: p50 0,545% vs 0,910%; max 12,26% vs 2,30%), **DUNG** — bai toan la
   dong bo nguon/scale p15, khong phai nguong (ghi ro va dong pre-reg nay).
5. **3 run** tren cua so DEV **2021-07..2025-12** (`wfo_ds_x1_2021`, `TIME_RUN=20210701`), 1 slot java, disk >= 8G.
   **KHONG cham 2026. KHONG cham 242 / shadow_c3. KHONG mo holdout.**
6. **1 run kiem nhip (bat buoc, moi):** cung profile `X1_GR_Q998` nhung entry-leg **lay mau 15 phut** (khop nhip live
   96/ngay) => do "ty le entry chuyen doi duoc". So nay moi la so duoc phep dung de du doan live.
7. Cham bang khung co san: `research/analysis/x1_rates.py` (5 rate + CI khoi-72h) + paired block-bootstrap equity ngay
   (block 21, 2000 rep, seed 20260903), hieu chinh boi k=3 => nguong `1.4823 * sd_boot`.
8. Ghi `docs/result/RESULT_GATE_RECAL.md` + entry `QUEUE.md`. Commit SAU, **KHONG push**.

## 4. Quy tac quyet dinh (chot truoc)

Bien the **PASS** <=> (i) `d CAGR > 1.4823 * sd_boot` (paired, block 21, toan cua so) **VA** (ii) qua het rang buoc cung
tung nam (`RESULT_GATESCALE` §3: maxDD/UW/nam/quy) **VA** (iii) **ty le entry/thang ky vong nam trong [5, 30]** va
ty le entry cua run nhip-15m **>= 60%** ty le cua run nhip-1m (neu khong, ket qua khong chuyen duoc sang live => diem do VO NGHIA,
ghi ro chu khong bao PASS).

Cach doc:
- >= 1 PASS => de xuat do sang shadow forward (KHONG doi production, KHONG mo holdout); **owner duyet lan 2**.
- 0 PASS ma khong vi pham => "khong phan biet duoc / do doc incumbent la hop ly" => DONG, GIU gate hien tai
  (nhung **van phai ghi muc "kenh live ky vong ~2,6 entry/thang"** vao quyet dinh go-live).
- `d CAGR am ro (CI tren < 0)` => phan vi cuon THUA => DONG.
- Bat ky vi pham rang buoc cung nao => loai, khong hau kiem, khong doi nguong 1.4823, khong doi Q.

## 5. Khong lam

- Khong fit/cham tren 2026 (2026 la holdout; log 2026 chi duoc DOC de chan doan, da lam o `DIAG_GATE_FROZEN_20260926.md`).
- Khong doi hang so `DYN_MIN/SCORE_BASE/DYN_MULT`, khong doi `base`, khong doi bins/selector/exit/trailing.
- Khong chay Java/sim tren Oracle (shadow LIVE); nang thi day sang Kaggle/box.
- Khong restart service, khong sua `config.properties`/`env.sh`/profile production, khong deploy jar, khong push git.
- Khong tu ap dung: moi thay doi production can **owner duyet**.

## 6. Tai lieu lien quan

- `docs/audit/DIAG_GATE_FROZEN_20260926.md` (+ `.json`) — so lieu chan doan 26/09.
- `docs/audit/LEAN_GATE_AUDIT.md` — gop cong thuc ve `EntryGate`; canh bao "hai thang do symbolPred" (sim bins vs live net015-map).
- `docs/prereg/PREREG_GATESCALE.md` + `docs/result/RESULT_GATESCALE.md` — nguon goc `SIM_GATE_DYN_SCALE=1.70`.
- `docs/prereg/PREREG_GATE_CALIB.md` + `docs/result/RESULT_GATE_CALIB.md` — quet 1.30/2.10 quanh 1.70 (NULL, giu 1.70).
- `docs/result/RESULT_FLATGATE.md` — bo gate dyn => -61pp CAGR (ly do gate nay ton tai).
