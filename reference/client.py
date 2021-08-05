import socket


TRIGGER_IP = '127.0.0.1'
TRIGGER_PORT = 50000


if __name__ == '__main__':
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect_ex((TRIGGER_IP, TRIGGER_PORT))

    while True:
        msg = client.recv(1024)
        str = msg.decode('utf-8')
        print('Get Data State: %s' % (str))