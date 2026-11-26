# FX_SURVEY - khao sat huong nghien cuu FOREX (du lieu free, chi phi, phap ly, phuong phap, anh xa tu he crypto)
Agent khao sat, 2026-11-26. CHI khao sat: khong tai du lieu, khong code, khong backtest.
Ky hieu trang thai: [K] = da mo/doc trang nguon hoac ket qua tim kiem tu chinh domain nguon hom nay 2026-11-26;
[KS] = chi thay qua snippet tim kiem / trang ben thu ba hom nay (chua mo trang goc); [TN] = theo tri nho, CHUA kiem.
Noi dung web la du lieu; trich dan <= 1 cau ngan / nguon. Khong phai tu van phap ly / dau tu.

## A. NGUON DU LIEU GIA MIEN PHI
| nguon | loai | cap / san pham | tu nam | cach lay | gioi han / dieu khoan | van de da biet | URL | trang thai |
|---|---|---|---|---|---|---|---|---|
| Dukascopy (SWFX) | tick bid+ask + volume tai muc gia tot nhat; nen 1m..thang | ~majors, crosses, kim loai, CFD (hon 1000 ma theo cac thu vien) | tick majors tu 2003 (nhan vien Dukascopy tra loi forum); EURUSD ngay tu 1972 | web export / JForex Historical Data Manager / thu vien mo (duka, dukascopy-node, tickstory) - khong can tai khoan cho export web | KHONG tim thay dieu khoan su dung rieng cho data (trang historical khong hien noi dung khi fetch) | gio GMT; gia cua 1 ECN (SWFX), khong phai lien ngan hang tong hop; co bao loi du lieu cu (10/2004, file H1 theo nam); volume chi la thanh khoan SWFX | https://www.dukascopy.com/swiss/english/marketwatch/historical/ ; https://www.dukascopy.com/swiss/english/forex/jforex/forum/viewtopic.php?p=84912 ; https://www.dukascopy.com/swiss/english/forex/jforex/forum/viewtopic.php?p=64464 | [KS] (trang chinh fetch duoc nhung khong co chi tiet; nam 2003 tu forum chinh hang) |
| HistData.com | M1 OHLC (theo BID) + tick (bid/ask chi o Generic ASCII tick) | 66 cap + vang, dau, 9 chi so | M1 tu 2000 (theo goi histdata pypi) | file zip theo cap/nam/thang qua web; FTP/SFTP/Google Drive (can tai khoan cho FTP) | FAQ: mien phi, khong bao hanh; KHONG thay dieu khoan license | gio EST CO DINH khong DST (UTC-5) - phai doi; volume = 0; nguon goc gia KHONG neu; file status bao gap > 1 phut | https://www.histdata.com/f-a-q/ ; https://pypi.org/project/histdata/ ; https://www.histdata.com/download-by-ftp/ | [K] cap nhat file thay ngay 2026-11-10 tren trang |
| TrueFX (Integral) | tick top-of-book bid/offer tu dealer bank | 15 cap (ben thu ba), trang chu noi "16+" | 05/2009 (script R cua ben thu ba) | dang ky mien phi -> tai zip theo thang | trang chu khong neu dieu khoan; khong xac nhan duoc trang Historical Downloads | khong biet con cap nhat toi 2025-26 khong | https://www.truefx.com/ ; https://forexsb.com/wiki/fsb/manual/truefx_data | [KS] - con hoat dong o muc trang chu; pham vi nam CHUA kiem |
| OANDA v20 API (tai khoan demo) | nen S5..thang, gia M/B/A (bid/ask rieng) | ~70 cap + CFD | candles "tu 2005" (mo ta ben thu ba) | REST, token tu tai khoan demo; max 5000 nen / request | phai mo tai khoan demo (owner tu lam - agent KHONG dang ky); dieu khoan API chua doc | gio UTC, dailyAlignment 17h New York; gia OANDA (market maker) | https://developer.oanda.com/rest-live-v20/instrument-ep ; https://developer.oanda.com/rest-live-v20/introduction/ | [K] endpoint + max 5000; do sau lich su [KS] |
| FRED (Fed H.10) | ty gia NGAY (noon NY buying rate) | ~20 dong tien vs USD | DEXUSEU 1999-01-04; DEXJPUS/DEXUSUK tu 1971 | CSV/API mien phi (API can key mien phi) | tag "Public Domain: Citation Requested" | khong co bid/ask, 1 diem/ngay luc trua NY; ngay le US trong | https://fred.stlouisfed.org/series/DEXUSEU ; https://fred.stlouisfed.org/data/exjpus | [K] (DEXUSEU cap nhat 2026-11-23) |
| ECB reference rates | ty gia tham chieu ngay EUR/x (~30 dong) | EUR vs ~30 | 1999 | CSV/XML zip, khong can tai khoan | ECB: chi de tham khao, khong khuyen dung cho giao dich | chot ~14:10 CET (concertation), dang ~16:00 CET | https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.so.html | [K] |
| BIS EER (NEER/REER) | chi so ty gia hieu dung danh nghia/thuc | 64 nen kinh te (broad), 26-27 (narrow) | broad tu 1994; narrow tu 1964 | bulk CSV/API; cung co tren FRED | "Terms of permitted use of BIS statistics" (chua doc chi tiet) | thang; dung cho VALUE/PPP | https://data.bis.org/topics/EER ; https://fred.stlouisfed.org/data/RBXMBIS | [K] |
| Stooq | nen ngay (va 5m/60m gioi han) | nhieu cap FX | dai (tu nam nao CHUA kiem) | tu 03/2026 CAN apikey (lay qua captcha); co han muc luot/ngay | dieu khoan chua doc | thay doi API dot ngot (pandas-datareader hong) | https://github.com/pydata/pandas-datareader/issues/1012 | [KS] |
| Yahoo Finance (yfinance) | nen ngay/gio (EURUSD=X tu 2003) | majors | 2003 (EURUSD=X, vi du YFinance.jl) | API khong chinh thuc | yfinance: API "intended for personal use only"; Yahoo cam dung thuong mai; co the bi chan / doi bat ky luc nao | du lieu khong co bid/ask, chat luong khong cam ket | https://raw.githubusercontent.com/ranaroussi/yfinance/main/README.md ; https://massive.com/compare/massive-vs-yfinance.md | [KS] - KHONG khuyen dung lam nguon chinh |
| Alpha Vantage | FX_DAILY / intraday | nhieu cap | - | key free | 25 request/ngay (5/phut); ben thu ba noi free chi tra 100 diem gan nhat cho daily | qua hep cho nghien cuu | https://www.alphavantage.co/support/ ; https://www.alphavantage.co/premium | [K] han muc; "100 diem" [KS] |
| Twelve Data | OHLC | 140+ cap | free khong co "deep history" | key free | 8 credit/phut, 800/ngay | lich su sau la tra phi | https://twelvedata.com/pricing ; https://support.twelvedata.com/en/articles/5335783-trial | [K] |
| Massive (truoc la Polygon.io) | aggregates FX (tu 2009-09-25 o goi tra phi) | 1750+ cap | Basic free: 2 NAM, EOD, khong co quotes | key free, 5 call/phut | flat file minute chi goi Starter $49/thang | free chi 2 nam -> vo dung cho WFO dai | https://massive.com/currencies ; https://massive.com/knowledge-base/article/how-far-back-does-massives-forex-and-gold-history-go-and-are-there-gaps | [K] |
| MetaTrader (lich su broker) | M1 / tick cua broker | theo broker | thuong vai nam | tai trong terminal (tai khoan demo) | theo broker | gio server broker (GMT+2/+3 co DST), gia RIENG broker, chat luong khac nhau | https://www.mql5.com/en/forum/475925 | [KS] |
| Kaggle / HuggingFace datasets | ban sao HistData / OANDA / Dukascopy | tuy bo | 2000-2002.. | tai file | license thuong "unknown" | ban sao, khong ro nguon/kiem tra -> chi dung doi chieu | https://baselight.app/u/kaggle/dataset/imetomi_eur_usd_forex_pair_historical_data_2002_2019 ; https://huggingface.co/datasets/elthariel/histdata_fx_1m/tree/main | [KS] |
| QuantConnect (OANDA data) | FX tick..ngay | 72 cap | 01/2007 | dung trong nen tang cloud | dieu kien tai ve CHUA kiem | chi dung trong LEAN | https://www.quantconnect.com/docs/v2/writing-algorithms/datasets/quantconnect/forex-data | [KS] |
Ket luan A: xuong song = Dukascopy tick (bid/ask, GMT, 2003+) + HistData M1 (2000+, de doi chieu, nho doi gio EST co dinh)
+ FRED/ECB ngay (1971/1999+, lam "gia chinh thuc" doc lap de kiem loi) + BIS REER. OANDA demo API la nguon thu 3 de doi chieu
(can owner mo demo). Cac API freemium (AV, Twelve, Massive, Yahoo) KHONG du dai / KHONG on dinh cho WFO 20 nam.

## B. DU LIEU PHU (tuong duong OI / funding / dong long)
| du lieu | tuong duong crypto | lich su free >= 10 nam? | nguon | trang thai |
|---|---|---|---|---|
| CFTC COT - Legacy (futures only tu 1986; F+O tu 1995), TFF (Traders in Financial Futures: dealer / asset manager / leveraged funds; du lieu tu 06/2006) | vi the theo nhom, hang tuan (giong L/S ratio + OI) | CO, mien phi, zip theo nam; du lieu thu 3 chot, phat hanh thu 6 15:30 ET; KHONG sua lai lich su | https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm ; https://cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm | [K] |
| Chenh lech lai suat (carry) - lai suat ngan han OECD/FRED, policy rate | funding rate | CO (FRED/OECD, thang/ngay, nhieu thap ky) | https://fred.stlouisfed.org (chuoi IR3TIB01xxM156N - TEN CHUOI [TN]) | [TN] |
| Swap qua dem cua broker | funding thuc tra | KHONG co lich su cong khai; chi so hien tai tren MT/broker | https://pepperstone.com/en/education/what-are-swaps-how-to-calculate-swaps/ | [KS] |
| Dukascopy SWFX Sentiment Index (ti le long/short cua "liquidity consumers") | L/S ratio retail | trang noi co "Historical Sentiment Index" mien phi, cap nhat 30 phut; do dai lich su + tai hang loat CHUA kiem | https://www.dukascopy.com/swiss/english/marketwatch/sentiment/ | [KS] |
| OANDA orderBook / positionBook (v20, them 09/2018) | ban do thanh ly / vi the retail | co tham so time; do sau lich su CHUA kiem; can tai khoan | https://developer.oanda.com/rest-live-v20/release-notes ; https://oanda-api-v20.readthedocs.io/en/latest/endpoints/instruments/instrumentpositionbook.html | [KS] |
| IG Client Sentiment | L/S retail | chi xem hien tai/ngan han tren nen tang; KHONG thay kho lich su free | https://www.ig.com/uk/trading-strategies/_how-to-trade-using-ig-client-sentiment-240912 | [KS] |
| Myfxbook Community Outlook | L/S retail | API free 100 request/24h, CHI snapshot hien tai; nguoi dung forum xac nhan khong lay duoc lich su qua API | https://myfxbook.com/id/api ; https://www.myfxbook.com/de/community/programming/getting-historical-sentiment-data/3108384,1 | [K] |
| Bien dong ham y | IV / basis | EVZ (Cboe euro vol) DA NGUNG 01/2025 (FRED EVZCLS 2007-2025); khong tim thay IV FX free khac | https://fred.stlouisfed.org/series/EVZCLS ; https://cdn.cboe.com/resources/release_notes/2025/20250113_Consultation-Results-Regarding-the-Cessation-of-the-RVOL-and-EVZ-Indices.pdf | [K] |
| Lich kinh te (thoi diem + ky vong + thuc te) | su kien | KHONG tim duoc nguon lich su free co cau truc dang tin trong luot nay (ForexFactory/Investing la web, dieu khoan chua kiem); FRED ALFRED co vintages so lieu vi mo (khong co ky vong) | https://alfred.stlouisfed.org/ | [KS]/CHUA |
| Khoi luong futures CME | volume / OI | COT co OI hang tuan (free); volume ngay CME free: CHUA kiem | (xem COT) | CHUA |
Ket luan B: chi COT + lai suat (carry) + REER la co lich su >= 10 nam, mien phi, chinh thong. Tam ly retail co lich su free
(Dukascopy) can kiem them; Myfxbook/IG chi co hien tai -> phai tu thu thap forward (khong backtest duoc).

## C. CHI PHI VA CAU TRUC THI TRUONG BAT BUOC MO HINH
- Spread + commission (vi du ECN): IC Markets Raw: spread TB EURUSD 0,1 pip + $3,5/lot/chieu ($7 round turn) ~ tong ~0,8 pip
  round-trip ~ 0,7 bp; Standard: tu 0,8 pip, khong commission. https://icmarkets.com/en/trading-accounts/raw-spread-account [K].
  Cross/exotic spread lon hon nhieu (CHUA lay so cu the - phai lay tu bang spread broker khi prereg).
- Spread gian rong quanh rollover 17:00 New York (21-22 UTC) va tin lon; manh nhat thu 4 (nguon blog, [KS]):
  https://lowspreadbroker-com.pages.dev/artigos/overnight-spread-widening . Mo hinh: spread theo gio x cap, lay tu bid/ask Dukascopy.
- Swap qua dem (tom-next) tinh luc 17:00 NY; thu 4 tinh 3 ngay (T+2 bu cuoi tuan) - Pepperstone/FXCM [K]:
  https://pepperstone.com/en-eu/learn-to-trade/trading-guides/what-are-swaps-how-to-calculate-swaps/ ;
  https://www.fxcm.com/markets/help/rollover-are-trades-held-over-the-weekend-affected-by-trade-rollover/ .
  Swap broker = chenh lech lai suat - markup broker (2 chieu deu co the am). Backtest carry PHAI dung swap broker uoc luong, khong
  dung lai suat thuan.
- Don bay / ky quy: EU (ESMA 2018) tran 30:1 majors, 20:1 non-majors; NCAs: 74-89% tai khoan CFD retail lo [K]:
  https://www.esma.europa.eu/node/84933 . Broker offshore cho 1:1000 (IC Markets Global, [K] trang account overview).
- Gio 24x5: mo ~ chu nhat 17:00 NY, dong thu 6 17:00 NY -> GAP cuoi tuan (stop khong khop dung gia). DST lech US/EU 2-3 tuan/nam.
- Khong co gia "chinh thuc": moi broker/ECN co feed rieng; Dukascopy (SWFX) != OANDA != broker MT. Can doi chieu >= 2 nguon.
- Truot gia / B-book / requote: broker market-maker la doi tac nguoc chieu; chua tim nguon so lieu dang tin -> mo hinh bao thu
  (vd +0,5-1 pip cho lenh stop, gap cuoi tuan = khop tai gia mo). [TN]
- Phi rut/nap qua ngan hang VN: xem muc D (co the khong hop phap).

## D. PHAP LY VIET NAM (KHONG phai tu van phap ly)
Tom tat (muc chac chan TRUNG BINH-CAO ve rui ro, THAP ve dieu luat cu the):
1. NHNN (bao cao gui Quoc hoi, LSVN 09/05/2025): NHNN KHONG cap phep bat ky san Forex nao tai VN; hoat dong san Forex "khong thuoc
   pham vi hoat dong ngoai hoi duoc phep"; viec thanh toan/chuyen tien ra nuoc ngoai cho giao dich san Forex la "khong duoc phep theo
   quy dinh hien hanh ve quan ly ngoai hoi"; NHNN chi dao TCTD chan thanh toan cho san Forex [K]:
   https://lsvn.vn/ngan-hang-nha-nuoc-khong-cap-phep-bat-ky-san-forex-nao-tai-viet-nam-a157359.html
2. Thong doc NHNN tra loi chat van (LSVN 12/11/2024): chi TCTD duoc cap phep kinh doanh ngoai hoi, dac biet tren thi truong quoc te [KS]:
   https://lsvn.vn/ngan-hang-nha-nuoc-chua-cap-phep-giao-dich-qua-san-forex-a149708.html
3. NHNN nhieu lan khuyen cao; nguoi tham gia "khong duoc phap luat bao ve" khi tranh chap [KS]: https://www.div.gov.vn/tang-cuong-quan-ly-doi-voi-giao-dich-tien-ao-san-forex ;
   Cong an Ha Noi canh bao "choi Forex" vua rui ro vua vi pham [KS]: https://thitruongtaichinhtiente.vn/print/35956.html
4. Che tai: ND 88/2019/ND-CP (sua boi ND 143/2021) xu phat hanh chinh linh vuc tien te/ngoai hoi, vd chuyen/mang ngoai te ra nuoc
   ngoai khong dung quy dinh 30-50 trieu (bao Phap luat, [KS]); KHONG tim thay dieu khoan nao dinh danh "ca nhan giao dich Forex qua
   broker nuoc ngoai" -> muc phat ap cho truong hop nay KHONG CHAC. NHNN dang soan ND thay ND 88 (chua kiem trang thai).
   https://doanhnhan.baophapluat.vn/cham-dut-tinh-trang-doi-100-usd-bi-phat-90-trieu-dong-24511.html ; https://sbv.gov.vn/documents/d/sbv_portal/600459
Danh gia: giao dich forex ky quy qua broker nuoc ngoai cua ca nhan cu tru VN = KHONG duoc cap phep, kenh chuyen tien la khong duoc phep,
khong duoc bao ve; rui ro phap ly + rui ro mat tien (broker lua dao pho bien). Muc phat hinh su/hanh chinh cu the cho ca nhan: CHUA chac.
Phuong an hop phap thay the (da kiem so bo):
- Ngan hang (TT 02/2021/TT-NHNN): giao ngay/ky han/hoan doi/quyen chon ngoai te voi TCTD - phuc vu nhu cau co chung tu, KHONG phai dau co
  [KS]: https://thuvienphapluat.vn/documents/law.aspx?id=c%3DRZNU5ETXTk
- HNX phai sinh: chi HDTL VN30, VN100, TPCP 5/10 nam - KHONG co HDTL tien te [K qua tin thang 3-10/2026].
- MXV (So GD Hang hoa VN, lien thong CME/ICE...): ~50 san pham nong san, nang luong, kim loai - KHONG thay HDTL tien te [KS]:
  https://vneconomy.vn/so-giao-dich-hang-hoa-viet-nam-15-nam-kien-tao-va-vuon-xa.htm
=> Ket luan thuc dung: nghien cuu forex o DANG NGHIEN CUU/PAPER la an toan; giao dich that tu VN hien KHONG co kenh hop phap ro rang.
   Owner phai tu hoi luat su truoc moi buoc giao dich that.

## E. PHUONG PHAP / "KY NANG TREN MANG" va BANG CHUNG
| ho | bang chung (bai, nam, ket qua) | suy giam sau cong bo? | hop von nho + chi phi retail? | danh gia |
|---|---|---|---|---|
| Carry (mua lai cao, ban lai thap) | Brunnermeier-Nagel-Pedersen 2008 NBER w14473: loi nhuan carry duong nhung LECH AM (sap khi thanh khoan/risk appetite giam, VIX tang) https://www.nber.org/papers/w14473 [K]; Lustig-Verdelhan binh luan cung tap https://nber.org/system/files/chapters/c7288/c7288.pdf [KS] | carry G10 kem sau 2008 khi lai suat ve 0 [TN - can kiem] | swap broker co markup -> an mot phan carry; can don bay nho | CO CAN CU (premium + rui ro sap ro rang) |
| Momentum cat ngang | Menkhoff-Sarno-Schmeling-Schrimpf 2012 JFE: spread winner-loser toi 10%/nam, nhung bi chi phi + gioi han arbitrage an mot phan; tap trung o dong tien kem thanh khoan https://openaccess.city.ac.uk/3296 [K] | phan lon loi o exotic/EM | KEM voi 28 cap G10 (cross-section hep, chi phi exotic cao) | TRANH CAI (cho retail G10) |
| Momentum chuoi thoi gian (trend) | Moskowitz-Ooi-Pedersen 2012 JFE: TSMOM co o ca 58 hop dong gom tien te https://papers.ssrn.com/abstract=2089463 [K]; Neely-Weller-Ulrich 2009 JFQA: loi nhuan quy tac MA/filter thap ky 70-80 la that nhung BIEN MAT dau 1990s https://iro.uiowa.edu/esploro/outputs/journalArticle/The-Adaptive-Markets-Hypothesis-Evidence-from/9984963054302771 [K] | CO, suy giam ro (quy tac ky thuat don gian) | chi phi thap neu tan suat thap (ngay/tuan) | TRANH CAI (diversified TSMOM co can cu; trend 1 cap FX ngay nay yeu) |
| Gia tri (PPP/REER) | Asness-Moskowitz-Pedersen 2013 JF: value co trong tien te, ket hop value+momentum tot hon https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf [K] | tan suat thang, ngang | chi phi thap; nhung it so lieu doc lap (thang x ~10 dong tien) | CO CAN CU nhung yeu, chu ky dai nhieu nam |
| Mean-reversion trong ngay | khong tim duoc bai hoc thuat cu the trong luot nay | - | spread an het edge nho | CHUA KIEM / nghi ngo |
| Breakout theo phien (London/NY open) | KHONG tim thay bang chung hoc thuat trong luot nay; chu yeu blog/khoa hoc | - | - | KHONG CO BANG CHUNG (chu yeu marketing) - can tu kiem neu muon |
| Giao dich quanh tin | Andersen-Bollerslev-Diebold-Vega 2003 AER: bat ngo tin vi mo tao buoc nhay gia ngay lap tuc https://www.nber.org/papers/w8959 [K] | buoc nhay xay ra trong giay/phut -> retail khong kip; spread gian rong | KHONG phu hop (toc do + spread + truot) | CO CAN CU ve hien tuong, KHONG khai thac duoc cho retail |
| Nguoc tam ly retail | Nolte & Nolte 2016 EJF (du lieu ~2000 khach OANDA): order flow retail CO thong tin du bao ngan han (khong phai thuan nguoc chieu) https://ideas.repec.org/a/taf/eurjfi/v22y2016i2p80-104.html [K]; Kaourma et al 2025 JIFMIM: retail EUR/USD giao dich nguoc chieu bat ngo tin, theo sentiment + gia qua khu https://clok.uclan.ac.uk/55052 [K] | - | du lieu lich su free han che | TRANH CAI (quang cao "contrarian" cua broker > bang chung) |
| Theo / nguoc vi the COT | Tornell-Yuan 2012 J Futures Markets: dinh/day net position huu ich; vi the dau co du bao TIEP DIEN, vi the hedger du bao DAO CHIEU https://econpapers.repec.org/RePEc:umb:econwp:09116 [K]; Bundesbank DP 41/2015: gia dan truoc vi the dau co EUR (vi the di theo gia) https://bundesbank.de/resource/blob/703976/fcd518354ae96703103d929dfea7582e/472B63F073F071307366337C94F8C870/2015-11-30-dkp-41-data.pdf [KS] | - | tuan, chi phi thap | TRANH CAI |
| Bien dong / carry sap khi vol tang | BNP 2008 (tren): VIX tang -> carry sap; dung lam GATE cho carry | - | phu hop (gate ngay) | CO CAN CU (lam bo loc rui ro, khong phai nguon loi rieng) |
| Grid / martingale / EA ban tren mang | khong co co so ky vong duong; noi bo he crypto: DCA khong gioi han + khong SL PHA HET edge (FINDINGS muc 1) | - | KHONG (don bay x gap cuoi tuan = chay tai khoan) | KHONG CO BANG CHUNG - chu yeu marketing; nguy hiem |
| Price action / SMC / ICT | khong tim thay nghien cuu hoc thuat kiem chung; ESMA: 74-89% retail CFD lo | - | - | KHONG CO BANG CHUNG - chu yeu marketing |

## F. ANH XA TU HE CRYPTO (doc LONG_INVENTORY, PROGRAM_SHORT_LEVZ, MASTER_NOTE B1/B2/B3, AGENT_RUNBOOK, FINDINGS)
| co che / bai hoc | sang forex? | vi sao | du lieu can |
|---|---|---|---|
| Mua sau cu sap (BIG_DOWN, gate p15) | MOT PHAN, yeu | FX it "flash crash" doc lap; su kien lon (CHF 2015, GBP 2016, JPY 2024) la vai lan / thap ky -> so su kien qua it; noi bo: edge BIG_DOWN mong manh theo nguong | tick bid/ask Dukascopy |
| Gate che do rolling (GDV2: phan vi 90 ngay cua diem, causal) | CO (ky thuat) | khung "deu lenh" doc lap thi truong; dung cho carry gate (VIX/ vol FX rolling) | VIX (FRED), vol thuc tu M1 |
| Xep hang cat ngang + quota top-K | YEU | 28 cap = ~8 dong tien doc lap (cap cheo tuong quan cao); top-K cua 8 = gan nhu sort toan bo; noi bo B3: model sort khop nhieu, IC dao dau | ngay/tuan, G10 |
| Sizing theo von + throttle U/U_MAX | CO | ap nguyen; them chuan hoa theo vol (FX vol thap, don bay cao) | - |
| Trailing / time-stop / SL | CO, phai mo hinh GAP | stop forex khong khop qua cuoi tuan / tin; noi bo B1: sim phai CUNG co che voi live (nen 1m) | M1/tick bid-ask |
| DCA | KHONG nen | FINDINGS muc 1: DCA khong gioi han pha edge; voi don bay FX + gap = rui ro chay tai khoan | - |
| "Dong long" OI + funding (LEVZ) | CO, thay bang COT (tuan) + carry/swap + sentiment | noi bo: crowded-long, funding factor, LEVZ tang 1 deu NO-GO tren crypto; B1-B3 cho tin hieu khong on dinh giua nam -> ky vong thap | COT 1986+/2006+, lai suat |
| Thoat theo trang thai (X14, STATE) | CO | vd thoat carry khi vol/VIX vuot phan vi rolling | VIX, vol |
| Hedge beta (USD index) | CO | beta FX chu yeu la USD; tinh DXY tu ro EUR/JPY/GBP... hoac Fed broad index | FRED DTWEX* [TN ten chuoi] |
| Ky luat: prereg, WFO khong nhin truoc, doi chung ngau nhien, holdout 1 lan, audit doc lap, sim=live | CO, DE HON | FX co 20-50 nam du lieu ngay -> nhieu nam OOS hon crypto (2021-2025) | - |
Bai hoc AM chuyen sang: (1) tin hieu dao dau giua nam (B3 IC OOF -0,45..+0,40) -> FX trong luoc tung thap ky cang de lech chu ky;
(2) model xep hang tren tap nho = khop nhieu; (3) so su kien doc lap it (LEVZ B2: 7 020 cau hinh chung ~450 lenh) -> o FX tin hieu thang/
tuan tren ~8 dong tien chi co vai tram quan sat doc lap / thap ky -> phai dem n_eff TRUOC khi chay; (4) "bo 5% lenh tot nhat" (R6) bat buoc.

## G. DE XUAT 3 NGHIEN CUU DAU TIEN (xep: can cu x du lieu free dai x chi phi thap)
G1. CARRY G10 + GATE BIEN DONG (repo "co can cu" + data dai nhat)
- Gia thuyet: ro carry G10 (long 3 lai cao / short 3 lai thap, rebalance thang) co premium duong sau chi phi; gate tat khi VIX hoac vol
  FX rolling > phan vi P (rolling 252 ngay, causal) giam DD ma khong mat > 1/2 premium.
- Du lieu: FRED H.10 ngay (1971/1999+), lai suat ngan han OECD/FRED (thang), VIX FRED (1990+), Dukascopy chi de uoc spread.
- Chia: train 1990-2005, kiem WFO tung nam 2006-2019, HOLDOUT 2020-2026 mo MOT lan. Loi the FX: 30+ nam, nhieu chu ky lai suat.
- Do: excess return sau swap uoc luong (lai suat - markup 0,5-1%/nam [gia dinh phai prereg]), Sharpe, maxDD, skew, loi theo thap ky.
- Doi chung: ro ngau nhien cung so vi the (>= 500 lan); ro EW dollar; ban khong gate.
- Rui ro khop: thap (it tham so); rui ro chinh = carry G10 chet sau 2008 (lai suat 0) -> co the ket qua am - van dang gia vi re.
- Cong: 1-2 ngay agent (Sonnet keo data + Opus thiet ke/audit).
G2. TREND THEO CHUOI THOI GIAN DA DONG TIEN (TSMOM 1-12 thang) + VALUE (REER) ket hop
- Gia thuyet: TSMOM 12m vol-scaled tren 8-10 dong tien vs USD co Sharpe > 0 OOS sau 2010; ket hop z(REER) cai thien (AMP 2013).
- Du lieu: FRED H.10 + BIS REER (1994+), chi phi tu spread Dukascopy.
- Chia: train 1975-1999, kiem WFO 2000-2019, holdout 2020-2026. Do: Sharpe, decay theo thap ky (kiem Neely-Weller suy giam).
- Doi chung: dau ngau nhien (sign-flip), lookback ngau nhien. Rui ro khop: chon lookback -> CHOT 1/3/12 thang truoc, khong tune.
- Cong: 1-2 ngay.
G3. COT TFF (leveraged funds / asset manager) lam tin hieu tuan - "dong long" phien ban FX
- Gia thuyet (prereg ca hai chieu): z-score 156 tuan cua net position leveraged funds o muc cuc tri du bao return 1-4 tuan (tiep dien
  theo Tornell-Yuan hoac dao chieu) - chon chieu tren train, KHONG doi sau.
- Du lieu: CFTC COT legacy 1986+ / TFF 2006+ (free), gia FRED ngay. Luu y lech thoi gian: vi the thu 3, cong bo thu 6 -> chi giao dich
  tu thu 2 sau (chong nhin truoc).
- Chia: train 1993-2009 (legacy non-commercial), kiem 2010-2019 (TFF), holdout 2020-2026. Do: hit rate, return/tuan, IC theo nam.
- Doi chung: xao tron ngay cong bo; tin hieu ngau nhien cung tan suat. Rui ro: so su kien cuc tri / dong tien it (~vai chuc / thap ky)
  -> tinh n_eff va MDE truoc; noi bo crypto: positioning (crowded-long, funding) deu NO-GO -> ky vong thap.
- Cong: 2-3 ngay.
KHONG NEN LAM:
- Grid/martingale/DCA/EA mua tren mang (khong co can cu; trai bai hoc FINDINGS muc 1).
- Scalping / news-trading / breakout phien tren M1 voi gia broker (chi phi + truot + B-book; khong co bang chung; du lieu free khong
  phan anh gia khop that cua broker).
- ML xep hang cat ngang 28 cap (n_eff nho; noi bo B3 da cho thay khop nhieu + dao dau).
- Giao dich that qua broker nuoc ngoai tu VN (muc D).

## H. KHONG KIEM DUOC / CON NGHI NGO
- Dieu khoan su dung du lieu cua Dukascopy, HistData, TrueFX (khong thay trang license); TrueFX con cap nhat toi 2026 hay khong.
- Do sau lich su that cua OANDA v20 candles / orderBook / positionBook (can tai khoan demo).
- Dukascopy "Historical Sentiment Index": do dai lich su va cach tai hang loat.
- Stooq: nam bat dau FX va han muc apikey; Yahoo: hien trang tai lich su (co bao ben thu ba la bi gioi han 2025 - CHUA kiem).
- Ten chuoi FRED lai suat ngan han (IR3TIB01*) va chi so USD broad (DTWEX*) - viet theo tri nho.
- Hieu qua carry G10 sau 2008 va hieu qua momentum/value sau cong bo - theo tri nho, chua co nguon trong file nay.
- Bang chung hoc thuat cho breakout phien / mean-reversion trong ngay: chua tim ky (co the ton tai bai nho).
- Phap ly: muc phat cu the cho ca nhan giao dich Forex qua broker nuoc ngoai; trang thai ND thay ND 88/2019; co rui ro hinh su khong.
- So lieu spread cross/exotic, truot gia, ti le B-book: chua co nguon dang tin.
- Noi bo: chi doc 5 tai lieu + runbook/FINDINGS (luot grep); khong doc ket qua LEVZ T1.
