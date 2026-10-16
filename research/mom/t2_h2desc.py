"""T2-MOM mo ta HAU KIEM (khong phai phep thu, khong doi verdict): do ben cua H2/H3 de quyet co dang forward hay dong han X1."""
import logging
import os
import sys

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/mom"))
import t2_mom as T  # noqa: E402

log = logging.getLogger("t2desc")
for tag, kw in [("base", {})] + [(f"off{k}", {"offset": k}) for k in range(1, 7)] + [("lb14", {"lb": 14}), ("lb28", {"lb": 28}), ("cost2x", {"ca": 0.002, "cb": 0.0012})]:
    df = T.run(**kw)[0]
    for h in ("H2", "H3"):
        s = T.summ(df[h])
        log.info("DESC %-6s %s full %+.2f E %+.2f C %+.2f maxdd %+.2f yrs+ %d/6 %s", tag, h, s["sh_full"], s["sh_E"], s["sh_C"], s["maxdd"], s["years_pos"], s["years"])
df = T.run()[0]
log.info("DESC boot_p H2 %.3f H3 %.3f | dsr H2 %s", T.boot_p(df.H2), T.boot_p(df.H3), T.dsr(df.H2))
