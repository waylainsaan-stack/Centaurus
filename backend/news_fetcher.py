import aiohttp
import asyncio
import logging
import json
import re
from datetime import datetime, timezone
import feedparser

logger = logging.getLogger(__name__)

COIN_KEYWORDS = {
    "BTC/USDT": ["bitcoin", "btc", "BTC"],
    "ETH/USDT": ["ethereum", "eth", "ETH"],
    "SOL/USDT": ["solana", "sol", "SOL"],
    "XRP/USDT": ["ripple", "xrp", "XRP"],
    "DOGE/USDT": ["dogecoin", "doge", "DOGE"],
    "ADA/USDT": ["cardano", "ada", "ADA"],
    "AVAX/USDT": ["avalanche", "avax", "AVAX"],
    "DOT/USDT": ["polkadot", "dot", "DOT"],
}


async def fetch_cryptopanic_news(symbol="BTC/USDT"):
    """Fetch news from CryptoPanic free RSS feed."""
    try:
        coin = symbol.split("/")[0].lower()
        url = f"https://cryptopanic.com/news/{coin}/rss/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    feed = feedparser.parse(text)
                    articles = []
                    for entry in feed.entries[:10]:
                        articles.append({
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "source": "CryptoPanic",
                            "summary": entry.get("summary", "")[:200],
                        })
                    return articles
    except Exception as e:
        logger.error(f"CryptoPanic fetch error: {e}")
    return []


async def fetch_coindesk_rss(symbol="BTC/USDT"):
    """Fetch news from CoinDesk RSS."""
    try:
        url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    feed = feedparser.parse(text)
                    keywords = COIN_KEYWORDS.get(symbol, [symbol.split("/")[0].lower()])
                    articles = []
                    for entry in feed.entries[:20]:
                        title = entry.get("title", "").lower()
                        summary = entry.get("summary", "").lower()
                        if any(kw.lower() in title or kw.lower() in summary for kw in keywords) or len(articles) < 3:
                            articles.append({
                                "title": entry.get("title", ""),
                                "link": entry.get("link", ""),
                                "published": entry.get("published", ""),
                                "source": "CoinDesk",
                                "summary": entry.get("summary", "")[:200],
                            })
                        if len(articles) >= 5:
                            break
                    return articles
    except Exception as e:
        logger.error(f"CoinDesk fetch error: {e}")
    return []


async def fetch_cointelegraph_rss(symbol="BTC/USDT"):
    """Fetch news from CoinTelegraph RSS."""
    try:
        url = "https://cointelegraph.com/rss"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    feed = feedparser.parse(text)
                    keywords = COIN_KEYWORDS.get(symbol, [symbol.split("/")[0].lower()])
                    articles = []
                    for entry in feed.entries[:20]:
                        title = entry.get("title", "").lower()
                        if any(kw.lower() in title for kw in keywords) or len(articles) < 2:
                            articles.append({
                                "title": entry.get("title", ""),
                                "link": entry.get("link", ""),
                                "published": entry.get("published", ""),
                                "source": "CoinTelegraph",
                                "summary": entry.get("summary", "")[:200],
                            })
                        if len(articles) >= 5:
                            break
                    return articles
    except Exception as e:
        logger.error(f"CoinTelegraph fetch error: {e}")
    return []


async def fetch_all_news(symbol="BTC/USDT"):
    """Fetch news from all sources concurrently."""
    results = await asyncio.gather(
        fetch_cryptopanic_news(symbol),
        fetch_coindesk_rss(symbol),
        fetch_cointelegraph_rss(symbol),
        return_exceptions=True,
    )

    all_news = []
    for r in results:
        if isinstance(r, list):
            all_news.extend(r)

    # Deduplicate by title
    seen = set()
    unique = []
    for article in all_news:
        title_key = article["title"][:50].lower()
        if title_key not in seen:
            seen.add(title_key)
            unique.append(article)

    return unique[:15]


async def analyze_news_sentiment(news_articles, symbol, ai_func):
    """Use AI to analyze sentiment of collected news articles.
    ai_func should be the ai_analyze_text function from server.
    """
    if not news_articles:
        return {"sentiment": "NEUTRAL", "score": 0, "summary": "No news available.", "signal": "HOLD"}

    headlines = "\n".join([f"- [{a['source']}] {a['title']}" for a in news_articles[:10]])

    prompt = f"""Analyze these crypto news headlines for {symbol} and provide market sentiment:

{headlines}

Respond in this exact JSON format:
{{"sentiment": "BULLISH|BEARISH|NEUTRAL", "score": -100 to 100, "summary": "1-2 sentence market summary", "signal": "BUY|SELL|HOLD"}}

Score guide: -100=extremely bearish, 0=neutral, 100=extremely bullish"""

    return prompt
