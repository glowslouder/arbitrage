# funding_arbitrage_multi.py – v1.1.0
# -----------------------------------------------------------------------------
# ➡️  Порівнюємо **чистий funding-rate** (частка за інтервал), без перерахунку в APR.
#     Шукаємо найбільшу різницю між біржами по кожній монеті й шлемо TG-алерт.
#     Формат алерту:  backpack −0.0100 % vs aevo +0.0100 %  →  Δ 0.0200 %
# -----------------------------------------------------------------------------
#   pip install aiohttp loguru rich orjson certifi
# -----------------------------------------------------------------------------
import asyncio, os, sys, time, ssl
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import aiohttp, orjson, certifi
from loguru import logger
from rich import print as rprint
from mongoengine import connect
from dotenv import load_dotenv
from os import getenv
import requests

from fundings_api import models

# ──────────────────────────── DJANGO SETTINGS ───────────────────────────────

load_dotenv()
DB_SETTINGS = {
    'db': 'admin',
    'username': getenv('MONGO_INITDB_ROOT_USERNAME'),
    'password': getenv('MONGO_INITDB_ROOT_PASSWORD'),
    'host': 'localhost'
}

# ───────────────────────────────── LOGURU ────────────────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    format="<white>{time:HH:mm:ss}</white> | <level>{level:<8}</level> | <cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True,
)

# ───────────────────────────────── CONFIG ────────────────────────────────────
CONFIG = {
    "telegram_token": os.getenv("TG_TOKEN", "7755792318:AAHnaz4RBpXROlE-jDFChPJaErU5C1INRm0"),
    # кома-розділений список chat-id
    "telegram_chat_id": os.getenv("TG_CHAT", "467666249, 437623181"),
    "symbols": ["AAVE", "ACT", "ADA", "ALT", "ARB", "AVAX", "AXL", "BNB", "BTC", "CHILLGUY", "DOGE", "DOT", "ENA", "ETH", "GOAT", "GRASS", "INIT", "INJ", "JUP", "LINK", "LTC", "MANTA", "ME", "MOODENG", "MOVE", "NEAR", "ONDO", "OP", "PENGU", "PNUT", "POL", "S", "SOL", "STRK", "SUI", "TAO", "TIA", "UMA", "UNI", "USUAL", "WIF", "WLD", "XRP"],

    # мін. різниця funding-rate у % (не APR!) для алерту
    "diff_threshold_pct": 0.05,   # 0.02 % == 2 bp
    "poll_sec": 60,
}

# ────────────────────────────── UTILITIES ────────────────────────────────────

def to_utc(ts):
    if isinstance(ts, str):
        ts = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    ts = int(ts)
    if ts > 1e18:
        ts //= 1_000_000_000
    elif ts > 1e15:
        ts //= 1_000_000
    elif ts > 1e12:
        ts //= 1_000
    elif ts > 1e10:
        ts //= 1_000
    return datetime.fromtimestamp(ts, tz=timezone.utc)

CHAT_IDS = [cid.strip() for cid in CONFIG["telegram_chat_id"].split(",") if cid.strip()]

async def send_telegram(text: str):
    tok = CONFIG["telegram_token"]
    if not tok or not CHAT_IDS:
        logger.warning("TG: token or chat-ids missing, skip send")
        return
    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_ctx)
    async with aiohttp.ClientSession(connector=connector) as s:
        for cid in CHAT_IDS:
            try:
                r = await s.post(url, json={"chat_id": cid,
                                            "text": text,
                                            "parse_mode": "Markdown"}, timeout=10)
                logger.debug(f"TG→{cid} {r.status}")
            except Exception as e:
                logger.error(f"TG send to {cid}: {e}")

@dataclass
class Funding:
    exchange: str
    symbol: str
    rate_frac: float # дробова, не відсотки
    index_price: float
    reset_time: int

# ───────────────────────────── FETCHERS ──────────────────────────────────────
async def fetch_backpack(session: aiohttp.ClientSession, base: str) -> Funding:
    sym = f"{base}_USDC_PERP"
    url = f"https://api.backpack.exchange/api/v1/markPrices?symbol={sym}"
    # logger.debug(f"GET {url}")
    async with session.get(url, timeout=10) as r:
        data = await r.json()
    last = data[0]
    rate_frac = float(last["fundingRate"])  # вже дробова
    index_price = float(last["indexPrice"])
    reset_time = float(last["nextFundingTimestamp"])
    return Funding("backpack", base, rate_frac, index_price, reset_time)

async def fetch_aevo(session: aiohttp.ClientSession, bases: list) -> Funding:
    url = "https://api.aevo.xyz/coingecko-statistics"
    async with session.get(url, timeout=10) as r:
        j = await r.json()
    out = []
    for c in j:
        if c["base_currency"] in bases and c["product_type"] == "Perpetual":
            rate_frac = float(c["funding_rate"])
            index_price = float(c['index_price'])
            reset_time = float(c['next_funding_rate_timestamp'])
            out.append(Funding("aevo", c["base_currency"], rate_frac, index_price, reset_time))
    return out

async def fetch_kiloex(session: aiohttp.ClientSession, bases: list) -> Funding:
    url = "https://opapi.kiloex.io/common/getCoingeckoApiData"
    # logger.debug(f"GET {url} (filter {base})")
    async with session.get(url, timeout=10) as r:
        txt = await r.text()
    j = orjson.loads(txt)
    out = []
    for c in j.get("contracts", []):
        if c.get("base_currency") in bases and c.get("product_type") == "PERP":
            raw = float(c["funding_rate"])
            # KiloEx повертає % → переводимо в дробову
            rate_frac = raw / 100.0
            index_price = float(c['index_price'])
            reset_time = float(c['end_timestamp'])
            out.append(Funding("kiloex", c.get("base_currency"), rate_frac, index_price, reset_time))
    return out

async def fetch_paradex(session: aiohttp.ClientSession, base: str) -> Funding:
    url = f"https://api.prod.paradex.trade/v1/markets/summary?market={base}-USD-PERP"
    async with session.get(url, timeout=10) as r:
        res = await r.json()
    rate_frac = float(res['results'][0]['funding_rate'])
    index_price = float(res['results'][0]['mark_price'])
    return Funding("paradex", base, rate_frac, index_price, -1)

FETCHERS = [{"backpack": fetch_backpack, "paradex": fetch_paradex}, {"aevo": fetch_aevo, "kiloex": fetch_kiloex}]

# ───────────────────────────── CORE LOGIC ────────────────────────────────────
async def collect_all(session):
    tasks_group1 = [asyncio.create_task(fn(session, sym))
             for sym in CONFIG["symbols"] for fn in FETCHERS[0].values()]
    out = []
    for t in asyncio.as_completed(tasks_group1):
        try:
            out.append(await t)
        except Exception as e:
            logger.error(e)
        # out.append(await t)
    tasks_group2 = [asyncio.create_task(fn(session, CONFIG['symbols'])) for fn in FETCHERS[1].values()]
    for t in asyncio.as_completed(tasks_group2):
        try:
            out.extend(await t)
        except Exception as e:
            logger.error(e)
    return out

# def calc_spreads(fundings: List[Funding]):
#     by: Dict[str, List[Funding]] = {}
#     for f in fundings:
#         by.setdefault(f.symbol, []).append(f)
#     for sym, lst in by.items():
#         if len(lst) < 2:
#             continue
#         best_long = max(lst, key=lambda x: x.rate_frac)
#         best_short = min(lst, key=lambda x: x.rate_frac)
#         diff_pct = (best_long.rate_frac - best_short.rate_frac) * 100  # у %
#         yield sym, diff_pct, best_long, best_short

# ────────────────────────── DATA SERIALIZATION ───────────────────────────────

def serialization(dict_data):
    serialized_data = models.MainFundingModel(fundings=dict_data)
    # logger.info(serialized_data.to_mongo().to_dict())
    return serialized_data

# ─────────────────────────────── MAIN LOOP ───────────────────────────────────
async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    try:
        connect(**DB_SETTINGS)
    except Exception as error:
        rprint("Failed to connect to database: ", error)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            t0 = time.time()
            rates = await collect_all(session)
            logger.info(f"Зібрано {len(rates)} ставок")
            dict_data = dict()
            for funding in rates:
                if funding.symbol not in dict_data: dict_data[funding.symbol] = {
                    funding.exchange: {
                        "rate": funding.rate_frac*100,
                        "index_price": funding.index_price,
                        "reset_time": funding.reset_time
                    }
                }
                else: dict_data[funding.symbol][funding.exchange] = {
                        "rate": funding.rate_frac*100,
                        "index_price": funding.index_price,
                        "reset_time": funding.reset_time
                    }
            # for sym, diff_pct, long, short in calc_spreads(rates):
            #     logger.success(
            #         f"{sym}: {short.exchange} {short.rate_frac*100:+.4f}% vs {long.exchange} {long.rate_frac*100:+.4f}% → Δ {diff_pct:+.4f}%"
            #     )
            #     if abs(diff_pct) >= CONFIG["diff_threshold_pct"]:
            #         text = (
            #             f"*{sym}*\n"
            #             f"{short.exchange}` {short.rate_frac*100:+.4f}%` → {long.exchange}` {long.rate_frac*100:+.4f}%`\n"
            #             f"Δ *{abs(diff_pct):.4f}%*"
            #         )
            #         await send_telegram(text)
            db_data = models.MainFundingModel.objects.all().order_by('-time')
            if timedelta(hours=1) > (db_data[0].time-db_data[1].time):
                db_data[0].delete()
            serialized_data = serialization(dict_data)
            serialized_data.save()
            logger.info(f"Цикл {round(time.time()-t0,2)}s → sleep {CONFIG['poll_sec']}s")
            await asyncio.sleep(CONFIG["poll_sec"])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        rprint("[bold]⏹ Зупинено користувачем[/]")