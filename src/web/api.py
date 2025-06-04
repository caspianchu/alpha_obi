from pathlib import Path
import json
from fastapi import FastAPI
from pydantic import BaseModel

from src.config import StrategyConfig

# 默认配置文件路径
CONFIG_PATH = Path("config/strategy_config.json").resolve()

# 读取初始配置
config = StrategyConfig.from_json(str(CONFIG_PATH))


class StrategyConfigModel(BaseModel):
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

    @classmethod
    def from_cfg(cls, cfg: StrategyConfig) -> "StrategyConfigModel":
        return cls(**cfg.to_dict())

app = FastAPI(title="Strategy Config API")

try:
    from fastapi import Knife4j

    Knife4j(app)
except Exception:
    # 如果环境中没有安装 knife4j 插件, 直接忽略
    pass


@app.get("/config", response_model=StrategyConfigModel)
def get_config() -> StrategyConfigModel:
    """读取当前策略参数"""
    return StrategyConfigModel.from_cfg(config)


@app.put("/config", response_model=StrategyConfigModel)
def update_config(new_cfg: StrategyConfigModel) -> StrategyConfigModel:
    """更新策略参数并保存到文件"""
    global config
    config = StrategyConfig.from_dict(new_cfg.dict())
    CONFIG_PATH.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return new_cfg
