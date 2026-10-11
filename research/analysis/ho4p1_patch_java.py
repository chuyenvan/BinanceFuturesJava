import sys, logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("patch")
p = "/home/ubuntu/claude_master/1011/ho4race_wt/src/main/java/com/binance/chuyennd/aerospike/DataManagerAerospikeFloatSim.java"
s = open(p, encoding="utf-8").read()
old_save = '''    public static void saveMarketDataBatch(Map<Long, MarketDataObject> dataMap) {
        if (dataMap == null || dataMap.isEmpty()) return;
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            dataMap.entrySet().parallelStream().forEach(entry -> {
                try {
                    long timestamp = entry.getKey();
                    MarketDataObject data = entry.getValue();

                    String keyString = fmt.format(new Date(timestamp));'''
new_save = '''    public static void saveMarketDataBatch(Map<Long, MarketDataObject> dataMap) {
        if (dataMap == null || dataMap.isEmpty()) return;
        try {
            // FIX HO4-P1 (race): truoc day 1 SimpleDateFormat DUNG CHUNG trong parallelStream (khong thread-safe)
            // => key phut ghep sai/trung => 2 phut de cung record => mat ~7% phut, khac nhau moi lan chay.
            // Nay dung marketDataKey() (ThreadLocal + pin GMT+7). Gia tri ghi KHONG doi.
            dataMap.entrySet().parallelStream().forEach(entry -> {
                try {
                    long timestamp = entry.getKey();
                    MarketDataObject data = entry.getValue();

                    String keyString = marketDataKey(timestamp);'''
assert s.count(old_save) == 1, "save block"
s = s.replace(old_save, new_save)
old_get = '''            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MARKET_DATA, keyString);

            // Dùng clientOracle vì set market_data đang lưu ở đây'''
new_get = '''            String keyString = marketDataKey(timestamp); // HO4-P1: pin GMT+7 (truoc: TZ JVM)
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_MARKET_DATA, keyString);

            // Dùng clientOracle vì set market_data đang lưu ở đây'''
assert s.count(old_get) == 1, "get block"
s = s.replace(old_get, new_get)
anchor = '''    /**
     * Ghi một Batch Market Data vào Aerospike (Dùng cho ExportMarketData2File)
     */'''
helper = '''    /** Format key phut cua set market_data_object (yyyyMMdd-HHmm, GMT+7). ThreadLocal vi SimpleDateFormat
     *  KHONG thread-safe (HO4-P1). GMT+7 == Asia/Ho_Chi_Minh voi moi ts sau 1975 => tren host/JVM +07
     *  key y het hanh vi cu; khac biet duy nhat: khong con phu thuoc -Duser.timezone. */
    private static final ThreadLocal<SimpleDateFormat> MARKET_KEY_FMT = ThreadLocal.withInitial(() -> {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd-HHmm");
        f.setTimeZone(java.util.TimeZone.getTimeZone("GMT+7"));
        return f;
    });

    /** Key Aerospike cho ban ghi market_data_object tai phut {@code timestamp} (thread-safe). */
    static String marketDataKey(long timestamp) {
        return MARKET_KEY_FMT.get().format(new Date(timestamp));
    }

'''
assert s.count(anchor) == 1, "anchor"
s = s.replace(anchor, helper + anchor)
open(p, "w", encoding="utf-8").write(s)
log.info("PATCH_OK")
