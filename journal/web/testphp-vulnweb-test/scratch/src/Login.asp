<%@LANGUAGE="VBSCRIPT" CODEPAGE="1252"%>
<!--#INCLUDE FILE="db.asp"-->
<%
InvalidLogin = false
if Request.ServerVariables("REQUEST_METHOD") = "POST" then 
	if Request.Form("tfUName")<>"" AND Request.Form("tfUPass")<>"" then
		set conn = GetConnection()
		sql = "SELECT uname, upass FROM users WHERE uname='" & Request.Form("tfUName") & "' AND upass='" & Request.Form("tfUPass") & "'"
		set rs = Server.CreateObject("ADODB.recordset")
		rs.Open sql, conn
		if not rs.EOF then
			Session.Contents("uname") = Request.Form("tfUName")
			if Request.QueryString("RetURL")<>"" then
				Response.Redirect(Request.QueryString("RetURL"))
			else
				Response.Redirect("Default.asp")
			end if
		else
			InvalidLogin = true
		end if
		
		rs.Close()
		conn.Close()
		
	end if
end if
%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html><!-- InstanceBegin template="/Templates/MainTemplate.dwt.asp" codeOutsideHTMLIsLocked="false" -->
<head>
<!-- InstanceBeginEditable name="doctitle" -->
<title>acuforum login</title>