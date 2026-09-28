<!--#INCLUDE FILE="logInput.asp"-->
<SCRIPT RUNAT=SERVER LANGUAGE=VBSCRIPT>
Function GetConnection()  
	dim conn
	set conn  = Server.CreateObject("ADODB.Connection")
	conn.Open "Provider=SQLNCLI11;Server=(local)\SQL;Database=acuforum;Uid=acunetix;Pwd=acunetixtrustno1;"
	
	set GetConnection = conn
End Function
</script>