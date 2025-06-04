# src/data_fetcher_ws.py

import asyncio
import ccxt.pro as ccxtpro
from .obi_calculator import OBICalculator
from typing import AsyncGenerator, Tuple, List


class OrderBookStreamer:
    def __init__(
            self,
            symbol: str = 'BTC/USDT',
            limit: int = 100,
            depth: float = 0.025,
            window_minutes: float = 10.0,
            sandbox_mode: bool = True
    ):
        self.symbol = symbol
        self.limit = limit
        # 初始化算京 imbalance 计算器
        self.obi_calc = OBICalculator(depth=depth, window_minutes=window_minutes)
        # WebSocket 交易所实例
        self.exchange = ccxtpro.binanceusdm({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })
        self.exchange.set_sandbox_mode(sandbox_mode)

    async def stream(self) -> AsyncGenerator[Tuple[int, List, List, float], None]:
        """
        异步生成器，每次 yield (timestamp, bids, asks, alpha)
        """
        try:
            while True:
                ob = await self.exchange.watch_order_book(
                    self.symbol,
                    self.limit
                )
                ts = ob['timestamp']
                bids = ob['bids']
                asks = ob['asks']
                # 计算 alpha
                alpha = self.obi_calc.compute_alpha(ts, bids, asks)
                # 真实地 yield 出去
                yield ts, bids, asks, alpha
        except Exception as e:
            print("WebSocket 错误，重试：", e)
            await asyncio.sleep(1)
            # 继续循环／重连
            await self.stream()

    async def close(self):
        await self.exchange.close()
