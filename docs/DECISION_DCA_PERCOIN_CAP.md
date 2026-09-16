# DECISION — DCA per-coin cap 15% (CHOT 2026-09-17)

User chot (chat 2026-09-17): *"Chốt trần per coin thôi giữ nó"*.
Trang thai: **CHOT lam ung vien** — CHUA vao san xuat (moi flag con default OFF, chua forward test).

## 1. Cau hinh duoc chot

Nen = profile `x1_gs_t170` + cac key sau:

| key | gia tri | ghi chu |
|---|---|---|
| `DCA_GRID_LEVELS` | `-0.30,-0.55,-0.75` | noi tu `-0.50,-0.75,-0.90` (ladder DCA song day: 20 -> 84 leg) |
| `CONC_CAP_PERCOIN_ENABLED` | `true` | guard MOI (truoc day chua co) |
| `CONC_CAP_PERCOIN_PCT` | `0.15` | tran tap trung 1 coin = 15% equity (rang buoc cung moi) |
| `CONC_CAP_AGG_DCA_ENABLED` | `false` | **BO** — da do: binding 0 lan (dinh lich su 16.76% << 0.30) |
| `DCA_GRID_WEIGHTS` | `1,1,3,8` | giu nguyen |
| `DCA_GRID_SCALE` | `19.5` | giu nguyen |

Bien the chot = `LOOSE_PC15` (md5 `printDone.csv`: `5cde7edd…`), byte-identical voi `LOOSE_AGG30_PC15`
(vi tran aggregate khong bao gio binding).

## 2. Bang chung (docs/RESULT_DCA_AGG_PERCOIN.md, commit `7aa21a7`)

| chi so | PARITY (T170) | CHOT (`LOOSE_PC15`) |
|---|---|---|
| n leg (DCA leg) | 1089 (20) | 1162 (84) |
| tap trung 1 coin | 9.77% | **12.51%** (<=15% ✓) |
| maxDD / UW | -11.84% / 92 ngay | -9.64% / 119 ngay |
| equity / CAGR | 111,070 / 29.27% | 122,043 / 32.00% |

- **Co che guard per-coin chay dung**: binding **45 lan** (chan 2 deep-leg `w=8` cua EVAA + JELLYJELLY,
  ratio 0.161 > 0.15), keo tap trung **17.15% -> 12.51%**.
- **0/5 rate chat luong XAU ngoai CI** (bootstrap block-72h x1.21, 2000 rep, seed 20260905).
- Chan cung bar moi (`docs/RISK_APPETITE.md`): khong nam am, `maxDD<=30%`, `UW<=200`, `quy>=-15%`,
  `tap trung 1 coin<=15%` — PASS het.
- Cong parity: flag OFF => `printDone.csv` byte-identical `efb793e2468ca3a7318da0f0ad23d4fc`.

## 3. Trung thuc ve muc do bang chung

- Day la **cai thien KIEM SOAT RUI RO**, **KHONG phai bang chung co alpha**: cac rate **trung tinh**
  (khong xau, nhung **khong rate nao tot hon co y nghia**).
- `maxDD -11.84 -> -9.64` la **so mot-lan-quan-sat** (khong co CI) — khong duoc doc la "tot hon ve thong ke".
- **DEV-only** => day la **UNG VIEN**. Xac nhan that phai o **forward/holdout**.
- Trần 15%/coin **RONG HON** thuc te cu (parity 9.77%) => da **chu dong chap nhan tap trung cao hon**.

## 4. Chua lam (co y thuc)

- Chua set default trong code (cac flag van default OFF).
- Chua dua vao profile production / chua chay parity tren cau hinh production.
- Chua forward test.
