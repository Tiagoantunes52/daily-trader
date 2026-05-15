"""
Market Sentiment Agent — NemoClaw skill.

Runs on a 30-minute loop:
  1. Search Brave News for each tracked symbol
  2. Score sentiment with local vLLM
  3. POST scores to the Daily Market Tips API
"""

import json
import logging
import os
import time

import httpx
import schedule

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("market-sentiment")

BRAVE_API_KEY = os.environ["BRAVE_API_KEY"]
SENTIMENT_API_KEY = os.environ["SENTIMENT_API_KEY"]
DAILY_TRADER_URL = os.getenv("DAILY_TRADER_URL", "http://host.openshell.internal:8001")
VLLM_URL = os.getenv("VLLM_URL", "http://host.openshell.internal:8000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "google/gemma-4-e4b")

# Symbols mirror daily-trader scheduler_service.py defaults
CRYPTO_SYMBOLS = ["bitcoin", "ethereum", "near", "solana", "tron"]
STOCK_SYMBOLS = ["AAPL", "GOOGL"]
ALL_SYMBOLS = CRYPTO_SYMBOLS + STOCK_SYMBOLS

# Brave News returns up to 20 results; we cap at 8 for prompt size
MAX_HEADLINES = 8


def brave_news(symbol: str, client: httpx.Client) -> list[dict]:
    """Fetch recent news headlines for *symbol* from Brave Search."""
    query = f"{symbol} market news price"
    try:
        resp = client.get(
            "https://api.search.brave.com/res/v1/news/search",
            params={"q": query, "count": MAX_HEADLINES, "freshness": "pd"},
            headers={"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return [{"title": r.get("title", ""), "description": r.get("description", "")} for r in results]
    except Exception as exc:
        log.warning("Brave search failed for %s: %s", symbol, exc)
        return []


def score_sentiment(symbol: str, headlines: list[dict], client: httpx.Client) -> dict | None:
    """Ask local LLM to score sentiment for *symbol* based on *headlines*."""
    if not headlines:
        return None

    headline_text = "\n".join(
        f"- {h['title']}" + (f": {h['description'][:120]}" if h.get("description") else "")
        for h in headlines
    )
    prompt = (
        f"You are a financial analyst. Given the following recent news headlines about {symbol}, "
        "rate the overall market sentiment.\n\n"
        f"Headlines:\n{headline_text}\n\n"
        "Respond with ONLY valid JSON in this exact format:\n"
        '{"score": <float -1.0 to 1.0>, "label": "<one of: very bearish, bearish, mildly bearish, '
        'neutral, mildly bullish, bullish, very bullish>", "key_theme": "<one sentence summary>"}'
    )

    try:
        resp = client.post(
            f"{VLLM_URL}/chat/completions",
            json={
                "model": VLLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 120,
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # Extract JSON block — model may wrap it in markdown fences
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception as exc:
        log.warning("LLM scoring failed for %s: %s", symbol, exc)
        return None


def push_sentiment(symbol: str, result: dict, headline_count: int, client: httpx.Client) -> bool:
    """POST sentiment result to the Daily Market Tips API."""
    try:
        resp = client.post(
            f"{DAILY_TRADER_URL}/api/sentiment",
            json={
                "symbol": symbol,
                "score": result["score"],
                "label": result["label"],
                "key_theme": result.get("key_theme"),
                "headline_count": headline_count,
            },
            headers={"X-Agent-Key": SENTIMENT_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        log.warning("Push failed for %s: %s", symbol, exc)
        return False


def run_cycle() -> None:
    log.info("Starting sentiment cycle for %d symbols", len(ALL_SYMBOLS))
    with httpx.Client() as client:
        for symbol in ALL_SYMBOLS:
            headlines = brave_news(symbol, client)
            if not headlines:
                log.info("%s: no headlines found, skipping", symbol)
                continue

            result = score_sentiment(symbol, headlines, client)
            if not result:
                log.info("%s: sentiment scoring returned nothing, skipping", symbol)
                continue

            ok = push_sentiment(symbol, result, len(headlines), client)
            status = "ok" if ok else "push-failed"
            log.info(
                "%s: score=%.2f label=%s headlines=%d [%s]",
                symbol, result["score"], result["label"], len(headlines), status,
            )
            # Respect rate limits — small pause between symbols
            time.sleep(1)

    log.info("Sentiment cycle complete")


if __name__ == "__main__":
    log.info("Market sentiment agent starting (interval: 30 min)")
    log.info("DAILY_TRADER_URL=%s  VLLM_URL=%s  MODEL=%s", DAILY_TRADER_URL, VLLM_URL, VLLM_MODEL)

    # Run once immediately on startup, then on schedule
    run_cycle()

    schedule.every(30).minutes.do(run_cycle)
    while True:
        schedule.run_pending()
        time.sleep(10)
