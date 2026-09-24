#!/usr/bin/env python3
"""COST_BREAKEVEN — VIEC (1): audit MO HINH CHI PHI cua sim + DIEM HOA VON theo nhom lenh.

Pre-reg: docs/prereg/PREREG_COST_LIQUIDITY.md (commit cd5e758, chot TRUOC khi do).

KHONG chay Java (khong dung jar sim): moi so lieu lay tu
  * doc CODE (hằng số chi phí)                       — src/main/java/.../Configs.java, OrderTargetInfoTest.java, DumpConfig.java
  * doc PROFILE dang chay                            — profiles/x1_gs_t170.properties
  * doc printDone.csv cua run T170 (cot profit/pnl/margin/funding/quantity/entry/level)
  * neon MOM15 anchor_mom15.npz (sinh boi range4h_topk.py, commit 62e01bf)
  * so da CONG BO cua 2 ung vien gan nhat (RESULT_FUNDING_TOPK_K13.md, RESULT_RANGE4H_TOPK.md)

Thuan Python, khong 2026, khong push.
"""
import os
import re
import json

import numpy as np
import pandas as pd

REPO = os.environ.get("CB_REPO", "/home/ubuntu/src/BinanceFuturesJava")
OUT = os.environ.get("LQ_OUT", "/tmp/liq_decide")
PRINT_DONE = os.environ.get(
    "LQ_PRINT_DONE", "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv")
ANCHOR = os.path.join(OUT, "anchor_mom15.npz")
COST_GRID = (0.0002, 0.0005, 0.0010, 0.0015)     # round-trip: maker / 0,05 / taker 0,10 / 0,15
COST_NAME = ("0,02% (maker)", "0,05%", "0,10% (taker)", "0,15%")
DEV_START = 1640995200 // 60                      # 2022-01-01
DEV_END = 1767225600 // 60                        # 2026-01-01
BASE = 1609459200 // 60                           # 2021-01-01
BLOCK_MIN = 72 * 60

REPORT = []
def say(s=""):
    REPORT.append(s)
    print(s)


# ---------------------------------------------------------------- doc CODE
def read_constants():
    cfg = open(os.path.join(REPO, "src/main/java/com/binance/chuyennd/tradecore/Configs.java"),
               encoding="utf-8").read().splitlines()
    prof = open(os.path.join(REPO, "profiles/x1_gs_t170.properties"), encoding="utf-8").read()

    def line_of(pat):
        for i, l in enumerate(cfg, start=1):
            if re.search(pat, l):
                return i, l.strip()
        return None, None

    def val(pat):
        for l in cfg:
            m = re.search(pat, l)
            if m:
                return m.group(1)
        return None

    rows = []
    for name, pat, fn in (
        ("RATE_FEE", r"RATE_FEE\s*=\s*([0-9.]+)f", "Configs.java:%(ln)d"),
        ("SLIPPAGE_RATE", r"SLIPPAGE_RATE\s*=\s*([0-9.]+)f", "Configs.java:%(ln)d"),
        ("APPLY_SLIPPAGE", r"APPLY_SLIPPAGE\s*=\s*(true|false)", "Configs.java:%(ln)d"),
        ("APPLY_FUNDING_FEE", r"APPLY_FUNDING_FEE\s*=\s*(true|false)", "Configs.java:%(ln)d"),
        ("FUNDING_MARK_NOTIONAL", r"FUNDING_MARK_NOTIONAL\s*=\s*(true|false)", "Configs.java:%(ln)d"),
        ("FUNDING_SCALE", r"FUNDING_SCALE\s*=\s*([0-9.]+)f", "Configs.java:%(ln)d"),
        ("RATE_PROFIT_STOP_MARKET", r"RATE_PROFIT_STOP_MARKET\s*=\s*([0-9.]+)f", "Configs.java:%(ln)d"),
        ("LEVERAGE_ORDER", r"LEVERAGE_ORDER\s*=\s*([0-9]+)", "Configs.java:%(ln)d"),
    ):
        ln, txt = line_of(pat)
        rows.append((name, val(pat), (fn % {"ln": ln}) if ln else "-"))

    # cac hang so CHI co trong profile dang chay
    prof_rows = []
    for k in ("SIM_RATE_PROFIT_STOP_MARKET", "SIM_APPLY_FUNDING", "SIM_FUNDING_MARK",
              "SIM_RATE_FEE", "SIM_SLIPPAGE_RATE", "SIM_FUNDING_SCALE", "CAPITAL_START",
              "DCA_GRID_ENABLED", "DCA_GRID_WEIGHTS", "SIM_GATE_DYN_SCALE", "TS_GIVEBACK_RATIO",
              "SIM_LOSER_TIME_STOP_HOURS", "SIM_BREAKER_MODE"):
        m = re.search(r"^%s=(.*)$" % k, prof, re.M)
        prof_rows.append((k, m.group(1).strip() if m else "**KHONG CO trong profile (dung default/env)**"))

    # noi AP cost
    appl = {}
    for pat, key in ((r"priceEntry\s*\*\s*Configs\.RATE_FEE", "RATE_FEE x1 chan (tren notional entry)"),
                     (r"Configs\.SLIPPAGE_RATE\s*\*\s*2", "SLIPPAGE_RATE x2 chan"),
                     (r"2\s*\*\s*Configs\.RATE_FEE\s*\+\s*2\s*\*\s*Configs\.SLIPPAGE_RATE",
                      "in 2*RATE_FEE + 2*SLIPPAGE (DumpConfig)")):
        n = 0
        for root, _, files in os.walk(os.path.join(REPO, "src/main/java")):
            for f in files:
                if f.endswith(".java"):
                    n += len(re.findall(pat, open(os.path.join(root, f), encoding="utf-8",
                                                  errors="ignore").read()))
        appl[key] = n
    return rows, prof_rows, appl


def part_constants():
    rows, prof_rows, appl = read_constants()
    say("## 1. Kiểm kê hằng số chi phí (đọc CODE, không suy đoán)")
    say("")
    say("### 1a. Hằng số trong `Configs.java`")
    say("")
    say("| Hằng | Giá trị trong code | file:dòng |")
    say("|---|---|---|")
    for n, v, src in rows:
        say("| `%s` | `%s` | `%s` |" % (n, v, src))
    say("")
    say("### 1b. Khoá trong `profiles/x1_gs_t170.properties` (profile ĐANG chạy của run T170)")
    say("")
    say("| Khoá | Giá trị |")
    say("|---|---|")
    for k, v in prof_rows:
        say("| `%s` | `%s` |" % (k, v))
    say("")
    say("### 1c. Nơi ÁP chi phí (số lần xuất hiện trong `src/main/java`)")
    say("")
    say("| Mẫu áp | Số site |")
    say("|---|---|")
    for k, v in appl.items():
        say("| %s | %d |" % (k, v))
    say("")


def part_verify(df):
    """Chung minh mo hinh chi phi THUC SU ap cho 1089 lenh."""
    t = df
    fee_slip = (t["quantity"] * t["entry"] * 0.002
                + t["quantity"] * t["entry"] * 0.003 * 2.0) / t["margin"] * 100.0
    fund_pct = -t["funding"] / t["margin"] * 100.0
    cost_impl = t["ret_gross"] - t["ret_net"]
    resid = cost_impl - (fee_slip - fund_pct)
    say("## 2. Mô hình chi phí ĐANG được áp cho đúng 1089 lệnh T170 (kiểm chứng số học)")
    say("")
    say("`calTp()` = `qty*(tp-entry) − qty*entry*RATE_FEE − qty*entry*SLIPPAGE_RATE*2 − calFundingFee()`")
    say("(nguồn `research/OrderTargetInfoTest.java` → gọi tại `TraceOrderDone.printOrderTestDone`).")
    say("")
    say("| Đại lượng | Giá trị quan sát |")
    say("|---|---|")
    say("| `fee_slip` mỗi lệnh = (qty·entry·0,002 + qty·entry·0,003·2)/margin | mean **%.6f%%**, median %.6f%%, min %.6f%%, max %.6f%% |"
        % (fee_slip.mean(), fee_slip.median(), fee_slip.min(), fee_slip.max()))
    say("| **= RATE_FEE + 2·SLIPPAGE_RATE** (hằng, không theo dữ liệu) | **0,800000%** |")
    say("| số lệnh khớp 0,800000%% (|Δ| < 1e-6 pp) | **%d/%d** |" % (int((np.abs(fee_slip - 0.8) < 1e-6).sum()), len(t)))
    say("| `funding_pct` mỗi lệnh (âm = ĐƯỢC thu) | mean **%+.4f%%**, median %+.4f%% |"
        % (fund_pct.mean(), fund_pct.median()))
    say("| `cost_implied` = gross%% − net%% | mean **%.4f%%**, median %.4f%% |" % (cost_impl.mean(), cost_impl.median()))
    say("| **sai số đóng** `cost_implied − (0,80 − funding_pct)` | max|Δ| = **%.3e pp** ⇒ mô hình đóng kín |"
        % float(np.abs(resid).max()))
    say("")
    return cost_impl, fee_slip, fund_pct


def part_groups(df, cost_impl, fee_slip, fund_pct):
    say("## 3. Điểm hòa vốn theo NHÓM LỆNH (T170) — equal-weight mỗi lệnh")
    say("")
    say("`net(c) = mean(ret_gross) − c`, `c` = chi phí **round-trip** mỗi lệnh; `c*` = `mean(ret_gross)`")
    say("(mức chi phí tối đa còn hòa vốn). Cột `net(0,80%)+funding` = net THỰC của run (đối chiếu).")
    say("")
    hdr = ("| Nhóm lệnh | n | mean gross (%) | funding thực (%/lệnh) | slip_proxy (%) | "
           + " | ".join("net@%s" % c for c in COST_NAME) + " | **c\\*** | %lệnh gross>c\\* | net thực (0,80%%+funding) |")
    say(hdr)
    say("|---|" + "---|" * (5 + len(COST_GRID) + 3))
    groups = [("TOAN BO 1089 lenh", df)] + [(str(lv), df[df["level"] == lv])
                                           for lv in df["level"].value_counts().index]
    out = []
    for name, g in groups:
        mg = float(g["ret_gross"].mean())
        n = len(g)
        fnd = float(fund_pct[g.index].mean())
        slip = float(np.nanmean(g["slip_proxy"])) * 100.0
        nets = [mg - c * 100.0 for c in COST_GRID]
        net_real = float(g["ret_net"].mean())
        share = float((g["ret_gross"] > mg).mean() * 100.0)
        out.append(dict(name=name, n=n, gross=mg, fund=fnd, slip=slip, cstar=mg,
                        net_real=net_real, nets=nets, share=share))
        say("| **%s** | %d | %+.3f | %+.4f | %.4f | %s | **%+.3f%%** | %.1f | %+.3f%% |"
            % (name, n, mg, fnd, slip, " | ".join("%+.3f%%" % x for x in nets), mg, share, net_real))
    say("")
    for c, o in zip(COST_NAME, out):
        pass
    say("**Đọc bảng:** cột `c*` là mức chi phí round-trip lớn nhất mà nhóm còn dương. Nếu `c*` **lớn hơn** mức")
    say("chi phí thực tế (0,04–0,10%) thì nhóm còn cửa; nếu `c*` **nhỏ hơn** thì chết vì chi phí.")
    return out


def part_anchor():
    z = np.load(ANCHOR)
    holds = [int(x) for x in z["holds"]]
    j = holds.index(1440)
    m_min = z["m_min"].astype(np.int64)
    dev = (m_min >= DEV_START) & (m_min < DEV_END)
    valid = ((z["m_valid"] >> j) & 1) == 1
    sel = dev & valid
    base = (z["m_raw"][j].astype(np.float64) - z["m_slip"].astype(np.float64)
            - z["m_fund"][j].astype(np.float64))
    b = base[sel]
    slip = z["m_slip"].astype(np.float64)[sel]
    say("## 4. Neo MOM15 (HOLD 24h, M-LEVEL k=1) — bộ đo còn lực?")
    say("")
    say("`base = mean(raw24 − slip − fund)` KHÔNG phí (đúng định nghĩa vòng trước); `net(c) = base − c`.")
    say("")
    say("| Đại lượng | Giá trị |")
    say("|---|---|")
    say("| n sự kiện DEV | **%d** |" % len(b))
    say("| **base (chưa phí)** | **%+.4f%%** |" % (100 * b.mean()))
    say("| slip TRUNG BÌNH mỗi sự kiện (proxy 0,5·(h−l)/c nến vào) | **%.4f%%** |" % (100 * slip.mean()))
    say("| funding trung bình mỗi sự kiện | **%+.4f%%** |" % (100 * z["m_fund"][j].astype(np.float64)[sel].mean()))
    for c, nm in zip(COST_GRID, COST_NAME):
        say("| net @ %s | **%+.4f%%** |" % (nm, 100 * b.mean() - c * 100))
    g4 = abs((100 * b.mean() - 0.10) - 1.6690) < 0.05
    say("| **[G4] đối chiếu `net @0,10%%` phải = +1,6690%% (±0,05pp)** | **%s** |"
        % ("OK" if g4 else "**LECH => VOID**"))
    say("| **c\* (chi phí round-trip tối đa còn dương)** | **%.3f%%** |" % (100 * b.mean()))
    say("")
    return dict(name="MOM15 (M-LEVEL k=1, 24h)", n=len(b), gross=100 * b.mean(),
                cstar=100 * b.mean(), slip=100 * slip.mean(),
                nets=[100 * b.mean() - c * 100 for c in COST_GRID], ok=bool(g4))


def part_candidates():
    """2 ung vien gan nhat — doc SO DA CONG BO (khong chay lai)."""
    say("## 5. 2 ứng viên gần nhất — đối chiếu (số ĐÃ CÔNG BỐ, không chạy lại)")
    say("")
    say("Với luật quay vòng: `cost = phí + slip` (slip cố định, KHÔNG đổi theo phí) ⇒")
    say("`gross_excl_fee = net@0,10% + 0,10%` và `net(c) = gross_excl_fee − c`, `c* = gross_excl_fee`.")
    say("")
    say("| Ứng viên | nguồn | net @0,05%% | net @0,10%% | net @0,15%% | gross_excl_fee = c* | slip/chu kỳ | Kết luận |")
    say("|---|---|---|---|---|---|---|---|")
    # (ten, net@0.0005, net@0.0010, net@0.0015, slip, nguon)
    cand = [
        ("FUNDING_TOPK_ROTATE K=20 (8h, LONG funding nhỏ nhất)",
         -0.1260, -0.1460, -0.1660, 0.1495, "RESULT_FUNDING_TOPK_K13.md §4"),
        ("FUNDING_TOPK_ROTATE K=5 (đối chiếu K lớn hơn)",
         -0.1999, -0.2223, -0.2447, 0.2660, "RESULT_FUNDING_TOPK_K13.md §4"),
        ("RANGE4H_TOPK K=10 (4h, LONG biên độ rộng nhất)",
         -0.3939, -0.4254, -0.4569, 0.3857, "RESULT_RANGE4H_TOPK.md §4"),
    ]
    out = []
    for nm, n5, n10, n15, slip, src in cand:
        gross = n10 + 0.10
        out.append(dict(name=nm, n=0, gross=gross, cstar=gross, slip=slip,
                        nets=[gross - c * 100 for c in COST_GRID], ok=None, src=src))
        say("| %s | %s | %+.4f%% | %+.4f%% | %+.4f%% | **%+.4f%%** (ÂM) | %.4f%% | **NO-GO — không mức phí nào cứu được** |"
            % (nm, src, n5, n10, n15, gross, slip))
    say("")
    say("⇒ Cả 2 ứng viên có `c*` **ÂM** ⇒ kể cả **phí exchange = 0** (và thậm chí phí âm tới "
        "%.3f%%/%.3f%%) vẫn âm: **nút thắt là `slip` (proxy 0,5·range nến), không phải phí**."
        % (out[-1]["cstar"], out[0]["cstar"]))
    say("")
    return out


def part_reality(df, cost_impl, fee_slip):
    say("## 6. So với THỰC TẾ — mô hình chi phí có khớp không?")
    say("")
    say("**Mốc thực tế dùng được trong repo** (đọc docs, không tự bịa):")
    say("- `docs/prereg/PREREG_HARNESS_CONTROL.md:38` — harness PYTHON: *\"taker `0.0005×2 = 0,10%` + slippage 0,5×(high−low)/entry + funding\"*.")
    say("- `docs/prereg/PREREG_HEDGE_OVERLAY_A.md:117` — *\"taker_fee = 0,05% … slippage = 1bp\"*.")
    say("- `docs/design/DESIGN_HEDGED_BOOK.md:112` — *\"taker fee 0,05%, slippage 1bp\"*.")
    say("- ⇒ Binance USDⓈ-M: **maker 0,02%/chân, taker 0,05%/chân** ⇒ round-trip **0,04%** (maker) / **0,10%** (taker).")
    say("")
    say("**Bằng chứng slip ĐO ĐƯỢC (fill thật):** đã quét repo — `ledger.csv` ở gốc là dữ liệu TEST tổng hợp")
    say("(symbol AAA/CCC, ts=0, `HedgeBook` mock), **không** phải fill thật; `docs/analysis/PHASE1_DECISION_SURFACE.md:40`")
    say("ghi rõ *\"CON THIEU: gia tri fee/slippage BASE chua xac nhan\"*; `docs/plan/ROADMAP.md:67` để ngỏ")
    say("*\"Calibrate chi phí từ log product thật khi có\"* ⇒ **repo KHÔNG có số slip thực.**")
    say("Nên phần slip chỉ có **proxy** `0,5·(h−l)/c` — và proxy này đo **biến động**, KHÔNG đo **tác động thị trường**.")
    say("")
    say("| Thành phần | Sim T170 đang tính | Harness Python | Thực tế (Binance) | Sim / thực tế |")
    say("|---|---|---|---|---|")
    say("| Phí (round-trip) | **0,200%** (`RATE_FEE`×1 chân) | 0,100% (taker×2) | **0,040%** maker / **0,100%** taker | **2,0×** vs maker·taker trung bình, **5,0×** vs maker |")
    say("| Slip (round-trip) | **0,600%%** (`SLIPPAGE_RATE`×2) | 2 × proxy 1m (`%s`/chân đo được → ~%.2f%%%% RT) | ~0,02–0,10%% (ước lượng công nghiệp cho coin thanh khoản) | **6–30×** (nếu lấy 0,02%%) |"
        % ("%.2f%%" % (100 * np.nanmean(df['slip_proxy'])), 200 * float(np.nanmean(df["slip_proxy"]))))
    say("| Tổng round-trip | **0,800%%** + funding | ≈%.2f%%%% + funding | 0,04–0,20%% | **4–20×** |"
        % (100 * (0.001 + 2 * float(np.nanmean(df["slip_proxy"])))))
    say("| Funding | CÓ (`SIM_APPLY_FUNDING=true`, `SIM_FUNDING_MARK=true`) | CÓ | CÓ | khớp |")
    say("")
    say("**Hai phát hiện audit (không phải suy đoán):**")
    say("")
    say("1. **`SIM_RATE_PROFIT_STOP_MARKET` KHÔNG phải chi phí.** Đó là *khoảng dời SL tối thiểu* (ngưỡng arm")
    say("   trailing stop), `Configs.java:169`. Nó **được chỉnh VÌ** chi phí round-trip (comment `Configs.java:164`")
    say("   ghi: nâng 0,01032 → 0,03 vì round-trip cost 0,008 ăn hết lợi nhuận của mọi lệnh thoát dưới ~0,016)")
    say("   — nhưng bản thân nó **không trừ vào PnL**. Đếm nó vào chi phí là **sai gấp đôi**.")
    say("2. **Mâu thuẫn nội bộ về con số round-trip.** `Configs.java:164` và `DumpConfig.java:68` —")
    say("   dòng `derived.cost_roundtrip=%.5f (fee %.5f x2 + slip %.5f x2)` — **in ra 0,010**, trong khi")
    say("   `calTp()` (đường THẬT) trừ **`RATE_FEE`×1 + `SLIPPAGE_RATE`×2 = 0,008**. Đã kiểm trên 1089 lệnh:")
    say("   `fee_slip` mean = **%.6f%%** ⇒ đường thật là **0,80%%**, con số 1,00%% chỉ là dòng in. **Đừng đọc DumpConfig để lấy chi phí.**"
        % fee_slip.mean())
    say("")
    say("**Bằng chứng số:** `cost_implied` = gross − net = **0,800%% − funding_pct**; mean = **%.4f%%**"
        % cost_impl.mean())
    say("(≈0,80%% trừ phần funding thu về). Slip proxy 1m trung bình mỗi lệnh = **%.4f%%**/chân, tức"
        % (100 * float(np.nanmean(df["slip_proxy"]))))
    say("proxy đã **%.1f×** mức `SLIPPAGE_RATE=0,30%%`/chân mà sim trừ — **hai harness bất đồng cả về hướng**."
        % (float(np.nanmean(df["slip_proxy"])) / 0.003))
    say("")


def main():
    say("=== COST_BREAKEVEN — VIEC (1) ===")
    say("Pre-reg docs/prereg/PREREG_COST_LIQUIDITY.md, commit cd5e758. Thuan Python.")
    say("")
    part_constants()
    df = pd.read_csv(PRINT_DONE)
    df["ret_net"] = 100.0 * df["pnl"] / df["margin"]
    df["ret_gross"] = df["profit"].astype(float)
    zp = os.path.join(OUT, "legs.npz")
    slip = None
    if os.path.exists(zp):
        z = np.load(zp, allow_pickle=True)
        slip = z["slip_proxy"].astype(np.float64)
        df["slip_proxy"] = slip
    cost_impl, fee_slip, fund_pct = part_verify(df)
    grp = part_groups(df, cost_impl, fee_slip, fund_pct)
    anc = part_anchor()
    cand = part_candidates()
    part_reality(df, cost_impl, fee_slip)
    say("## 7. Tổng hợp điểm hòa vốn")
    say("")
    say("| Nhóm | mean gross (%) | net @0,02% | @0,05% | @0,10% | @0,15% | c\\* (%) | cửa? |")
    say("|---|---|---|---|---|---|---|---|")
    allg = [anc] + cand + grp
    for g in allg:
        v = "CÒN CỬA (c\\* ≥ 0,10%)" if g["cstar"] >= 0.10 else (
            "cửa hẹp (0,04 ≤ c\\* < 0,10)" if g["cstar"] >= 0.04 else
            ("CHỈ còn nếu phí ≈ 0" if g["cstar"] > 0 else "**KHÔNG CỬA — c\\* ÂM**"))
        say("| %s | %+.3f | %s | **c\\*=%+.3f** | %s |"
            % (g["name"], g["gross"], " | ".join("%+.3f%%" % x for x in g["nets"]), g["cstar"], v))
    say("")
    with open(os.path.join(OUT, "report_cost.txt"), "w") as f:
        f.write("\n".join(REPORT) + "\n")
    print("\nSAVED", os.path.join(OUT, "report_cost.txt"))


if __name__ == "__main__":
    main()
