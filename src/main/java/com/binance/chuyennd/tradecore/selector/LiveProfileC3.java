package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * CO PROFILE C3-SHADOW cho duong LIVE — <b>MAC DINH TAT</b>.
 *
 * <p>Bat bang {@code LIVE_PROFILE=c3_shadow}. Khi TAT, moi ham o day tra gia tri
 * lam duong live chay Y HET HEAD (cong hoi quy: xem {@code LiveProfileC3Test}).
 *
 * <p>Khi BAT, profile ap 5 khac biet C3 <-> live 242 da liet ke o
 * {@code docs/L1_SHADOW_C3.md} muc 2:
 * <ol>
 *   <li>(a) arm trailing {@code RATE_PROFIT_STOP_MARKET} 0.05 -> <b>0.07</b></li>
 *   <li>(b) time-stop 168h cho cum CHUA arm — live khong co, port tu sim
 *       ({@code SimulatorMarketLevelTicker1MStopLoss:672})</li>
 *   <li>(c) ratchet: bo dead-zone {@code x5.21847} -> ratchet LIEN TUC nhu sim</li>
 *   <li>(d) sizing compound tren equity giay ({@code PAPER_EQUITY} + PnL shadow), tran 4.5% equity</li>
 *   <li>(e) {@code SELECTOR_RANK_TOPK=8} — thuan cau hinh, khong can code</li>
 * </ol>
 *
 * <p>🔒 {@code SHADOW_NO_PUSH} bi <b>HARDCODE true</b> khi profile bat: khong doc env, khong
 * co duong nao dat lenh that. Day la dieu kien an toan, khong phai tham so.
 */
public final class LiveProfileC3 {

    private static final Logger LOG = LoggerFactory.getLogger(LiveProfileC3.class);

    private LiveProfileC3() {
    }

    public static final String PROFILE_NAME = "c3_shadow";

    /** (a) nguong arm trailing cua C3. */
    public static final float ARM_RATE = 0.07f;
    /** (b) time-stop cho cum chua arm (gio). */
    public static final int TIME_STOP_HOURS = 168;
    /** (c) he so dead-zone ratchet khi profile BAT = 1 (ratchet lien tuc, giong sim). */
    public static final float RATCHET_DEADZONE_MULT_ON = 1.0f;
    /** (d) tran size mot lenh theo equity giay. */
    public static final float SIZE_CAP_OF_EQUITY = 0.045f;

    private static final boolean ON;
    private static final float PAPER_EQUITY;

    static {
        String v = Cfg.get("LIVE_PROFILE");
        ON = v != null && PROFILE_NAME.equalsIgnoreCase(v.trim());
        float eq = 0f;
        if (ON) {
            String pe = Cfg.get("PAPER_EQUITY");
            try {
                if (pe != null && !pe.trim().isEmpty()) eq = Float.parseFloat(pe.trim());
            } catch (NumberFormatException e) {
                LOG.warn("PAPER_EQUITY='{}' khong phai so -> 0 (sizing se bi chan)", pe);
            }
            LOG.info("🟡 [LIVE_PROFILE=c3_shadow] BAT — arm={} timeStop={}h ratchet=LIEN TUC "
                            + "paperEquity={} sizeCap={}%. SHADOW_NO_PUSH=true (hardcode, khong doc env).",
                    ARM_RATE, TIME_STOP_HOURS, eq, SIZE_CAP_OF_EQUITY * 100f);
        }
        PAPER_EQUITY = eq;
    }

    /** true khi {@code LIVE_PROFILE=c3_shadow}. Moi nhanh moi PHAI nam sau ham nay. */
    public static boolean on() {
        return ON;
    }

    /** Von giay khoi diem. 0 khi profile tat. */
    public static float paperEquity() {
        return PAPER_EQUITY;
    }

    /**
     * 🔒 Chan day lenh that. Profile bat => LUON true (khong doc env). Profile tat => tra
     * {@code null} de goi y "dung duong cu" ({@code Cfg.get("SHADOW_NO_PUSH")}).
     */
    public static boolean forceNoPush() {
        return ON;
    }

    /** (a) nguong arm: profile bat -> 0.07; tat -> {@code def} (gia tri live hien tai). */
    public static float armRate(float def) {
        return ON ? ARM_RATE : def;
    }

    /** (c) he so dead-zone ratchet: profile bat -> 1.0; tat -> {@code def} (5.21847). */
    public static float ratchetDeadzoneMult(float def) {
        return ON ? RATCHET_DEADZONE_MULT_ON : def;
    }
}
