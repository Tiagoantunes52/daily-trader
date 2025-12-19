"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from src.utils.config import Config, EmailConfig, SchedulerConfig


def test_email_config_default_retry_delays():
    """Test that email config has default retry delays."""
    config = EmailConfig(
        smtp_server="smtp.test.com",
        smtp_port=587,
        sender_email="test@test.com",
        sender_password="password",
    )
    assert config.retry_delays == [300, 900, 1800]


def test_scheduler_config_default_timezone():
    """Test that scheduler config has default timezone."""
    config = SchedulerConfig(morning_time="06:00", evening_time="18:00")
    assert config.timezone == "UTC"


def test_config_validation_missing_email():
    """Test that config validation fails without sender email."""
    with patch.dict(
        os.environ,
        {
            "SENDER_EMAIL": "",
            "SENDER_PASSWORD": "password",
            "MORNING_TIME": "06:00",
            "EVENING_TIME": "18:00",
        },
    ):
        config = Config()

        with pytest.raises(ValueError, match="SENDER_EMAIL"):
            config.validate()


def test_config_validation_missing_password():
    """Test that config validation fails without sender password."""
    with patch.dict(
        os.environ,
        {
            "SENDER_EMAIL": "test@test.com",
            "SENDER_PASSWORD": "",
            "MORNING_TIME": "06:00",
            "EVENING_TIME": "18:00",
        },
    ):
        config = Config()

        with pytest.raises(ValueError, match="SENDER_PASSWORD"):
            config.validate()


def test_config_validation_invalid_time_format():
    """Test that config validation fails with invalid time format."""
    with patch.dict(
        os.environ,
        {
            "SENDER_EMAIL": "test@test.com",
            "SENDER_PASSWORD": "password",
            "MORNING_TIME": "25:00",
            "EVENING_TIME": "18:00",
        },
    ):
        config = Config()

        with pytest.raises(ValueError, match="Invalid time"):
            config.validate()


def test_config_validation_valid_times():
    """Test that config validation passes with valid times."""
    with patch.dict(
        os.environ,
        {
            "SENDER_EMAIL": "test@test.com",
            "SENDER_PASSWORD": "password",
            "MORNING_TIME": "06:00",
            "EVENING_TIME": "18:00",
        },
    ):
        config = Config()

        assert config.validate() is True
