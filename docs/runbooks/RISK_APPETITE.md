# RISK_APPETITE — nguong RUI RO (khau vi) dung cho MOI bai cham diem

Chot 2026-09-16 boi user (chat): *"nới maxdd lên 30 và uw dãn ra 200, ci vẫn 2 cho chuẩn"*.
Day la thay doi **KHAU VI RUI RO**, KHONG phai thay doi **NGUONG BANG CHUNG**.

## 1. Nguong moi (thay nguong cu)

| rang buoc | CU | MOI |
|---|---|---|
| `maxDD` (theo nam) | <= 15% | **<= 30%** |
| `UW` (ngay) | <= 120 | **<= 200** |
| nam am | khong | khong (GIU) |
| quy xau nhat | >= -5% | **>= -15%** |
| tap trung 1 coin | "khong tang so parity" | **<= 15% equity** |
| **tap trung 1 coin** | (chua co) | **<= 15% equity** (chot 2026-09-17) |
| NGUONG BANG CHUNG | >= 2 rate ngoai CI | **GIU NGUYEN** (`>=2`, bootstrap block-72h, x1.21, 2000 rep, seed 20260905) |

> Chú thích 2026-09-19: hệ số `x1.21` ở dòng trên là hệ số **CŨ**. Vụ `DCA_ROUND_CAP` /
> `DCA_AGG_PERCOIN` cho thấy hệ số này từng bị **nhân chồng** với hệ số CI đúng. Hệ số CI chuẩn
> hoá hiện nay là **`inflate(k) = sqrt(2 ln k)`** theo `docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md`
> giai đoạn 2 (§ B.1); mọi phép chấm điểm CI **BẮT BUỘC** gọi `x1_rates.py --k <so_round>` để
> lấy đúng hệ số theo `k`, không hardcode `x1.21` hay `x1.7936`.

Ghi chu: nguong cu `UW <= 120` da duoc ghi nhan la **KHONG dat duoc** tren cua so 48 thang
(`docs/runbooks/AGENT_RUNBOOK.md` muc 3: ca hai arm FAIL — 2024=121 ngay, 2025=302/227 ngay). Nguong 200
phu hop hon voi do dai cua so hien tai.

## 2. HAU QUA — phai biet truoc khi dung

- Nguong rui ro la **cua PHU QUYET (veto)**, khong phai bang chung. Noi rong veto => chap nhan
  nhieu ung vien di tiep hon.
- Cu the: `C3_mom006` (maxDD -20.75%, UW 133 ngay, 2024Q2 -8.3%) truoc day bi **LOAI vi FAIL 3/4
  rang buoc cung**; duoi nguong MOI **no PASS cong rui ro**. No van bi loai — nhung bi loai bang
  **bang chung** (0/5 rate chat luong ngoai CI), khong con bang rui ro.
- => Tu nay cac ung vien rui ro cao nhung "chua chung minh duoc gi" se duoc dua sang vong cham
  BANG CHUNG thay vi bi chan som. Day la lua chon da duoc chap nhan (doi lay quyen thu nhieu ung
  vien hon), nhung lam tang nguy co false-positive neu vong bang chung bi noi long sau nay.
- **CANH BAO noi bo:** thay doi nay duoc dua ra SAU khi da nhin thay ket qua `DROP` (equity +28%).
  Vi vay no chi duoc dung o tang **khau vi**; **KHONG** duoc dung de dien giai lai bang chung cua
  `DROP`/`SIZE`.

## 3. Cham lai 6 bien the gan nhat duoi nguong MOI (chi doc lai `sim.out`, KHONG chay sim)

MaxDD nam xau nhat / UW dai nhat (tu `sim.out` tung run, da co san):

| bien the | maxDD nam xau nhat | UW dai nhat | nguong CU | nguong MOI |
|---|---|---|---|---|
| PARITY (T170) | -11.84 (2022) | 92 (2024) | PASS | PASS |
| SIZE `DOWN50` | -11.89 (2022) | 119 (2024) | PASS | PASS |
| SIZE `DOWN25` | -11.87 (2022) | 119 (2024) | PASS | PASS |
| SIZE `UP50` | -11.80 (2022) | 88 (2024) | PASS | PASS |
| SEL `DROP` | -11.65 (2022) | 119 (2024) | PASS | PASS |
| SEL `MIX` | -11.66 (2022) | 119 (2024) | PASS | PASS |
| SEL `DROP_TOP8` | -11.56 (2022) | 119 (2024) | PASS | PASS |

- Ca 7 dong deu **PASS ca nguong CU lan MOI**; khong nam nao am. => Noi nguong **khong doi ket qua**
  cua 6 bien the nay (chung da PASS tu truoc).
- Ket luan PRIMARY van la **0/3 rate ngoai CI** cho ca 6 bien the => **NULL, giu T170**.
  Nguong rui ro **khong the** bien mot ket qua 0/3 thanh WIN.
- Nguong MOI chi tro thanh rang buoc **binding** khi mot bien the co `maxDD > 11.89%` hoac
  `UW > 119 ngay`.

## 4. Chot bo sung 2026-09-16 22:52 (chat)

- `khong nam am`: **GIU CUNG, tuyet doi** (user: *"năm âm thì trade làm gì, gửi ngân hàng cho nhanh"*).
- `quy xau nhat`: noi tu `>= -5%` len **`>= -15%`** (user chot "15 ok"). Ly do: nhat quan voi maxDD
  30%/nam (1 quy xau nhat ~ nua drawdown nam) va van la mot cua chan co nghia.
- Bang `quy xau nhat` khong co trong `sim.out` cua 6 run gan nhat o dang doc truc tiep => **chua do
  lai** cho 6 bien the. KHONG anh huong ket luan cu (khong bien the nao cham quy).
- Khong con muc nao treo trong file nay.
- Nguong trong `docs/runbooks/AGENT_RUNBOOK.md` muc 0.3 tro ve file nay.

## 5. Chot bo sung 2026-09-17 (chat)

- **Trần tập trung 1 coin = `<= 15%` equity** (user: *"Ok với 0.3 nhưng chặn max cap trên một coin 15%"*,
  roi *"Chốt trần per coin thôi giữ nó"*). Day la rang buoc **CUNG** thay cho luat cu "khong tang so parity".
  Luu y co y thuc: nguong nay **RONG HON** thuc te cu (parity 9.77%), tuc chu dong chap nhan tap trung cao hon.
- Co che thuc thi: `CONC_CAP_PERCOIN_ENABLED`/`CONC_CAP_PERCOIN_PCT` (moi, default OFF/0.15) — chan lenh
  moi khi `(margin coin + lenh moi)/equity > pct`. Da do that: binding 45 lan, ha tap trung 17.15% -> 12.51%.
- Tran aggregate `CONC_CAP_AGG_DCA_PCT` **BO** (dat 0.30 nhung binding 0 lan — dinh lich su chi 16.76%).

## 5. Chot bo sung 2026-09-17 (chat)

- **Tap trung 1 coin <= 15% equity** (user chot: *"chặn max cap trên một coin 15%"*). Day la rang
  buoc rui ro MOI, ap cho moi bai cham diem. Co che thuc thi: guard `CONC_CAP_PERCOIN_ENABLED`/
  `CONC_CAP_PERCOIN_PCT` (0.15) trong `SimulatorMarketLevelTicker1MStopLoss.createOrder` — chan HAN
  khi `(margin hien co cua coin + margin leg moi) / equity > 15%`. Da duoc prove trong
  `docs/result/RESULT_DCA_AGG_PERCOIN.md` (tap trung 17.15% -> 12.51%, khong lam XAU rate nao).
- Tran aggregate `CONC_CAP_AGG_DCA_PCT` giu nguyen mac dinh 0.45; user chot 0.30 cho experiment nay
  nhung tren lich su no KHONG binding (dinh tong DCA-grid 16.76% < 30%).

## 6. Chot bo sung 2026-09-24 (chat)

- **`maxDD` (theo nam): noi tu `<= 30%` len `<= 40%`** — user: *"toi san sang voi maxdd co the len 30 hay
  40% deu ok no chi la so lo tam thoi ko chay duoc tk vi danh 1x"*.
- Ly do da **kiem chung bang du lieu** (`printDone.csv`, T170, khong phai suy doan):
  - `margin/(quantity*entry)` = **1.0000 tren 1089/1089 leg** ⇒ **1x isolated**, khong co don bay.
  - **Max concurrent margin = 52,151 USDT** tai 2025-10-11 = **~47% equity** luc do ⇒ exposure < 1x
    ⇒ **khong the chay tk** ⇒ drawdown la **tam thoi** (dung nhu user noi).
- **BO SUNG 2026-09-24 (do lai T100 + GD92, `docs/result/RESULT_FRAGILITY_N.md`)**:
  - `lv = 1.0000` tren **2559/2559 (T100)** va **2632/2632 (GD92)** ⇒ 1x tren **ca ba nen**.
  - Max concurrent margin: **T170 55,964** (2025-10-11) · **T100 67,248** (2025-11-07) ·
    **GD92 66,998** (2025-10-11) ⇒ **54.7% / 57.1% / 57.5% equity**. **0 moc** nao co
    `exposure > equity` ⇒ **khong the chay tk** ca ba nen.
  - ⇒ Menh de *"1x nen khong chay duoc tk"* **duoc XAC NHAN bang du lieu**, khong con la suy doan.
  - **Nhung kenh MAT THAT khong nam o 1x**: (a) **tap trung 1 coin** — T100 **28.51%** equity
    (coin CUDIS, 2025-11-12) **vuot tran 15%**; GD92 14.38%; T170 9.77% (FTT). (b) **ngay su kien**:
    2022-05-12 (LUNA) −12.06% / −13.55% equity **trong 1 ngay**. (c) **funding = n×eps**
    (`Σfunding/ΣPnL`: T170 −2.76% · T100 −10.73% · GD92 −6.33%).
  - **Delist gan nhu khong xay ra trong mau**: chi **1/6,280 leg** co `pnl/margin <= -0.90`
    (T100, −2,088 USDT = 2.4% tong PnL). ⇒ "lo tam thoi" dung trong mau nay, nhung **do la may**
    (FTT 2022-11: giu toi 9.8% equity, stop cat trong ~1 ngay).
- **LUU Y QUAN TRONG**: `maxDD` **khong phai rang buoc dang chan ket qua nao**.
  T170 −11.84% · T100 −16.13% · GD92 −16.55% — **ca ba deu duoi ca tran CU 30%**.
  ⇒ Noi nguong nay **khong mo khoa them ung vien nao** cho den hien tai.
  Rang buoc **dang chan that su** la **`UW <= 200`** (T100 248 · GD92 278) va **tap trung 1 coin
  `<= 15%`** (T100 27.08–28.35%).
- **TREO — cho user chot** (ghi ro, khong tu quyet):
  1. `quy xau nhat`: giu `>= -15%` hay noi `>= -20%` cho tuong thich voi maxDD 40%/nam?
  2. `UW <= 200`: giu hay noi?
  3. tap trung 1 coin `<= 15%`: giu hay noi? — Ghi chu: khi danh 1x, **tap trung 1 coin la nguon
     MAT THAT duy nhat** (coin delist ve 0 khi dang giu thi khong hoi phuc duoc), nen khuyen nghi GIU.
- Cac phan con lai cua file (khong nam am; quy xau nhat; tap trung 1 coin; NGUONG BANG CHUNG >=2 rate
  ngoai CI) **giu nguyen**.

## 7. Chot bo sung 2026-09-24 (lan 2, chat) — khau vi sau khi XAC NHAN 1x

User: *"tap trung <= 15% la cai gi. quy ok giam 20% cung ok uu tien dai han hon. uw co the keo len 250
uu tien ca nam van lai on dinh hon co khi keo dai ra se tim duoc mo hinh keo no lai nhung ko uu tien.
uu tien nhat la nhieu lenh de on dinh"*

| rang buoc | truoc | MOI (2026-09-24, lan 2) |
|---|---|---|
| `maxDD` (theo nam) | <= 30% | **<= 40%** (xem §6) |
| `quy xau nhat` | >= -15% | **>= -20%** |
| `UW` (ngay) | <= 200 | **<= 250** |
| `tap trung 1 coin` | <= 15% equity | **<= 15% (GIU)** |
| `nam am` | khong | **khong (GIU)** |
| NGUONG BANG CHUNG | >= 2 rate ngoai CI | **GIU NGUYEN** |

- **Uu tien chien luoc (ghi de nho)**: *"uu tien nhat la NHIEU LENH de ON DINH"*; uu tien **dai han**
  hon ngan han; `UW` dai "co the keo dai ra se tim duoc mo hinh keo no lai" nhung **KHONG uu tien**.

### 7.1 `tap trung 1 coin` nghia la gi (dinh nghia chinh thuc)

- Tai **MOI thoi diem**: `tong margin cua TAT CA vi the dang mo tren MOT coin / equity hien tai <= 15%`.
  Vi chien luoc danh **1x** nen `margin == notional` ⇒ day la **ty trong von thuc su dat vao 1 coin**.
- Co che: `CONC_CAP_PERCOIN_ENABLED` / `CONC_CAP_PERCOIN_PCT` — chan **leg MOI** khi
  `(margin coin + margin leg moi)/equity > pct`. (DCA grid `1,1,3,8` don vao 1 coin nen tran nay
  chinh la **phanh cua DCA**.)
- **Ly do ton tai**: khi danh 1x, **day la KENH MAT THAT DUY NHAT** — coin delist/ve 0 khi dang giu thi
  **khong hoi phuc**, khac han `maxDD`/`UW` (chi la lo TAM THOI).
- Do duoc (`RESULT_FRAGILITY_N`): T170 **9.77%** (FTT) · GD92 **14.38%** (JELLYJELLY) ·
  **T100 28.51%** (CUDIS, 2025-11-12) · `hn-g-cp` (GD92+CAP) **15.29%**.

### 7.2 HAU QUA NGAY — cham lai cac nen nhieu lenh duoi khau vi MOI

| nen | maxDD | UW | conc | ket qua duoi khau vi MOI |
|---|---|---|---|---|
| T170 | -11.84% | 92 | 9.77% | PASS het |
| T100 | -16.13% | 248 | **27.23%** | **FAIL chi vi TAP TRUNG** (UW 248 <= 250 da dat) |
| GD92 | -16.55% | **278** | 14.38% | FAIL vi UW (>250) |
| GD92+CAP (`hn-g-cp`) | -17.65% | 249 | **15.29%** | **FAIL chi vi TAP TRUNG** (vuot 0.29 diem) |

- ⇒ Tu nay **tap trung 1 coin la rang buoc RUI RO DUY NHAT con chan** cac nen nhieu lenh.
- ⇒ **NHUNG**: ha rao rui ro **KHONG tao ra bang chung** — ca 4 nen van **0/5 rate ngoai CI**.
- ⇒ Doi trong: tran tap trung **lam GIAM n** (chan leg moi). Voi uu tien "nhieu lenh", day la **danh doi
  phai do bang so** (dang do: `PREREG_CONC_CAP_HIGHN.md`).

### 7.3 SUA CACH DO `maxDD` (2026-09-24) — BAT BUOC dung MTM MOC PHUT

`docs/result/RESULT_INTRADAY_DD.md` (commit `ea6bf11`) chung minh **chuoi equity DAILY da CHE MAT drawdown
that**. Nguyen nhan: `BudgetManagerSimple: Update` chi xuat **1 moc/ngay tai 00:00Z** (1644 dong/run),
con `unPMin` la **day CHAY TICH LUY** chu khong phai day trong ngay ⇒ khong co duong MTM trong ngay
trong log. Da **tai tao MTM moc phut tu du lieu 1m** (2,367,360 moc) va kiem chung
(`min_chay(unP_low)` vs `unPMin` lech **0.001–0.003%**).

| nen | maxDD NGAY | **maxDD PHUT (that)** | Δ | UW ngay / phut |
|---|---|---|---|---|
| T170 | -11.84% | **-19.96%** | **-8.12 pp** | 92 / 144.4 |
| KEEPLEG0 | -11.21% | **-19.96%** | **-8.75 pp** | 147 / 147.2 |
| T100 | -16.13% | **-26.26%** | **-10.13 pp** | 248 / 248.2 |
| GD92 | -16.55% | **-24.30%** | **-7.76 pp** | 278 / 277.8 |

- **Nam xau nhat theo MTM la 2025** voi T170/KEEPLEG0 (-19.96%), KHONG phai 2022 ⇒ moi bang
  `maxDD theo nam` cu **dang xep sai nam xau nhat** (2025: daily -4.23% vs phut -19.96%).
- Cua so **2025-10-09..13**: daily **0.00%** vs phut **-19.57…-20.70%** (bien the `bar.low` -23.7…-24.5%).
- **8/10 cu giam intraday lon nhat la HE THONG** (coin xau nhat chi dong gop 9–18% do sau, 13–30 coin
  mo cung luc); chi 2022-11 (FTT 32%) la don le. ⇒ Rui ro duoi la **thi truong**, khong phai 1 coin/1 lenh.
- **Khong verdict nao doi huong** (0/4 doi PASS/FAIL): tran `maxDD <= 40%` van PASS (max -26.26%),
  nhung **bien an toan that MONG hon nhieu** (T100 chi con cach tran **13.7 pp** thay vi 23.9 pp).
- **TU NAY**: moi bao cao `maxDD`/`UW` **PHAI dung MTM moc phut**; so daily chi de doi chieu.
- **Gioi han**: chua mo hinh margin-call/thanh ly ⇒ moi so la **CAN DUOI** cua rui ro that;
  1 quan sat lich su, **khong co CI**.

## 8. Chot bo sung 2026-09-26 (chat) — TRẦN GROSS EXPOSURE 70 % (CỨNG) + PHÍ CHUẨN 0,6 %/vòng

Nguon: **quyet dinh owner 26/09 05:35** (nguon duy nhat). Bang chung: `docs/result/RESULT_CAP70_FEE06.md`
· pre-reg `docs/prereg/PREREG_CAP70_FEE06.md` (`6f37caa`) · quyet dinh `docs/decisions/DECISION_GROSS_CAP70_FEE06.md`.

| rang buoc | CU | MOI (2026-09-26) |
|---|---|---|
| **gross exposure** | *khong co tran*; chi **quan sat** 54–58 % | **<= 70 % equity — CUNG / binding** |
| **phi chuan nghien cuu** | **0,8 %/vong** | **0,6 %/vong** |

- **`maxDD` / `UW` / `quy xau nhat` / `tap trung 1 coin` / `nam am` / NGUONG BANG CHUNG**: **GIU NGUYEN**
  (nhu §7 / §6). Muc nay chi **THEM** tran gross + **THAY** moc phi.
- **THAY THE cu the**: (1) cau "quan sat gross 54–58 %" tro thanh **mo ta**, **KHONG** con la nguong — nguong
  binding la **70 %**; (2) moi con so o cac vong truoc dung **0,8 %** phai doc lai la **moc cu**; moc
  nghien cuu tu nay la **0,6 %** (0,8 % van bao de doi chieu).
- **He qua da do (pool P32, duong RE, KHONG build lai):**
  - **MUC:** `break-even fee` ro top-K = **1,2006 %/vong (K=8) → 1,2678 % (K=32)** ⇒ o **0,6 %** net/coin
    ≈ **+0,60…+0,67 %/vong** (o 0,8 % ≈ +0,40…+0,47 %). Ro duong o ca 2 muc.
  - **`K`:** moi Δ cua `K ∈ {10,12,16,32}` vs `K=8` — ca `net/tick` sau size lan `net/1dv-gross` — **TRONG CI**
    o **ca 3 cach ap tran** va **ca 4 muc phi** ⇒ **khong co `K*` do duoc** ⇒ **GIU `K = 8`**.
  - **Delta alpha xep hang = 0 BAT BIEN theo phi**: `Δ(f=0,004) = Δ(f=0,006) = Δ(f=0,008)` tren **24/24 cap**
    (lech `0,00e+00`); o `f=0,006` **0/12 cap** ngoai CI ⇒ **phi 0,6 % khong cuu duoc `Δ = 0`**.
  - **Kiem hop le o `f=0,006`:** `A45 − 45deploy = +0,00035` (TRONG CI); `V5 − V1 = −0,00018` (TRONG CI).
- **Tran 70 % la rang buoc BUOC CO, khong phai cho phep noi** (do tren pool P32, neo POST-HOC `2,0 %/lenh`
  tren coin PHAN BIET): `gross_TB(K=8) = 48,8 %` nhung `gross_max = 84 %` ⇒ neu siet **moi tick <= 70 %** thi
  **size ≈ 0,83× hien hanh** (≈ 1,67 % equity/lenh thay 2,0 %), TB tut con **40,7 %**. Cach chuan hoa theo TB
  (size 1,43×) giu TB = 70 % nhung **max van 120,5 %** ⇒ **KHONG** dat tran CUNG.
- ⚠️ **Gioi han (bat buoc doc):** con so gross la **quy doi POST-HOC** (neo `2,0 %/lenh` tren coin phan biet);
  ban neo tren **so VI THE `e_t`** cho `K=8` = **821 %** (vo ly) ⇒ chi **ti le giua cac `K`** doc duoc.
  **CHUA** mo hinh hoa de-dup live / DCA nhieu chan / tran size·notional / funding. `net/tick` tuyet doi la
  **MO HINH**, khong phai equity LIVE.
- **Viec treo (chua lam, khong tu quyet):** (1) chon cach ap tran (A hay B) + them guard gross-exposure
  (tuong tu `CONC_CAP_PERCOIN_*`) va **prove binding** bang sim **shadow** — khong cham LIVE;
  (2) `CONC_CAP_PERCOIN_PCT = 0,15` **giu nguyen** (noi `K` khong lam xau tran 1-coin: ti trong ≈ 1/so coin
  phan biet, 4,1 % → 3,0 % khi 8 → 12 ⇒ rang buoc bind la **gross**, khong phai conc).

### §8-ERRATA (2026-09-27) — **TRẦN GROSS 70 % KHÔNG BIND**: bỏ kết luận "size ≈ 0,83×"

`RESULT_GROSS_ASYMMAP` (`42a48cd`) đối chiếu 2 công thức `gross` và kết luận:
số cũ **48,82 %** lấy `d` (số vị thế đồng thời) từ **POOL ỨNG VIÊN** (`d_mean 24,409`) trong khi **ledger thật** `d_mean = 0,531` (lệch **46×**).
Theo **định nghĩa đúng (ledger)**: gross K=8 = **1,74 % TB / 49,53 % MAX** ⇒ **< `U_MAX=0,60`** ⇒ **trần 70 % KHÔNG bind** ở K=8.
⇒ **BỎ** câu *"size phải co còn 0,83× để vừa trần 70 %"* (đã ghi trước đó dựa trên `gross_max[pool]=84 %`). Xem `docs/analysis/RULERS_CURRENT.md` §11.
