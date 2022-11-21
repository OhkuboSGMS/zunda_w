import psutil
for sock in psutil.net_connections():
    if sock.laddr and sock.laddr.port ==50021:
            print(sock.laddr)