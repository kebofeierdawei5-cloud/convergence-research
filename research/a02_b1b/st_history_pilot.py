from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import requests

ORIGIN_DATES={
 "2023Q3":"2023-09-28","2023Q4":"2023-12-29","2024Q1":"2024-03-29","2024Q2":"2024-06-28",
 "2024Q3":"2024-09-30","2024Q4":"2024-12-31","2025Q1":"2025-03-31","2025Q2":"2025-06-30",
 "2025Q3":"2025-09-30","2025Q4":"2025-12-31","2026Q1":"2026-03-31"
}

def sha256(b:bytes)->str: return hashlib.sha256(b).hexdigest()

def df_from_rs(rs):
    import pandas as pd
    rows=[]
    if rs.error_code!='0': return None, {'error_code':rs.error_code,'error_msg':rs.error_msg}
    while rs.next(): rows.append(rs.get_row_data())
    return pd.DataFrame(rows,columns=rs.fields), None

def current_csi800_codes(root:Path):
    url='https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000906cons.xls'
    r=requests.get(url,timeout=90,headers={'User-Agent':'Mozilla/5.0 (IIOS-B1B2)'},allow_redirects=True)
    raw=r.content; p=root/'seed'/'current_000906cons.xls'; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)
    meta={'requested_url':url,'final_url':r.url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'http_status':r.status_code,'size_bytes':len(raw),'sha256':sha256(raw),'exact_bytes':True}
    (root/'seed'/'current_000906cons.xls.meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    import pandas as pd
    xls=pd.ExcelFile(p,engine='xlrd')
    candidates=[]
    for sheet in xls.sheet_names:
        df=pd.read_excel(p,sheet_name=sheet,engine='xlrd',header=None)
        for col in range(df.shape[1]):
            vals=df.iloc[:,col].astype(str).str.extract(r'(\d{6})',expand=False).dropna().tolist()
            hits=[v for v in vals if len(v)==6]
            if len(set(hits))>=700: candidates.append((len(set(hits)),hits))
    if not candidates: raise RuntimeError('cannot identify 000906 constituent-code column')
    codes=sorted(set(candidates[0][1]))
    if len(codes)!=800: raise RuntimeError(f'expected 800 current CSI800 codes, got {len(codes)}')
    (root/'seed'/'current_csi800_codes.json').write_text(json.dumps(codes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return codes

def run_pilot(root:Path,codes:list[str],limit:int):
    import baostock as bs
    login=bs.login()
    if login.error_code!='0': raise RuntimeError(f'baostock login failed: {login.error_code} {login.error_msg}')
    out=root/'st_history'; out.mkdir(parents=True,exist_ok=True)
    receipt={'schema_version':'IIOS-A02-B1B2-ST-HISTORY-PILOT-0.1','retrieved_at':datetime.now(timezone.utc).isoformat(),'sample_size':min(limit,len(codes)),'provider':'BAOSTOCK','provider_role':'FREE_SECONDARY_PIT_CANDIDATE','records':{}}
    try:
        for code6 in codes[:limit]:
            code=('sh.' if code6.startswith(('600','601','603','605','688','689')) else 'sz.')+code6
            rs=bs.query_history_k_data_plus(code,'date,code,tradestatus,isST',start_date='2023-01-01',end_date='2026-03-31',frequency='d',adjustflag='3')
            df,err=df_from_rs(rs)
            if err: receipt['records'][code6]={'status':'BLOCKED','error':err}; continue
            p=out/f'{code6}.csv'; df.to_csv(p,index=False,encoding='utf-8')
            origin_rows={}
            if not df.empty and 'date' in df.columns:
                bydate={str(r['date']):r for _,r in df.iterrows()}
                for origin,day in ORIGIN_DATES.items():
                    row=bydate.get(day)
                    origin_rows[origin]=None if row is None else {'date':str(row['date']),'tradestatus':str(row.get('tradestatus','')),'isST':str(row.get('isST',''))}
            receipt['records'][code6]={'status':'CONDITIONAL','path':str(p.relative_to(root)),'rows':len(df),'sha256':sha256(p.read_bytes()),'origin_rows':origin_rows,'known_at':None,'reason':'Historical isST observation is available from the free API, but source-side publication/vintage known_at is not exposed by the result.'}
    finally: bs.logout()
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return receipt

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); ap.add_argument('--limit',type=int,default=50); args=ap.parse_args()
    root=Path(args.out).resolve(); root.mkdir(parents=True,exist_ok=True)
    codes=current_csi800_codes(root)
    rec=run_pilot(root,codes,args.limit)
    print(json.dumps({'sample_size':rec['sample_size'],'records_ok':sum(1 for v in rec['records'].values() if v.get('status')=='CONDITIONAL')},ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())