# Design Document: Daily Market Tips

## Overview

The Daily Market Tips system is a scheduled email delivery service that provides expert-analyzed trading recommendations for cryptocurrencies and stocks. The system fetches market data from multiple sources, applies technical analysis, and delivers curated tips via email at scheduled times (morning and evening). Each tip includes source attribution and historical context to support informed trading decisions.

## Technology Stack

- **Language**: Python 3.12
- **Web Framework**: FastAPI (for REST API and dashboard)
- **Scheduler**: APScheduler (for scheduled email deliveries)
- **Email**: smtplib with email library (standard library)
- **Database**: In-memory database with SQLAlchemy ORM
- **Unit Testing**: pytest
- **Property-Based Testing**: Hypothesis (Python property testing framework)
- **Market Data APIs**: 
  - CoinGecko API (free crypto data)
  - Alpha Vantage API (free stock data)
  - yfinance (alternative stock data)
- **Technical Analysis**: TA-Lib or pandas_ta (technical indicators)
- **Frontend**: React with TypeScript (for dashboard UI)
- **HTTP Client**: requests library (for API calls)

## Architecture

The system follows a modular, event-driven architecture with both email and web dashboard delivery:

```
┌─────────────────────────────────────────────────────────────┐
│                    Scheduler Service                         │
│              (Triggers at morning/evening times)             │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐    ┌────────▼──────────┐
│  Market Data     │    │  Analysis Engine  │
│  Aggregator      │    │  (Technical       │
│  (Fetch from     │    │   Analysis)       │
│   multiple APIs) │    │                   │
└───────┬──────────┘    └────────┬──────────┘
        │                        │
        └────────────┬───────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐    ┌────────▼──────────┐
│  Email Template  │    │  Dashboard API    │
│  Formatter       │    │  & Web UI         │
└────────┬─────────┘    └────────┬──────────┘
         │                       │
┌────────▼─────────┐    ┌────────▼──────────┐
│  Email Service   │    │  Web Server       │
│  (Send via SMTP) │    │  (Display tips)   │
└──────────────────┘    └───────────────────┘
```

## Components and Interfaces

### 1. Scheduler Service
- **Responsibility**: Trigger market analysis and email delivery at scheduled times
- **Interface**: 
  - `scheduleDeliveries(morningTime, eveningTime)` - Set up recurring delivery schedule
  - `executeDelivery(deliveryType)` - Execute morning or evening delivery

### 2. Market Data Aggregator
- **Responsibility**: Fetch current and historical market data from multiple sources
- **Interface**:
  - `fetchCryptoData(symbols)` - Get crypto prices, volumes, and trends
  - `fetchStockData(symbols)` - Get stock prices, volumes, and trends
  - `getHistoricalData(symbol, period)` - Get historical price data (24h, 7d, 30d)
  - **Returns**: Data with source attribution

### 3. Analysis Engine
- **Responsibility**: Apply technical analysis to generate trading recommendations
- **Interface**:
  - `analyzeCrypto(marketData)` - Generate crypto trading tips
  - `analyzeStocks(marketData)` - Generate stock trading tips
  - **Returns**: Tips with reasoning and source citations

### 4. Email Template Formatter
- **Responsibility**: Format tips and market data into email-ready HTML/text
- **Interface**:
  - `formatEmailContent(tips, marketData)` - Create email body with tips and data
  - `formatTip(tip)` - Format individual tip with source and reasoning

### 5. Email Service
- **Responsibility**: Send formatted emails to users
- **Interface**:
  - `sendEmail(recipient, subject, content)` - Send email with retry logic
  - `logDelivery(status, recipient, timestamp)` - Track delivery attempts

### 6. Dashboard API & Web UI
- **Responsibility**: Provide web interface to view market tips and exchange data
- **Interface**:
  - `getTips(filters)` - Retrieve tips with optional filtering by type (crypto/stock) or date
  - `getMarketData(symbols)` - Get current and historical market data
  - `getTipHistory(days)` - Get historical tips from past N days
  - **Returns**: JSON data formatted for web display

## Data Models

### MarketData
```
{
  symbol: string,
  type: "crypto" | "stock",
  currentPrice: number,
  priceChange24h: number,
  volume24h: number,
  historicalData: {
    period: "24h" | "7d" | "30d",
    prices: number[],
    timestamps: number[]
  },
  source: {
    name: string,
    url: string,
    fetchedAt: timestamp
  }
}
```

### TradingTip
```
{
  symbol: string,
  type: "crypto" | "stock",
  recommendation: "BUY" | "SELL" | "HOLD",
  reasoning: string,
  confidence: number (0-100),
  indicators: string[],
  sources: {
    name: string,
    url: string
  }[],
  generatedAt: timestamp
}
```

### EmailContent
```
{
  recipient: string,
  subject: string,
  deliveryType: "morning" | "evening",
  tips: TradingTip[],
  marketData: MarketData[],
  generatedAt: timestamp
}
```

### DashboardTip
```
{
  id: string,
  symbol: string,
  type: "crypto" | "stock",
  recommendation: "BUY" | "SELL" | "HOLD",
  reasoning: string,
  confidence: number (0-100),
  indicators: string[],
  sources: {
    name: string,
    url: string
  }[],
  generatedAt: timestamp,
  deliveryType: "morning" | "evening"
}
```

## Error Handling

- **Data Fetch Failures**: Log error and use cached data if available; skip that source if cache unavailable
- **Analysis Failures**: Log error and skip analysis for affected symbols
- **Email Send Failures**: Implement exponential backoff retry (3 attempts with 5min, 15min, 30min delays)
- **Scheduling Failures**: Log error and attempt to reschedule for next cycle
- **Invalid Configuration**: Validate delivery times on startup; fail fast with clear error messages

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Exchange data includes source attribution
*For any* email sent by the system, all exchange data presented SHALL include source attribution (provider name and URL)
**Validates: Requirements 1.3, 2.3**

### Property 2: Historical data is included with exchange data
*For any* exchange data presented, the data SHALL include historical price trends for at least one of the specified periods (24h, 7d, or 30d)
**Validates: Requirements 1.4**

### Property 3: All tips include reasoning
*For any* trading tip generated, the tip SHALL include a non-empty reasoning field explaining the recommendation
**Validates: Requirements 2.2**

### Property 4: Tips are categorized by type
*For any* set of tips generated, all tips SHALL be properly categorized as either "crypto" or "stock" with no mixed or undefined types
**Validates: Requirements 2.5**

### Property 5: Analysis references indicators
*For any* market analysis performed, the resulting tips SHALL reference at least one established technical analysis indicator
**Validates: Requirements 2.1**

### Property 6: Email delivery executes on schedule
*For any* configured delivery time (morning or evening), when that time is reached, the system SHALL initiate the email sending process
**Validates: Requirements 3.2**

### Property 7: Failed emails are retried
*For any* email send failure, the system SHALL attempt retry with exponential backoff (3 attempts minimum)
**Validates: Requirements 3.3**

### Property 8: Updated email addresses are used
*For any* user email address update, all subsequent deliveries SHALL use the new email address
**Validates: Requirements 3.4**

## Testing Strategy

### Unit Testing
- Test individual components in isolation (data fetching, analysis, formatting)
- Test error handling and retry logic
- Test data model validation
- Test scheduler initialization with various time configurations

### Property-Based Testing
- Use a property-based testing framework (e.g., Hypothesis for Python, fast-check for JavaScript)
- Configure each property test to run a minimum of 100 iterations
- Each property test SHALL be tagged with the format: **Feature: daily-market-tips, Property {number}: {property_text}**
- Generate random market data, tips, and email configurations to verify properties hold across diverse inputs
- Test edge cases: empty data sets, missing sources, malformed timestamps, invalid email addresses
