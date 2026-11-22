# ADD24: danh sach entry CO THE chua key - xac dinh bang TEN (HOTFIX_KS_DEV / cmp_classes.py). Dung chung cho make_stub + C0.
import re
KEYRX = re.compile(r'^com/binance/(chuyennd/config/PrivateConfig|client/impl/BinanceApiInternalFactory|chuyennd/client/ClientSingleton|'
                   r'chuyennd/client/BinanceFuturesClientSingleton|chuyennd/c3live/client/C3LiveClient|chuyennd/c3live/canary/C3LiveCanary)'
                   r'(\$[^/]*)?\.class$')
ORIG = '/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2_hotfixks'
ORIG_MD5 = '01cfbb4324fb4a10b615dc3c976ddc73'
KSE = 'com/binance/chuyennd/ops/KillSwitchEngine.class'
KSE_MD5 = 'd560bd8d1e55bcd4d82e6156e45b8f04'
STUB = '/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43'
