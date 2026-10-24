import struct, zlib, gzip, re, datetime as dt
import numpy as np, snappy
B = open('/home/ubuntu/claude_master/parity_v11w/live/raw/gate_ratio_live.bin','rb').read()
i=0; T=[]; R=[]; bad=0
while i+12 <= len(B):
    mg, ln, crc = struct.unpack('>iiI', B[i:i+12])
    if mg != 0x47525231 or ln < 0 or i+12+ln > len(B): bad+=1; i+=1; continue
    c = B[i+12:i+12+ln]
    if zlib.crc32(c) & 0xffffffff != crc: bad+=1; i+=1; continue
    a = np.frombuffer(snappy.uncompress(c), dtype=np.dtype([('t','>i8'),('r','>f4')]))
    T.append(a['t'].astype(np.int64)); R.append(a['r'].astype(np.float32)); i += 12+ln
t = np.concatenate(T); r = np.concatenate(R)
print('n',len(t),'bad',bad,'sorted',bool(np.all(np.diff(t)>=0)), 'dupTs', len(t)-len(np.unique(t)))
o=np.argsort(t,kind='stable'); t=t[o]; r=r[o]
print('first', dt.datetime.utcfromtimestamp(t[0]/1000), 'last', dt.datetime.utcfromtimestamp(t[-1]/1000))
L = gzip.open("/home/ubuntu/claude_master/parity_v11w/live/raw/loglines_1021.gz","rt",errors="ignore").read().splitlines() + gzip.open("/home/ubuntu/claude_master/parity_v11w/live/full_1022_0000_0705.log.gz","rt",errors="ignore").read().splitlines()
pat = re.compile(r'^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)')
def lt(s):
    m=pat.match(s); d,mo,y,hh,mi,ss=map(int,m.groups())
    return int(dt.datetime(y,mo,d,hh,mi,ss,tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp()*1000)
P=0.99995083; H=3600000
rows=[]
for s in L:
    if '[GATE-RATIO] q_t=' in s:
        tt=lt(s); q=float(re.search(r'q_t9=([0-9.]+)',s).group(1)); buf=int(re.search(r'buffer=(\d+)',s).group(1))
        rows.append((tt,q,buf))
def qd(cut, kind):
    a=np.sort(r[:np.searchsorted(t,cut,'left')]); m=len(a)
    if kind=='floor_m1': k=int(np.floor(P*(m-1)))
    elif kind=='floor_m': k=int(np.floor(P*m))
    elif kind=='ceil_m_1': k=int(np.ceil(P*m))-1
    return float(a[min(k,m-1)]), m, a
print('local_log  buf_log  q_log  | m(ts<h)  rep_floor_m1  rep_floor_m  rep_ceil  | m(ts<h-1h) prev_floor_m1 | rank_from_top_of_qlog_in(ts<h)')
for tt,q,buf in rows:
    h=(tt//H)*H
    a1,m1,arr=qd(h,'floor_m1'); a2,_,_=qd(h,'floor_m'); a3,_,_=qd(h,'ceil_m_1'); a4,m4,_=qd(h-H,'floor_m1')
    idx=np.where(np.abs(arr.astype(np.float64)-q)<5e-12)[0]
    rk = [len(arr)-1-j for j in idx]
    loc=dt.datetime.utcfromtimestamp(tt/1000+7*3600).strftime('%m-%d %H:%M')
    print(loc, buf, '%.9g'%q, '|', m1, '%.9g'%a1, '%.9g'%a2, '%.9g'%a3, '|', m4, '%.9g'%a4, '|', rk[:3], 'tail(1-p)(m-1)=%.3f'%((1-P)*(m1-1)))
# top records around switch
h=int(dt.datetime(2026,10,21,6,0,tzinfo=dt.timezone.utc).timestamp()*1000)
sel=r[:np.searchsorted(t,h)]; tt_=t[:np.searchsorted(t,h)]
o=np.argsort(sel)[::-1][:40]
print('top-40 records ts<06:00UTC (rank, value, ts UTC):')
for k,j in enumerate(o): print(k, '%.9g'%sel[j], dt.datetime.utcfromtimestamp(tt_[j]/1000))
# records added 05:00-06:00 UTC with value >= 0.0071
w=(t>=h-H)&(t<h)
print('records 05-06UTC',int(w.sum()),'max r',float(r[w].max()))
w2=(t>=h)&(t<h+H); print('records 06-07UTC',int(w2.sum()),'max', float(r[w2].max()))
