# DECISION — Doi BASELINE nghien cuu sang FLATGRID KEEPLEG0 (2026-09-24)

## Quyet dinh
Ngay **2026-09-24**, user **CHOT** trong chat: *"thay baseline moi la 1;1;1;1 di"*.
Baseline nghien cuu (moc so sanh + cong parity) chuyen tu **T170** sang **FLATGRID KEEPLEG0**.

| | T170 (baseline CU) | **KEEPLEG0 (baseline MOI)** |
|---|---|---|
| profile | `profiles/x1_gs_t170.properties` | **`profiles/t170_flat_keepleg0.properties`** |
| `DCA_GRID_WEIGHTS` | 1,1,3,8 | **1,1,1,1** |
| `DCA_GRID_SCALE` | 19.5 | **6.0** |
| run tham chieu | `java/devrun/X1_GS_T170_2021` | **`java/devrun/FG_KEEPLEG0`** |
| `printDone.csv` md5 | `efb793e2468ca3a7318da0f0ad23d4fc` | **`99e42b75cf1a2142f9cd14dc72e371ba`** |
| leg | 1,089 | **1,085** |
| equity cuoi | 111,070 | **103,083** |
| CAGR | 29.27% | 27.14% |
| maxDD toan ky | -11.84% | **-11.21%** |
| UW toan ky (ngay) | 92 | 147 |
| tran tap trung 1 coin (ly thuyet) | 58.5% | **18.0%** |
| max conc do duoc | 8.71% | **6.98%** |

`diff profiles/t170_flat_keepleg0.properties profiles/x1_gs_t170.properties` = **DUNG 2 dong**
(`DCA_GRID_SCALE` + `DCA_GRID_WEIGHTS`), khong doi bat ky key nao khac.

## DAY LA QUYET DINH KHONG DUOC BANG CHUNG HO TRO — phai ghi ro, khong duoc hieu la "win"

- `docs/RESULT_FLATGRID.md`: KEEPLEG0 **KHONG dat luat thang** (0 rate ngoai CI huong TOT) va
  **FAIL rang buoc cung UW** theo nguong CU (147 > 120 ngay). Theo luat incumbent cu, T170 le ra
  duoc giu nguyen.
- Ly do doi baseline la **DONG BO voi production**: shadow C3 production (paper) da chay KEEPLEG0
  tu **2026-09-19** (`docs/DECISION_SHADOW_FLATGRID_KEEPLEG0.md`, commit `2fd7357`). Nghien cuu ma
  do tren mot cau hinh khac cai dang chay that la do mot thu khac.
- Gia phai tra: **CAGR -2.13pp · equity -7.19% · UW +55 ngay**. Cai doi lai: **tran tap trung
  1 coin 58.5% -> 18.0%** (ly thuyet) va max conc do duoc **8.71% -> 6.98%**.
- Voi khau vi MOI (`docs/RISK_APPETITE.md` §6–§7), UW 147 **PASS** (`<= 250`) — nen objection cu
  cua KEEPLEG0 (UW 147 > 120) khong con hieu luc.

## HAU QUA — BAT BUOC

1. **Cong parity MOI**: moi run moi KHONG override DCA phai tai hien
   **`99e42b75cf1a2142f9cd14dc72e371ba` / 1,085 leg / eq 103,083**. `efb793e2` (T170) **khong con
   la moc baseline** — chi con la "**nen cu**" de doi chieu khi can.
2. **Ket luan cu KHONG tu dong chuyen**: moi ket luan tren truc exit / gap / sizing / gate duoc do
   tren nen **T170 (1,1,3,8)** ⇒ **pham vi hieu luc la nen cu**. Neu can ket luan tren baseline moi
   thi phai **chay lai** voi **pre-reg moi**.
3. **Khong doi gi khac**: khau vi rui ro (`docs/RISK_APPETITE.md` §6–§7: `maxDD <= 40%/nam` ·
   `UW <= 250` · `quy >= -20%` · khong nam am · `conc <= 15%`) van dung; **nguong bang chung
   (>= 2 rate ngoai CI) GIU NGUYEN**; luat "**khong push**" giu nguyen.

## Vi sao `1,1,1,1` mot minh la KHONG DU — phai kem `SCALE=6.0`

Cong thuc: `margin(bac i) = equity x F_BASE x throttle x tierMult x w[i] x DCA_GRID_SCALE / sum(w)`.
`sum(w)` nam o **MAU SO**: `1,1,3,8` (sum 13) -> `1,1,1,1` (sum 4) ma **giu** `SCALE=19.5` se phong
moi bac len **13/4 = 3.25 lan**; va bat bien `TONG = F_BASE x SCALE` (doc lap voi `w`) ⇒
**`FLAT_KEEPSCALE` KHONG giam tran tap trung MOT CHUT NAO** (van 58.5%).

| cau hinh | W | SCALE | bac0 | TRAN 1 coin | conc do duoc | ket qua |
|---|---|---|---|---|---|---|
| T170 goc | 1,1,3,8 | 19.5 | 4.500% | 58.5% | 8.71% | — |
| `FLAT_KEEPSCALE` | 1,1,1,1 | 19.5 | **14.625%** | **58.5%** | **16.73%** | **FAIL** rao nam |
| **`FLAT_KEEPLEG0`** | **1,1,1,1** | **6.0** | 4.500% | **18.0%** | **6.98%** | baseline moi |

⇒ Yeu cau *"chinh luoi DCA 1:1:1:1"* **chi dung khi kem `SCALE=6.0`** (giu margin bac 0 = 4.5%).

## Ghi chu 1x (boi canh khau vi)
`margin == notional` da kiem: `1.0000` tren **1089/1089 · 2559/2559 · 2632/2632** leg
(`docs/RESULT_FRAGILITY_N.md`) ⇒ danh **1x**, khong don bay; max concurrent margin ~47–58% equity
⇒ **khong the chay tk** ⇒ `maxDD`/`UW` la **lo TAM THOI**. **Kenh MAT THAT duy nhat = tap trung
1 coin** (delist/ve 0 khi dang giu) ⇒ tran `conc <= 15%` giu **CUNG**.

## BO SUNG 2026-09-24 — BAT `CONC_CAP_PERCOIN = 15%` lam MAC DINH (user chot "Ok")

- **Baseline** `profiles/t170_flat_keepleg0.properties` them:
  `CONC_CAP_PERCOIN_ENABLED=true` + `CONC_CAP_PERCOIN_PCT=0.15`.
- **Production** `/home/ubuntu/shadow_c3/app/conf/env.sh` them dung 2 key do (da `cp -a` backup
  `env.sh.bak_*` truoc khi sua). **CHUA restart service** ⇒ chi co hieu luc o lan restart ke tiep.
- **Tren KEEPLEG0 day la NO-OP trong mau**: `RESULT_GATESCALE_KEEPLEG0` nhom (1) — `[CONC-PC] MODE
  pct=0.15`, `blocked=0`, printDone **y het** khi OFF (conc do duoc **7.12%** << 15%). ⇒ Parity
  `99e42b75` **khong doi**; gia tri nam o **bao hiem** (chan kenh MAT THAT duy nhat khi danh 1x).
- Bang chung quan trong: conc 1 coin **co the len toi 40.43%** (gate 1.25, `RESULT_GATESCALE_SWEEP`),
  va tren T100 cap 15% cat conc **27.23% → 10.83%** ma PnL **+8.36%** (`RESULT_CONC_CAP_HIGHN`).
