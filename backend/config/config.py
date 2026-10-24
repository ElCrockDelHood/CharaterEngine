"""Configuration management for CHARACTER ENGINE backend.

This module provides configuration management with support for:
- Base configuration
- Environment-specific overrides
- Secrets management
- Configuration validation
"""

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class Environment(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


@dataclass(frozen=True)
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "character_engine"
    username: str = "postgres"
    password: str = ""  # From secrets
    pool_size: int = 10
    max_overflow: int = 20
    echo_sql: bool = False


@dataclass(frozen=True)
class SecurityConfig:
    """Security configuration."""
    secret_key: str = ""  # From secrets
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_max_length: int = 128
    password_hash_algorithm: str = "argon2id"  # Password hashing algorithm
    session_timeout_minutes: int = 60  # Session timeout in minutes
    max_sessions_per_account: int = 5  # Maximum concurrent sessions per account


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting configuration."""
    registration_requests_per_minute: int = 5
    authentication_requests_per_minute: int = 10
    api_requests_per_minute: int = 100
    api_requests_per_hour: int = 1000


@dataclass(frozen=True)
class APIConfig:
    """API configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors_origins: list = field(default_factory=lambda: ["http://localhost:3000"])
    max_request_size: int = 10 * 1024 * 1024  # 10MB


@dataclass(frozen=True)
class Config:
    """Main configuration."""
    environment: Environment = Environment.DEVELOPMENT
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    api: APIConfig = field(default_factory=APIConfig)

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration."""
        # Validate environment
        if not isinstance(self.environment, Environment):
            raise ValueError(f"Invalid environment: {self.environment}")

        # Validate required secrets in production
        if self.environment == Environment.PRODUCTION:
            if not self.database.password:
                raise ValueError("Database password must be set in production")
            if not self.security.secret_key:
                raise ValueError("SECRET_KEY must be set in production")

        # Validate port
        if not (1 <= self.api.port <= 65535):
            raise ValueError(f"Invalid port: {self.api.port}")

        # Validate rate limits
        if self.rate_limit.registration_requests_per_minute < 1:
            raise ValueError("Registration rate limit must be at least 1")
        if self.rate_limit.authentication_requests_per_minute < 1:
            raise ValueError("Authentication rate limit must be at least 1")


class ConfigManager:
    """Configuration manager for loading and validating configuration."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Configuration directory path
        """
        if config_dir is None:
            config_dir = Path(__file__).parent / "config"
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._environment = self._detect_environment()

    def _detect_environment(self) -> Environment:
        """Detect current environment from environment variable."""
        env_str = os.getenv("CHARACTER_ENGINE_ENV", "development")
        try:
            return Environment(env_str.lower())
        except ValueError:
            return Environment.DEVELOPMENT

    def load_config(self) -> Config:
        """Load configuration from files and environment variables.

        Returns:
            Validated configuration object
        """
        # Load base configuration
        base_config = self._load_base_config()

        # Load environment-specific configuration
        env_config = self._load_environment_config()

        # Load secrets
        secrets = self._load_secrets()

        # Merge configurations
        config = self._merge_configs(base_config, env_config, secrets)

        return config

    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration file."""
        base_config_path = self.config_dir / "base.json"

        if base_config_path.exists():
            with open(base_config_path) as f:
                return json.load(f)

        # Return default configuration if file doesn't exist
        return {}

    def _load_environment_config(self) -> Dict[str, Any]:
        """Load environment-specific configuration."""
        env_config_path = self.config_dir / f"{self._environment.value}.json"

        if env_config_path.exists():
            with open(env_config_path) as f:
                return json.load(f)

        return {}

    def _load_secrets(self) -> Dict[str, str]:
        """Load secrets from environment variables."""
        secrets = {}

        # Database password
        if db_password := os.getenv("DATABASE_PASSWORD"):
            secrets["database_password"] = db_password

        # Secret key
        if secret_key := os.getenv("SECRET_KEY"):
            secrets["secret_key"] = secret_key

        return secrets

    def _merge_configs(self, base_config: Dict[str, Any],
                        env_config: Dict[str, Any],
                        secrets: Dict[str, str]) -> Config:
        """Merge configuration sources in priority order.

        Priority: Environment > Base > Defaults > Secrets
        """
        merged = {}

        # Start with base configuration
        merged.update(base_config)

        # Override with environment configuration
        merged.update(env_config)

        # Apply secrets
        if "database_password" in secrets:
            merged["database_password"] = secrets["database_password"]
        if "secret_key" in secrets:
            merged["secret_key"] = secrets["secret_key"]

        # Create configuration objects
        config = Config(
            environment=self._environment,
            database=DatabaseConfig(
                host=merged.get("database_host", "localhost"),
                port=merged.get("database_port", 5432),
                database=merged.get("database_name", "character_engine"),
                username=merged.get("database_username", "postgres"),
                password=merged.get("database_password", ""),
                pool_size=merged.get("database_pool_size", 10),
                max_overflow=merged.get("database_max_overflow", 20),
                echo_sql=merged.get("database_echo_sql", False)
            ),
            security=SecurityConfig(
                secret_key=merged.get("secret_key", ""),
                algorithm=merged.get("security_algorithm", "HS256"),
                access_token_expire_minutes=merged.get("access_token_expire_minutes", 30),
                refresh_token_expire_days=merged.get("refresh_token_expire_days", 7),
                password_min_length=merged.get("password_min_length", 8),
                password_max_length=merged.get("password_max_length", 128)
            ),
            rate_limit=RateLimitConfig(
                registration_requests_per_minute=merged.get("registration_requests_per_minute", 5),
                authentication_requests_per_minute=merged.get("authentication_requests_per_minute", 10),
                api_requests_per_minute=merged.get("api_requests_per_minute", 100),
                api_requests_per_hour=merged.get("api_requests_per_hour", 1000)
            ),
            api=APIConfig(
                host=merged.get("api_host", "0.0.0.0"),
                port=merged.get("api_port", 8000),
                debug=merged.get("api_debug", True),
                cors_origins=merged.get("cors_origins", ["http://localhost:3000"]),
                max_request_size=merged.get("max_request_size", 10 * 1024 * 1024)
            )
        )

        return config


def get_config(config_dir: Optional[Path] = None) -> Config:
    """Get configuration instance.

    Args:
        config_dir: Configuration directory path

    Returns:
        Validated configuration object
    """
    manager = ConfigManager(config_dir)
    return manager.load_config()
