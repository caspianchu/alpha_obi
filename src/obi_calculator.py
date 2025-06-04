# src/obi_calculator.py

import numpy as np
from typing import List, Tuple
from collections import deque


class OBICalculator:
    """
    根据 HFTBacktest 原文逻辑计算 Order Book Imbalance（OBI）并标准化为 alpha。

    算法步骤：
      1. mid_price = (best_bid + best_ask) / 2
      2. 取区间 [mid*(1-depth), mid*(1+depth)]
      3. sum_bid_qty = ∑ 买盘量(price >= lower_bound)
      4. sum_ask_qty = ∑ 卖盘量(price <= upper_bound)
      5. raw = sum_bid_qty - sum_ask_qty
      6. 将 raw 添加到长度为 window 的滑动缓冲区（deque）
      7. m = mean(buffer), s = std(buffer)
      8. alpha = (raw - m) / s

    其中：
      depth    = 0.025        # 2.5% from mid price
      interval = NANOSECONDS  # 例如 1_000_000_000 for 1s
      window   = 3_600_000_000_000 // interval  # 样本数 = 1 小时 / interval :contentReference[oaicite:0]{index=0}
    """

    def __init__(
            self,
            depth: float = 0.025,
            window_minutes: float = 10.0,
    ):
        self.depth = depth
        # 窗口长度：10 分钟 = 10 * 60 秒 = 600 秒，换算成毫秒就是 600 * 1000
        self.window_ms = int(window_minutes * 60 * 1000)
        # history 存放 (timestamp_ns, raw_imbalance) 元组
        self.history: deque[Tuple[int, float]] = deque()

    def compute_raw_imbalance(
            self,
            bids: List[Tuple[float, float]],
            asks: List[Tuple[float, float]]
    ) -> float:
        """计算当前 tick 的 raw imbalance = ∑bid_qty − ∑ask_qty"""
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2.0

        lower = mid_price * (1 - self.depth)
        upper = mid_price * (1 + self.depth)

        sum_bid = sum(qty for price, qty in bids if price >= lower)
        sum_ask = sum(qty for price, qty in asks if price <= upper)

        return float(sum_bid - sum_ask)

    def compute_alpha(
            self,
            ts: int,
            bids: List[Tuple[float, float]],
            asks: List[Tuple[float, float]]
    ) -> float:
        """
        将本次 raw imbalance 推入 history，
        然后对 history 做均值-标准差标准化，返回 alpha 信号。
        """
        # （1）先清理掉过期数据
        self._purge_expired(ts)

        raw = self.compute_raw_imbalance(bids, asks)
        self.history.append((ts, raw))

        # （3）提取队列里所有的 raw 值，做均值-标准差
        arr = np.array([item[1] for item in self.history], dtype=float)
        m = np.nanmean(arr)
        s = np.nanstd(arr)
        # 若窗口内波动为零，则返回 0 避免除零
        if s == 0 or np.isnan(s):
            alpha = 0.0
        else:
            alpha = float((raw - m) / s)
        return alpha

    def _purge_expired(self, current_ts_ms: int):
        """
        弹出所有时间戳早于 (current_ts_ms - window_ms) 的元素，
        保证队列里只剩下最近 window_minutes 分钟内的数据。
        """
        cutoff = current_ts_ms - self.window_ms
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()