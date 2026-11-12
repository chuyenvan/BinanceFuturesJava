"""R4u BIG_DOWN-SEL: va DetectEntrySignal2TradeNormal (giu LF/UTF-8, assert moi cho thay dung 1 lan)."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("patch")
P = "src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java"
s = open(P, "rb").read().decode("utf-8")


def rep(old, new):
    global s
    c = s.count(old)
    assert c == 1, (c, old[:80])
    s = s.replace(old, new)


# 1) bien pool S1 cua tick (truoc khoi leg market-signal)
rep("""            if (levelChange != null) {
                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;""",
    """            // [V12 R4u BIG_DOWN-SEL 2026-11-09] pool S1 cua tick: tinh 1 LAN (leg market-signal can truoc vong selector);
            //   vong selector ben duoi dung lai => scoreAll/S1-dump van 1 lan/tick. Profile TAT => khong dung.
            TreeMap<Float, String> s1PoolTick = null;
            boolean s1PoolTried = false;
            if (levelChange != null) {
                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;""")

# 2) leg market-signal: c3 => thu tu S1-map nhu sim
rep("""                Set<String> symbol2BUY = new HashSet<>();
                symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbol(numberOrder,
                        symbol2FinalTicker, symbolLocked, sortedCandidates));
""",
    """                Set<String> symbol2BUY = new HashSet<>();
                if (com.binance.chuyennd.tradecore.selector.LiveProfileC3.on()) {
                    // [V12 R4u BIG_DOWN-SEL] c3: chon coin THEO DUNG sim (bins S1-map, Simulator:368-380), KHONG theo
                    //   tier1Score (Funding/net015-raw) — xem BigDownSelect. Profile TAT => duong cu nguyen van.
                    s1PoolTick = buildS1Pool(time);
                    s1PoolTried = true;
                    symbol2BUY.addAll(bigDownSelectS1(time, levelChange, numberOrder, s1PoolTick,
                            symbol2FinalTicker, symbolLocked));
                } else {
                    symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbol(numberOrder,
                            symbol2FinalTicker, symbolLocked, sortedCandidates));
                }
""")

# 3) vong selector dung lai pool S1 cua tick
rep("""                TreeMap<Float, String> s1Pool = buildS1Pool(time);""",
    """                TreeMap<Float, String> s1Pool = s1PoolTried ? s1PoolTick : buildS1Pool(time);   // [V12 R4u]""")

# 4) tach phan tinh thuan cua buildValueMap
head = """    private boolean buildValueMap(long time, TreeMap<Float, String> s1Pool) {
        selMapPred.clear();
"""
tail = """        if (a == null) return false;
        selMapPred.putAll(a.symbolPred);
"""
i = s.index(head)
j = s.index(tail, i)
assert s.count(head) == 1 and s.count(tail) == 1
mid = s[i + len(head):j]
assert mid.rstrip().endswith("LiveBuildMap.assign(uni, sc, pw);"), mid[-120:]
pure = mid.replace("return false;", "return null;")
newfn = ("""    /**
     * [V12 R4u] phan TINH THUAN cua {@link #buildValueMap}: KHONG ghi selMapPred/LATEST_SEL_MAPPRED, KHONG log [MAP] tick.
     * null = chua san sang (caller PHAI bo, khong thay bang gia tri khac).
     */
    private com.binance.chuyennd.tradecore.selector.LiveBuildMap.Assigned computeValueMap(TreeMap<Float, String> s1Pool) {
""" + pure + """        return a;
    }

""")
s = s[:i] + newfn + head + """        com.binance.chuyennd.tradecore.selector.LiveBuildMap.Assigned a = computeValueMap(s1Pool);
""" + s[j:]

# 5) ham chon leg market-signal (dat ngay truoc buildS1Pool doc)
anchor = """    /**
     * [C3-SHADOW] Pool xep theo score S1 (thap = tot) tren DUNG tap coin ma selector live da"""
rep(anchor, """    /**
     * [V12 R4u BIG_DOWN-SEL 2026-11-09] leg market-signal (BIG_DOWN/SMALL_*) cua c3: top-n theo symbolPred S1-map (= gia tri
     * gate GV-I cua vong selector), bo coin dang giu (vi the that {@code symbolLocked} HOP so c3 theo nguon
     * {@link GatePreFilter} — quy uoc sim isSymbolRunning), bo coin thieu ticker, KHONG loc maxThres — y het
     * {@code MarketBigChangeDetector.getTopSymbolArray} cua sim. Chua co S1/thang map => 0 leg (fail-closed, KHONG
     * quay ve tier1/pNoPump). Mot dong {@code [BIG_DOWN-SEL]} cho parity.
     */
    private java.util.List<String> bigDownSelectS1(long time, MarketLevelChange levelChange, int numberOrder,
                                                   TreeMap<Float, String> s1Pool,
                                                   Map<String, KlineObjectSimple> tickers, Set<String> symbolLocked) {
        com.binance.chuyennd.tradecore.selector.LiveBuildMap.Assigned a =
                com.binance.chuyennd.tradecore.selector.EntryPoolGate.usable(s1Pool) ? computeValueMap(s1Pool) : null;
        if (a == null) {
            LOG.warn("[BIG_DOWN-SEL] {} level={} n={} CHUA co S1/thang net015-map -> 0 leg (KHONG thay bang tier1/pNoPump)",
                    Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, numberOrder);
            return java.util.Collections.emptyList();
        }
        final java.util.function.Predicate<String> held = GatePreFilter.heldPredicate(GatePreFilter.source(
                        com.binance.chuyennd.tradecore.selector.LiveProfileC3.on(),
                        com.binance.chuyennd.c3live.runtime.C3LiveHook.enabled(),
                        com.binance.chuyennd.c3live.runtime.C3LiveHook.liveAdapter()),
                BudgetManager.getInstance().symbol2Pos.keySet());
        java.util.List<String> sel = com.binance.chuyennd.tradecore.selector.BigDownSelect.select(a.symbolPred,
                numberOrder, s -> symbolLocked.contains(s) || held.test(s), s -> tickers.get(s) != null);
        LOG.info("[BIG_DOWN-SEL] {} level={} n={} pool={} top={}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
                numberOrder, a.size(), com.binance.chuyennd.tradecore.selector.BigDownSelect.describe(sel, a.symbolPred));
        return sel;
    }

""" + anchor)
open(P, "wb").write(s.encode("utf-8"))
log.info("PATCH_OK")
