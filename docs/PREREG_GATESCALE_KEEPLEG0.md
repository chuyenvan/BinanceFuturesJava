# PREREG — GATE-SCALE + CONC_CAP tren NEN PRODUCTION (FLATGRID KEEPLEG0)

Chot **TRUOC** khi chay bat ky sim moi nao. Ngay 2026-09-24. Branch `module`.
Sim chay **tren Kaggle CPU kernel** (`docs/KAGGLE_SIM.md`) — **KHONG** chay Java/sim tren Oracle
(Oracle chi duoc `mvn -o package`). **KHONG** `claude-run`/Claude Code. **KHONG** push.
DEV only: cua so `2021-07-01 .. 2025-12-31` (**KHONG** cham 2026/holdout/242/shadow_c3).

---

## 0. Vi sao co vong nay — do tren NEN THAT, khong phai nen nghien cuu

Tu **2026-09-19** shadow C3 production chay **FLATGRID KEEPLEG0**
(`docs/DECISION_SHADOW_FLATGRID_KEEPLEG0.md`, commit `2fd7357`): `DCA_GRID_WEIGHTS=1,1,1,1` +
`DCA_GRID_SCALE=6.0`, moi key khac giu nguyen T170. Nhung **baseline nghien cuu van la T170
(1,1,3,8)** ⇒ moi phep do gate-scale / conc-cap dang chay tren mot cau hinh **khac** cai dang
chay that. Vong nay do **tren chinh nen KEEPLEG0**, de tra loi 3 cau hoi cua owner:

- uu tien so 1: **"nhieu lenh de on dinh"** (`docs/RISK_APPETITE.md` §7);
- **"chinh luon cai luoi DCA 1:1:1:1 nhe, de the kia thi cai 15% chi la chua gap nhung van co the
  gap"** ⇒ khao sat `n` va tran tap trung 15% **tren dung cau hinh dang chay**.

Day la phep do **mot chieu, do luong** — khong phai open-search: chi **2 num** duoc doi
(`SIM_GATE_DYN_SCALE`, `CONC_CAP_PERCOIN_*`), moi thu khac **CO DINH**; thang do **khoa truoc**;
khong them/bo/doi diem sau khi thay so.

---

## 1. Su that da xac minh (dung lai, KHONG suy dien lai)

| moc | cau hinh | n | equity | md5 `printDone.csv` | nguon |
|---|---|---|---|---|---|
| `x1_gs_t170` (**T170**) | 1,1,3,8 + scale 19.5, gate 1.70 | 1,089 | 111,070 | `efb793e2468ca3a7318da0f0ad23d4fc` | `kaggle_sim/out/t170-x1-2021` (md5 da kiem lai trong vong nay) |
| `t170_flat_keepleg0` (**KEEPLEG0**) | **1,1,1,1 + scale 6.0**, gate 1.70 | **1,085** | **103,083** | `99e42b75cf1a2142f9cd14dc72e371ba` | Oracle `java/devrun/FG_KEEPLEG0` (`docs/RESULT_FLATGRID.md`, commit `e9e5965`) |

- `diff profiles/x1_gs_t170.properties profiles/t170_flat_keepleg0.properties` = **DUNG 2 dong**
  (`DCA_GRID_SCALE` 19.5→6.0, `DCA_GRID_WEIGHTS` 1,1,3,8→1,1,1,1). Da kiem lai trong vong nay.
- KEEPLEG0 toan ky: maxDD **−11.21%** · UW **147** · conc do duoc **6.98%** · tran ly thuyet
  **18.0%** (vs T170 58.5%) · **0/3 rate ngoai CI** (`docs/RESULT_FLATGRID.md` §1/§3/§5).
- ⚠️ **KHONG dung `FLAT_KEEPSCALE`** (1,1,1,1 giu SCALE 19.5): tran tap trung **van 58.5%**,
  conc do duoc 16.73%, FAIL rao nam (`docs/RESULT_FLATGRID.md` §6). Khong lien quan vong nay.
- Khau vi MOI (`docs/RISK_APPETITE.md` §6–§7, chot 2026-09-24): `maxDD<=40%/nam` ·
  **`UW<=250`** · `quy>=-20%` · **khong nam am** · **`conc<=15%`** · nguong bang chung **`>=2` rate
  ngoai CI** (bootstrap block-72h, 2000 rep, seed 20260905; bao **CA** `x1.21` legacy **LAN**
  `inflate(k)=sqrt(2 ln k)`).

---

## 2. Nen, num, thang do — KHOA TRUOC

**Nen (base) = KEEPLEG0** = `prof_x1_gs_t170` + **DUNG 2 dong**
`DCA_GRID_WEIGHTS=1,1,1,1`, `DCA_GRID_SCALE=6.0`.

Bundle `chuyendinh/sim-x1-2021-bundle` (= `wfo_ds_x1_2021`, `leakFreeFrom=2021-07-01`),
`sim_end_date=20251231`, **jar mac dinh cua bundle** (= jar da tao ra `t170-x1-2021` md5
`efb793e2`), khong `jar_ds`, khong override key nao khac ngoai muc 2 duoi day.
⚠️ Bundle la **snapshot**: chi chua **3** profile (`x1_c3_full`, `x1_c3_full_regime_brc`,
`x1_gs_t170`) ⇒ moi bien the duoc dien dat bang **override tren `x1_gs_t170`**, tuong duong
byte-for-byte voi mot file profile co them dung cac dong do (kernel copy profile roi ghi
`prof_run.properties`; file nay duoc luu lai o `out/<tag>/prof_run.properties` lam bang chung).

### 2.1 Nhom (1) — CONC_CAP tren nen KEEPLEG0 (2 chan)

| chan | tag | override them |
|---|---|---|
| KEEPLEG0 OFF (moc) | `kg0-g170` | — |
| KEEPLEG0 + CAP 15% | `kg0-cap` | `CONC_CAP_PERCOIN_ENABLED=1`, `CONC_CAP_PERCOIN_PCT=0.15` |

Hai chan nay **chi khac nhau DUNG 2 dong**. Do: guard co **BIND that** khong (`[CONC-PC] MODE`,
`[CONC-PC] SUMMARY blocked=N`, so dong `[CONC-PC] SKIP`), so voi moc tran: **conc · so lan bind ·
PnL · 5 rate · rao cung**. `blocked=0` ⇒ **BAT BUOC ghi ro ket qua chan nay la TAM THUONG** (cap
no-op, khong phai "cap an toan").
CI cua cap nay: **k=2 ⇒ `inflate(2)=1.177410`**.

### 2.2 Nhom (2) — GATE-SCALE tren nen KEEPLEG0 (5 chan moi + moc)

Thang **KHOA TRUOC** (6 diem, khong them/bo/doi sau khi thay so):

**{1.70 (moc = KEEPLEG0), 1.55, 1.40, 1.25, 1.10, 1.00}**

| scale | tag | trang thai |
|---|---|---|
| 1.70 | `kg0-g170` | **moc** — chay trong nhom (1) (tai su dung) |
| 1.55 | `kg0-g155` | **CHAY MOI** |
| 1.40 | `kg0-g140` | **CHAY MOI** |
| 1.25 | `kg0-g125` | **CHAY MOI** |
| 1.10 | `kg0-g110` | **CHAY MOI** |
| 1.00 | `kg0-g100` | **CHAY MOI** |

Moi chan = KEEPLEG0 + **DUNG 1 dong** `SIM_GATE_DYN_SCALE=<v>`. Co che: `>1` = gate CHAT hon (it
lenh), `<1` = LONG hon ⇒ ky vong `n` **don dieu nghich** voi scale. Khong don dieu ⇒ ghi ro co che
bat thuong.
CI cua thang nay: **k=6 ⇒ `inflate(6)=1.893018`**.

### 2.3 Nhom (3) — KEEPLEG0 + CAP + scale tot nhat (1 chan, LUAT CHOT TRUOC)

Goi `s*` = diem scale trong §2.2 cho **n CAO NHAT** ma **R-PASS khau vi MOI** (§4), **khong tinh
moc 1.70**; bang nhau ⇒ chon scale **NHO hon** (nhieu lenh hon — dung uu tien cua owner).
**Neu khong diem nao ngoai moc R-PASS** ⇒ `s* = 1.00` (diem nhieu lenh nhat) va chan (3) tro thanh
**stress test**: cap 15% co **cuu** duoc diem nhieu-lenh-nhat khong? (ghi ro cach doc nay).
Chan `kg0-cap-s<v>` = KEEPLEG0 + CAP 15% + `SIM_GATE_DYN_SCALE=<s*>`.

**Tong: 8 chan** (1 nhom-1 moc/OFF + 1 cap + 5 thang + 1 nhom-3).

---

## 3. Cong PARITY (BAT BUOC — chay TRUOC khi doc bat ky so nao)

| # | doi tuong | bat buoc | y nghia |
|---|---|---|---|
| P1 | `x1_gs_t170` ⇒ `kaggle_sim/out/t170-x1-2021/storage/printDone.csv` | md5 `efb793e2468ca3a7318da0f0ad23d4fc` | chung minh **khong dung toi baseline cu** (1,1,3,8) |
| P2 | `t170_flat_keepleg0` **khong override** ⇒ `kg0-g170` | **1,085 leg / 103,083** (va, neu byte-identical, md5 `99e42b75cf1a2142f9cd14dc72e371ba`) | chung minh nen KEEPLEG0 tren Kaggle = nen dang chay that |

**Bat ky cong nao FAIL ⇒ DUNG NGAY, bao RO, khong doc tiep so nao.** Lech P2 ma giai thich duoc
bang so (vd lech do ticker `file` vs `aerospike`, xem `docs/KAGGLE_SIM.md` §0) thi ghi ro tung
dong lech; khong giai thich duoc ⇒ DUNG.

---

## 4. Rao cung + luat quyet dinh — KHOA TRUOC

**(R-MOI)** khau vi MOI (`RISK_APPETITE.md` §6–§7) — kiem **CA theo nam LAN toan ky**:

| rang buoc | nguong |
|---|---|
| `maxDD` | `<= 40%` |
| `UW` | `<= 250` ngay |
| `qmin` (quy xau nhat) | `>= -20%` |
| nam am | **khong** (`ret%` nam `>= 0`) |
| tap trung 1 coin | `<= 15%` equity (toan ky, max theo thoi gian) |

**(R-CU)** (phu, bao cao song song): `maxDD<=30%` · `UW<=200` · `qmin>=-15%` · ko nam am · conc<=15%.

**E-PASS** (bang chung) = `>= 2/5` rate **ngoai CI cung huong TOT** **VA** `0` rate **ngoai CI
XAU**, so voi **nen KEEPLEG0 (1.70)** — doi tuong so la **cau hinh dang chay**. "Ngoai CI" = ngoai
o **CA HAI** do rong (`x1.21` legacy **va** `inflate(k)`); CI block-72h, 2000 rep, seed 20260905,
neo block co dinh `2021-07-01` (khuon `gd92xexit_score.ci_pair`). Huong TOT: `win%`/`mP|SM`/`mP|SL`/
`meanP` tang, `TSloss%` giam. Tham chieu vs **T170** bao cao kem nhung **KHONG** dung de quyet dinh.

**PASS = R-MOI PASS VA E-PASS.**

- **(c)** "muc scale cho `n` CAO NHAT ma PASS TOAN BO rao khau vi MOI" = argmax `n` tren cac diem
  **R-MOI PASS** (bao kem diem do co E-PASS hay khong). Khong diem nao ngoai moc R-MOI PASS ⇒
  tra loi **"khong co"**.
- **Ky vong ghi truoc (co the sai, phai bao dung):** `n` tang theo chieu giam scale; `maxDD`/`UW`
  **XAU dan** khi `n` tang (nhieu lenh hon, book mo lon hon); `conc` **khong** tang manh vi KEEPLEG0
  da rat phang (6.98% << 15%) ⇒ **du doan (1) CAP se gan nhu KHONG bind** (`blocked` nho/0 ⇒ ket qua
  tam thuong); **du doan (c): khong co** (diem scale thap nhat se FAIL UW >= 250 hoac maxDD).
  Neu nguoc lai ⇒ ket qua **bat ngo**, phai ghi ro.
- Ket qua duong (neu co) **chi la UNG VIEN**, can forward; **khong tu tich hop san xuat**, khong doi
  incumbent, khong sua/xoa test cu.

---

## 5. Do luong BAT BUOC cho MOI chan

1. **Co che:** `n`, `meanP/leg`, `win%`, `TSloss%`, `hold_med`, `turnover`, `SumPnL`, `equity`,
   `CAGR%`.
2. **5 rate** + CI **CA HAI** do rong vs moc KEEPLEG0 (va vs T170 phu).
3. **Rao cung R-MOI + R-CU** — CA theo nam LAN toan ky.
4. **`maxDD` · `UW`** (nam + toan ky) — output TRUNG TAM.
5. **Do venh theo nam:** `SD` va `range(max-min)` cua `ret%` nam.
6. **Bang PnL CHI TIET THEO NAM** (n · PnL USDT · ret% · maxDD% · UW · qmin% · equity) cho **moi**
   chan.
7. **`Σfunding/ΣPnL`** (do theo `n`).
8. **drop-top-K:** bo `K` leg **tot nhat** = `1`, `top1%`, `top5%` ⇒ `ΔPnL%` (moc KEEPLEG0 va diem
   scale tot nhat o (2)).
9. **conc 1 coin max theo thoi gian** (dinh nghia §7.1 `RISK_APPETITE`).

---

## 6. Thu tu bat buoc + khong lam

1. **Commit file nay + runner + scorer TRUOC** khi push kernel.
2. Cong parity §3 (P1, P2). FAIL ⇒ DUNG.
3. Push 8 chan Kaggle (toi da 5 song song; chi phi Kaggle **0**). **Khong** chay sim/JVM tren Oracle.
4. Fetch + cham diem (§5). Kiem co che (`n` don dieu theo scale).
5. `docs/RESULT_GATESCALE_KEEPLEG0.md` + tra loi (a)(b)(c)(d). Commit SAU (khong push). Don temp.

**Khong lam:** khong doi thang do; khong them num/bien the; khong chay 2026/holdout/242/shadow;
khong chay Java tren Oracle (chi `mvn -o package` neu that su can); khong `claude-run`; khong push;
khong merge `gd92-recheck`; khong tu tich hop san xuat; khong doi nguong §4 sau khi thay so.

---

## 7. Cau hoi trung tam phai tra loi (bang so)

- **(a)** Tren **nen PRODUCTION (KEEPLEG0)**, `n` tang theo gate-scale the nao? (co don dieu
  khong; `n` tai 1.00 la bao nhieu).
- **(b)** Rui ro **TOT hon hay XAU hon khi `n` tang**: `maxDD` · `UW` · `SD ret% nam` · `conc`.
- **(c)** Muc scale nao cho `n` **CAO NHAT** ma **PASS TOAN BO** rao khau vi MOI?
- **(d)** Ket qua nay **co KHAC** so voi ket qua tren nen **1,1,3,8** khong? (`PREREG_GATESCALE_SWEEP`
  / `docs/PREREG_GATESCALE_SWEEP.md` — neu **chua co** `RESULT_GATESCALE_SWEEP.md` thi ghi ro
  **"chua doi chieu duoc"**, khong suy dien.)
