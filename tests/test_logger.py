"""Property-based tests for structured logging."""

import json
import sys
from io import StringIO

from hypothesis import given
from hypothesis import strategies as st

from src.utils.logger import StructuredLogger


class TestLoggerJSONFormat:
    """Tests for JSON log format compliance."""

    @given(
        level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        message=st.text(min_size=1),
        context_keys=st.lists(st.text(min_size=1, max_size=20), max_size=5),
        context_values=st.lists(st.one_of(st.text(), st.integers(), st.booleans()), max_size=5),
    )
    def test_log_entries_have_required_fields(self, level, message, context_keys, context_values):
        """
        **Feature: observability-logging, Property 11: Log entries have required fields**
        **Validates: Requirements 3.1, 3.3**

        For any log entry written, the output SHALL be valid JSON containing
        timestamp, level, component, and message fields.
        """
        # Prepare context dict
        context = {}
        for key, value in zip(context_keys, context_values, strict=False):
            # Ensure keys are valid identifiers
            if key and key[0].isalpha():
                context[key] = value

        # Capture stdout
        captured_output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            logger = StructuredLogger("test_component")
            logger.log(level, message, context if context else None)

            # Restore stdout
            sys.stdout = original_stdout
            output = captured_output.getvalue().strip()

            # Verify output is valid JSON
            log_entry = json.loads(output)

            # Verify required fields exist
            assert "timestamp" in log_entry, "Missing 'timestamp' field"
            assert "level" in log_entry, "Missing 'level' field"
            assert "component" in log_entry, "Missing 'component' field"
            assert "message" in log_entry, "Missing 'message' field"

            # Verify field values
            assert log_entry["level"] == level.upper()
            assert log_entry["component"] == "test_component"
            assert log_entry["message"] == message

            # Verify timestamp is ISO8601 format
            assert log_entry["timestamp"].endswith("Z")
            assert "T" in log_entry["timestamp"]

            # Verify context is included if provided
            if context:
                assert "context" in log_entry
                assert log_entry["context"] == context

        finally:
            sys.stdout = original_stdout

    @given(
        message=st.text(min_size=1),
        context=st.dictionaries(
            st.text(min_size=1, max_size=20).filter(lambda x: x[0].isalpha()),
            st.one_of(st.text(), st.integers(), st.booleans()),
            max_size=5,
        ),
    )
    def test_log_entries_preserve_context(self, message, context):
        """
        **Feature: observability-logging, Property 12: Log entries preserve context**
        **Validates: Requirements 3.2**

        For any log entry written with context fields, the output SHALL include
        all provided context fields.
        """
        # Capture stdout
        captured_output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            logger = StructuredLogger("test_component")
            logger.info(message, context if context else None)

            # Restore stdout
            sys.stdout = original_stdout
            output = captured_output.getvalue().strip()

            log_entry = json.loads(output)

            # Verify all context fields are preserved
            if context:
                assert "context" in log_entry
                for key, value in context.items():
                    assert key in log_entry["context"]
                    assert log_entry["context"][key] == value

        finally:
            sys.stdout = original_stdout

    @given(
        message=st.text(min_size=1),
        exception_type=st.sampled_from(
            [ValueError, TypeError, RuntimeError, KeyError, AttributeError]
        ),
    )
    def test_error_log_entries_include_exception_details(self, message, exception_type):
        """
        **Feature: observability-logging, Property 13: Error log entries include exception details**
        **Validates: Requirements 3.4**

        For any log entry with an error, the output SHALL include exception type,
        message, and stack trace.
        """
        # Capture stdout
        captured_output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            logger = StructuredLogger("test_component")

            # Create and log an exception
            try:
                raise exception_type("Test error message")
            except exception_type as e:
                logger.error(message, exception=e)

            # Restore stdout
            sys.stdout = original_stdout
            output = captured_output.getvalue().strip()

            log_entry = json.loads(output)

            # Verify exception details are included
            assert "exception" in log_entry
            assert "type" in log_entry["exception"]
            assert "message" in log_entry["exception"]
            assert "stack_trace" in log_entry["exception"]

            # Verify exception type matches
            assert log_entry["exception"]["type"] == exception_type.__name__
            assert "Test error message" in log_entry["exception"]["message"]
            assert "raise exception_type" in log_entry["exception"]["stack_trace"]

        finally:
            sys.stdout = original_stdout
