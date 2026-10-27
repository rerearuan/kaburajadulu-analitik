"""Bounded collection + transparent heuristic screening. Only use authorized data access."""
import argparse, csv, json, os, pathlib, re, time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
from dotenv import load_dotenv

TZ=ZoneInfo('Asia/Jakarta')
START=date(2026,1,1); END=date(2026,10,26)
OUT=pathlib.Path('outputs')
# Preserve the 36 TK-1/TK-2 discovery terms. A and D are essential for topic variety.
QUERIES={
'A':['cari kerja','mencari kerja','lowongan kerja','lamar kerja','rekrutmen','fresh graduate','peluang kerja','karier'],
'B':['susah cari kerja','sulit cari kerja','pengangguran','PHK','kena PHK','gaji rendah','upah minimum','syarat pengalaman','pengalaman kerja','pekerjaan kontrak','kerja tidak sesuai jurusan','pasar kerja Indonesia'],
'C':['kerja di luar negeri','bekerja di luar negeri','kerja ke luar negeri','cari kerja di luar negeri','kabur aja dulu','#KaburAjaDulu','kerja di Jepang','kerja di Singapura'],
'D':['jobs in Indonesia','job market Indonesia','unemployment Indonesia','layoffs Indonesia','low wages Indonesia','working abroad from Indonesia','Indonesians working abroad','leave Indonesia for work']}
PRIORITY={'B':0,'C':1,'A':2,'D':3}
# Search dates are padded; local WIB date is authoritative.
DATE_RE=re.compile(r'https?://\S+|@\w+')
WORK=re.compile(r'(?i)\b(kerja|bekerja|pekerjaan|pekerja|pencari kerja|pengangguran|nganggur|karier|career|job|jobs|employment|unemploy\w*|recruit\w*|rekrut\w*|lamar|lowongan|upah|gaji|salary|wage\w*|phk|layoff\w*|fresh grad\w*|kontrak|karyawan|magang|interview|loker|honorer|visa kerja|work visa|perusahaan|company|perantau|working abroad)\b')
PROBLEM=re.compile(r'(?i)(susah|sulit|susahnya|susah banget|frustrasi|cemas|resah|krisis|terbatas|kurang|tidak ada|ga ada|nggak ada|gak ada|belum dapat|belum dapet|pengangguran|nganggur|phk|layoff|upah rendah|gaji rendah|pengalaman kerja|ketidakpastian|kontrak|tidak sesuai jurusan|penuh persaingan|jobless|unemploy|low wages|low salary)')
ABROAD=re.compile(r'(?i)(luar negeri|mancanegara|overseas|abroad|kabur\s*aja\s*dulu|#kaburajadulu|ke jepang|di jepang|ke singapura|di singapura|ke korea|di korea|ke australia|di australia|pindah negara|kerja di (?:japan|singapore|korea|china|belanda|eropa)|work(?:ing)? (?:in|at|for) (?:japan|singapore|china|korea)|visa sponsorship)')
INDONESIA=re.compile(r'(?i)(indonesia|\bindo\b|\bri\b|\bui\b|jakarta|surabaya|bandung|jogja|jogjakarta|yogyakarta|rupiah|\bidr\b|\bbpjs\b|\bumr\b|\bumk\b|\bwni\b|anak bangsa|di sini|di negara ini)')
NOISE=re.compile(r'(?i)(giveaway|diskon|promo kode|slot gacor|togel|seminar|webinar|event study abroad|register now|pendaftaran seminar|pertandingan|la liga|jual akun|open jastip)')
PROMO=re.compile(r'(?i)(lowongan kerja.{0,40}(dibutuhkan|terbuka)|dibutuhkan segera|daftar sekarang|pendaftaran dibuka|rekrutmen dibuka|join (?:our|us)|program penempatan|pendaftaran program|apply now|open recruitment)')
INCIDENTAL=re.compile(r'(?i)(selingkuh|privacy pasien|privasi pasien|kecelakaan lalu lintas|kemalangan di tambak|kisah percintaan)')


def load_jsonl(path):
    if not path.exists():return []
    rows=[]
    with path.open(encoding='utf8') as f:
        for line in f:
            try: rows.append(json.loads(line))
            except (ValueError,TypeError):pass
    return rows

def append_jsonl(path,entry):
    with path.open('a',encoding='utf8') as f: f.write(json.dumps(entry,ensure_ascii=False)+'\n')

def windows(mode):
    current=START
    while current<END:
        if mode=='weekly': stop=min(current+timedelta(days=7),END)
        else:
            stop=min(date(current.year + (current.month==12), (current.month%12)+1,1), END)
        yield current,stop
        current=stop

def build_tasks(mode, groups):
    """Spread work across months AND query families; keep old keys for resume.

    All original weekly ranges are retained, including cross-month weeks.
    Filtering January is applied only to new task scheduling (not raw/derive).
    """
    all_windows=list(windows(mode))
    months=[f'2026-{m:02d}' for m in range(1,11)]
    by_month={m:[] for m in months}
    # Rotate among topic families, rather than exhausting one keyword in all months.
    families=[g for g in ('C','B','A','D') if g in groups]
    rotating_keywords=[]
    for k in range(max(len(QUERIES[g]) for g in families)):
        for g in families:
            if k<len(QUERIES[g]): rotating_keywords.append((g,QUERIES[g][k]))
    for start,end in all_windows:
        month=start.strftime('%Y-%m')
        for g,keyword in rotating_keywords:
            search=keyword if keyword.startswith('#') else '"'+keyword+'"'
            query=f'{search} since:{(start-timedelta(days=1)).isoformat()} until:{end.isoformat()}'
            key=f'{start.isoformat()}__{end.isoformat()}__{g}__{keyword.casefold()}'
            by_month[month].append(dict(key=key,window_start=str(start),window_end=str(end),group=g,keyword=keyword,query=query))
    ordered=[]
    for i in range(max(len(v) for v in by_month.values())):
        for month in months:
            if i<len(by_month[month]): ordered.append(by_month[month][i])
    return ordered


def wib_date(stamp):
    try:
        d=datetime.fromisoformat(str(stamp).replace('Z','+00:00'))
        return d.astimezone(TZ).date() if d.tzinfo else None
    except (TypeError,ValueError): return None

def screen(text):
    """Recall-oriented eligibility pre-screen, NOT a verified research annotation."""
    text=DATE_RE.sub(' ',text or '').strip()
    if len(text)<24: return 'exclude_auto','too_short'
    if NOISE.search(text):return 'review','possible_promo_or_event'
    if PROMO.search(text):return 'review','possible_recruitment_promotion'
    if INCIDENTAL.search(text):return 'review','possible_incidental_mention'
    work=bool(WORK.search(text)); problem=bool(PROBLEM.search(text)); abroad=bool(ABROAD.search(text)); indo=bool(INDONESIA.search(text))
    if work and (problem or abroad or indo):return 'candidate','employment_context'
    if work:return 'review','work_context_not_specific'
    if abroad:return 'review','abroad_without_clear_work'
    return 'exclude_auto','no_employment_topic'

def print_monthly_summary(monthly_data):
    print("\n" + "=" * 76)
    print("MONITORING DISTRIBUSI BULANAN (WIB):")
    print(f"{'Bulan':<9} | {'RAW':<6} | {'Unik Valid':<11} | {'Candidate (Rel)':<16} | {'Review':<8} | {'Exclude':<8}")
    print("-" * 76)
    for m in sorted(monthly_data.keys()):
        d = monthly_data[m]
        print(f"{m:<9} | {d['raw']:<6} | {d['unique_valid']:<11} | {d['candidate_unverified']:<16} | {d['needs_review']:<8} | {d['auto_excluded']:<8}")
    print("=" * 76 + "\n")

def derive():
    """Rebuild all outputs from raw, with ID dedup and collision-aware evidence."""
    raw=load_jsonl(OUT/'raw_tweets.jsonl')
    data={}; valid_occurrences=0; invalid_date=0; missing=0
    monthly_data = {f'2026-{m:02d}': {'raw': 0, 'unique_valid': 0, 'candidate_unverified': 0, 'needs_review': 0, 'auto_excluded': 0, 'confirmed_relevant': 0} for m in range(1, 11)}
    for wrap in raw:
        rec=wrap.get('record',{})
        if not isinstance(rec,dict):continue
        pid=str(rec.get('id') or '')
        dt=wib_date(rec.get('createdAt'))
        if not pid or not dt or not str(rec.get('text') or '').strip():missing+=1;continue
        m_raw = dt.strftime('%Y-%m')
        if m_raw in monthly_data:
            monthly_data[m_raw]['raw'] += 1
        # For v3 archived records, requested month is sufficient; newest script uses exact WIB window.
        begin=wrap.get('window_start')
        end=wrap.get('window_end')
        if begin and end: valid=date.fromisoformat(begin)<=dt<date.fromisoformat(end)
        else:
            mm=wrap.get('month_requested','')
            valid=(mm == dt.strftime('%Y-%m')) and START<=dt<END
        if not valid:invalid_date+=1;continue
        valid_occurrences+=1
        if pid not in data:
            data[pid]=dict(post_id=pid,text_raw=rec['text'],timestamp_wib=dt.isoformat(),permalink=rec.get('url',''),query_groups=set(),matched_queries=set(),run_ids=set())
        row=data[pid]
        for k,field in [('query_group','query_groups'),('matched_query','matched_queries'),('apify_run_id','run_ids')]:
            if wrap.get(k): row[field].add(wrap[k])
    # Manually reviewed decisions override heuristic and persist by post ID.
    decisions={}
    reviewfile=OUT/'manual_labels.csv'
    if reviewfile.exists():
        with reviewfile.open(encoding='utf-8-sig',newline='') as f:
            for item in csv.DictReader(f):
                if item.get('decision','').strip().lower() in ('include','exclude'):
                    decisions[item['post_id']]=item['decision'].strip().lower()
    fields=['post_id','text_raw','timestamp_wib','permalink','query_groups','matched_queries','run_ids','auto_label','auto_reason','manual_decision','final_status']
    statuses={}
    with (OUT/'screened_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in sorted(data.values(),key=lambda r:r['timestamp_wib']):
            lab,reason=screen(row['text_raw']);manual=decisions.get(row['post_id'],'')
            status=('confirmed_relevant' if manual=='include' else 'confirmed_excluded' if manual=='exclude' else 'candidate_unverified' if lab=='candidate' else 'needs_review' if lab=='review' else 'auto_excluded')
            statuses[status]=statuses.get(status,0)+1
            m_str = row['timestamp_wib'][:7]
            if m_str in monthly_data:
                monthly_data[m_str]['unique_valid'] += 1
                if status in monthly_data[m_str]:
                    monthly_data[m_str][status] += 1
            writer.writerow({**row,'query_groups':json.dumps(sorted(row['query_groups']),ensure_ascii=False),'matched_queries':json.dumps(sorted(row['matched_queries']),ensure_ascii=False),'run_ids':json.dumps(sorted(row['run_ids'])),'auto_label':lab,'auto_reason':reason,'manual_decision':manual,'final_status':status})
    stats={'raw_records_stored':len(raw),'raw_valid_date_occurrences':valid_occurrences,'raw_outside_requested_window':invalid_date,'raw_missing_required_fields':missing,'unique_valid_wib':len(data),'predicted_relevant_unique_unverified':statuses.get('candidate_unverified',0),'confirmed_relevant_unique':statuses.get('confirmed_relevant',0),'pending_manual_review':statuses.get('candidate_unverified',0)+statuses.get('needs_review',0),'confirmed_excluded_unique':statuses.get('confirmed_excluded',0),'auto_excluded_unique':statuses.get('auto_excluded',0),'statuses':statuses,'monthly_breakdown':monthly_data}
    (OUT/'collection_summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf8')
    return stats

def run_actor(sess,task,limit,poll,attempts):
    actor=os.getenv('APIFY_ACTOR_ID','scrapesmith~x-twitter-search-scraper')
    payload={'searchTerms':[task['query']],'sort':'Latest','maxTweets':limit,'maxItems':limit}
    log={**task,'status':'STARTING','run_id':'','raw':0,'valid_wib':0,'invalid_wib':0,'error':'','started_at':datetime.now(timezone.utc).isoformat()}
    try:
        r=sess.post(f'https://api.apify.com/v2/acts/{actor}/runs',json=payload,timeout=60);r.raise_for_status()
        rid=r.json()['data']['id'];log['run_id']=rid
        final=None
        for _ in range(attempts):
            resp=sess.get(f'https://api.apify.com/v2/actor-runs/{rid}',timeout=60);resp.raise_for_status()
            final=resp.json()['data'];status=final.get('status','UNKNOWN')
            if status in ('SUCCEEDED','FAILED','TIMED-OUT','ABORTED'):break
            time.sleep(poll)
        log['status']=final.get('status','UNKNOWN')
        if log['status']!='SUCCEEDED':
            log['error']='Run incomplete; inspect Apify Console. Do not blindly retry.'
            return log
        did=final.get('defaultDatasetId')
        if not did:raise ValueError('Missing dataset ID')
        offset=0
        while True:
            r=sess.get(f'https://api.apify.com/v2/datasets/{did}/items',params={'format':'json','offset':offset,'limit':1000},timeout=90);r.raise_for_status()
            items=r.json()
            if not isinstance(items,list):raise ValueError('Unexpected dataset API response')
            for item in items:
                rawrow={**task,'month_requested':task['window_start'][:7],'query_group':task['group'],'matched_query':task['keyword'],'search_query':task['query'],'apify_run_id':rid,'record':item,'collected_at_utc':datetime.now(timezone.utc).isoformat()}
                append_jsonl(OUT/'raw_tweets.jsonl',rawrow)
                log['raw']+=1
                dt=wib_date(item.get('createdAt'))
                if dt and date.fromisoformat(task['window_start'])<=dt<date.fromisoformat(task['window_end']):log['valid_wib']+=1
                else:log['invalid_wib']+=1
            offset+=len(items)
            if len(items)<1000:break
        return log
    except (requests.RequestException,ValueError,KeyError,TypeError) as e:
        log['status']='ERROR';log['error']=str(e);return log

def main():
    load_dotenv()
    p=argparse.ArgumentParser(description='Cost-bounded X research collector: raw, unique, and heuristic-relevant counts')
    p.add_argument('--execute',action='store_true',help='Perform billable Actor calls; omitted means dry-run')
    p.add_argument('--window',choices=['weekly','monthly'],default='weekly')
    p.add_argument('--groups',default='B,C,A,D',help='Priority groups, comma separated; default all 36 keywords')
    p.add_argument('--target',type=int,default=1000)
    p.add_argument('--start-month',default='2026-02',help='Earliest month of NEW scraping tasks (default 2026-02). Old RAW remains untouched.')
    p.add_argument('--stop-mode',choices=['predicted','confirmed'],default='predicted',help='predicted=automatic candidate stopping; confirmed=only manual include labels')
    p.add_argument('--max-per-query',type=int,default=30)
    p.add_argument('--max-runs',type=int,default=12,help='Hard cap on new Actor runs for this invocation')
    p.add_argument('--max-new-raw',type=int,default=500,help='Safety cap: stop starting new runs once this many raw results have been retrieved in invocation (can overshoot by one run)')
    p.add_argument('--estimated-usd-limit',type=float,default=1.0,help='Conservative estimated charge cap per invocation; not an Apify billing guarantee')
    p.add_argument('--assumed-usd-per-1000',type=float,default=0.15,help='Replace with actual actor price shown on your account')
    p.add_argument('--min-date-hit-rate',type=float,default=0.2)
    p.add_argument('--delay',type=float,default=1.0)
    a=p.parse_args()
    if not re.fullmatch(r'2026-(0[1-9]|10)',a.start_month):p.error('--start-month must be 2026-01 through 2026-10')
    if a.target<1 or a.max_runs<1 or a.max_new_raw<1 or not (1<=a.max_per_query<=1000) or a.assumed_usd_per_1000<=0 or a.estimated_usd_limit<=0 or not 0<=a.min_date_hit_rate<=1:p.error('Invalid limits')
    groups=set(x.strip().upper() for x in a.groups.split(','))
    if not groups or groups-set(QUERIES):p.error('groups must be subset of A,B,C,D')
    OUT.mkdir(exist_ok=True)
    tasks=build_tasks(a.window,groups)
    (OUT/'planned_tasks.json').write_text(json.dumps(tasks,ensure_ascii=False,indent=2),encoding='utf8')
    previous=load_jsonl(OUT/'target_run_log.jsonl')
    completed={x.get('key') for x in previous if x.get('status')=='SUCCEEDED'}
    started={x.get('key') for x in previous if x.get('status') not in ('SUCCEEDED',None)}
    pending=[x for x in tasks if x['window_start'][:7]>=a.start_month and x['key'] not in completed and x['key'] not in started]
    stats=derive()
    print(f"INITIAL | raw={stats['raw_records_stored']} | unique={stats['unique_valid_wib']} | predicted_relevant_unverified={stats['predicted_relevant_unique_unverified']} | confirmed_relevant={stats['confirmed_relevant_unique']}")
    print_monthly_summary(stats['monthly_breakdown'])
    print(f'PLAN | {len(tasks)} total planned tasks; {len(pending)} eligible pending from {a.start_month}; first: {pending[0]["query"] if pending else "none"}')
    print('JANUARY NEW SCRAPING | disabled' if a.start_month>'2026-01' else 'JANUARY NEW SCRAPING | enabled')
    print('NEXT 12 | ' + ', '.join(t['window_start'][:7]+':'+t['keyword'] for t in pending[:12]))
    if not a.execute:
        print('DRY-RUN ONLY | No Apify API calls. Plan in outputs/planned_tasks.json');return
    token=os.getenv('APIFY_API_TOKEN')
    if not token:p.error('Set APIFY_API_TOKEN in .env')
    sess=requests.Session();sess.headers.update({'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    new_raw=0;estimated=0.0;new_runs=0
    def count_for_goal(s):
        return (s['predicted_relevant_unique_unverified']+s['confirmed_relevant_unique']) if a.stop_mode=='predicted' else s['confirmed_relevant_unique']
    if count_for_goal(stats)>=a.target:
        print('TARGET MET for mode '+a.stop_mode+'; candidate predictions are NOT verified.');return
    print('STOP MODE: '+a.stop_mode+' | Only manual include labels count as confirmed relevant.')
    for task in pending:
        if new_runs>=a.max_runs or new_raw>=a.max_new_raw:break
        # Given per-result pricing, reserve enough space for the next full run.
        projected=estimated+(a.max_per_query*a.assumed_usd_per_1000/1000)
        if projected>a.estimated_usd_limit:
            print('STOP: conservative estimated USD limit before next run.');break
        log=run_actor(sess,task,a.max_per_query,5,120)
        append_jsonl(OUT/'target_run_log.jsonl',log)
        new_runs+=1;new_raw+=log['raw'];estimated+=log['raw']*a.assumed_usd_per_1000/1000
        stats=derive()
        print(f"[{new_runs}] {task['group']} {task['window_start']}..{task['window_end']} {task['keyword']} | {log['status']} raw_run={log['raw']} valid_run={log['valid_wib']} | raw_total={stats['raw_records_stored']} unique={stats['unique_valid_wib']} predicted={stats['predicted_relevant_unique_unverified']} confirmed={stats['confirmed_relevant_unique']}",flush=True)
        if log['status']!='SUCCEEDED':print('STOP: inspect status before retrying.');break
        if log['raw'] and log['valid_wib']/log['raw']<a.min_date_hit_rate:
            print('STOP: poor date-window hit rate; adjust Actor query before scaling.');break
        if count_for_goal(stats)>=a.target:
            print('TARGET MET ('+a.stop_mode+'): '+str(count_for_goal(stats))+' unique; predictions still require manual review.');break
        time.sleep(a.delay)
    stats=derive()
    print_monthly_summary(stats['monthly_breakdown'])
    print(f'DONE | new_runs={new_runs} new_raw={new_raw} estimated_USD_this_invocation={estimated:.4f} (not actual billed cost)')
    print('Outputs: outputs/raw_tweets.jsonl, outputs/screened_candidates.csv, outputs/collection_summary.json, outputs/target_run_log.jsonl')
    print('Review outputs/manual_labels.csv; auto-screening is NOT manual confirmation.')
if __name__=='__main__':main()
