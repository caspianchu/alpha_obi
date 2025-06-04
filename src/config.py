# src/config.py

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

@dataclass
class StrategyConfig:
    symbol: str
    order_qty: float
    c1: float
    half_spread: float
    skew: float
    limit: int
    depth: float
    window_minutes: float
    api_key: str
    secret: str
    price_delta_threshold: float
    sandbox_mode: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            symbol=data["symbol"],
            order_qty=float(data["order_qty"]),
            c1=float(data["c1"]),
            half_spread=float(data["half_spread"]),
            skew=float(data["skew"]),
            limit=int(data["limit"]),
            depth=float(data["depth"]),
            window_minutes=float(data["window_minutes"]),
            api_key=str(data.get("api_key", "")),
            secret=str(data.get("secret", "")),
            price_delta_threshold=float(data.get("price_delta_threshold", 0.5)),
            sandbox_mode=data.get("sandbox_mode", True)
        )

    @classmethod
    def from_json(cls, file_path: str):
        """
        支持两种方式：
        1) 绝对路径，例如 "/Users/.../alpha_obi/config/strategy_config.json"
        2) 相对路径，相对项目根（而不是当前脚本所在目录）
        """
        # 先把传入的 file_path 转成 Path 对象
        p = Path(file_path)
        # 如果传入的是相对路径，我们把它视作相对项目根
        if not p.is_absolute():
            # __file__ 是 src/config.py 的路径
            # parent.parent 会指到项目根 alpha_obi 目录
            project_root = Path(__file__).resolve().parent.parent
            p = (project_root / file_path).resolve()

        if not p.exists():
            raise FileNotFoundError(f"配置文件不存在: {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "order_qty": self.order_qty,
            "c1": self.c1,
            "half_spread": self.half_spread,
            "skew": self.skew,
            "limit": self.limit,
            "depth": self.depth,
            "window_minutes": self.window_minutes,
            "api_key": self.api_key,
            "secret": self.secret,
            "price_delta_threshold": self.price_delta_threshold,
            "sandbox_mode": self.sandbox_mode
        }
