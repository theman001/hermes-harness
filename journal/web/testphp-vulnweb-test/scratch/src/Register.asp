<%@LANGUAGE="VBSCRIPT" CODEPAGE="1252"%>
<!--#INCLUDE FILE="db.asp"-->
<%
if Request.ServerVariables("REQUEST_METHOD") = "POST" then 
	if Request.Form("tfUName")<>"" AND Request.Form("tfUPass")<>"" then
		set conn = GetConnection()
		
		sql  = "INSERT INTO users (uname, upass, email, realname, avatar) VALUES ("
		sql  = sql & "'" & Request.Form("tfUName") & "',"
		sql  = sql & "'" & Request.Form("tfUPass") & "',"
		sql  = sql & "'" & Request.Form("tfEmail") & "',"
		sql  = sql & "'" & Request.Form("tfRName") & "',"
		sql  = sql & "'')"
		conn.Execute sql
		conn.Close()
		Response.Redirect("Login.asp?RetURL=" & Request.QueryString("RetURL"))
	end if
end if
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html><!-- InstanceBegin template="/Templates/MainTemplate.dwt.asp" codeOutsideHTMLIsLocked="false" -->
<head>
<!-- InstanceBeginEditable name="doctitle" -->
<title>acuforum register</title>