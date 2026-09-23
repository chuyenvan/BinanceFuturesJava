import aerospike, snappy, struct

def parse_map(buf):
    """MinuteDataFinal.tickers -> {sym:(o,h,l,c,v)}"""
    out={}
    p=0; n=len(buf)
    while p<n:
        tag=buf[p]; p+=1
        fn=tag>>3; wt=tag&7
        if wt==2:
            ln=0; sh=0
            while True:
                bb=buf[p]; p+=1; ln|=(bb&0x7f)<<sh; sh+=7
                if not bb&0x80: break
            sub=buf[p:p+ln]; p+=ln
            if fn==1:
                out.update(parse_entry(sub))
        elif wt==0:
            while buf[p]&0x80: p+=1
            p+=1
        elif wt==5: p+=4
        elif wt==1: p+=8
        else: raise ValueError('wt %d'%wt)
    return out

def parse_entry(sub):
    p=0; n=len(sub); key=None; val=None
    while p<n:
        tag=sub[p]; p+=1
        fn=tag>>3; wt=tag&7
        if wt==2:
            ln=0; sh=0
            while True:
                bb=sub[p]; p+=1; ln|=(bb&0x7f)<<sh; sh+=7
                if not bb&0x80: break
            raw=sub[p:p+ln]; p+=ln
            if fn==1: key=raw.decode('utf-8','replace')
            elif fn==2: val=parse_kline(raw)
        elif wt==5:
            raw=sub[p:p+4]; p+=4
        else:
            raise ValueError('entry wt %d'%wt)
    return {key:val} if key is not None else {}

def parse_kline(buf):
    p=0; n=len(buf); d={}
    while p<n:
        tag=buf[p]; p+=1
        fn=tag>>3; wt=tag&7
        if wt==5:
            d[fn]=struct.unpack_from('<f',buf,p)[0]; p+=4
        elif wt==0:
            while buf[p]&0x80: p+=1
            p+=1
        elif wt==2:
            ln=0; sh=0
            while True:
                bb=buf[p]; p+=1; ln|=(bb&0x7f)<<sh; sh+=7
                if not bb&0x80: break
            p+=ln
        elif wt==1: p+=8
    return (d.get(1),d.get(2),d.get(3),d.get(4),d.get(5))

def get(key):
    c=aerospike.client({'hosts':[('103.157.218.242',3222)]})
    rec=c.get(('ticker','kline_1m_opt',key))
    return parse_map(snappy.decompress(rec[2]['data']))

if __name__=='__main__':
    import sys
    for k in sys.argv[1:]:
        m=get(k)
        print(k, "nsym",len(m), "BTC", m.get('BTCUSDT'))
