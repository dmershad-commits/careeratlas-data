"""Bounded official-link audit; never treats access blocks as closed vacancies."""
import concurrent.futures, gzip, json, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from urllib.parse import urlsplit

ALLOWED={"jobs.smartrecruiters.com","job-boards.greenhouse.io","boards.greenhouse.io","jobs.unicef.org","careers.un.org","careers.unesco.org","careers.unops.org"}
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args): return None
def check(url):
    if urlsplit(url).hostname not in ALLOWED: return "unchecked"
    try:
        with build_opener(NoRedirect).open(Request(url,headers={"User-Agent":"CareerAtlas vacancy link check","Range":"bytes=0-4095"}),timeout=8) as r:
            r.read(4096)
            return "reachable"
    except HTTPError as e:
        return "broken" if e.code in (404,410) else "unknown"
    except Exception: return "unknown"
def expired(j,now):
    try: return datetime.fromisoformat(j["deadline"].replace("Z","+00:00")).replace(tzinfo=timezone.utc) <= now
    except (ValueError,KeyError,TypeError,AttributeError): return False
def run(root):
    public=Path(root)/"public"; now=datetime.now(timezone.utc)
    data=json.loads(gzip.decompress((public/"jobs.json.gz").read_bytes()))
    hp=public/"link-health.json"
    try: history=json.loads(hp.read_text())
    except (OSError,ValueError): history={}
    active=[j for j in data["jobs"] if not j.get("closed") and j.get("availability")=="listed" and not expired(j,now)]
    candidates=sorted({j["url"] for j in active if urlsplit(j["url"]).hostname in ALLOWED},key=lambda u:(history.get(u,{}).get("failures",0)!=1,history.get(u,{}).get("checked_at","")))[:300]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for url,result in zip(candidates,pool.map(check,candidates)):
            old=history.get(url,{})
            history[url]={"status":result,"checked_at":now.isoformat(),"failures":old.get("failures",0)+1 if result=="broken" else 0}
    urls={j["url"] for j in data["jobs"]}
    history={u:v for u,v in history.items() if u in urls}
    for j in data["jobs"]:
        h=history.get(j["url"],{})
        # Two separate collection audits required before suppression.
        j["link_status"]="broken" if h.get("failures",0)>=2 else h.get("status","unchecked")
        if j["link_status"]=="broken" and h.get("failures",0)<2: j["link_status"]="suspected"
        j["link_checked_at"]=h.get("checked_at")
        if j["link_status"]=="broken": j["availability"]="unavailable"
    status=json.loads((public/"status.json").read_text())
    status["quality"]={"links_checked_this_run":len(candidates),"confirmed_broken":sum(j["link_status"]=="broken" for j in data["jobs"]),"expired":sum(expired(j,now) for j in data["jobs"]),"scope":"Rotating 300 supported official links per run; 403,429,redirects and timeouts remain unknown."}
    (public/"jobs.json.gz").write_bytes(gzip.compress(json.dumps(data,ensure_ascii=False,separators=(",",":")).encode(),mtime=0))
    hp.write_text(json.dumps(history,separators=(",",":")))
    (public/"status.json").write_text(json.dumps(status,indent=2))
    print(json.dumps(status["quality"]))
if __name__=="__main__": run(sys.argv[1] if len(sys.argv)>1 else ".")
