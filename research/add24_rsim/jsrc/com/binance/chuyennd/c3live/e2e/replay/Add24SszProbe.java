package com.binance.chuyennd.c3live.e2e.replay;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.PrintWriter;

/** ADD24 S-SZ (DEV-B): f_jar(E_sim, U_sim, leg0) = LiveGridSizing.legBudget(TradeUtils.managerBudget(null, M_run, E_sim, PREDICT), 0)
 *  goi THANG ham cua jar STUB (khong viet lai). In: ssz_in.csv ; Out: ssz_jar.csv (ts,symbol,f_jar). */
public final class Add24SszProbe {
    private Add24SszProbe() {
    }

    public static void main(String[] a) throws Exception {
        File in = new File(a[0]);
        try (BufferedReader br = new BufferedReader(new FileReader(in)); PrintWriter pw = new PrintWriter(new File(a[1]))) {
            String h = br.readLine();
            String[] cols = h.split(",");
            int iT = 0, iS = 1, iE = -1, iM = -1, iL = -1;
            for (int i = 0; i < cols.length; i++) {
                if (cols[i].equals("E_sim")) iE = i;
                if (cols[i].equals("M_run")) iM = i;
                if (cols[i].equals("level")) iL = i;
            }
            pw.println("ts,symbol,level,f_jar,F_BASE,U_MAX,SCALE,ratio0,apply");
            String ln;
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(",");
                Float e = Float.parseFloat(p[iE]);
                Float m = Float.parseFloat(p[iM]);
                com.binance.chuyennd.object.MarketLevelChange lv = com.binance.chuyennd.object.MarketLevelChange.valueOf(p[iL]);
                Float mb = com.binance.chuyennd.tradecore.TradeUtils.managerBudget(null, m, e, lv);
                Float f = com.binance.chuyennd.tradecore.selector.LiveGridSizing.legBudget(mb, 0);
                pw.println(p[iT] + "," + p[iS] + "," + p[iL] + "," + f + "," + com.binance.chuyennd.tradecore.Configs.F_BASE + ","
                        + com.binance.chuyennd.tradecore.Configs.U_MAX + "," + com.binance.chuyennd.tradecore.Configs.DCA_GRID_SCALE + ","
                        + com.binance.chuyennd.tradecore.DcaUtils.gridLegWeightRatio(0) + ","
                        + com.binance.chuyennd.tradecore.selector.LiveGridSizing.on());
            }
        }
    }
}
