#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time     : 2021/7/19 8:37 下午
# @Author   : Hanyiik
# @File     : index.py
# @Function : 根据 trigger 读取 gNautilus 设备采集的脑电数据

import importlib
import sys
importlib.reload(sys)


import socket
from threading import Thread

import numpy as np

import pygds as g

import pdb
import warnings
warnings.filterwarnings("ignore")


TRIGGER_IP = '127.0.0.1'
TRIGGER_PORT = 50000

DEVICE_IP = '127.0.0.1'
DEVICE_PORT = 6001

BLOCK_RUNTIME = 5       # 闪烁时间为 3s
SAMPLE_RATE = 250       # gNautilus 设备的采样率


class receive_data_with_trigger:

    def __init__(self):
        self.read = False           # False - 不读 | True - 读
        self.trigger_thread = None  # 该线程负责接收 Trigger 并实时改变 self.read 的值
        self.receive_thread = None  # 该线程负责接收设备发送来的 EEG 数据

        self.eeg = None             # 用于存放 gNautilus 设备发送来的 EEG 数据
        self.length = 0             # EEG 数据的最终总长度 ---> (16, length)

        self.block_eeg = None       # 用于存放 gNautilus 设备发送来的每个 Block 的 EEG 数据
        self.block_length = 0       # 每个 Block 的 EEG 数据的总长度 ---> (16, block_length)

        self.standard_block_length = int(SAMPLE_RATE * BLOCK_RUNTIME * 1)  # 理论 Block 长度 = 采样率 * 理论闪烁时间 = 625

        self.run = True


    def set_read(self, server_ip=TRIGGER_IP, server_port=TRIGGER_PORT):
        """
        :: 功能: 接收 AR 端发来的 trigger
        :: 输入: server_ip - AR 端 IP 地址
                server_port - AR 端端口号
        :: 输出: 动态改变 self.read 的值
        :: 用法: 丢给线程去做
        """
        server_addr = (server_ip, server_port)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect_ex(server_addr)

        while self.run:
            msg = client.recv(1024)
            str = msg.decode('utf-8')
            if str == '1':          # trigger 开始
                self.read = True
            elif str == '2':        # trigger 结束
                self.read = False
            elif str == '3':        # trigger 程序关了
                self.read = False
                self.run = False
            else:
                RuntimeError("Trigger有问题")


    def print_status(self):
        while True:
            print(self.read)


    def concatData(self, new_data):
        new_data = new_data.astype(np.float64)
        if self.eeg is None:
            self.eeg = new_data
        else:
            self.eeg = np.concatenate((self.eeg, new_data), axis=1)  # (16, old + new)
        # 更新已经取得的eeg数据长度
        self.length = self.eeg.shape[1]

    def concatBlock(self, new_data):
        new_data = new_data.astype(np.float64)
        if self.block_eeg is None:
            self.block_eeg = new_data
        else:
            self.block_eeg = np.concatenate((self.block_eeg, new_data), axis=1)  # (16, old + new)
        # 更新已经取得的eeg数据长度
        self.block_length = self.block_eeg.shape[1]


    def init_block(self):
        self.block_eeg = None
        self.block_length = 0


    def receive_EEG_from_device(self):
        self.init_block()

        while self.read and self.block_length <= self.standard_block_length:
            data = self.device.GetData(SAMPLE_RATE)
            data = data.T  # 转置 (xxx, 16) ---> (16, xxx)
            self.concatBlock(data)
            self.concatData(data)

        if self.block_length != self.standard_block_length:
            print(f'收到的 Block 数据长度为：{self.block_length}，理论应为：{self.standard_block_length}')
            print(self.block_eeg)
            print(self.block_eeg.shape)
        else:
            print(f'读取到{self.block_length}长度的数据！')


    def setDevice_gNautilus(self, scans=125, sample_rate=250, time=200):
        """
        :param scans: 计算公式：(scans * 1000) / sample_rate = time
        :param sample_rate:采样率
        :param time: 取数据的间隔, ms,不能低于30ms
        :return: (sample_rate * time, 16)
        """
        self.device = g.GDS()
        cd = g.ConnectedDevices()

        minf_s = sorted(self.device.GetSupportedSamplingRates()[0].items())[0]
        self.device.SamplingRate, self.device.NumberOfScans = minf_s        # (250, 8) 每 32ms 取一次数据
        sensitivities = self.device.GetSupportedSensitivities()[0]

        for ch in self.device.Channels:
            ch.Acquire = True
            ch.BipolarChannel = -1  # -1 => to GND
            ch.Sensitivity = sensitivities[3]
            ch.UsedForNoiseReduction = 0
            ch.UsedForCAR = 0
            ch.BandpassFilterIndex = 13  # 带通13
            ch.NotchFilterIndex = 0  # 陷波
            ch.NoiseReduction = 0
            ch.CAR = 0
            ch.ValidationIndicator = 0
            ch.AccelerationData = 0
            ch.LinkQualityInformation = 0
            ch.BatteryLevel = 0

        self.device.Channels[1].Acquire = True
        self.device.SetNetworkChannel(14)
        self.device.SetConfiguration()

    def openDevice_gNautilus(self):
        pass

    def closeDevice_gNautilus(self):
        self.device.Close()
        del self.device


    def start(self):
        """
        :: 功能: 开始动态读取 EEG 数据
        :: 输入: 无
        :: 输出:
        :: 用法:
        """
        # 与 gNautilus 建立连接
        print('正在与 gNautilus 建立连接 ---------')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((DEVICE_IP, DEVICE_PORT))
        s.listen(5)
        print('请运行客户端程序 ---------')
        conn, addr = s.accept()
        print(f"与{addr}的连接建立成功 ---------")

        # 初始化 gNautilus
        print('开始初始化设备 ---------')
        self.setDevice_gNautilus()
        self.openDevice_gNautilus()
        print('设备初始化成功 ---------')

        # 读取 Trigger
        print('开始读取 Trigger ---------')
        self.trigger_thread = Thread(target=self.set_read)
        self.trigger_thread.start()


        while self.run:
            if not self.read:
                continue
            else:
                self.receive_thread = Thread(target=self.receive_EEG_from_device)
                self.receive_thread.start()
            self.receive_thread.join()

        self.trigger_thread.join()     # main process waits for the finalization of this thread.

        s.close()
        print('与 gNautilus 的连接已关闭 ---------')
        self.closeDevice_gNautilus()
        print('gNautilus 资源已释放 ---------')



if __name__ == '__main__':
    r = receive_data_with_trigger()
    r.start()
