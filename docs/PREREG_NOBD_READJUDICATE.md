# PREREG_NOBD_READJUDICATE — T170 co con thang khi TAT HAN phan PnL khong-qua-gate?

Pre-reg, COMMIT TRUOC khi doi bat cu thu gi. KHONG 242, KHONG `git push`, holdout 2026 nguyen ven
(`SIM_END_DATE=20251231`).

## 0. Cau hoi + tai sao can THI NGHIEM THAT (khong phai audit giay nua)
`docs/AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE.md` (commit d3379e5) da do tren giay:
- `BIG_DOWN` + `DCA_LEVEL1` la hai loai leg **KHONG chiu `GATE_DYN_SCALE`** (`EntryGate.threshold()`:
  `if (symbolPred == null) return thrBase;`).
- So "ve" BIG_DOWN **doc lap hoan toan voi gate scale** (248 leg / 124 tick / 54 ngay, giong het o ca
  T100/T130/T170) nhung **gia tri moi ve** tang theo do chat cua gate (46.6 → 53.3 → 65.5 USD/leg).
- Ti trong PnL tu phan khong-qua-gate: T100 22.7% → T130 27.9% → **T170 38.1%**.
- Tren leg-level rate entry-only, T170 hon T100 ca 3 diem uoc luong nhung **chi con 1/2 rate ngoai CI**
  (meanP roi vao trong CI).

**VA audit do DA TU BAC BO cach lam giay cho phan rui ro**: duong equity dung lai tu `cumsum(pnl)` khong
tai lap duoc ban that (T170 ALL-leg dung lai ra maxDD −6.18/UW 158 trong khi ban THAT la −11.84/UW 92),
vi bo qua unrealized mark-to-market. => **Hard-constraint khong the cham tren giay. Phai chay sim that.**

## 1. THIET KE
### 1.1 Trang thai ON = "khong co leg nao khong-qua-gate"
Tat **hoan toan** hai duong tao leg:
- **BIG_DOWN / market-signal Best-N** — vong `symbol2BUY` (Simulator dong ~332).
- **DCA_LEVEL1** — ca hai call-site `DcaProcessor.getDCA(...)` (dong ~280 va ~309).

### 1.2 **KHONG THEM FLAG MOI — dung hai knob DA CO** (sai lech co chu dich so voi de bai, giai trinh)
De bai de nghi viet flag moi `DISABLE_UNGATED_DCA` + unit test. **Toi khong lam vay**, vi khi doc code
thay hai knob co san da phu **chinh xac** hai nhom can tat, moi knob o **DUNG MOT diem quyet dinh**:

| knob | co san tu | diem quyet dinh DUY NHAT | tat duoc nhom |
|---|---|---|---|
| `SELECTOR_ONLY_ENTRY=1` | key profile (tien to `SELECTOR_`) | `Simulator:332` `if (!Configs.SELECTOR_ONLY_ENTRY) { ... }` | **BIG_DOWN** (toan bo vong market-signal) |
| `WFO_DISABLE_DCA=1` | env INFRA (`Cfg.INFRA_KEYS`) | `DcaProcessor.getDCA:25` `return emptyList()` | **DCA_LEVEL1** (ca 2 call-site) |

Ly do chon huong nay (ghi ro de master phan xu):
1. **KHONG doi mot dong code nao => rui ro pha parity = 0.** Day la gia tri lon nhat: cau hoi nay la ve
   tinh hop le cua incumbent, khong duoc de mot bug moi lam nhiem ket qua.
2. **Dung tien le cua chinh du an**: V3 (`PREREG_DCA_GATEWIDEN_V3`) va V4 (`PREREG_DCA_MORELEGS_V4`) deu
   da chay sweep bang knob co san, khong them code.
3. `grep` xac nhan moi knob chi co **mot** diem quyet dinh (ngoai dong LOG) => khong co tac dung phu an.

**Doi lai, phai co PHEP KIEM THAY THE cho unit test** (vi khong co code moi de unit-test):
**cong "ZERO-LEG"** — moi ban ON phai co **0 dong** `level=BIG_DOWN` va **0 dong** `level=DCA_LEVEL1`
trong `printDone.csv`, va **100%** dong con lai la `PREDICT_SYMBOL_TRADE`. Day la kiem chung **truc tiep
tren san pham that**, manh hon unit test cho muc dich nay. FAIL => dung, khong bao cao ket qua.

### 1.3 Ba config ON (chi khac nhau DUNG mot dong `SIM_GATE_DYN_SCALE`)
| tag | profile nguon | `SIM_GATE_DYN_SCALE` | them |
|---|---|---|---|
| `NB_T100_NOBD` | `profiles/x1_c3_full.properties` | (khong khai = 1.00) | `SELECTOR_ONLY_ENTRY=1` + env `WFO_DISABLE_DCA=1` |
| `NB_T130_NOBD` | `profiles/x1_gs_t130.properties` | 1.30 | nhu tren |
| `NB_T170_NOBD` | `profiles/x1_gs_t170.properties` | 1.70 | nhu tren |

Ba profile goc chi khac nhau DUNG dong `SIM_GATE_DYN_SCALE` (da `diff` xac nhan). Profile ON duoc sinh
bang `sed` doi `SELECTOR_ONLY_ENTRY=0` → `=1`; se `diff` de chung minh **dung 1 dong doi**.

## 2. CONG PARITY (OFF) — bat buoc PASS truoc khi chay ON
| cong | tag | profile | md5 ky vong |
|---|---|---|---|
| OFF scale 1.00 | `NB_PAR_T100` | `x1_c3_full.properties` | `dc16e4da...` (n=2559) |
| OFF scale 1.30 | `NB_PAR_T130` | `x1_gs_t130.properties` | `68510567...` (n=1580) |
| OFF scale 1.70 | — | — | **`efb793e2...` (n=1089) — DA PASS 2 lan tren CHINH jar nay** (`DS_PARITY_V3`, `DS_PARITY_V4`) |

Ghi ro: T170-OFF **khong chay lai** vi da duoc chung minh hai lan tren dung jar hien tai (HEAD `d3379e5`,
jar khong doi tu V2). `DS_PARITY_V4` con manh hon: profile T170 + 4 key DCA khai bao nhung tat, van ra
`efb793e2`. T100/T130 **chua** tung chay lai tren jar nay nen **PHAI** chay — do cung la phep kiem rang
cac thay doi code V1/V2 (flag `DCA_SIGNAL_*`, tie-break) khong dung vao hai baseline do.

## 3. CHAM DIEM (khoa truoc)
- Dataset `/home/ubuntu/wfo_ds_x1_2021`, `configs/sim_dev_file_2021.properties`, `SIM_END_DATE=20251231`,
  harness `k_runarm.sh` (them env `WFO_DISABLE_DCA=1` cho cac ban ON).
- Bootstrap **y het vong goc**: block-72h, NREP=2000, SEED=20260905, paired theo khoi.
- **Multiplicity: k = 2** (hai hypothesis THUC SU test: `T170_NOBD − T100_NOBD` va `T130_NOBD − T100_NOBD`;
  T100_NOBD la **baseline/control**, khong phai ung vien). => **`CI_INFLATE = sqrt(2·ln 2) = 1.1774`**.
  **KHONG dung 1.21** (hang so sai da phat hien o `RESULT_DCA_MORELEGS_V4` PHU LUC A: 1.21 ≈ k=2.08).
  Se bao cao **ca hai** (1.177 chinh thuc + 1.21 de doi chieu lich su) nhung **phan quyet theo 1.177**.
  Tinh bang script rieng (`nobd_score.py`); **KHONG sua `c3_rates.py`**.
- **Rang buoc cung theo TUNG NAM** (tren equity THAT tu `sim.out`): maxDD <= 15%, UW <= 120 ngay,
  ret nam >= 0, ret quy >= -5%.
- **THANG** = (>= 2 rate CHAT LUONG trong {win%, TSloss%, meanP} ngoai CI theo huong TOT) **VA**
  (rang buoc cung PASS **TAT CA** cac nam). Moi truong hop khac => **NULL**. Cham RIENG tung config.

## 4. BAO CAO BAT BUOC
1. Cong ZERO-LEG cho ca 3 ban ON (so leg BIG_DOWN / DCA_LEVEL1 phai = 0).
2. Bang day du 3 ban NOBD: n, win%, TSloss%, meanP, mMargin, maxDD%, UW, equity, CAGR% — **tong va theo nam**.
3. **So sanh voi 3 baseline GOC (co BIG_DOWN)**: mat bao nhieu % CAGR va % equity o **tung** scale.
4. CI (1.177 chinh thuc, 1.21 doi chieu) + hard-constraint **tung nam** cho tung config.
5. Verdict: **T170_NOBD co con thang T100_NOBD/T130_NOBD khong** — noi thang, khong dien giai mem.
6. Neu ranking giua 3 scale DOI khi ca ba deu khong con BIG_DOWN => neu bat.

## 5. KY VONG GHI TRUOC (de khong bao chua sau)
Tu audit d3379e5: entry-only leg-level, T170 − T100 chi con **1** rate ngoai CI. Neu sim that khop voi
phan ra tren giay thi **ky vong T170_NOBD KHONG dat nguong >=2 rate** => NULL. Nhung **hard-constraint
thi khong doan duoc** (audit da tu bac bo cach uoc luong rui ro tren giay) — day chinh la phan ma thi
nghiem nay them thong tin that so voi audit. Ghi truoc de: (a) neu dung thi khong ai phai giai thich lai;
(b) neu SAI thi do la phat hien dang chu y.

## 6. CAM KET
- Tham so muc 1.3 + luat muc 3 DA KHOA truoc khi chay. KHONG tune sau ket qua. KHONG them config.
- Cong parity OFF + cong ZERO-LEG phai PASS truoc khi bao cao bat ky ket qua ON nao.
- Day la thi nghiem **danh gia tinh hop le cua incumbent**, KHONG phai de xuat doi incumbent. Du ket qua
  the nao, viec giu/doi T170 thuoc ve master va user.
- KHONG deploy, KHONG 242, KHONG `git push`. Holdout 2026 KHONG mo.
