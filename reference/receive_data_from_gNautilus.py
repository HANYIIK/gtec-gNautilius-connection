#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time     : 2021/7/18 8:34 上午
# @Author   : Hanyiik
# @File     : receive_data_from_gNautilus.py
# @Function : 从设备中得到 eeg 数据（指定size）

import importlib
import sys
importlib.reload(sys)


import socket
import multiprocessing
from threading import Thread
import mne

import numpy as np

import pygds as g

import warnings
warnings.filterwarnings("ignore")


TRIGGER_TIME = 0.6  # Trigger 间隔(单位: s)
RUNTIME = 60        # 期望程序运行时间(单位: s)


class Get_EEG_from_device_gNautilus:

    def __init__(self):
        self.eeg = None                             # 用于存放 gNautilus 设备发送来的 EEG 数据 ---> Numpy Array 类型
        self.length = 0                             # EEG 数据长度 ---> (16, length)
        self.times = int(250 * RUNTIME * 1)         # 把该程序运行时间控制在 1 分钟

        self.queue = multiprocessing.Queue()        # 多进程并发的Queue队列 ---> 用于解决多进程间的通信问题

        self.getDataFromDevice = True
        self.samples = int(250 * TRIGGER_TIME) + 1  # model 每次处理的 EEG 数据长度 ---> 151（假设设备每 0.6s 发一次）

        self.run = True


    def concatData(self, new_data):
        new_data = new_data.astype(np.float64)
        if self.eeg is None:
            self.eeg = new_data
        else:
            self.eeg = np.concatenate((self.eeg, new_data), axis=1)  # (16, old + new)
        # 更新已经取得的eeg数据长度, self.length == 15000 时停止运行
        self.length = self.eeg.shape[1]

    def receive_EEG_from_device(self):
        """
        接受从gNautilus传过来的数据，假设现在每隔 0.6s 传一次，采样频率为250Hz
        """

        while self.getDataFromDevice and self.length <= self.times: # 把时间控制在 1 分钟
            data = self.device.GetData(250)
            data = data.T  # 转置 (150, 16) ---> (16, 150)
            self.concatData(data)

        print('停止接收 EEG 数据--------')
        self.closeDevice_gNautilus()
        print('释放 gNautilus 设备-------')

    def acquire_eeg(self):
        self.setDevice_gNautilus()
        self.openDevice_gNautilus()

        self.thread = Thread(target=self.receive_EEG_from_device)   # 用于获取 EEG 数据的线程
        self.thread.start()

        start = 0

        while start <= self.times - self.samples:
            end = start + self.samples

            while self.length < self.samples or end > self.length:
                pass        # 等线程再接收一会儿 >_<

            cur_data = self.eeg[:, start:end]
            cur_data = mne.filter.filter_data(cur_data, 250, 2, 45, picks=list(range(16)), verbose=0)
            cur_data = (cur_data - np.mean(cur_data)) / np.std(cur_data)
            '''
                把 cur_data 输入进 model 搞事情 。。。
            '''
            print(cur_data)

            start += 1

            if start + self.samples > self.length >= self.times:
                break

            if self.length >= self.times:
                self.getDataFromDevice = False

        self.thread.join()

        if self.getDataFromDevice:
            self.getDataFromDevice = False
            print('释放设备-------')
            self.closeDevice_gNautilus()

        print('分析结束-------')
        self.run = False


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
        self.device.SamplingRate, self.device.NumberOfScans = minf_s
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


if __name__ == "__main__":

    test = Get_EEG_from_device_gNautilus()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 6001))  # 客户端IP 地址与端口号
    s.listen(5)
    print("Waiting for the connection between gNautilus and local...")
    conn, addr = s.accept()

    test.acquire_eeg()

    conn.close()
    print("Connection from {} is closed".format(addr))
