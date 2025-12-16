# Implementation Plan: Daily Market Tips

- [x] 1. Set up project structure and core configuration
  - Create directory structure for models, services, API routes, and utilities
  - Set up environment configuration for API keys, email settings, and delivery times
  - Initialize database schema for storing tips, market data, and delivery logs
  - _Requirements: 1.1, 1.2, 3.1_

- [x] 2. Implement Market Data Aggregator
  - Create interfaces for market data fetching from multiple sources
  - Implement crypto data fetcher (fetch current prices, volumes, and source attribution)
  - Implement stock data fetcher (fetch current prices, volumes, and source attribution)
  - Implement historical data retrieval (24h, 7d, 30d trends with timestamps)
  - _Requirements: 1.3, 1.4_

- [x] 2.1 Write property test for market data source attribution
  - **Feature: daily-market-tips, Property 1: Exchange data includes source attribution**
  - **Validates: Requirements 1.3, 2.3**

- [x] 2.2 Write property test for historical data inclusion
  - **Feature: daily-market-tips, Property 2: Historical data is included with exchange data**
  - **Validates: Requirements 1.4**

- [x] 3. Implement Analysis Engine
  - Create technical analysis indicator functions (moving averages, RSI, MACD, etc.)
  - Implement crypto analysis logic (generate BUY/SELL/HOLD recommendations with reasoning)
  - Implement stock analysis logic (generate BUY/SELL/HOLD recommendations with reasoning)
  - Ensure all tips include confidence scores and indicator references
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3.1 Write property test for tip reasoning inclusion
  - **Feature: daily-market-tips, Property 3: All tips include reasoning**
  - **Validates: Requirements 2.2**

- [x] 3.2 Write property test for tip categorization
  - **Feature: daily-market-tips, Property 4: Tips are categorized by type**
  - **Validates: Requirements 2.5**

- [x] 3.3 Write property test for indicator references
  - **Feature: daily-market-tips, Property 5: Analysis references indicators**
  - **Validates: Requirements 2.1**

- [x] 4. Implement Email Service
  - Create email template formatter (HTML and plain text formats)
  - Implement SMTP email sending with retry logic (exponential backoff: 5min, 15min, 30min)
  - Implement delivery logging and failure tracking
  - Create email content builder combining tips and market data with source citations
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.3_

- [x] 4.1 Write property test for email retry logic
  - **Feature: daily-market-tips, Property 7: Failed emails are retried**
  - **Validates: Requirements 3.3**

- [x] 5. Implement Scheduler Service
  - Create scheduler that triggers at configured morning and evening times
  - Implement delivery orchestration (fetch data → analyze → format → send email)
  - Implement configuration validation for delivery times
  - Add logging for all scheduled events and execution status
  - _Requirements: 3.1, 3.2_

- [x] 5.1 Write property test for scheduled delivery execution
  - **Feature: daily-market-tips, Property 6: Email delivery executes on schedule**
  - **Validates: Requirements 3.2**

- [ ] 6. Implement Dashboard API
  - Create REST API endpoints for retrieving tips and market data
  - Implement filtering by asset type (crypto/stock) and date range
  - Implement historical tip retrieval (past N days)
  - Add pagination for large result sets
  - _Requirements: 1.3, 1.4, 2.2, 2.3_

- [ ] 7. Implement Dashboard Web UI
  - Create responsive web interface for viewing current tips
  - Display market data with source attribution and historical charts
  - Implement filtering and search functionality
  - Add tip history view with date range selection
  - _Requirements: 1.3, 1.4, 2.2, 2.3_

- [ ] 8. Implement User Configuration Management
  - Create user profile management (email address, delivery times, asset preferences)
  - Implement email address update functionality with validation
  - Store user preferences in database
  - _Requirements: 3.4_

- [ ] 8.1 Write property test for email address updates
  - **Feature: daily-market-tips, Property 8: Updated email addresses are used**
  - **Validates: Requirements 3.4**

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Integration and End-to-End Testing
  - Test complete flow: scheduler triggers → data fetch → analysis → email send
  - Test complete flow: scheduler triggers → data fetch → analysis → dashboard update
  - Test error scenarios: API failures, email send failures, invalid data
  - Verify retry logic works correctly for failed operations
  - _Requirements: 1.1, 1.2, 3.2, 3.3_

- [ ] 11. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
