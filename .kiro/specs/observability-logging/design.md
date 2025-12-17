# Design Document: Observability and Logging

## Overview

The Observability and Logging system adds comprehensive visibility into the Daily Market Tips application by implementing structured logging, execution tracing, debug endpoints, and metrics collection. This enables developers to understand system behavior, diagnose issues, and track the complete flow of operations from scheduler trigger through email delivery.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    All Services                              │
│              (Scheduler, Analysis, Email, etc.)             │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐    ┌────────▼──────────┐
│  Structured      │    │  Trace Context    │
│  Logger          │    │  Manager          │
│  (JSON format)   │    │  (Trace IDs)      │
└───────┬──────────┘    └────────┬──────────┘
        │                        │
        └────────────┬───────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐    ┌────────▼──────────┐
│  In-Memory       │    │  Debug API        │
│  Event Store     │    │  Endpoints        │
│  (Recent logs)   │    │  (Query logs)     │
└──────────────────┘    └───────────────────┘
```

## Components and Interfaces

### 1. Structured Logger
- **Responsibility**: Provide consistent, JSON-formatted logging across all components
- **Interface**:
  - `log(level, message, context)` - Log with level and context fields
  - `debug(message, context)` - Log debug message
  - `info(message, context)` - Log info message
  - `warning(message, context)` - Log warning message
  - `error(message, context, exception)` - Log error with exception
  - **Returns**: None (logs to stdout/file)

### 2. Trace Context Manager
- **Responsibility**: Manage trace IDs for tracking operations through the system
- **Interface**:
  - `create_trace()` - Generate new trace ID
  - `get_current_trace()` - Get current trace ID from context
  - `set_trace(trace_id)` - Set trace ID in context
  - `clear_trace()` - Clear trace ID from context
  - **Returns**: Trace ID string

### 3. Event Store
- **Responsibility**: Store recent log entries and events in memory for querying
- **Interface**:
  - `add_event(event)` - Add log event to store
  - `get_recent_events(limit)` - Get most recent events
  - `get_events_by_trace(trace_id)` - Get all events for a trace
  - `get_events_by_type(event_type, limit)` - Get events of specific type
  - `clear_old_events(max_age_seconds)` - Remove events older than threshold
  - **Returns**: List of events

### 4. Debug API Endpoints
- **Responsibility**: Expose system state and logs through HTTP endpoints
- **Interface**:
  - `GET /debug/status` - Current scheduler and system status
  - `GET /debug/execution-history` - Recent delivery attempts
  - `GET /debug/fetch-history` - Recent data fetch attempts
  - `GET /debug/errors` - Recent errors
  - `GET /debug/metrics` - Aggregated statistics
  - `GET /debug/trace/{trace_id}` - Complete trace for operation
  - **Returns**: JSON with requested information

## Data Models

### LogEntry
```
{
  timestamp: ISO8601 string,
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL",
  component: string,
  message: string,
  trace_id: string (optional),
  context: {
    [key: string]: any
  },
  exception: {
    type: string,
    message: string,
    stack_trace: string
  } (optional)
}
```

### Event
```
{
  id: string (UUID),
  timestamp: ISO8601 string,
  trace_id: string,
  event_type: "delivery_start" | "delivery_complete" | "fetch_start" | "fetch_complete" | "analysis_start" | "analysis_complete" | "email_sent" | "error",
  component: string,
  message: string,
  context: {
    [key: string]: any
  },
  duration_ms: number (optional)
}
```

### ExecutionHistory
```
{
  delivery_id: string,
  trace_id: string,
  delivery_type: "morning" | "evening",
  started_at: ISO8601 string,
  completed_at: ISO8601 string (optional),
  status: "in_progress" | "success" | "failed",
  error_message: string (optional),
  tips_generated: number,
  recipients_sent: number
}
```

### FetchHistory
```
{
  fetch_id: string,
  trace_id: string,
  source: string,
  symbols: string[],
  started_at: ISO8601 string,
  completed_at: ISO8601 string,
  status: "success" | "failed",
  records_fetched: number,
  error_message: string (optional)
}
```

### Metrics
```
{
  total_deliveries: number,
  successful_deliveries: number,
  failed_deliveries: number,
  success_rate: number (0-100),
  average_delivery_duration_ms: number,
  total_tips_generated: number,
  total_emails_sent: number,
  total_fetch_attempts: number,
  successful_fetches: number,
  failed_fetches: number,
  average_fetch_duration_ms: number,
  recent_errors_count: number,
  uptime_seconds: number
}
```

## Error Handling

- **Logger Failures**: If logging fails, errors are printed to stderr but don't crash the application
- **Event Store Full**: Old events are automatically purged when store exceeds size limit
- **Trace Context Loss**: If trace context is lost, operations continue with a new trace ID
- **Debug Endpoint Errors**: Return 500 with error message if internal error occurs

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Delivery operations are logged
*For any* delivery operation, the event store SHALL contain both a delivery_start and delivery_complete event with matching trace IDs
**Validates: Requirements 1.1**

### Property 2: Fetch operations are logged with required fields
*For any* market data fetch operation, the log entry SHALL include source, symbols, and result (success/failure)
**Validates: Requirements 1.2**

### Property 3: Analysis operations are logged with indicators
*For any* analysis operation, the log entry SHALL include the indicators calculated and the resulting recommendation
**Validates: Requirements 1.3**

### Property 4: Email operations are logged with required fields
*For any* email send operation, the log entry SHALL include recipient, subject, and delivery status
**Validates: Requirements 1.4**

### Property 5: Error logging includes full context
*For any* error that occurs, the error log entry SHALL include exception type, message, and stack trace
**Validates: Requirements 1.5**

### Property 6: Debug status endpoint returns scheduler state
*For any* call to the debug status endpoint, the response SHALL include current scheduler status and next scheduled delivery times
**Validates: Requirements 2.1**

### Property 7: Execution history includes required fields
*For any* delivery event in the event store, querying the execution history endpoint SHALL return entries with timestamps and status
**Validates: Requirements 2.2**

### Property 8: Fetch history includes required fields
*For any* fetch event in the event store, querying the fetch history endpoint SHALL return entries with sources and results
**Validates: Requirements 2.3**

### Property 9: Error log endpoint returns recent errors
*For any* error event in the event store, querying the error log endpoint SHALL return entries with timestamps and context
**Validates: Requirements 2.4**

### Property 10: Metrics calculation is accurate
*For any* set of delivery events in the event store, the metrics endpoint SHALL return success_rate equal to (successful_deliveries / total_deliveries) * 100
**Validates: Requirements 2.5**

### Property 11: Log entries have required fields
*For any* log entry written, the output SHALL be valid JSON containing timestamp, level, component, and message fields
**Validates: Requirements 3.1, 3.3**

### Property 12: Log entries preserve context
*For any* log entry written with context fields, the output SHALL include all provided context fields
**Validates: Requirements 3.2**

### Property 13: Error log entries include exception details
*For any* log entry with an error, the output SHALL include exception type, message, and stack trace
**Validates: Requirements 3.4**

### Property 14: Trace IDs are assigned to operations
*For any* delivery operation, the system SHALL assign a unique trace ID that is included in all related log entries
**Validates: Requirements 4.1, 4.2**

### Property 15: Trace endpoint returns complete history
*For any* trace ID, querying the trace endpoint SHALL return all log entries for that trace in chronological order
**Validates: Requirements 4.3, 4.4**

## Testing Strategy

### Unit Testing
- Test logger with various log levels and context fields
- Test trace context manager (create, get, set, clear operations)
- Test event store (add, query, purge operations)
- Test metrics calculation with various event combinations
- Test debug endpoint response formatting

### Property-Based Testing
- Use Hypothesis (Python) to generate random log entries and verify JSON format compliance
- Generate random delivery events and verify trace completeness
- Generate random error scenarios and verify error context inclusion
- Generate random event sequences and verify metrics accuracy
- Generate random trace IDs and verify they're properly propagated

### Integration Testing
- Test logging during actual scheduler execution
- Test trace propagation through complete delivery flow
- Test debug endpoints with real event store data
- Test event store purging with time-based cleanup

