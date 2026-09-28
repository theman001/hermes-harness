<%@LANGUAGE="VBSCRIPT" CODEPAGE="1252"%>
<%
Session.Contents.Remove("uname")
if Request.QueryString("RetURL")<>"" then
	Response.Redirect(Request.QueryString("RetURL"))
else
	Response.Redirect("Default.asp")
end if
%>