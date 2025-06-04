# tests/alpha_test.py
import sys
import asyncio
import time
from datetime import datetime
from src.data_fetcher_ws import OrderBookStreamer
from src.visualizer import AlphaVisualizer


async def main(symbol: str, limit: int):
    streamer = OrderBookStreamer(symbol=symbol, limit=limit)
    visualizer = AlphaVisualizer()

    ts_history = []
    alpha_history = []
    last_plot = time.time()

    try:
        async for ts, bids, asks, alpha in streamer.stream():
            # 累积历史
            ts_history.append(datetime.fromtimestamp(ts / 1000))
            alpha_history.append(alpha)

            # 每 5 分钟触发一次绘图
            if time.time() - last_plot >= 300:  # 300 秒 = 5 分钟
                visualizer.bar_plot("Alpha Bar Chart", ts_history, alpha_history)
                last_plot = time.time()

    finally:
        await streamer.close()
        visualizer.close()


if __name__ == '__main__':
    asyncio.run(main('BTC/USDT', 100))
