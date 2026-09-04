# CEIL_RESULT — tran oracle theo TUNG outcome, va lo hong CHAN TRONG nhan

Chay 2026-09-04, Oracle CPU. Script `research/analysis/ceil.py`, log `/home/ubuntu/cov/CEIL.out`.
**MO TA (descriptive), khong phai kiem gia thuyet** — khong chon ung vien, khong verdict
pass/fail, chi la tinh chat cua NHAN + du doan da co. Vi vay khong can pre-reg.
4,595 tick / 772,013 dong / 303 khoi 72h. CHI DEV.

## 0. VI SAO LAM

Con so duoc dan khap noi — "**S1 bat 17.8% tran oracle**, `vol_7d` tho bat 19.8% => khoang trong
80% la du dia cua **thong tin moi**, khong phai model" — duoc do tren **`g1lite`**. Ma chinh
`SELECTOR_FEATURES` C.4 da chung minh `g1lite` **BI VOL-CONFOUND** (`vol_7d` tho **thang** S1
tren no, -0.0210 YYY). Tran tren **`g1_replay`** (nhan sat tien that) **CHUA TUNG duoc tinh.**

## 1. TRAN KHAC NHAU RAT XA GIUA CAC OUTCOME

`edge5` = trung binh theo tick cua (mean outcome top-5 − mean outcome pool). `K=5`, tick >= 10 dong.

| outcome | tran ORACLE | S1 edge5 | **S1 bat** | CI95 | `vol_7d` bat | G015 bat |
|---|---|---|---|---|---|---|
| `g1lite` (nhan train) | +38.04% | +6.67% | **17.5%** | [13.1%, 22.1%] | **20.0%** | 11.6% |
| `maxFav_72h` | +38.35% | +7.78% | 20.3% | [15.9%, 24.8%] | **23.3%** | 13.8% |
| **`g1_replay`** (exit that) | **+22.93%** | **+1.18%** | **5.2%** | **[1.4%, 8.9%]** | 4.9% | 3.4% |
| `retEnd_72h` (lai cuoi ky) | +30.12% | -0.04% | **-0.1%** | [-6.0%, +5.8%] | 1.4% | 1.2% |

**Hieu S1 − `vol_7d` tho** (ghep cap, khoi 72h, kem hieu chinh do phu `f=1.21` cua `COV_RESULT`):

| outcome | d | CI95 | sau hieu chinh f=1.21 | |
|---|---|---|---|---|
| `g1lite` | -0.93% | [-3.43, +1.30] | [-3.78, +1.92] | chua 0 |
| `g1_replay` | **+0.06%** | [-0.93, +1.01] | [-1.11, +1.24] | chua 0 |
| `retEnd_72h` | -0.46% | [-2.49, +1.37] | [-2.88, +1.96] | chua 0 |
| `maxFav_72h` | -1.17% | [-3.56, +0.98] | [-3.91, +1.56] | chua 0 |

## 2. BA KET LUAN

1. **Con so "17.8% tran" la tren nhan SAI.** Tren `g1_replay` — nhan gan tien nhat — S1 chi bat
   **5.2%**, khong phai 17.5%. Tuc **du dia lon hon 3.4 lan** so voi cach ke cu: khoang trong la
   **~95%**, khong phai 80%. Moi phat bieu "he da gan can du dia model" dua tren 17.8% **phai
   doc lai**.
2. **Nhung lap luan TUONG DOI thi van dung:** tren `g1_replay`, `vol_7d` tho bat **4.9%** so voi
   S1 **5.2%** — **hoa** (d=+0.06%, CI chua 0). Nen cau "mot feature duy nhat da dat xap xi cung
   muc" **van dung**, chi la ca hai deu o **~5%**, khong phai ~18-20%.
3. **`retEnd_72h`: S1 bat -0.1%, CI [-6.0%, +5.8%]** — dung bang 0. Khong model nao xep hang duoc
   loi suat cuoi ky. Toan bo edge selector nam o **hinh dang duong gia**.

## 3. 🔴 LO HONG CHAN TRONG — cai nay nang hon ca muc 1

Doc `research/pipeline/path_labels.py` va doi chieu profile dang chay:

| | nhan `g1_replay` / `g1lite` | he C2b THAT |
|---|---|---|
| **chan trong** | **72 gio (3 ngay)**, `NH=72` | loser giu toi **168 gio (7 ngay)** (`SIM_LOSER_TIME_STOP_HOURS=168`) |
| arm | **5%** (`ARM=0.05`) | **7%** (`SIM_RATE_PROFIT_STOP_MARKET=0.07`) |
| tran nha | 8% (`CAP=0.08`) | 8% STRONG / **3% WEAK** (chia theo `symbolPred>0.29`) |
| luoi | **1 gio** (72 close gio) | **1 phut** |
| het chan trong | MTM close cuoi | khong ap dung |

**He qua nghiem trong:** `docs/C2B_SPEC.md §5.1` da xac dinh **`STOP_LOSS_DONE` = time-stop 7 ngay**
(khong co SL truoc arm), va do la **15% lenh, TB -19% DEV / -25% VAL, tong -28,977 / -37,314**.
Nhung **nhan dung de cham moi thi nghiem selector dong lai o ngay thu 3**.

=> **Toan bo phan LO cua he xay ra SAU khi cua so nhan da dong.** Nghia la moi phep do edge da
chay (rank-IC, edge5, permutation importance, FS 16 ung vien, S1CUT 5 bo cat, tran oracle o muc 1)
**deu khong the phat hien mot cai thien nao o phia tranh lo** — vi outcome cham diem ket thuc
truoc khi lo duoc hien thuc hoa.

Day la cach giai thich nghich ly "edge khong mong" vs "baseline mong": **hai ben do hai cua so
khac nhau**. Tang xep hang do 72h (chi thay phia lai), tang equity do toan bo (gom lo ngay thu 7).
Ca hai dung, va chung **khong noi ve cung mot thu**.

## 4. VIEC RE NHAT, GIA TRI CAO NHAT — de xuat

Sinh lai nhan voi **`NH=168`** (khop time-stop that) va **`ARM=0.07`** (khop profile), roi:
(a) do lai tran + %bat; (b) do lai rank-IC cua S1/G015/`vol_7d`; (c) chi khi (a)(b) cho thay nhan
moi KHAC nhan cu moi train lai S1 tren no. Chi phi: vong lap vector tren ma tran da nap — phut,
khong phai gio; **khong can train** cho buoc (a)(b).
⚠️ Phai pre-reg truoc buoc (c) (do la phep so model). Buoc (a)(b) la mo ta, khong can.
⚠️ `path_labels.py` doc `CLOSES_1H.bin` cat tai 2025-01-01 va **lay mau pool**
(`p15>=0.006` giu het + 25% ngau nhien phan con lai) => keo chan trong 72->168 se giam so dong
dung duoc o duoi.
