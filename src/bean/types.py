# src/types.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Optional
from loguru import logger

@dataclass
class TickContext:
    """
    本类封装一次 on_tick() 触发时的完整状态：
      - ts：原始时间戳（毫秒级）
      - bids/asks：从交易所拿到的深度快照（[(price, qty), ...]）
      - alpha：当前计算得出的 OBI Z-score
      - mid_price：(best_bid + best_ask) / 2
      - bid_price/ask_price：本次要挂的限价
      - bid_tick/ask_tick：限价对应的离散 Tick
      - position：当前持仓（正是多、负是空、0 是空仓）
      - buy_qty/sell_qty：实际要下单的数量（先平仓后建新仓）
      - extra：可选字段，用于以后扩展，例如记录本地时间或其他调试信息。
    """
    ts: int
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    alpha: float

    mid_price: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_tick: Optional[int] = None
    ask_tick: Optional[int] = None
    position: Optional[float] = None
    buy_qty: Optional[float] = None
    sell_qty: Optional[float] = None

    # 预留一个 dict，用于保存其他想记录的调试字段
    extra: dict = field(default_factory=dict)

    def log(self, level: str = "INFO") -> None:
        """
        使用 Loguru 将本次 TickContext 中的所有关键信息按行打印出来，方便阅读和调试。
        level: 日志级别，可选 "DEBUG"/"INFO"/"WARNING"/"ERROR"…
        """
        # 1. 时间字段：把毫秒级 ts 转成人类可读的本地时间
        ts_readable = datetime.fromtimestamp(self.ts / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")

        # 2. 取 BBO：best bid/ask 便于快速查看
        best_bid = self.bids[0][0] if self.bids else None
        best_ask = self.asks[0][0] if self.asks else None

        # 3. 构造一行简洁的摘要
        summary = (
            f"TS={ts_readable} | "
            f"Mid={self.mid_price:.2f} | "
            f"BestBid={best_bid:.2f}/{self.bids[0][1]:.4f} | "
            f"BestAsk={best_ask:.2f}/{self.asks[0][1]:.4f} | "
            f"α={self.alpha:.4f} | "
            f"Pos={self.position:+.4f} | "
            f"Bid={self.bid_price:.2f}(tick={self.bid_tick})[{self.buy_qty:.4f}] | "
            f"Ask={self.ask_price:.2f}(tick={self.ask_tick})[{self.sell_qty:.4f}]"
        )

        # 4. 详细字段：把 asdict 转成小字典（略去 bids/asks 全量数据，聚焦关键字段）
        # details = {
        #     "ts":             ts_readable,
        #     "alpha":          self.alpha,
        #     "mid_price":      self.mid_price,
        #     "position":       self.position,
        #     "bid_price":      self.bid_price,
        #     "ask_price":      self.ask_price,
        #     "bid_tick":       self.bid_tick,
        #     "ask_tick":       self.ask_tick,
        #     "buy_qty":        self.buy_qty,
        #     "sell_qty":       self.sell_qty,
        #     **self.extra     # 合并任何额外上下文
        # }

        # 5. 调用 Loguru 打印：先打印摘要行，再打印详细字典
        logger.log(level, summary)
        #logger.log(level, f"Details: {details}")