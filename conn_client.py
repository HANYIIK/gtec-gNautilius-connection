#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time     : 2021/7/18 8:40 上午
# @Author   : Hanyiik
# @File     : conn_client.py
# @Function : 与端口 6001（gNautilus）建立连接

import socket
from index import DEVICE_IP, DEVICE_PORT
import _pickle as cPickle

if __name__ == "__main__":

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((DEVICE_IP, DEVICE_PORT))

    while True:
        # print(s.recv(34000))
        print(cPickle.loads(s.recv(34000)))

    s.close()
