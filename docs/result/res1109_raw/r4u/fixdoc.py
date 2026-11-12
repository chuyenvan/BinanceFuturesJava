"""R4u: don javadoc (doc goc theo computeValueMap; buildValueMap co doc ngan)."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
P = "src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java"
s = open(P, "rb").read().decode("utf-8")
old = """    /**
     * [V12 R4u] phan TINH THUAN cua {@link #buildValueMap}: KHONG ghi selMapPred/LATEST_SEL_MAPPRED, KHONG log [MAP] tick.
     * null = chua san sang (caller PHAI bo, khong thay bang gia tri khac).
     */
    private com.binance.chuyennd.tradecore.selector.LiveBuildMap.Assigned computeValueMap("""
new = """    private com.binance.chuyennd.tradecore.selector.LiveBuildMap.Assigned computeValueMap("""
assert s.count(old) == 1
s = s.replace(old, new)
old2 = """        return a;
    }

    private boolean buildValueMap(long time, TreeMap<Float, String> s1Pool) {"""
new2 = """        return a;
    }

    /**
     * [V12 R4u] tach tu ban cu: phan TINH (thuan, khong ghi state) o {@link #computeValueMap} — dung chung voi leg
     * market-signal ({@code bigDownSelectS1}); ham nay ghi selMapPred/LATEST_SEL_MAPPRED + log [MAP] nhu cu.
     *
     * @return false khi chua san sang — caller PHAI bo tick, khong duoc thay bang gia tri khac.
     */
    private boolean buildValueMap(long time, TreeMap<Float, String> s1Pool) {"""
assert s.count(old2) == 1
s = s.replace(old2, new2)
s = s.replace("""     * @return false khi chua san sang — caller PHAI bo tick, khong duoc thay bang gia tri khac.
     */
    private com.binance.chuyennd.tradecore.selector.LiveBuildMap.Assigned computeValueMap(""",
              """     * @return null khi chua san sang (R4u: tach thanh ham thuan) — caller PHAI bo tick, khong thay bang gia tri khac.
     */
    private com.binance.chuyennd.tradecore.selector.LiveBuildMap.Assigned computeValueMap(""")
open(P, "wb").write(s.encode("utf-8"))
logging.info("FIXDOC_OK")
