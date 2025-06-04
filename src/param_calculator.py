import ccxt.async_support as ccxt
import asyncio
from loguru import logger
from dataclasses import dataclass
import numpy as np

@dataclass
class MarketData:
    best_bid: float
    best_ask: float
    maker_fee: float
    taker_fee: float
    tick_size: float


class MarketMakerParamCalculatorV2:
    def __init__(self,
                 market_data: MarketData,
                 order_qty: float,
                 alpha_std: float,
                 epsilon_profit: float = 0.5):
        self.market_data = market_data
        self.order_qty = order_qty
        self.alpha_std = alpha_std
        self.epsilon_profit = epsilon_profit

    def calculate_half_spread(self) -> float:
        mid_price = (self.market_data.best_bid + self.market_data.best_ask) / 2
        total_fee = self.market_data.maker_fee + self.market_data.taker_fee
        min_half_spread = (mid_price * total_fee) / 2 + self.epsilon_profit / (2 * self.order_qty)
        return np.ceil(min_half_spread / self.market_data.tick_size) * self.market_data.tick_size

    def calculate_c1(self, half_spread: float) -> float:
        return half_spread * (1 + 1 / self.alpha_std)

    def calculate_skew(self, half_spread: float) -> float:
        mid_price = (self.market_data.best_bid + self.market_data.best_ask) / 2
        capital = self.order_qty * mid_price
        ratio = max(0.04, 0.1 - 0.06 * np.log10(capital))
        return half_spread * ratio

    def get_params(self):
        half_spread = self.calculate_half_spread()
        c1 = self.calculate_c1(half_spread)
        skew = self.calculate_skew(half_spread)
        return {
            "order_qty": self.order_qty,
            "half_spread": half_spread,
            "c1": round(c1, 2),
            "skew": round(skew, 2)
        }


async def fetch_market_data(symbol: str, exchange: ccxt.Exchange) -> MarketData:
    orderbook = await exchange.fetch_order_book(symbol)
    best_bid = orderbook['bids'][0][0]
    best_ask = orderbook['asks'][0][0]

    market = await exchange.load_markets()
    tick_size = market[symbol]['precision']['price']
    tick_size = 1 / (10 ** tick_size)

    maker_fee = 0.0002  # Binance Futures标准
    taker_fee = 0.0005

    return MarketData(
        best_bid=best_bid,
        best_ask=best_ask,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        tick_size=tick_size
    )


async def main():
    symbol = 'ME/USDT:USDT'
    order_qty = 10
    alpha_std = 1

    exchange = ccxt.binanceusdm({
        'enableRateLimit': True,
    })

    try:
        market_data = await fetch_market_data(symbol, exchange)
        calculator = MarketMakerParamCalculatorV2(
            market_data=market_data,
            order_qty=order_qty,
            alpha_std=alpha_std,
            epsilon_profit=0.5
        )
        params = calculator.get_params()

        logger.info(f"Market Data: {market_data}")
        logger.info(f"Calculated Params: {params}")

    except Exception as e:
        logger.error(f"Error fetching data or calculating params: {e}")

    finally:
        await exchange.close()


if __name__ == '__main__':
    asyncio.run(main())
