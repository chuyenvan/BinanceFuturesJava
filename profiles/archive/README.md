# profiles/archive — profile cua THI NGHIEM DA DONG

19 profile duoi day KHONG dung lam baseline va KHONG con co che nao trong cay doc chung
(cac co tuong ung da xoa o L7, `docs/L7_LEAN_GATE.md`). Giu lai de tai lap lich su.

| profile | thi nghiem | commit tao | ket qua |
|---|---|---|---|
| `b4_rg95`, `b4_rg95w180`, `b4_rg97` | B4 rolling-percentile gate (`SIM_GATE_ROLLING_*`) | `c1785b9` (pre-reg `a0c7ad6`) | `docs/B4_RESULT.md` |
| `x1_gd88`, `x1_gd92`, `x1_gd96`, `x1_gd2_G9*W*` (6) | GATEDYN gate truot theo phan vi | `3cdccd0` / `272d8f1` | `docs/AUDIT_GATEDYN_GD92.md` |
| `x1_c3_full_cap12`, `..._cap16`, `..._not40` | BOOKCAP tran BOOK/VON | `573dd1f` | ket qua **NULL** |
| `x1_holddca_e25`, `..._e50`, `..._e100` | HOLDDCA om bag + DCA 1:1 | `f10f6ca` | **0/3 PASS, ca ba THUA** |
| `x1_c3_full_flatgate` | FLATGATE (gate phang cua 242) | `ee00475` | `docs/RESULT_FLATGATE.md` — TE HON RO |
