
"""
DevTrace application configuration.

This module centralizes application settings so that configuration is not
hardcoded across multiple files. It loads values from environment variables
and the repository-root .env file. Environment variables take precedence
over values in .env, allowing developers to use different configurations
without modifying source code.

This module only manages configuration; it does not create database
connections. Database connection and session management are handled
separately in app/db/session.py.
"""

# lru_cache allows us to reuse the same Settings object instead of repeatedly
# reading and validating configuration whenever get_settings() is called.
from functools import lru_cache

# Path provides a reliable way to construct filesystem paths independently
# of the operating system and the terminal's current working directory.
from pathlib import Path

# Field defines validation rules, defaults, and environment-variable aliases.
# SecretStr protects sensitive values, such as passwords, from being exposed
# accidentally when the value is displayed or logged.
from pydantic import Field, SecretStr

# BaseSettings loads and validates configuration from environment variables
# and .env files. SettingsConfigDict specifies how that loading is performed.
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the repository root using this file's location:
# app/core/config.py -> app/core -> app -> repository root.
# This prevents .env loading from depending on where a command is executed.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Construct the absolute path to the repository's .env file.
# The actual file contains local configuration and must not be committed.
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    Define and validate the configuration required by DevTrace.

    Each attribute represents a setting. Its default is used when no
    corresponding environment variable or .env value is provided.
    Field aliases connect Python attribute names to the environment-variable
    names already used by the project.
    """

    # Application metadata used by FastAPI for its title and API version.
    # APP_NAME and APP_VERSION can override these defaults.
    app_name: str = Field(
        default="DevTrace API",
        validation_alias="APP_NAME",
    )
    app_version: str = Field(
        default="0.1.0",
        validation_alias="APP_VERSION",
    )

    # Identifies the environment in which the application is running.
    # APP_ENV might be set to development, testing, or production.
    environment: str = Field(
        default="development",
        validation_alias="APP_ENV",
    )

    # Controls FastAPI's debug mode. It defaults to False to avoid enabling
    # debug behavior accidentally when the setting is not configured.
    debug: bool = Field(
        default=False,
        validation_alias="DEBUG",
    )

    # Database server hostname. "localhost" is suitable when PostgreSQL
    # is exposed on the same machine as the backend.
    db_host: str = Field(
        default="localhost",
        min_length=1,
        validation_alias="DB_HOST",
    )

    # TCP port used to connect to PostgreSQL.
    # The default 5433 matches the current Docker host-port mapping.
    # The ge/le constraints reject values outside the valid port range.
    db_port: int = Field(
        default=5433,
        ge=1,
        le=65535,
        validation_alias="DB_PORT",
    )

    # Name of the database used by the application.
    # min_length=1 prevents an empty database name from being accepted.
    db_name: str = Field(
        default="devtrace_db",
        min_length=1,
        validation_alias="DB_NAME",
    )

    # PostgreSQL login role used by the backend.
    # This should be an application role with only the permissions it needs.
    db_user: str = Field(
        default="devtrace_app",
        min_length=1,
        validation_alias="DB_USER",
    )

    # Database password is stored as SecretStr so that its normal
    # representation is masked rather than displaying the actual password.
    # An empty default permits configuration loading, but database access
    # will fail until valid credentials are supplied.
    db_password: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="DB_PASSWORD",
    )

    # Configure how Pydantic Settings reads configuration:
    # - env_file: load values from the absolute .env path defined above.
    # - env_file_encoding: read the file as UTF-8.
    # - case_sensitive=False: environment-variable matching is case-insensitive.
    # - extra="ignore": ignore unrelated entries in .env instead of rejecting
    #   them, since the file may contain settings for other tools.
    # - validate_default=True: validate default values as well as supplied ones.
    #
    # Environment variables take precedence over values from the .env file.
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )


# Cache the Settings instance so that repeated calls reuse one validated
# configuration object. Clear this cache in tests when changing environment
# variables and needing to load a fresh configuration.
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()


# Create a convenient shared settings object for modules that need
# configuration, for example: from app.core.config import settings.
settings = get_settings()
