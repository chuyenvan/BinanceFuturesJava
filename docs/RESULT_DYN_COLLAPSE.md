# RESULT_DYN_COLLAPSE — Dynamic (path) collapse probe

Pre-reg: PREREG_DYN_COLLAPSE (commit 8b9078b). Script: research/analysis/dyn_collapse_probe.py.
CHI DO. Khong sim/overlay/deploy/tune. Khong cham 242/push. Holdout 2026 nguyen (ledger toan entry<=2025).

## Setup thuc te
- Ledger PST<=2025: n=1996, all BUY, collapse_total=123 (STOP_LOSS_DONE & profit<=-20).
- Tai t=entry+D chi lay lenh CON MO (te_ms>t). SURVIVORSHIP (n giam theo D):
  D=4h n=1418 (collapse 123 = 8.7%), D=12h n=1004 (122 = 12.2%), D=24h n=720 (122 = 16.9%).
  => Gan het collapse (~122/123) van con mo den 24h: collapse la qua trinh CHAM; winner nhanh thoat som,
     nen ty le collapse tang theo D la do mau thu hep, khong phai tin hieu manh len.
- Coverage close_t + featv2_t = 100% ca 3 D. NaN cells trong feats: 643/498/329 (nho, XGB xu ly native).
- deltaOI: featv2 khong co OI LEVEL raw -> dung oi_delta24h/oi_delta_3d (causal tai t) + d_oi_z (delta z ke tu entry).

## AUC walk-forward (XGB, purge 72h, 16 fold quy 2022-2025)
| D    | A price-path | B oi/funding | C full | C-A    | H0 mean+-sd | verdict |
|------|-------------|--------------|--------|--------|-------------|---------|
| 4h   | 0.656       | 0.589        | 0.632  | -0.024 | 0.445+-0.025| DONG    |
| 12h  | 0.623       | 0.526        | 0.607  | -0.016 | 0.445+-0.031| DONG    |
| 24h  | 0.701       | 0.555        | 0.656  | -0.044 | 0.471+-0.031| DONG    |

## Single-feature AUC OI/funding (huong)
- Manh nhat deu la DELTA-ke-tu-entry: d_oi_z 0.696/0.673/0.685 (huong -), d_ls_toptrader 0.648/0.673/0.687 (+),
  d_ls_global 0.627/0.661/0.677 (+). oi_z_t ~0.62-0.64.
- Funding gan vo dung: fund_last/fund_sum_3d/fund_z_30d/fund_trend/fund_flip ~0.50-0.55.
- d_oi_z huong AM (OI-z tut cung khi collapse) = ECHO cua gia tut, khong phai tin hieu doc lap => trong mo hinh
  da co price-path, cac delta nay khong them gia tri (xem C<A).

## VERDICT: DONG (moi D) — theo luat PREREG muc QUYET DINH
- GREEN can: C>=0.65 VA C-A>=0.03 VA C>H0(+3sd). 
- C>=0.65 chi dat o D=24h (0.656); nhung C-A<0 o CA BA D (C luon THAP hon A) => dieu kien "OI/funding them
  gia tri NGOAI gia" FAIL hoan toan.
- (B) oi/funding ONLY ~0.53-0.59, khong bao gio gan 0.65 => OI/funding KHONG dan.
- Nguoc lai (A) price-path la tin hieu chinh va MANH len theo D (24h AUC=0.701, tren H0 ro).
=> Ket luan pre-reg nhanh DONG: gia da du; them OI/funding chi lam loang. Trailing (cat theo gia) da nam
   dung tin hieu collapse; theo doi/cat theo OI-funding khong bo sung gi tren T170. Khong co tin hieu SOM
   ngoai gia. KHONG lam overlay follow-up.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
