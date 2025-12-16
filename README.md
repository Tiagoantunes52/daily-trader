# Daily Market Tips

A comprehensive system that delivers expert-analyzed market insights for cryptocurrencies and stocks via email and web dashboard. The system aggregates market data from multiple sources, applies technical analysis, and sends curated trading tips twice daily to help users make informed buy/sell decisions.

## Overview

Daily Market Tips is a full-stack application consisting of:

- **Backend API**: Python FastAPI service that aggregates market data, performs technical analysis, and manages email delivery
- **Email Service**: Automated twice-daily email delivery with retry logic and delivery tracking
- **Web Dashboard**: React-based interface for viewing current tips, market data, and historical analysis
- **Scheduler**: APScheduler-based service for triggering deliveries at configured times

## Features

### Core Functionality

- **Twice-Daily Email Delivery**: Automated morning and evening market tips via email
- **Multi-Source Data Aggregation**: Fetches crypto and stock data from multiple APIs with source attribution
- **Technical Analysis**: Applies established indicators (RSI, MACD, moving averages) to generate recommendations
- **Web Dashboard**: View current tips, market data, and historical analysis with filtering and pagination
- **User Configuration**: Manage email addresses, delivery times, and asset preferences
- **Retry Logic**: Exponential backoff retry mechanism for failed email deliveries
- **Source Attribution**: All tips include data source citations and links

### Data Coverage

- **Cryptocurrencies**: Bitcoin, Ethereum, and other major digital assets
- **Stocks**: Major indices and individual equities
- **Historical Data**: 24-hour, 7-day, and 30-day trend analysis

## Project Structure

```
daily-market-tips/
├── src/                          # Backend source code
│   ├── api/                      # FastAPI routes
│   │   └── routes.py             # REST API endpoints
│   ├── database/                 # Database layer
│   │   ├── db.py                 # Database connection
│   │   └── models.py             # SQLAlchemy models
│   ├── models/                   # Data models
│   │   ├── market_data.py        # Market data structures
│   │   └── trading_tip.py        # Trading tip structures
│   ├── services/                 # Business logic
│   │   ├── market_data_aggregator.py  # Data fetching
│   │   ├── analysis_engine.py         # Technical analysis
│   │   ├── email_service.py           # Email delivery
│   │   ├── scheduler_service.py       # Scheduled tasks
│   │   └── user_service.py            # User management
│   └── utils/                    # Utilities
│       └── config.py             # Configuration management
├── frontend/                     # React dashboard
│   ├── src/
│   │   ├── components/           # React components
│   │   ├── pages/                # Page components
│   │   ├── api/                  # API client
│   │   └── test/                 # Test setup
│   ├── package.json
│   ├── vite.config.js
│   └── vitest.config.js
├── tests/                        # Backend tests
│   ├── test_analysis_engine.py
│   ├── test_email_service.py
│   ├── test_market_data_aggregator.py
│   ├── test_scheduler_service.py
│   ├── test_user_service.py
│   ├── test_dashboard_api.py
│   ├── test_integration_e2e.py
│   └── conftest.py
├── main.py                       # Application entry point
├── requirements.txt              # Python dependencies
└── .env.example                  # Environment configuration template
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- `uv` (Python package manager)
- npm

### Backend Setup

1. Clone the repository and navigate to the project root:

```bash
git clone <repository-url>
cd daily-market-tips
```

2. Install Python dependencies with `uv`:

```bash
uv sync
```

This will create a virtual environment and install all dependencies from `pyproject.toml`. The virtual environment will be created in `.venv` by default.

3. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your settings:
# - SMTP email credentials
# - API keys for market data sources
# - Delivery times (morning/evening)
```

4. Run the backend:

```bash
uv run python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# Delivery Times (24-hour format)
MORNING_DELIVERY_TIME=06:00
EVENING_DELIVERY_TIME=18:00

# API Keys
COINGECKO_API_KEY=your-key
ALPHAVANTAGE_API_KEY=your-key

# Database
DATABASE_URL=sqlite:///./market_tips.db

# Timezone
TIMEZONE=UTC
```

## Running Tests

### Backend Tests

Run all backend tests:

```bash
uv run pytest tests/ -v
```

Run specific test file:

```bash
uv run pytest tests/test_analysis_engine.py -v
```

Run property-based tests only:

```bash
uv run pytest tests/ -v -k "property"
```

### Frontend Tests

Run all frontend tests:

```bash
cd frontend
npm test
```

Run tests in watch mode:

```bash
cd frontend
npm run test:watch
```

## API Endpoints

### Tips

- `GET /api/tips` - Get current tips with optional filtering
  - Query params: `asset_type` (crypto/stock), `days` (1-90), `skip` (0+), `limit` (1-100)

- `GET /api/tip-history` - Get historical tips
  - Query params: `asset_type`, `days`, `skip`, `limit`

### Market Data

- `GET /api/market-data` - Get market data for symbols
  - Query params: `symbols` (comma-separated)

### User Management

- `POST /api/users` - Create user profile
- `GET /api/users/{user_id}` - Get user profile
- `PUT /api/users/{user_id}/email` - Update email address
- `PUT /api/users/{user_id}/delivery-times` - Update delivery times
- `PUT /api/users/{user_id}/preferences` - Update asset preferences

## Architecture

### Data Flow

```
Scheduler Service
    ↓
Market Data Aggregator (fetch from APIs)
    ↓
Analysis Engine (apply technical analysis)
    ↓
Email Service (format and send)
    ↓
Dashboard API (persist and serve)
    ↓
Web Dashboard (display to users)
```

### Key Components

**Market Data Aggregator**: Fetches real-time and historical data from multiple sources (CoinGecko, Alpha Vantage) with source attribution.

**Analysis Engine**: Applies technical indicators (RSI, MACD, moving averages) to generate BUY/SELL/HOLD recommendations with confidence scores.

**Email Service**: Formats tips into HTML/text emails and sends via SMTP with exponential backoff retry logic (5min, 15min, 30min).

**Scheduler Service**: Triggers market analysis and email delivery at configured morning and evening times.

**Dashboard API**: REST API for retrieving tips and market data with filtering, pagination, and historical queries.

## Testing Strategy

The project uses a dual testing approach:

### Unit Tests

Verify specific examples, edge cases, and error conditions for individual components.

### Property-Based Tests

Use Hypothesis framework to verify universal properties that should hold across all inputs:

- **Property 1**: Exchange data includes source attribution
- **Property 2**: Historical data is included with exchange data
- **Property 3**: All tips include reasoning
- **Property 4**: Tips are categorized by type
- **Property 5**: Analysis references indicators
- **Property 6**: Email delivery executes on schedule
- **Property 7**: Failed emails are retried
- **Property 8**: Updated email addresses are used

All tests run with minimum 100 iterations for property-based tests.

## Correctness Properties

The system is designed around formal correctness properties:

1. **Source Attribution**: Every piece of market data includes its source
2. **Historical Context**: Market data always includes historical trends
3. **Reasoning**: Every trading recommendation includes analysis reasoning
4. **Categorization**: Tips are properly categorized by asset type
5. **Technical Basis**: All recommendations reference technical indicators
6. **Scheduled Delivery**: Emails are sent at configured times
7. **Reliability**: Failed emails are retried with exponential backoff
8. **User Preferences**: User email updates are immediately applied

## Performance

- **Email Delivery**: Typically completes within 5 seconds
- **Market Data Fetch**: ~2-3 seconds for all sources
- **Analysis Generation**: ~1-2 seconds for all assets
- **Dashboard Response**: <500ms for API queries

## Error Handling

- **API Failures**: Gracefully falls back to cached data
- **Email Failures**: Retries with exponential backoff (3 attempts)
- **Invalid Data**: Logged and skipped without stopping delivery
- **Configuration Errors**: Fail fast with clear error messages

## Dependency Management

### Using `uv`

The project uses `uv` for fast and reliable Python dependency management. Dependencies are defined in `pyproject.toml`.

**Install `uv`:**

```bash
# Using pip
pip install uv

# Or using Homebrew (macOS)
brew install uv

# Or using Cargo (Rust)
cargo install uv

# See installation guide: https://docs.astral.sh/uv/getting-started/installation/
```

**Common `uv` commands:**

```bash
# Sync dependencies (install/update from pyproject.toml)
uv sync

# Sync with dev dependencies
uv sync --all-extras

# Run a command in the virtual environment
uv run python main.py
uv run pytest tests/

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update dependencies
uv sync --upgrade
```

**Project Configuration:**

- Dependencies are defined in `pyproject.toml` under `[project] dependencies`
- Dev dependencies (pytest, hypothesis) are under `[project.optional-dependencies] dev`
- The virtual environment is created in `.venv` by default

## Deployment

### Production Considerations

1. Use environment-specific configuration
2. Set up proper logging and monitoring
3. Configure SMTP with production credentials
4. Use a production database (PostgreSQL recommended)
5. Set up scheduled backups
6. Configure email rate limiting
7. Monitor delivery success rates

### Docker Deployment

```bash
docker build -t daily-market-tips .
docker run -p 8000:8000 -p 3000:3000 --env-file .env daily-market-tips
```

## Troubleshooting

### Email Not Sending

- Check SMTP credentials in `.env`
- Verify firewall allows SMTP port (587)
- Check email service logs for errors
- Verify recipient email is valid

### Missing Market Data

- Verify API keys are configured
- Check API rate limits
- Review aggregator logs for fetch errors
- Ensure internet connectivity

### Dashboard Not Loading

- Verify backend API is running on port 8000
- Check browser console for errors
- Verify CORS configuration
- Clear browser cache

## Contributing

1. Create a feature branch
2. Write tests for new functionality
3. Ensure all tests pass
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions, please open an issue on the project repository.

## Changelog

### Version 1.0.0

- Initial release
- Twice-daily email delivery
- Web dashboard with filtering and pagination
- Technical analysis with multiple indicators
- User configuration management
- Comprehensive test suite with property-based testing
