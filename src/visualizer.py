# src/visualizer.py

import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter


class AlphaVisualizer:
    """
    负责接收一批 (ts_history, alpha_history) 数据，
    并为每次调用生成一个新的 Figure 进行绘图。
    """

    def __init__(self, title: str = "Real-Time Alpha"):
        # 打开交互模式（可选，能在终端直接看到刷新）
        plt.ion()


    @staticmethod
    def tsl_plot(title, ts_list, alpha_list):
        """
        每次都新建一个 Figure，并一次性画出完整时序。

        :param title:
        :param ts_list: list of datetime.datetime
        :param alpha_list: list of float
        """
        # 1. 新建 Figure & Axes
        fig, ax = plt.subplots()

        # 2. 绘制曲线
        ax.plot(ts_list, alpha_list, lw=1)

        # 3. 标题与标签
        ax.set_title(title)
        ax.set_xlabel("Time")
        ax.set_ylabel("Alpha (Z-score)")

        # 4. 格式化 X 轴时间显示
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
        fig.autofmt_xdate()

        # 5. 显示并让后端处理事件
        fig.show()
        plt.pause(0.001)

    @staticmethod
    def bar_plot(title, ts_list, alpha_list):
        """
        每次都新建一个 Figure，并一次性画出完整时序的柱状图。

        :param title:
        :param ts_list: list of datetime.datetime
        :param alpha_list: list of float
        """
        # 1. 生成每根柱子的颜色：正→绿，负→红
        colors = ['green' if a >= 0 else 'red' for a in alpha_list]
        # 2. 高度用绝对值
        heights = [abs(a) for a in alpha_list]

        # 3. 新建 Figure & Axes
        fig, ax = plt.subplots(figsize=(8, 4))

        # 4. 绘制柱状图
        ax.bar(ts_list, heights, color=colors, width=0.0005)  # width 根据时序密度可调

        # 5. 标题与标签
        ax.set_title(title)
        ax.set_xlabel("Time")
        ax.set_ylabel("Alpha Magnitude")

        # 6. 格式化 X 轴时间显示
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
        fig.autofmt_xdate()

        # 7. 显示并让后端处理事件
        fig.show()
        plt.pause(0.001)  # 强制刷新 GUI

    def close(self):
        """
        关闭所有 Figure
        """
        plt.ioff()
        plt.close("all")
