import asyncio
import uvicorn

from src.web.api import app, config as api_config
from src.data_fetcher_ws import OrderBookStreamer
from src.strategy import MarketMakingStrategy


class TradingApp:
    """Simple application that runs the strategy and exposes the config API."""

    def __init__(self) -> None:
        self.cfg = api_config
        self.streamer = None
        self.strategy = None

    async def start_strategy(self) -> None:
        """Start the market making strategy using the current configuration."""
        self.streamer = OrderBookStreamer(
            symbol=self.cfg.symbol,
            limit=self.cfg.limit,
            depth=self.cfg.depth,
            window_minutes=self.cfg.window_minutes,
        )
        self.strategy = MarketMakingStrategy(
            symbol=self.cfg.symbol,
            order_qty=self.cfg.order_qty,
            c1=self.cfg.c1,
            half_spread=self.cfg.half_spread,
            skew=self.cfg.skew,
            max_position_btc=0.01,
            api_key=self.cfg.api_key,
            secret=self.cfg.secret,
            price_delta_threshold=self.cfg.price_delta_threshold,
        )
        await self.strategy.initialize()
        await self.strategy.exchange.load_markets()

        try:
            async for ts, bids, asks, alpha in self.streamer.stream():
                # If configuration has changed, update strategy parameters
                if api_config != self.cfg:
                    self.cfg = api_config
                    self.strategy.order_qty = self.cfg.order_qty
                    self.strategy.c1 = self.cfg.c1
                    self.strategy.half_spread = self.cfg.half_spread
                    self.strategy.skew = self.cfg.skew
                    self.strategy.price_delta_threshold = self.cfg.price_delta_threshold
                    self.streamer.limit = self.cfg.limit
                    self.streamer.obi_calc.depth = self.cfg.depth
                    self.streamer.obi_calc.window_ms = int(self.cfg.window_minutes * 60 * 1000)
                try:
                    await self.strategy.on_tick(ts, bids, asks, alpha)
                except Exception as e:
                    print(f"策略处理错误: {e}")
        finally:
            await self.streamer.close()
            await self.strategy.close()

    async def start_api(self) -> None:
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    async def run(self) -> None:
        await asyncio.gather(self.start_strategy(), self.start_api())


if __name__ == "__main__":
    asyncio.run(TradingApp().run())
