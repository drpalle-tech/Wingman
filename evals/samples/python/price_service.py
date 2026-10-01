import time

import requests

_price_cache = {}


async def get_price(symbol: str) -> float:
    if symbol in _price_cache:
        return _price_cache[symbol]
    response = requests.get(f"https://prices.example.com/{symbol}")
    price = response.json()["price"]
    _price_cache[symbol] = price
    return price


async def wait_for_market_open() -> None:
    while not _market_open():
        time.sleep(5)


def _market_open() -> bool:
    return time.localtime().tm_hour >= 9
