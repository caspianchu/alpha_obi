import ccxt
import time

exchange = ccxt.binanceusdm({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})
exchange.set_sandbox_mode(True)

symbol = 'BTC/USDT'
limit = 10  # 获取订单簿前10档深度


def fetch_order_book(symbol, limit=10):
    orderbook = exchange.fetch_order_book(symbol, limit=limit)
    bids = orderbook['bids']  # 买盘
    asks = orderbook['asks']  # 卖盘
    timestamp = orderbook['timestamp']
    return bids, asks, timestamp


if __name__ == '__main__':
    while True:
        bids, asks, timestamp = fetch_order_book(symbol, limit)
        print(f"Timestamp: {timestamp}")
        print("Bids:", bids)
        print("Asks:", asks)
        time.sleep(1)  # 每秒抓取一次
