# LABEL_ROI2 — them `g1lite` (NHAN THAT CUA C2b), va TACH chan troi khoi cong thuc

Chay 2026-09-04, `research/analysis/lab2_label_roi.py`, log `/home/ubuntu/cov/LAB2.out`.
**MO TA.** 970 lenh `PREDICT_SYMBOL_TRADE` cua run **C2b**, join label **100%**,
`g1_replay` phu **90.5%** (878/970 — pool `path_labels` da lay mau). `ret = pnl/margin`.
`g1lite` duoc tinh **dung cong thuc `ledger.py:40`** tu `maxFav_h`/`retEnd_h` => phu 100%,
khong can join ledger.

Ly do lam: `LABEL_ROI_RESULT` (chay `label_align.py`) **thieu chinh `g1lite`** — nhan that cua
S1/C2b — vi script do khong tinh no. Khong co no thi khong tra loi duoc "nhan dang dung xep thu may".

## 1. NHAN DANG DUNG — C2b xep THU NHAT

| nhan | spearman vs ROI that | AUC | within-tick rho | %tick>0 |
|---|---|---|---|---|
| **`g1lite` 72h  <= NHAN THAT CUA S1/C2b** | **+0.474** | **0.928** | **+0.392** | **82%** |
| `g1lite` 72h ARM 7% (khop arm that cua C2b) | +0.476 | 0.921 | +0.373 | 80% |
| `maxFav_72h` (tho) | +0.472 | 0.923 | +0.354 | 79% |
| `pathq 72h` = `fav/abs(adv)` | +0.452 | 0.900 | +0.351 | 77% |
| `g1_replay` 72h (mo phong exit G1) | +0.437 | 0.873 | +0.344 | 78% |
| `retEnd_72h` | +0.373 | 0.807 | +0.282 | 70% |
| `maxFav_4h >= 6%` <= NHAN THAT CUA G015 | +0.175 | 0.658 | — | — |
| `-pNoPump` = diem G015 dang deploy | **-0.019** | 0.518 | +0.004 | 47% |

## 2. TACH CHAN TROI (cung cong thuc `g1lite`, chi doi `h`) — DON DIEU va LON

| | spearman | AUC | within-tick | %tick>0 |
|---|---|---|---|---|
| `g1lite` **4h** | +0.258 | 0.747 | +0.202 | 70% |
| `g1lite` **24h** | +0.396 | 0.875 | +0.309 | 75% |
| `g1lite` **72h** | **+0.474** | **0.928** | **+0.392** | **82%** |

⇒ **Chan troi dai hon TOT HON, don dieu.** 4h -> 72h **gan gap doi** tuong quan
(+0.258 -> +0.474). Day khong phai chuyen "xap xi nhau" — day la hieu ung lon va sach.

## 3. TACH CONG THUC (cung chan troi 72h) — GAN NHU PHANG

`maxFav_72h` +0.472 · `g1lite` +0.474 · `g1lite` ARM7 **+0.476** · `pathq` +0.452 —
**tat ca trong nhieu cua nhau**. Chi `retEnd_72h` +0.373 la kem ro.

⇒ **Chan troi quyet dinh gan het; cong thuc gan nhu khong quan trong** — mien la o ho
`maxFav`, khong phai `retEnd`.

## 4. HAI DINH CHINH BAT BUOC cho cac doc truoc

### 4.1 `g1_replay` KHONG phai "nhan sat tien nhat" — do duoc nguoc lai

`path_labels.py` docstring goi `g1_replay` la *"ban 'tan cung' cua label: chinh la thu sim kiem
tien"*. **Do truc tiep voi ROI that thi no KEM HON `g1lite`**: +0.437 vs **+0.474**,
AUC 0.873 vs **0.928**. `AUDIT A11` cung ra dung thu tu do (`g1lite 0.584 > g1_replay 0.507`).
Ly do co the: `g1_replay` tinh tren **luoi GIO** (72 close gio) va tham so exit cua no
(arm 5%, cap 8%, khong co nhanh WEAK) **khong khop** ban deploy.
⇒ **Moi cho tôi da goi `g1_replay` la "nhan gan tien nhat" (`CEIL_RESULT`, `C4H_RESULT`) la SAI.**
Nhan gan tien nhat do duoc la **`g1lite` 72h**.

### 4.2 `CEIL_RESULT` muc 2.1 phai RUT

`CEIL_RESULT` viet: *"con so 17.8% la tren nhan SAI; tren `g1_replay` S1 chi bat 5.2% => du dia
lon hon 3.4 lan"*. **Rut cau do.** Lap luan dua tren tien de "`g1_replay` la nhan gan tien nhat",
ma muc 4.1 da bac tien de do. Phat bieu dung:

- Nhan tot nhat lam proxy cho tien la **`g1lite` 72h**, va do dung la nhan S1 **dang** dung.
- Tren nhan do, S1 bat **17.5%** [13.1%, 22.1%] tran oracle; doi chung `vol_7d` tho bat **20.0%**.
- Nen **khoang trong la ~82%, khong phai ~95%**, va **lap luan tuong doi van dung**:
  mot feature tho van sanh ngang model 9 feature.
- Cai `CEIL_RESULT` van **dung**: `%bat` **bien thien hon 5 lan** tuy nhan (25.8% -> 0.0%), nen
  moi phat bieu "con Y% du dia" **vo nghia neu khong ghi ro nhan**. Gio da biet nhan nao dung.

### 4.3 Lech arm 5% vs 7% la THAT nhung KHONG dang ke
Toi da neu lech nay o `C2B_SPEC` va `CEIL_RESULT`. Do duoc: `g1lite` ARM7 (+0.476) vs
ARM5 (+0.474) — **chenh +0.002, trong nhieu**. ⇒ lech arm **khong phai van de chat luong nhan**.
Cai **chua kiem duoc** la lech **chan troi 72h vs time-stop that 168h**: file nhan chi co
**4h/12h/24h/72h**, khong co 168h. Muon kiem phai sinh lai nhan tu `CLOSES_1H.bin` voi `NH=168`
(`path_labels.py` lam duoc). Va muc 2 cho thay chan troi la truc **quan trong nhat**, nen
day la phep do dang uu tien.

## 5. Ve `-pNoPump` (diem G015 deploy): doc voi range restriction
spearman **-0.019**, AUC 0.518, within-tick **+0.004 / 47% tick duong**. Tap nay **da bi loc boi
chinh diem do** (top-8) => **range restriction** (bay da ghi o `selector_edge_evidence §3`).
Ket luan dung: **trong tap duoc admit, diem G015 khong con mang thong tin xep hang nao them** —
khong phai "G015 vo gia tri toan cuc". Nhung chinh dai luong do dang dat `dyn_thr` va chia nhanh
exit STRONG/WEAK tai `symbolPred > 0.29`.
