# src/strategy.py

import math

import ccxt.async_support as ccxt
from typing import Tuple, Optional, Any
from loguru import logger

from src.bean.types import TickContext


class MarketMakingStrategy:
    """
    做市策略核心逻辑（永续合约）：
      1) calculate_prices(...)：传入最新 bids/asks/alpha，按 tick size + 仓位倾斜 计算实际挂单价格
      2) manage_orders(...)：根据 bid_tick/ask_tick 对比当前 open_orders 来撤单或补单

    核心思路：
      - 每次 on_tick 被调用时，先用最新 bids/asks/alpha 和当前持仓算目标 bid/ask
      - 如果 mid 波动超过阈值，就“全量刷新”挂单（先撤单再挂单）；否则只做“缺失订单补单”即可
    """

    def __init__(
            self,
            symbol: str,
            order_qty: float,
            c1: float,
            half_spread: float,
            skew: float,
            max_position_btc: float,
            price_delta_threshold: float = 0.5,
            api_key: Optional[str] = None,
            secret: Optional[str] = None,
            enableRateLimit: bool = True
    ):
        self.symbol = symbol
        self.order_qty = order_qty
        self.c1 = c1
        self.half_spread = half_spread
        self.skew = skew
        self.max_position_btc = max_position_btc
        self.price_delta_threshold = price_delta_threshold
        self.last_mid: Optional[float] = None
        self.api_key = api_key
        self.secret = secret

        # 异步 REST 下单客户端
        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': enableRateLimit,
            'options': {'defaultType': 'future'},
            'apiKey': self.api_key,
            'secret': self.secret,
        })
        self.exchange.set_sandbox_mode(True)

        self.tick_size: Optional[float] = None
        self.precision: Optional[int] = None

    async def initialize(self) -> None:
        """
        加载市场信息，获取 tick_size 与 precision
        """
        markets = await self.exchange.load_markets()
        if self.symbol not in markets:
            raise ValueError(f"Symbol {self.symbol} 不存在于交易所市场列表。")
        market = markets[self.symbol]
        info = market.get('info', {})

        tick_size = 0.0
        precision = None

        # 1) 从 info['filters'] 里找到 PRICE_FILTER.tickSize
        filters = info.get('filters')
        if isinstance(filters, list):
            for f in filters:
                if f.get('filterType') == 'PRICE_FILTER':
                    try:
                        tick_size = float(f.get('tickSize', 0))
                    except (ValueError, TypeError):
                        tick_size = 0.0
                    break

        # 2) 如果没拿到，再试 precision['price']
        if tick_size <= 0:
            price_prec = market.get('precision', {}).get('price')
            if price_prec is not None:
                try:
                    tick_size = 1.0 / (10 ** int(price_prec))
                except (ValueError, TypeError):
                    tick_size = 0.0

        # 3) 如果仍然没拿到，再试 info['pricePrecision']
        if tick_size <= 0:
            pp = info.get('pricePrecision')
            if pp is not None:
                try:
                    tick_size = 1.0 / (10 ** int(pp))
                except (ValueError, TypeError):
                    tick_size = 0.0

        # 4) 最终判断
        if tick_size <= 0:
            raise RuntimeError(f"获取不到 {self.symbol} 的 tickSize，请检查！")

        # 5) 由 tick_size 计算 price precision
        try:
            precision = int(round(-math.log10(tick_size)))
        except (ValueError, TypeError):
            precision = 8

        self.tick_size = tick_size
        self.precision = precision
        logger.info(f"[initialize] Symbol={self.symbol}, tick_size={self.tick_size}, precision={self.precision}")

    async def calculate_prices(self, ctx: TickContext) -> TickContext:
        """
        结合 alpha 与仓位做“reservation_price”与“边界”逻辑，返回目标 bid/ask 价格与 tick。
        """
        bids = ctx.bids
        asks = ctx.asks
        alpha = ctx.alpha

        # 1) best_bid, best_ask, mid
        best_bid = bids[0][0] if bids else 0.0
        best_ask = asks[0][0] if asks else 0.0
        mid_price = (best_bid + best_ask) / 2.0

        # 2) fair_price = mid + c1 * alpha
        fair_price = mid_price + self.c1 * alpha

        # 3) 异步获取当前持仓（张数）
        # 3.1. 拿到所有仓位
        all_positions = await self.exchange.fetch_positions()

        # 3.2. 循环筛选当前合约那条记录
        position = 0.0
        for pos_info in all_positions:
            # 先做 symbol 匹配
            # pos_info['symbol'] 里通常是 "BTC/USDT:USDT"，和 self.symbol 要完全一致
            if pos_info.get('symbol') == self.symbol:
                # 从 pos_info["info"]["positionAmt"] 里读字符串"-0.924"
                info = pos_info.get('info', {})
                raw_amt = info.get('positionAmt', None)
                if raw_amt is not None:
                    # 直接把 "-0.924" 转成 -0.924（浮点），不要再 round/int
                    position = float(raw_amt)
                else:
                    # 如果万一 info 里没有 positionAmt，就 fallback 用 contracts + side
                    cnt = float(pos_info.get('contracts', 0.0))  # 0.924
                    side = pos_info.get('side', '').lower()  # "short" 或 "long"
                    # 如果是空头，position 取负；如果是多头，position 取正
                    position = -cnt if side == 'short' else cnt
                break

        # 4) 标准化仓位
        normalized_position = position / self.order_qty if self.order_qty != 0 else 0.0

        # 5) reservation_price = fair_price - skew * normalized_position
        reservation_price = fair_price - self.skew * normalized_position

        # 6) raw_bid_price = min(round(reservation_price - half_spread), best_bid)
        #    raw_ask_price = max(round(reservation_price + half_spread), best_ask)
        # 然后再保证 raw_bid_price < best_bid 几一个 tick
        raw_bid_price = (reservation_price - self.half_spread)
        if raw_bid_price >= best_bid:
            raw_bid_price = best_bid - self.tick_size
        # raw_ask_price = max((reservation_price + self.half_spread), best_ask)
        raw_ask_price = (reservation_price + self.half_spread)
        if raw_ask_price <= best_ask:
            raw_ask_price = best_ask + self.tick_size

        # 7) 四舍五入到最近 tick
        bid_tick = math.floor(raw_bid_price / self.tick_size)
        ask_tick = math.ceil(raw_ask_price / self.tick_size)

        bid_price = bid_tick * self.tick_size
        ask_price = ask_tick * self.tick_size

        bid_price = float(f"{bid_price:.{self.precision}f}")
        ask_price = float(f"{ask_price:.{self.precision}f}")

        # bid_price, ask_price, bid_tick, ask_tick, mid_price, position
        ctx.bid_price = bid_price
        ctx.ask_price = ask_price
        ctx.bid_tick = bid_tick
        ctx.ask_tick = ask_tick
        ctx.mid_price = mid_price
        ctx.position = position
        return ctx

    async def manage_orders(self, ctx: TickContext) -> None:
        """
        差量更新挂单：
          - 如果第一次 / mid 跳动 ≥ 阈值：全量撤单再挂
          - 否则：只补缺失的那边订单（若对手吃掉再补）
        """
        bid_tick = ctx.bid_tick
        ask_tick = ctx.ask_tick
        bid_price = ctx.bid_price
        ask_price = ctx.ask_price
        position = ctx.position

        try:
            open_orders = await self.exchange.fetch_open_orders(self.symbol)
        except Exception:
            open_orders = []

        # existing_buy_ticks, existing_sell_ticks 保存目前已有挂单的 Tick id
        existing_buy_ticks = set()
        existing_sell_ticks = set()
        for order in open_orders:
            price = float(order.get("price", 0.0))
            tick = int(round(price / self.tick_size))
            if order.get("side") == "buy":
                existing_buy_ticks.add(tick)
            elif order.get("side") == "sell":
                existing_sell_ticks.add(tick)

        # —— 3. 根据当前 position 计算要挂的“剩余量” buy_qty / sell_qty ——
        if position > 0:
            buy_qty = max(self.order_qty - position, 0.0)
            sell_qty = self.order_qty
        elif position < 0:
            sell_qty = max(self.order_qty - abs(position), 0.0)
            buy_qty = self.order_qty
        else:
            buy_qty = self.order_qty
            sell_qty = self.order_qty

        # —— 3.  批量下单 ——
        to_create = []
        if bid_tick not in existing_buy_ticks and buy_qty > 0:
            to_create.append({
                "symbol": self.symbol,
                "side": "buy",
                "type": "limit",
                "amount": buy_qty,
                "price": bid_price,
                "timeInForce": "GTC",
            })

        if ask_tick not in existing_sell_ticks and sell_qty > 0:
            to_create.append({
                "symbol": self.symbol,
                "side": "sell",
                "type": "limit",
                "amount": sell_qty,
                "price": ask_price,
                "timeInForce": "GTC",
            })

        if to_create:
            await self.exchange.cancel_all_orders(self.symbol)
            await self.exchange.create_orders(to_create)
            ctx.buy_qty = buy_qty
            ctx.sell_qty = sell_qty
            ctx.log()

    async def on_tick(
            self,
            ts: int,
            bids: list,
            asks: list,
            alpha: float
    ) -> None:
        """
        每次收到新的深度数据和 alpha，就重算一次 bid/ask 并尝试更新挂单。
        """
        ctx = TickContext(ts=ts, bids=bids, asks=asks, alpha=alpha)

        # 1) 先算出目标 bid_price/ask_price + 对应 tick
        ctx = await self.calculate_prices(ctx)

        # 2) 再根据信号来撤单/补单
        await self.manage_orders(ctx)

    async def close(self) -> None:
        await self.exchange.close()
