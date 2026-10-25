import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.ExchangeInfoParser;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.c3live.universe.UniverseDiff;
import java.nio.file.Paths;
import java.util.*;

public class UniCheck {
    public static void main(String[] a) throws Exception {
        ExchangeInfo ei = ExchangeInfoParser.parseFile(Paths.get(a[0]));
        long now = Long.parseLong(a[1]);
        SymbolUniverseLive u = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults(), () -> ei, s -> System.out.println("ALERT " + s));
        UniverseDiff d = u.apply(ei, now);
        System.out.println("SUMMARY " + d.summary());
        Map<String, Integer> reasons = new TreeMap<>();
        int buyable = 0, tradfi = 0;
        List<String> buy = new ArrayList<>();
        for (String s : ei.getSymbols().keySet()) {
            Optional<String> w = u.whyNotBuyable(s, now);
            String r = w.isPresent() ? w.get().split(" ")[0] : "BUYABLE";
            reasons.merge(r, 1, Integer::sum);
            if (!w.isPresent()) buy.add(s);
            if (u.classification(s).map(v -> v.isTradFi()).orElse(false)) tradfi++;
        }
        System.out.println("REASONS " + reasons);
        System.out.println("TRADFI_VERDICTS " + tradfi);
        System.out.println("MARKET_INDEX " + u.marketIndexMembers().size());
        for (String s : new String[]{"IBKRUSDT", "UNITREEUSDT", "NAVERUSDT", "JPMUSDT", "TENCENTUSDT", "POWRUSDT", "MDTUSDT", "ALLUSDT", "PREDICTUSDT", "XAUUSDT", "PAXGUSDT", "VELODROMEUSDT", "BTCUSDT", "MITOUSDT", "PTBUSDT"}) {
            System.out.println("SYM " + s + " buyable=" + u.isBuyable(s, now) + " why=" + u.whyNotBuyable(s, now).orElse("-") + " cls=" + u.classification(s).orElse(null) + " idx=" + u.marketIndexMembers().contains(s));
        }
        // stale check
        System.out.println("STALE+61m BTC why=" + u.whyNotBuyable("BTCUSDT", now + 61 * 60_000L).orElse("-"));
        // tradfi in buyable?
        int leak = 0;
        for (String s : buy) if (ei.getSymbols().get(s).getContractType().toUpperCase().contains("TRADIFI")) leak++;
        System.out.println("LEAK_TRADIFI_IN_BUYABLE " + leak + " BUYABLE " + buy.size());
    }
}
