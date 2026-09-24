# PREREG ? Lam phang luoi DCA: 1,1,3,8 -> 1,1,1,1

Viet TRUOC khi chay. Khoa tham so. Khong tune lai sau khi thay ket qua.
Ngay: 2026-09-15. Nen: T170 (INCUMBENT). Dataset: `wfo_ds_x1_2021` (2021-07 -> 2025-12).

Yeu cau goc cua user: *"van phai bo cai 1,1,3,8. de 1,1,1,1 thoi, khong cuu duoc thi thoi
chu khong rui ro vay."* ? tuc muc tieu la **GIAM TAP TRUNG RUI RO**, chap nhan mat hieu qua.

---

## 0. Phat hien BAT BUOC phai xu ly truoc khi thiet ke (day la ly do co 2 bien the)

Tu `docs/diag/DIAG_BIGDOWN_CONCENTRATION.md`:

```
margin(bac i) = equity x F_BASE x throttle x tierMult x w[i] x DCA_GRID_SCALE / sum(w)
```

`sum(w)` nam o MAU. Doi `1,1,3,8` (sum=13) thanh `1,1,1,1` (sum=4) ma **giu nguyen**
`DCA_GRID_SCALE=19.5` se **phong to MOI bac len 13/4 = 3.25 lan**:

| Cau hinh | W | SCALE | sum | bac0 | bac1 | bac2 | bac3 | **TONG** |
|---|---|---|---|---|---|---|---|---|
| T170 goc | 1,1,3,8 | 19.5 | 13 | 4.500% | 4.500% | 13.500% | 36.000% | **58.500%** |
| FLAT_KEEPSCALE | 1,1,1,1 | 19.5 | 4 | **14.625%** | 14.625% | 14.625% | 14.625% | **58.500%** |
| FLAT_KEEPLEG0 | 1,1,1,1 | **6.0** | 4 | 4.500% | 4.500% | 4.500% | 4.500% | **18.000%** |

(so lay tu `_fg1.sh`, tinh truc tiep tu cong thuc; da doi chieu voi bat bien ma
`DcaGridScalarTest.clusterExposureIsBudgetTimesScale` khang dinh: `TONG = F_BASE x SCALE`,
**doc lap voi w**.)

**Hai he qua phai noi thang:**

1. **`FLAT_KEEPSCALE` KHONG giam tap trung rui ro MOT CHUT NAO.** Tong khi nhoi het luoi van dung
   **58.5% equity** ? y het T170 goc. No chi doi HINH DANG phan bo. Va no lam **rui ro entry dau
   tang gap 3.25 lan** (4.5% -> 14.625%). Voi `U_MAX=0.60`, chi ~4 vi the dong thoi la cham tran
   (4 x 14.625% = 58.5%), thay vi ~8 nhu hien nay => **day la mot he thong KHAC HAN, don bay len
   3.25 lan tren tung lenh**, khong phai "T170 voi luoi phang".
2. **`FLAT_KEEPLEG0` moi dung tinh than yeu cau.** Chinh `SCALE` xuong **6.0** (tinh chinh xac:
   can `F_BASE x S / 4 = 0.045` => `S = 0.045 x 4 / 0.03 = 6.0`, khong lam tron) thi bac 0 giu
   nguyen **4.500%** ? **risk-per-trade luc vao lenh KHONG DOI so voi T170** ? va tran tap trung
   1 coin tut tu **58.5% -> 18.0%**.

**Vi vay chay CA HAI**, khong phai de chon cai dep hon, ma de user nhin thay cai bay:
KEEPSCALE la dieu se xay ra neu chi sua mot dong `DCA_GRID_WEIGHTS` nhu cach hieu truc quan.

---

## 1. Hai config (KHOA ? khong them bien the nao khac)

| Tag run | Profile | Khac T170 goc |
|---|---|---|
| `FG_PARITY_T170` | `profiles/x1_gs_t170.properties` | **khong khac gi** (cong parity) |
| `FG_KEEPSCALE` | `profiles/t170_flat_keepscale.properties` | `DCA_GRID_WEIGHTS=1,1,1,1` |
| `FG_KEEPLEG0` | `profiles/t170_flat_keepleg0.properties` | `DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0` |

`diff` da chay va xac nhan: keepscale khac T170 dung **1 dong**, keepleg0 dung **2 dong**.
Ca ba profile deu 20 key. **KHONG sua mot dong code Java nao** ? `DCA_GRID_WEIGHTS` va
`DCA_GRID_SCALE` da duoc parameterize qua `Cfg.get` (`Configs.java:187-190` va `:254-255`),
va `managerBudget` tu dong dung `dcaGridTotalWeight()` moi nen mau tu cap nhat, khong can sua gi.

### CAM KET KHOA PHAM VI
Chi chay **dung 2 bien the tren**. **KHONG** do them bat ky bo trong so nao khac
(1,1,2,4 / 1,2,3,4 / 1,1,1 / ...), **KHONG** do them gia tri `DCA_GRID_SCALE` nao khac ngoai
19.5 (giu) va 6.0 (tinh ra tu rang buoc "bac0 khong doi"), du ket qua ra sao. Neu ca hai deu
that bai => NULL, dong lai, khong mo vong 2.

---

## 2. Cong parity (bat buoc)

Khong co thay doi code => parity phai la **byte-identical**, khong phai "gan giong".

- `FG_PARITY_T170` chay lai profile T170 y nguyen tren cung jar
  (`target/binance-java-sdk-1.2.4.jar`, md5 `a577c8481727c159062e9353f612c256`).
- Dieu kien PASS: `md5sum storage/printDone.csv` == **`efb793e2468ca3a7318da0f0ad23d4fc`**
  (md5 cua `X1_GS_T170_2021/storage/printDone.csv` hien co, da xac minh truoc khi viet doc nay).
- Neu md5 LECH => **DUNG TOAN BO**, bao cao, khong dien giai ket qua 2 bien the.

---

## 3. Cham diem (khoa truoc)

- So sanh tung bien the vs **T170 goc**, block-72h paired bootstrap
  (`BLOCK_H=72`, `NREP=2000`, `SEED=20260905`) ? y het moi vong truoc.
- **k = 2** (dung 2 gia thuyet: KEEPSCALE, KEEPLEG0).
  `CI_INFLATE = sqrt(2 x ln 2) = 1.177410` ? dung tu dau, **KHONG** dung hang so 1.21 cu
  (xem `docs/audit/AUDIT_READJUDICATE_CI_RESCORE.md`).
- 3 ty le chat luong: `win%`, `TSloss%`, `meanP`.
- **Luat THANG:** >= 2/3 ty le nam ngoai CI theo huong tot **VA** rang buoc cung PASS ca 5 nam.
- **Rang buoc cung moi nam:** `maxDD <= 15%`, `UW <= 120 ngay`, `return nam >= 0`, `return quy >= -5%`.

---

## 4. Do lai TAP TRUNG RUI RO (muc tieu that su cua yeu cau nay)

Lam lai dung phuong phap `docs/diag/DIAG_BIGDOWN_CONCENTRATION.md` muc 4 cho ca 2 bien the:
so cum cham bac 1/2/3, **max % equity don vao 1 coin**, PnL cac cum cham bac sau.
Day la **tieu chi chinh** cua viec nay ? khong phai PnL.

---

## 5. DU DOAN GHI TRUOC (de doi chieu, chap nhan sai)

1. **`FG_KEEPLEG0` se gan nhu TRUNG voi T170.** Ly do: bac 0 va bac 1 co margin Y HET
   (4.5% ca hai cau hinh, vi `w=1`); chi bac 2 (4.5% thay vi 13.5%) va bac 3 (4.5% thay vi 36%)
   moi khac. Ma tren T170 chi co **4/1069 cum tung cham bac 2 va 0 cum cham bac 3**. => tac dong
   bac nhat cham vao <= 4 leg. Du doan: **0/3 ty le ngoai CI (NULL hai chieu)**, equity cuoi lech
   duoi +/-3%, hard-constraint PASS y nhu T170.
   *(Luu y: van se co sai lech lan truyen vi margin doi -> `marginRunning` doi -> `throttle` doi
   cho MOI lenh sau do. Nen "gan trung" chu khong "trung".)*
2. **`FG_KEEPSCALE` se TE HON RO RET.** Moi entry to gap 3.25 lan, `u` cham `U_MAX=0.60` rat nhanh,
   so vi the dong thoi tut tu ~8 xuong ~4. Du doan: **FAIL rang buoc cung** (maxDD > 15%) o it nhat
   1 nam, va **max tap trung 1 coin KHONG giam** (van ~58.5% tran ly thuyet).
3. **Tap trung rui ro:** KEEPLEG0 tran ly thuyet 58.5% -> **18.0%**; do thuc te tren T170 la
   8.71% max => du doan KEEPLEG0 xuong con **~5-6%** max.

## 6. Dieu KHONG lam
Khong push. Khong cham box 242. Khong dong holdout 2026. Khong sua/xoa test cu.
Khong doi incumbent du ket qua the nao ? viec doi incumbent can holdout, khong phai DEV.
