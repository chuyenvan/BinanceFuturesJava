# RESULT — DCA ROUND CAP (siet tong margin moi luot DCA)

> ⚠️ **ĐÍNH CHÍNH 2026-09-19**: Verdict PRIMARY của round này đổi từ **PASS sang FAIL**. Hệ
> số CI dùng trong bản gốc (`1.7936`) bị **nhân chồng** hai lớp hệ số (`1.21 × 1.4823`); hệ số
> đúng cho `k=3` là **`1.4823`** (= `sqrt(2 ln 3)`). Rescore lại ở hệ số đúng: biến thể
> `CAP10_LOOSE` và `LOOSE` có `win%` lệch **−1.33pp / −1.39pp**, CI95 `[−2.42,−0.04]` /
> `[−2.49,−0.12]` — **NGOÀI CI, rate XẤU** ⇒ **PRIMARY FAIL** (trước đây báo PASS chỉ vì CI quá
> rộng). Kết luận loại bỏ round này (do vi phạm chặn tập trung `max1coin`) **được củng cố
> thêm**, không đảo ngược. Chi tiết đầy đủ + bảng rescore: `docs/AUDIT_CI_INFLATE_STANDARDIZATION.md`
> § B.2 ("RESCORE — CA 2 ROUND ĐỔI TỪ PRIMARY PASS SANG PRIMARY FAIL"). Nội dung bên dưới GIỮ
> NGUYÊN để truy vết, KHÔNG xoá/sửa.

> **Ket qua (da chay sim + cham).** Branch `module`. KHONG push. DEV 2021-07..2025-12.
> Pre-reg: `docs/PREREG_DCA_ROUND_CAP.md`. Baseline/parity T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc`.

## 0. Tom tat mot dong

**NULL — giu T170.** Tran 10%/luot (CAP10) **KHONG binding** tren lich su (DCA flow luon < 10%
equity/luot). Noi nguong `-0.30/-0.55/-0.75` tang DCA **4.2x** (20 -> 84-86 leg) va **TANG tap
trung** (9.77% -> 12.5% / 17.2% equity 1 coin) => vi pham CHAN #3. Tran "moi luot" (FLOW) **khong
chan duoc** tap trung (STOCK) — tap trung tich luy QUA nhieu luot, moi luot deu <= 10%.

## 1. Parity + co che

| run | md5 printDone.csv | ghi chu |
|---|---|---|
| PARITY | `efb793e2...` | byte-identical ✓ (flag OFF) |
| CAP10 | `efb793e2...` | byte-identical ✓ (cap khong cat) |

- PARITY OFF = byte-identical `efb793e2468ca3a7318da0f0ad23d4fc` ✓ (xac nhan ca truoc va sau fix).
- Co che chay dung: `[DCA-CAP] MODE rank=drop capPct=0.1` + `SUMMARY` moi run.

## 2. Bang 3 bien the (so parity)

| chi so | PARITY | CAP10 | CAP10_LOOSE | LOOSE |
|---|---|---|---|---|
| n leg (toan bo) | 1089 | 1089 | 1162 | 1164 |
| **n leg DCA** | 20 | 20 | 84 | 86 |
| win% | 88.25 | 88.25 | 86.92 | 86.86 |
| TSloss% | 9.73 | 9.73 | 10.07 | 9.97 |
| mP\|SM | 7.642 | 7.642 | 8.203 | 8.125 |
| mP\|SL | -16.992 | -16.992 | -12.905 | -12.157 |
| meanP | 5.244 | 5.244 | 6.078 | 6.103 |
| maxDD (nam) | -11.84% | -11.84% | -9.64% | -9.64% |
| UW (ngay) | 92 | 92 | 119 | 119 |
| quy xau nhat | -0.9% | -0.9% | -1.7% | -1.7% |
| nam am | khong | khong | khong | khong |
| **tap trung max 1 coin** | **9.77%** | 9.77% | **12.51%** | **17.15%** |
| cap luot: rounds/roundsCut/legsCut | — | 14/0/0 | 250/37/45 | (tat) |
| equity cuoi | 111070 | 111070 | 122043 | 124238 |
| CAGR% | 29.27 | 29.27 | 32.00 | 32.53 |

Ghi chu: equity/CAGR KHONG phai tieu chi (chi de tham chieu). CAP10 = parity byte-identical.

## 3. PRIMARY = khong rate XAU ngoai CI (bootstrap B4)

CI bootstrap block-72h, 2000 rep, seed 20260905, no rong `1.21 x B4` (`B4 = sqrt(2 ln 3) = 1.4823`
=> tong `1.7936`). "XAU" = (variant - parity) ngoai CI va nguoc huong tot.

| variant | win | tsloss | mp_sm | mp_sl | meanP | so rate XAU |
|---|---|---|---|---|---|---|
| CAP10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | **0** |
| CAP10_LOOSE | -1.327 (trong CI) | +0.335 (trong CI) | +0.562 | +4.087 | +0.834 | **0** |
| LOOSE | -1.390 (trong CI) | +0.232 (trong CI) | +0.483 | +4.835 | +0.860 | **0** |

- Ca 3 variant deu **0 rate XAU ngoai CI** => PRIMARY PASS (khong lam XAU co y nghia thong ke).
- Luu y: win% va TSloss% di NGUOC huong (xau hon) nhung NAM TRONG CI (khong y nghia) — noi nguong
  trao win% lay maxDD tot hon (dang "giao dich nhieu hon, win thap hon nhung cat lo tot hon").

## 4. CHAN (veto)

1. **Khong nam am** ✓ (ca 4 deu khong nam am).
2. **maxDD <= 30%/nam, UW <= 200 ngay, quy >= -15%** ✓ (ca 4 PASS: maxDD -9.64..-11.84, UW 92-119,
   quy -0.9..-1.7).
3. **Tap trung max % equity 1 coin KHONG tang so parity** ✗:
   - CAP10: 9.77% = parity ✓.
   - CAP10_LOOSE: 12.51% > 9.77% ✗ **FAIL**.
   - LOOSE: 17.15% > 9.77% ✗ **FAIL**.
4. **So leg DCA / tong n leg** (bao cao): 20/1089 -> 84/1162 (CAP10_LOOSE), 86/1164 (LOOSE). Tang
   DCA la muc dich cua noi nguong (khong phai loi).

## 5. Phan tich

1. **CAP10 = NULL (no-op).** DCA flow lich su luon < 10% equity/luot (dinh 4.50% equity o 6 leg
   2025-10-11). Tran 10% khong cat gi => byte-identical parity.
2. **Noi nguong -0.30 tang DCA 4.2x** (20 -> 84-86 leg), cai thien maxDD (-11.84 -> -9.64) va
   CAGR (29.3 -> 32.0/32.5) NHUNG tang tap trung.
3. **Goc loi = tap trung STOCK, tran luot = FLOW.** Tran "moi luot <= 10%" khong chan duoc tap
   trung vi 1 coin tich luy margin QUA nhieu luot (leg dau o luot 1, DCA-1 o luot 2, DCA-2 o luot
   3 — moi luot deu <= 10% nhung tong cum > 10%): LOOSE dinh EVAA 17.15% (3 leg), CAP10_LOOSE cat
   leg sau (w=8) nen ha EVAA xuong duoi GAL 12.51% nhung van > parity 9.77% (vi cum GAL toan leg
   nong, khong luot nao vuot 10%).
4. **Con duong dung neu muon chong tap trung** la guard STOCK `CONC_CAP_AGG_DCA` (da co san, default
   OFF) — cap TONG margin nam trong leg DCA, khong phai tran "moi luot".

## 6. Ket luan + quyet dinh

- **PRIMARY PASS** (ca 3, khong rate XAU ngoai CI) nhung **CHAN tap trung FAIL** cho CAP10_LOOSE va
  LOOSE. CAP10 PASS nhung la **no-op** (cap khong binding).
- Theo pre-reg muc 4.5: PASS = co che dung + khong rate XAU + het CHAN. => **Khong variant nao PASS
  thuc chat** (CAP10 NULL; CAP10_LOOSE/LOOSE vi pham tap trung).
- **Khong tu chon variant.** Bao ca ca 3 de master/user quyet (day la thay doi khau vi rui ro).

Commit: pre-reg `38a7984`, code `a89fc95`, fix giu-thu-tu `43fe27e`.
