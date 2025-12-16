# Daily Market Tips Dashboard

A responsive React web interface for viewing market tips and trading recommendations.

## Features

- **Current Tips View**: Display latest market tips with filtering and pagination
- **Tip History**: Browse historical tips with date range selection
- **Market Data Charts**: Visual representation of price trends and market data
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Real-time Filtering**: Filter tips by asset type (crypto/stock) and date range
- **Source Attribution**: All tips include source citations and links

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable React components
│   │   ├── TipCard.jsx      # Individual tip display
│   │   ├── MarketDataChart.jsx  # Market data visualization
│   │   ├── FilterBar.jsx    # Filtering controls
│   │   └── Pagination.jsx   # Pagination controls
│   ├── pages/               # Page components
│   │   ├── CurrentTips.jsx  # Current tips page
│   │   └── TipHistory.jsx   # Historical tips page
│   ├── api/                 # API client
│   │   └── client.js        # Axios API client
│   ├── test/                # Test setup
│   ├── App.jsx              # Main app component
│   ├── App.css              # App styles
│   ├── index.css            # Global styles
│   └── main.jsx             # Entry point
├── package.json
├── vite.config.js
├── vitest.config.js
└── index.html
```

## Installation

```bash
cd frontend
npm install
```

## Development

Start the development server:

```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000` and will proxy API requests to `http://localhost:8000`.

## Building

Build for production:

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Testing

Run tests:

```bash
npm test
```

Run tests in watch mode:

```bash
npm run test:watch
```

## API Integration

The dashboard communicates with the backend API at `/api`:

- `GET /api/tips` - Retrieve current tips with filtering
- `GET /api/market-data` - Get market data for symbols
- `GET /api/tip-history` - Get historical tips

## Components

### TipCard
Displays individual trading tips with:
- Symbol and asset type
- Recommendation (BUY/SELL/HOLD)
- Reasoning and confidence score
- Technical indicators
- Source citations
- Timestamp

### MarketDataChart
Shows market data with:
- Current price and 24h change
- 24h trading volume
- Historical price chart
- Source attribution

### FilterBar
Provides filtering options:
- Asset type (crypto/stock)
- Time range (24h, 7d, 30d, 90d)
- Custom date range

### Pagination
Handles result pagination with:
- Previous/Next navigation
- Page number selection
- Total count display

## Styling

The dashboard uses CSS custom properties for theming:

```css
--primary-color: #2563eb
--secondary-color: #64748b
--success-color: #10b981
--warning-color: #f59e0b
--danger-color: #ef4444
--background: #f8fafc
--surface: #ffffff
--border: #e2e8f0
--text-primary: #1e293b
--text-secondary: #64748b
```

## Responsive Design

The dashboard is fully responsive with breakpoints at:
- Desktop: 1400px max-width
- Tablet: 768px
- Mobile: < 768px

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
