<%@LANGUAGE="VBSCRIPT" CODEPAGE="1252"%>
<!--#INCLUDE FILE="db.asp"-->
<%
if Request.QueryString("id") = "" then
	Response.Redirect("Default.asp")
end if
set conn = GetConnection()
set rs   = Server.CreateObject("ADODB.recordset")
rs.Open "SELECT name, descr FROM forums WHERE id=" & Request.QueryString("id"), conn
ForumName = rs.Fields.Item("name")
ForumDesc = rs.Fields.Item("descr")
rs.Close()
if Session.Contents("uname")<>"" then
	if Request.ServerVariables("REQUEST_METHOD") = "POST" then 
			if Request.Form("tfSubject")<>"" AND Request.Form("tfText")<>"" then
			
			If InStr(1, Request.Form("tfText"), "<a href=") > 0 then
				Response.End
			end if

			If InStr(1, Request.Form("tfSubject"), "<a href=") > 0 then
				Response.End
			end if
			
			sql = "SELECT (MAX(id)+1) as nextId, COUNT(id) as total FROM threads WHERE forumid=" & Request.QueryString("id")
			set rs 	= Server.CreateObject("ADODB.recordset")
			rs.Open sql, conn
						
			if rs.fields.item("total")>100 then
				rs.Close()
				sqldel = "DELETE FROM threads WHERE forumid=" & Request.QueryString("id")								
				conn.Execute sqldel
				sqldel = "DELETE FROM posts WHERE forumid=" & Request.QueryString("id")
				conn.Execute sqldel
				nextId = 0				
			else			
				if isnull(rs.fields.item("nextId")) then
					nextId = 0
				else
					nextId = rs.fields.item("nextId")
				end if				
				rs.Close()			
			end if
		
			sql = "INSERT INTO threads (id, forumid, poster, title, postdate) VALUES ("
			sql = sql & nextId & ","
			sql = sql & Request.QueryString("id") & ","
			sql = sql & "'" & Session.Contents("uname") & "',"
			sql = sql & "'" & Replace(Request.Form("tfSubject"), "'", "''", 1, -1, 1) & "',"
			sql = sql & "GETDATE())"

			conn.Execute sql
			
			ThreadId = nextId
		
			sql = "INSERT INTO posts (id, threadid, forumid, poster, title, message, postdate) VALUES ("
			sql = sql & "0,"
			sql = sql & ThreadId & ","
			sql = sql & Request.QueryString("id") & ","
			sql = sql & "'" & Session.Contents("uname") & "',"
			sql = sql & "'" & Replace(Request.Form("tfSubject"), "'", "''", 1, -1, 1) & " - " & Request.ServerVariables("REMOTE_ADDR") & "',"
			sql = sql & "'" & Replace(Request.Form("tfText"), "'", "''", 1, -1, 1) & "', GETDATE())"
			
			conn.Execute sql
		end if
	end if
end if
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html><!-- InstanceBegin template="/Templates/MainTemplate.dwt.asp" codeOutsideHTMLIsLocked="false" -->
<head>
<!-- InstanceBeginEditable name="doctitle" -->
<title>acuforum <%Response.Write(ForumName)%></title>