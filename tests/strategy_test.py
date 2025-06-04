# tests/strategy_test.py
from src.config import StrategyConfig
from src.data_fetcher_ws import OrderBookStreamer
from src.strategy import MarketMakingStrategy
import asyncio


async def main():
    cfg = StrategyConfig.from_json('config/strategy_config.json')
    streamer = OrderBookStreamer(
        symbol=cfg.symbol,
        limit=cfg.limit,
        depth=cfg.depth,
        window_minutes=cfg.window_minutes
    )
    strategy = MarketMakingStrategy(
        symbol=cfg.symbol,
        order_qty=cfg.order_qty,
        c1=cfg.c1,
        half_spread=cfg.half_spread,
        skew=cfg.skew,
        max_position_btc=0.01,
        api_key=cfg.api_key,
        secret=cfg.secret,
        price_delta_threshold=cfg.price_delta_threshold,
    )
    # 先 load_markets 拿到 tick_size/precision
    await strategy.initialize()
    await strategy.exchange.load_markets()

    try:
        async for ts, bids, asks, alpha in streamer.stream():
            #await strategy.on_tick(ts, bids, asks, alpha)
            try:
                # 由外部循环按 tick 调用 on_tick
                await strategy.on_tick(ts, bids, asks, alpha)
            except Exception as e:
                print(f"策略处理错误: {e}")
    finally:
        await streamer.close()
        await strategy.close()


if __name__ == '__main__':
    asyncio.run(main())
