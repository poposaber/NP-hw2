import socket

tester_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tester_socket.connect(("127.0.0.1", 30000))