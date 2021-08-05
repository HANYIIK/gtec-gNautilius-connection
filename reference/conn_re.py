import socket


TRIGGER_IP = '127.0.0.1'
TRIGGER_PORT = 50000


if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TRIGGER_IP, TRIGGER_PORT))

    while True:
        print(s.recv(34000))

    s.close()