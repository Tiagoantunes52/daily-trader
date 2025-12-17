# Implementation Plan: Observability and Logging

- [x] 1. Set up structured logging infrastructure
  - Create a structured logger module that outputs JSON-formatted logs
  - Implement log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Add context field support for including operation metadata
  - Configure logger to write to stdout and optional file
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 1.1 Write property test for JSON log format
  - **Feature: observability-logging, Property 11: Log entries have required fields**
  - **Validates: Requirements 3.1, 3.3**

- [x] 2. Implement trace context management
  - Create trace context manager using contextvars for thread-safe trace ID storage
  - Implement create_trace() to generate unique trace IDs
  - Implement get_current_trace() and set_trace() for context access
  - Implement clear_trace() for cleanup
  - _Requirements: 4.1, 4.2_

- [x] 2.1 Write property test for trace ID assignment
  - **Feature: observability-logging, Property 14: Trace IDs are assigned to operations**
  - **Validates: Requirements 4.1, 4.2**

- [x] 3. Create in-memory event store
  - Implement event store class with add_event() method
  - Implement get_recent_events(limit) to retrieve most recent events
  - Implement get_events_by_trace(trace_id) for trace queries
  - Implement get_events_by_type(event_type, limit) for type-based queries
  - Implement clear_old_events(max_age_seconds) for automatic cleanup
  - Add configurable size limit with automatic purging of old events
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3.1 Write property test for event store ordering
  - **Feature: observability-logging, Property 15: Trace endpoint returns complete history**
  - **Validates: Requirements 4.3, 4.4**

- [x] 4. Integrate logging into scheduler service
  - Add structured logging to schedule_deliveries() method
  - Log delivery start with trace ID and delivery type
  - Log market data fetch operations with source and symbols
  - Log analysis operations with indicators and recommendations
  - Log email send operations with recipient and status
  - Log errors with full exception context
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 4.1 Write property test for delivery operation logging
  - **Feature: observability-logging, Property 1: Delivery operations are logged**
  - **Validates: Requirements 1.1**

- [x] 4.2 Write property test for fetch operation logging
  - **Feature: observability-logging, Property 2: Fetch operations are logged with required fields**
  - **Validates: Requirements 1.2**

- [x] 4.3 Write property test for analysis operation logging
  - **Feature: observability-logging, Property 3: Analysis operations are logged with indicators**
  - **Validates: Requirements 1.3**

- [x] 4.4 Write property test for email operation logging
  - **Feature: observability-logging, Property 4: Email operations are logged with required fields**
  - **Validates: Requirements 1.4**

- [x] 4.5 Write property test for error logging
  - **Feature: observability-logging, Property 5: Error logging includes full context**
  - **Validates: Requirements 1.5**

- [x] 5. Integrate logging into market data aggregator
  - Add structured logging to fetch_crypto_data() method
  - Add structured logging to fetch_stock_data() method
  - Log each fetch attempt with source, symbol, and result
  - Log errors with full context
  - _Requirements: 1.2_

- [x] 6. Integrate logging into analysis engine
  - Add structured logging to analyze_crypto() method
  - Add structured logging to analyze_stocks() method
  - Log indicators calculated and recommendations generated
  - Log errors with full context
  - _Requirements: 1.3_

- [x] 7. Integrate logging into email service
  - Add structured logging to send_email() method
  - Log recipient, subject, and delivery status
  - Log retry attempts with delay information
  - Log errors with full context
  - _Requirements: 1.4_

- [x] 8. Create debug API endpoints
  - Implement GET /debug/status endpoint returning scheduler status and next delivery times
  - Implement GET /debug/execution-history endpoint returning recent delivery attempts
  - Implement GET /debug/fetch-history endpoint returning recent fetch attempts
  - Implement GET /debug/errors endpoint returning recent errors
  - Implement GET /debug/metrics endpoint returning aggregated statistics
  - Implement GET /debug/trace/{trace_id} endpoint returning complete trace
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 8.1 Write property test for debug status endpoint
  - **Feature: observability-logging, Property 6: Debug status endpoint returns scheduler state**
  - **Validates: Requirements 2.1**

- [x] 8.2 Write property test for execution history endpoint
  - **Feature: observability-logging, Property 7: Execution history includes required fields**
  - **Validates: Requirements 2.2**

- [x] 8.3 Write property test for fetch history endpoint
  - **Feature: observability-logging, Property 8: Fetch history includes required fields**
  - **Validates: Requirements 2.3**

- [x] 8.4 Write property test for error log endpoint
  - **Feature: observability-logging, Property 9: Error log endpoint returns recent errors**
  - **Validates: Requirements 2.4**

- [x] 8.5 Write property test for metrics endpoint
  - **Feature: observability-logging, Property 10: Metrics calculation is accurate**
  - **Validates: Requirements 2.5**

- [x] 8.6 Write property test for trace endpoint
  - **Feature: observability-logging, Property 15: Trace endpoint returns complete history**
  - **Validates: Requirements 4.3, 4.4**

- [x] 9. Implement metrics calculation
  - Create metrics calculator that aggregates event store data
  - Calculate total_deliveries, successful_deliveries, failed_deliveries
  - Calculate success_rate as (successful / total) * 100
  - Calculate average_delivery_duration_ms from event timestamps
  - Calculate total_tips_generated and total_emails_sent
  - Calculate fetch statistics (total, successful, failed, average duration)
  - Calculate recent_errors_count and uptime_seconds
  - _Requirements: 2.5_

- [x] 9.1 Write property test for metrics accuracy
  - **Feature: observability-logging, Property 10: Metrics calculation is accurate**
  - **Validates: Requirements 2.5**

- [x] 10. Add context field support to logger
  - Modify logger to accept and preserve context fields in log entries
  - Ensure context fields are included in JSON output
  - _Requirements: 3.2_

- [x] 10.1 Write property test for context field preservation
  - **Feature: observability-logging, Property 12: Log entries preserve context**
  - **Validates: Requirements 3.2**

- [x] 11. Add exception handling to logger
  - Modify logger to capture exception type, message, and stack trace
  - Include exception details in error log entries
  - _Requirements: 3.4_

- [x] 11.1 Write property test for error log exception details
  - **Feature: observability-logging, Property 13: Error log entries include exception details**
  - **Validates: Requirements 3.4**

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

