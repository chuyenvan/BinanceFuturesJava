# RESULT — DCA AGGREGATE CAP 0.30 + PER-COIN CAP 15%

> **Ket qua (da chay sim + cham).** Branch `module`. KHONG push. DEV 2021-07..2025-12.
> Pre-reg: `docs/PREREG_DCA_AGG_PERCOIN.md`. Baseline/parity T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc`.

## 0. Tom tat mot dong

**Per-coin 15% la cong cu DUNG — chan duoc tap trung (17.15% -> 12.51%), khong lam XAU bat ky rate
nao, khong vi pham chan nao.** Tran AGGREGATE 0.30 la **no-op** (dinh tong DCA-grid chi 16.76% < 30%,
0 lan binding) => thiet ke user chot `LOOSE_AGG30_PC15` thuc te tuong duong `LOOSE_PC15` (byte-identical).

## 1. Parity

| run | md5 printDone.csv | ghi chu |
|---|---|---|
| PARITY (T170) | `efb793e2...` | byte-identical ✓ (flag OFF) |

Flag moi `CONC_CAP_PERCOIN_ENABLED` default OFF => printDone byte-identical `efb793e2468ca3a7318da0f0ad23d4fc` ✓.

## 2. Bang 4 run (so parity)

| chi so | PARITY | LOOSE_AGG30 | LOOSE_AGG30_PC15 | LOOSE_PC15 |
|---|---|---|---|---|
| n leg (toan bo) | 1089 | 1164 | 1162 | 1162 |
| **n leg DCA** | 20 | 86 | 84 | 84 |
| win% | 88.25 | 86.86 | 86.92 | 86.92 |
| TSloss% | 9.73 | 9.97 | 10.07 | 10.07 |
| mP\|SM | 7.642 | 8.125 | 8.203 | 8.203 |
| mP\|SL | -16.992 | -12.157 | -12.905 | -12.905 |
| meanP | 5.244 | 6.103 | 6.078 | 6.078 |
| maxDD (nam) | -11.84% | -9.64% | -9.64% | -9.64% |
| UW (ngay) | 92 | 119 | 119 | 119 |
| quy xau nhat | -0.9% | -1.7% | -1.7% | -1.7% |
| nam am | khong | khong | khong | khong |
| **tap trung max 1 coin** | 9.77% | **17.15%** ✗ | **12.51%** ✓ | **12.51%** ✓ |
| aggregate DCA-grid peak | 9.19% | 16.76% | 16.76% | 16.76% |
| per-coin guard binding (blocked) | — | — | 45 | 45 |
| aggregate guard binding (skip) | — | 0 | 0 | — |
| equity cuoi | 111070 | 124238 | 122043 | 122043 |
| CAGR% | 29.27 | 32.53 | 32.00 | 32.00 |

Ghi chu: equity/CAGR KHONG phai tieu chi (chi de tham chieu).

## 3. PRIMARY = khong rate XAU ngoai CI (bootstrap B4)

CI bootstrap block-72h, 2000 rep, seed 20260905, no rong `1.21 x B4` (`B4 = sqrt(2 ln 3) = 1.4823`
=> tong `1.7936`). "XAU" = (variant - parity) ngoai CI va nguoc huong tot.

| variant | win | tsloss | mp_sm | mp_sl | meanP | so rate XAU |
|---|---|---|---|---|---|---|
| LOOSE_AGG30 | -1.390 (trong CI) | +0.232 (trong CI) | +0.483 | +4.835 | +0.860 | **0** |
| LOOSE_AGG30_PC15 | -1.327 (trong CI) | +0.335 (trong CI) | +0.562 | +4.087 | +0.834 | **0** |
| LOOSE_PC15 | -1.327 (trong CI) | +0.335 (trong CI) | +0.562 | +4.087 | +0.834 | **0** |

- Ca 3 variant deu **0 rate XAU ngoai CI** => PRIMARY PASS. (win%/TSloss% di nguoc huong nhung nam
  trong CI, giong vong truoc — trao win% lay maxDD tot hon.)

## 4. CHAN (veto)

1. **Khong nam am** ✓ (ca 4).
2. **maxDD <= 30%/nam, UW <= 200 ngay, quy >= -15%** ✓ (ca 4: maxDD -9.64..-11.84, UW 92-119, quy -0.9..-1.7).
3. **Tap trung 1 coin <= 15%** (rang buoc MOI, user chot 2026-09-17):
   - LOOSE_AGG30: 17.15% > 15% ✗ **FAIL** (aggregate 0.30 KHONG chan tap trung).
   - LOOSE_AGG30_PC15: 12.51% <= 15% ✓.
   - LOOSE_PC15: 12.51% <= 15% ✓.
4. **So leg DCA / tong n leg** (bao cao): 20/1089 -> 86/1164 (AGG30) -> 84/1162 (PC15). Tang DCA la
   muc dich cua noi nguong (khong phai loi).

## 5. CO CHE (do truc tiep printDone + log)

1. **Per-coin 15%** hoa dong DUNG: `[CONC-PC] MODE pct=0.15` + `SUMMARY blocked=45`. 45 skip = 2 cum
   deep-leg bi chan: **EVAA** (leg w=8 margin 15084, ratio 0.161) va **JELLYJELLY** (leg w=8 margin
   12775, ratio 0.161). Ket qua max tap trung giam 17.15% -> 12.51% ✓.
2. **Aggregate 0.30** la **no-op**: `[CONC-CAP] SKIP` count = 0 o ca LOOSE_AGG30 va LOOSE_AGG30_PC15.
   Dinh tong DCA-grid = 16.76% equity << 30% => tran 0.30 KHONG BAO GIO binding tren lich su nay.
3. => `LOOSE_AGG30_PC15` va `LOOSE_PC15` **byte-identical** (md5 `5cde7edd...`): khi per-coin 15% da
   bat, them aggregate 0.30 KHONG doi gi (aggregate khong binding).

## 6. Phan tich

1. **Goc loi da dung:** vong truoc xac dinh tap trung la STOCK, can tran STOCK. Tran per-coin 15%
   chan DUNG 2 deep-leg (w=8) cua EVAA va JELLYJELLY la nhung cum vuot 15% (16.1%/17.15%), ha tap
   trung ve 12.51% ma khong dong cham vao cac cum khac.
2. **Aggregate 0.30 thua:** tong DCA-grid toan so chi dat 16.76% equity (dinh), xa duoi 30%. Vi 1 coin
   (EVAA/JELLYJELLY) da chiem gan nhu toan bo tong DCA-grid, tran "tong" 0.30 khong bao gio cham truoc
   tran "1 coin" 0.15. Neu muon aggregate co y nghia, nguong phai dat ~0.15-0.17 (bang muc tap trung 1
   coin) — ngoai pham vi pre-reg nay.
3. **Chi phi cua tran:** 2 deep-leg bi chan lam mat mot phan equity (124238 -> 122043, CAGR 32.53 ->
   32.00) va mp_sl giam nhe (-12.157 -> -12.905), nhung maxDD/UW giu nguyen (-9.64%/119) va ca 5 rate
   deu nam trong CI. Day la doi chap nhan duoc de dat rang buoc tap trung.

## 7. Ket luan + quyet dinh

- **PRIMARY PASS** (ca 3, 0 rate XAU ngoai CI) + **CHAN PASS** cho LOOSE_AGG30_PC15 va LOOSE_PC15
  (tap trung 12.51% <= 15%). LOOSE_AGG30 FAIL chan tap trung (17.15%).
- Theo pre-reg muc 4.5: bao cao ca 3, **KHONG tu chon mot** (thay doi khau vi rui ro => master/user quyet).
- Khuyen nghi ky thuat (khong phai quyet dinh): `LOOSE_AGG30_PC15` (thiet ke user chot) = `LOOSE_PC15`
  ve hieu luc; aggregate 0.30 du thua, co the bo.

Commit: pre-reg `b40c9c9`.
