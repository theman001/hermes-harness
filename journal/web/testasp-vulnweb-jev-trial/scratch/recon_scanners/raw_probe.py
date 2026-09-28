
import socket
def raw(req, label):
    s = socket.create_connection(("testasp.vulnweb.com", 80), timeout=15)
    s.sendall(req.encode())
    data = b""
    try:
        while True:
            c = s.recv(4096)
            if not c: break
            data += c
    except Exception:
        pass
    s.close()
    print("==== %s ====" % label)
    print(data.decode("latin-1")[:700])
    print()

raw("GET /aspnet_client HTTP/1.0\r\n\r\n", "no-host /aspnet_client HTTP/1.0")
raw("GET / HTTP/1.0\r\n\r\n", "no-host / HTTP/1.0")
raw("GET /aspnet_client HTTP/1.1\r\nHost: testasp.vulnweb.com\r\nConnection: close\r\n\r\n", "host /aspnet_client 1.1")
raw("GET /aspnet_client/ HTTP/1.0\r\n\r\n", "no-host /aspnet_client/ 1.0")
raw("GET /default.aspx HTTP/1.0\r\n\r\n", "no-host /default.aspx 1.0")
