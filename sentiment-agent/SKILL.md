---
name: market-sentiment
description: Continuously crawls news via Brave Search, scores sentiment with the local LLM, and pushes results to the Daily Market Tips API.
version: 1.0.0
entry: main.py
schedule: "*/30 * * * *"
---

# Market Sentiment Skill

Runs every 30 minutes inside the NemoClaw sandbox. For each tracked symbol it:

1. Searches Brave News for recent headlines (last 24 h)
2. Sends headlines to the local vLLM model for sentiment scoring
3. POSTs the score back to the Daily Market Tips API at `host.openshell.internal:8001`

## Environment variables required (set in sandbox or `.env`)

| Variable | Description |
|---|---|
| `BRAVE_API_KEY` | Brave Search subscription token |
| `SENTIMENT_API_KEY` | Shared secret for the `/api/sentiment` endpoint |
| `DAILY_TRADER_URL` | Base URL of the Daily Market Tips API (default: `http://host.openshell.internal:8001`) |
| `VLLM_URL` | LLM base URL — set to `https://openrouter.ai/api/v1` for OpenRouter (default: `http://host.openshell.internal:8000/v1`) |
| `VLLM_MODEL` | Model ID passed to the LLM API (default: `google/gemma-4-e4b`) |
| `LLM_API_KEY` | API key for external providers. Falls back to `OPENAI_API_KEY`. Leave unset for local vLLM. |
