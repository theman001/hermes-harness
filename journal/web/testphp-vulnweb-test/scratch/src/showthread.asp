<%@LANGUAGE="VBSCRIPT" CODEPAGE="1252"%>
<!--#INCLUDE FILE="db.asp"-->
<%
if Request.QueryString("id") = "" then
	Response.Redirect("Default.asp")
end if
set conn = GetConnection()
set rs   = Server.CreateObject("ADODB.recordset")
rs.Open "SELECT b.title, b.forumid, b.id as threadid, a.name FROM forums a, threads b WHERE a.id = b.forumid AND b.id=" & Request.QueryString("id"), conn
ThreadTitle = rs.Fields.Item("title")
ForumName   = rs.Fields.Item("name")
ForumId     = rs.Fields.Item("forumid")
rs.Close()
if Session.Contents("uname")<>"" then
	if Request.ServerVariables("REQUEST_METHOD") = "POST" then 
		if Request.Form("tfSubject")<>"" AND Request.Form("tfText")<>"" then
			sql = "SELECT (MAX(id)+1)AS nextId, COUNT(id) AS total FROM posts WHERE threadid=" & Request.QueryString("id")
			set rs 	= Server.CreateObject("ADODB.recordset")
			rs.Open sql, conn			
			
			if rs.fields.item("total")>100 then
				rs.Close()
				sqldel = "DELETE FROM posts WHERE id<>0 AND threadid=" & Request.QueryString("id")
				conn.Execute sqldel
				nextId = 1				
			else
				nextId = rs.fields.item("nextId")			
				rs.Close()			
			end if
		
			sql = "INSERT INTO posts (id, threadid, forumid, poster, title, message, postdate) VALUES ("
			sql = sql & nextId & ","
			sql = sql & Request.QueryString("id") & ","
			sql = sql & ForumId & ","
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
<title>acuforum
<%Response.Write(ThreadTitle)%>
</title>