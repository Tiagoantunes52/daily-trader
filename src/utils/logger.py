"""Structured logging module with JSON output support."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class StructuredLogger:
    """Logger that outputs JSON-formatted log entries."""

    def __init__(self, component: str, file_path: str | None = None):
        """
        Initialize the structured logger.

        Args:
            component: Name of the component using this logger
            file_path: Optional path to write logs to file
        """
        self.component = component
        self.file_path = file_path
        if file_path:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    def _format_log_entry(
        self,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
        exception: dict[str, Any] | None = None,
    ) -> str:
        """
        Format a log entry as JSON.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            context: Optional context fields
            exception: Optional exception details

        Returns:
            JSON-formatted log entry
        """
        entry = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": level,
            "component": self.component,
            "message": message,
        }

        if context:
            entry["context"] = context

        if exception:
            entry["exception"] = exception

        return json.dumps(entry)

    def _write_log(self, log_entry: str) -> None:
        """
        Write log entry to stdout and optional file.

        Args:
            log_entry: JSON-formatted log entry
        """
        try:
            print(log_entry, file=sys.stdout)
            if self.file_path:
                with open(self.file_path, "a") as f:
                    f.write(log_entry + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}", file=sys.stderr)

    def debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log a debug message."""
        log_entry = self._format_log_entry("DEBUG", message, context)
        self._write_log(log_entry)

    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log an info message."""
        log_entry = self._format_log_entry("INFO", message, context)
        self._write_log(log_entry)

    def warning(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Log a warning message."""
        log_entry = self._format_log_entry("WARNING", message, context)
        self._write_log(log_entry)

    def error(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        exception: Exception | None = None,
    ) -> None:
        """Log an error message with optional exception details."""
        exc_dict = None
        if exception:
            import traceback

            exc_dict = {
                "type": type(exception).__name__,
                "message": str(exception),
                "stack_trace": traceback.format_exc(),
            }

        log_entry = self._format_log_entry("ERROR", message, context, exc_dict)
        self._write_log(log_entry)

    def critical(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        exception: Exception | None = None,
    ) -> None:
        """Log a critical message with optional exception details."""
        exc_dict = None
        if exception:
            import traceback

            exc_dict = {
                "type": type(exception).__name__,
                "message": str(exception),
                "stack_trace": traceback.format_exc(),
            }

        log_entry = self._format_log_entry("CRITICAL", message, context, exc_dict)
        self._write_log(log_entry)

    def log(
        self,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
        exception: Exception | None = None,
    ) -> None:
        """
        Log a message with specified level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            context: Optional context fields
            exception: Optional exception
        """
        level = level.upper()
        if level == "DEBUG":
            self.debug(message, context)
        elif level == "INFO":
            self.info(message, context)
        elif level == "WARNING":
            self.warning(message, context)
        elif level == "ERROR":
            self.error(message, context, exception)
        elif level == "CRITICAL":
            self.critical(message, context, exception)
        else:
            self.info(message, context)
