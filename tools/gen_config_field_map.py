"""Phan loai field Configs theo NOI DUOC DOC — ban SUA LOI.

Hai loi cua ban dau (da bat duoc truoc khi xoa gi):
 1. Field dung BEN TRONG Configs.java viet TRAN (khong co tien to `Configs.`) => bi bao DEAD.
    Vi du DCA_GRID_WEIGHTS (dung trong dcaGridTotalWeight/dcaGridWeight) va TS_PNOPUMP_WEAK_THR
    (dung trong getter) — ca hai la LOI cua C2b ma bi xep DEAD. Xoa theo do la pha he.
 2. Xep zone theo tien to package: `ai_ml/onnx/entry/AIRejectFilter` la ENGINE (simulator goi
    truc tiep) nhung bi xep TOOL vi nam duoi ai_ml/. => AI_DYNAMIC_MULTIPLIER/MIN bi bao TOOL_ONLY.

Sua: (a) dem ca cach dung tran trong Configs.java; (b) dung ALLOWLIST file engine tuong minh.
BAI HOC: ban do nay chi de DIEU HUONG. KHONG duoc xoa field chi vi ban do noi DEAD —
phai kiem bang byte-identity (doi gia tri qua profile, so printDone) hoac doc tay cho dung.
"""
import os, re, subprocess, collections

R = "/home/ubuntu/src/BinanceFuturesJava"
SRC = R + "/src/main/java/com/binance/chuyennd"
CFG = SRC + "/tradecore/Configs.java"

# file thuoc ENGINE (duoc simulator hoac live goi truc tiep) — allowlist tuong minh
ENGINE_SIM = {
    "research/SimulatorMarketLevelTicker1MStopLoss.java", "research/OrderTargetInfoTest.java",
    "research/BudgetManagerSimple.java",
}
ENGINE_SHARED = {
    "tradecore/TradeUtils.java", "tradecore/MarketBigChangeDetector.java", "tradecore/DcaUtils.java",
    "tradecore/DcaProcessor.java", "tradecore/CoinRankManager.java", "tradecore/HoldoutSeal.java",
    "ai_ml/onnx/entry/AIRejectFilter.java",
}
def is_live(rel): return rel.startswith("trading/")

decl = re.compile(r'^\s*public\s+static\s+(?:final\s+)?[\w\[\]<>,.\s]+?\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|;)')
fields, decl_lines = [], {}
for i, line in enumerate(open(CFG, encoding="utf-8"), 1):
    m = decl.match(line)
    if m:
        fields.append(m.group(1)); decl_lines.setdefault(m.group(1), i)
fields = sorted(set(fields))

def grep_files(pat, path):
    return subprocess.run(["grep", "-rlE", "--include=*.java", pat, path],
                          capture_output=True, text=True).stdout.split()

def count_in(pat, path):
    o = subprocess.run(["grep", "-cE", pat, path], capture_output=True, text=True).stdout.strip()
    return int(o) if o.isdigit() else 0

rows = []
for f in fields:
    pat = r"Configs\." + f + r"\b"
    rels = []
    for p in grep_files(pat, SRC):
        rel = p.replace(SRC + "/", "")
        if rel in ("tradecore/Configs.java", "tradecore/DumpConfig.java"):
            continue
        if count_in(pat, p) > 0:
            rels.append(rel)
    # (a) cach dung TRAN trong chinh Configs.java, tru dong khai bao
    bare = count_in(r"(^|[^\w.])" + f + r"\b", CFG) - 1   # bo dong khai bao
    zones = set()
    for rel in rels:
        if rel in ENGINE_SIM: zones.add("SIM")
        elif is_live(rel): zones.add("LIVE")
        elif rel in ENGINE_SHARED: zones.add("SHARED_ENGINE")
        elif rel.startswith("ai_ml/"): zones.add("TOOL")
        else: zones.add("OTHER")
    if bare > 0: zones.add("SELF")
    if not zones: b = "DEAD"
    elif zones <= {"TOOL"}: b = "TOOL_ONLY"
    elif zones <= {"SELF"}: b = "SELF_ONLY"
    elif zones <= {"TOOL", "SELF"}: b = "TOOL+SELF"
    elif "SIM" in zones and "LIVE" in zones: b = "SIM+LIVE"
    elif "SHARED_ENGINE" in zones: b = "ENGINE_SHARED"
    elif "SIM" in zones: b = "ENGINE_SIM"
    elif "LIVE" in zones: b = "ENGINE_LIVE"
    else: b = "OTHER"
    rows.append((f, b, rels, bare))

cnt = collections.Counter(b for _, b, _, _ in rows)
print("so field:", len(rows)); print("phan bo:", dict(cnt))

with open(R + "/docs/CONFIG_FIELD_MAP.md", "w", encoding="utf-8") as fh:
    fh.write("# BAN DO FIELD CAU HINH — sinh tu ma nguon (tools/gen_config_field_map.py)\n\n")
    fh.write("**KHONG go tay.** Chay lai sau moi lan doi code.\n\n")
    fh.write("## ⚠️ Ban do nay chi de DIEU HUONG, KHONG de quyet dinh xoa\n\n")
    fh.write("Ban dau tien cua script nay co false positive: xep `DCA_GRID_WEIGHTS` va\n")
    fh.write("`TS_PNOPUMP_WEAK_THR` la DEAD — ca hai la LOI cua C2b. Ly do: field dung ben trong\n")
    fh.write("`Configs.java` viet TRAN (khong co tien to `Configs.`), va `AIRejectFilter` nam duoi\n")
    fh.write("`ai_ml/` nhung la ENGINE. Da sua ca hai. Nhung bai hoc giu nguyen:\n\n")
    fh.write("> Muon xoa mot field: phai chung minh bang **byte-identity** (doi gia tri qua profile\n")
    fh.write("> roi so `printDone.csv`) hoac doc tay tung cho doc. Khong xoa chi vi ban do noi DEAD.\n\n")
    fh.write("Nhan cung KHONG noi field co REACHABLE duoi mot cau hinh cu the: mot field\n")
    fh.write("`ENGINE_SIM` van co the TRO voi C2b vi bi co khac tat (vd `MAX_CONCURRENT_ORDERS`\n")
    fh.write("chi song khi `BREAKER_MODE != OFF`). Xem `docs/C2B_SPEC.md` muc 8.\n\n")
    fh.write("| nhan | nghia |\n|---|---|\n")
    fh.write("| `ENGINE_SIM` | doc trong engine backtest (`research/**`) |\n")
    fh.write("| `ENGINE_LIVE` | doc trong `trading/**` — san giao dich that |\n")
    fh.write("| `SIM+LIVE` | ca hai engine |\n")
    fh.write("| `ENGINE_SHARED` | doc trong file engine dung chung (`TradeUtils`, `AIRejectFilter`, `DcaUtils`...) |\n")
    fh.write("| `SELF_ONLY` | chi dung ben trong `Configs.java` (getter, ham dan xuat) |\n")
    fh.write("| `TOOL_ONLY` / `TOOL+SELF` | chi doc trong `ai_ml/**` tool (HPO/WFO/validation/probe) — khong anh huong engine |\n")
    fh.write("| `DEAD` | khong tim thay cho doc nao |\n\n")
    fh.write("Tong %d field. Phan bo: %s\n" % (len(rows), dict(cnt)))
    for b in ("DEAD", "SELF_ONLY", "TOOL_ONLY", "TOOL+SELF", "ENGINE_LIVE",
              "ENGINE_SIM", "SIM+LIVE", "ENGINE_SHARED", "OTHER"):
        sub = [r for r in rows if r[1] == b]
        if not sub: continue
        fh.write("\n## %s (%d)\n\n| field | doc o dau | dung tran trong Configs |\n|---|---|---|\n" % (b, len(sub)))
        for f, _, rels, bare in sub:
            w = ", ".join("`%s`" % x for x in rels[:3]) or "—"
            if len(rels) > 3: w += " +%d" % (len(rels) - 3)
            fh.write("| `%s` | %s | %d |\n" % (f, w, max(0, bare)))
print("da sinh docs/CONFIG_FIELD_MAP.md")

print("\n=== UNG VIEN XOA (DEAD / TOOL_ONLY / TOOL+SELF) — VAN PHAI KIEM TRUOC KHI XOA ===")
for f, b, rels, bare in rows:
    if b in ("DEAD", "TOOL_ONLY", "TOOL+SELF"):
        print("  %-32s %-10s bare=%-3d %s" % (f, b, max(0, bare), ", ".join(rels[:2]) or "-"))
