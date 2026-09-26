"""Tests for configuration management."""

import os
import json
import pytest
from pathlib import Path
from backend.config.config import (
    Config,
    ConfigManager,
    DatabaseConfig,
    SecurityConfig,
    RateLimitConfig,
    APIConfig,
    Environment,
    get_config
)


class TestEnvironment:
    """Test Environment enum."""
    
    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TEST.value == "test"
        assert Environment.PRODUCTION.value == "production"
    
    def test_environment_from_string(self):
        """Test creating environment from string."""
        assert Environment("development") == Environment.DEVELOPMENT
        assert Environment("test") == Environment.TEST
        assert Environment("production") == Environment.PRODUCTION
    
    def test_environment_invalid_string(self):
        """Test invalid environment string."""
        with pytest.raises(ValueError):
            Environment("invalid")


class TestDatabaseConfig:
    """Test DatabaseConfig dataclass."""
    
    def test_default_values(self):
        """Test default database configuration."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "character_engine"
        assert config.username == "postgres"
        assert config.password == ""
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.echo_sql is False
    
    def test_custom_values(self):
        """Test custom database configuration."""
        config = DatabaseConfig(
            host="custom-host",
            port=3306,
            database="custom-db",
            username="custom-user",
            password="custom-pass",
            pool_size=20,
            max_overflow=40,
            echo_sql=True
        )
        assert config.host == "custom-host"
        assert config.port == 3306
        assert config.database == "custom-db"
        assert config.username == "custom-user"
        assert config.password == "custom-pass"
        assert config.pool_size == 20
        assert config.max_overflow == 40
        assert config.echo_sql is True
    
    def test_immutability(self):
        """Test that configuration is immutable."""
        config = DatabaseConfig()
        with pytest.raises(Exception):  # FrozenInstanceError
            config.host = "new-host"


class TestSecurityConfig:
    """Test SecurityConfig dataclass."""
    
    def test_default_values(self):
        """Test default security configuration."""
        config = SecurityConfig()
        assert config.secret_key == ""
        assert config.algorithm == "HS256"
        assert config.access_token_expire_minutes == 30
        assert config.refresh_token_expire_days == 7
        assert config.password_min_length == 8
        assert config.password_max_length == 128
    
    def test_custom_values(self):
        """Test custom security configuration."""
        config = SecurityConfig(
            secret_key="test-secret",
            algorithm="RS256",
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
            password_min_length=12,
            password_max_length=256
        )
        assert config.secret_key == "test-secret"
        assert config.algorithm == "RS256"
        assert config.access_token_expire_minutes == 60
        assert config.refresh_token_expire_days == 30
        assert config.password_min_length == 12
        assert config.password_max_length == 256


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass."""
    
    def test_default_values(self):
        """Test default rate limit configuration."""
        config = RateLimitConfig()
        assert config.registration_requests_per_minute == 5
        assert config.authentication_requests_per_minute == 10
        assert config.api_requests_per_minute == 100
        assert config.api_requests_per_hour == 1000
    
    def test_custom_values(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(
            registration_requests_per_minute=10,
            authentication_requests_per_minute=20,
            api_requests_per_minute=200,
            api_requests_per_hour=2000
        )
        assert config.registration_requests_per_minute == 10
        assert config.authentication_requests_per_minute == 20
        assert config.api_requests_per_minute == 200
        assert config.api_requests_per_hour == 2000


class TestAPIConfig:
    """Test APIConfig dataclass."""
    
    def test_default_values(self):
        """Test default API configuration."""
        config = APIConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is True
        assert config.cors_origins == ["http://localhost:3000"]
        assert config.max_request_size == 10 * 1024 * 1024
    
    def test_custom_values(self):
        """Test custom API configuration."""
        config = APIConfig(
            host="127.0.0.1",
            port=9000,
            debug=False,
            cors_origins=["http://example.com"],
            max_request_size=20 * 1024 * 1024
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.debug is False
        assert config.cors_origins == ["http://example.com"]
        assert config.max_request_size == 20 * 1024 * 1024


class TestConfig:
    """Test Config dataclass."""
    
    def test_default_values(self):
        """Test default configuration."""
        config = Config()
        assert config.environment == Environment.DEVELOPMENT
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.rate_limit, RateLimitConfig)
        assert isinstance(config.api, APIConfig)
    
    def test_custom_values(self):
        """Test custom configuration."""
        config = Config(
            environment=Environment.TEST,
            database=DatabaseConfig(database="test-db"),
            security=SecurityConfig(secret_key="test-key"),
            rate_limit=RateLimitConfig(registration_requests_per_minute=10),
            api=APIConfig(port=9000)
        )
        assert config.environment == Environment.TEST
        assert config.database.database == "test-db"
        assert config.security.secret_key == "test-key"
        assert config.rate_limit.registration_requests_per_minute == 10
        assert config.api.port == 9000
    
    def test_validation_valid(self):
        """Test configuration validation with valid values."""
        config = Config()
        assert config._validate() is None  # Should not raise
    
    def test_validation_invalid_environment(self):
        """Test configuration validation with invalid environment."""
        with pytest.raises(ValueError):
            Config(environment="invalid")
    
    def test_validation_production_without_secret(self):
        """Test production configuration requires secret key."""
        with pytest.raises(ValueError, match="SECRET_KEY must be set"):
            Config(
                environment=Environment.PRODUCTION,
                database=DatabaseConfig(password="test-pass"),
                security=SecurityConfig(secret_key="")
            )
    
    def test_validation_production_without_db_password(self):
        """Test production configuration requires database password."""
        with pytest.raises(ValueError, match="Database password must be set"):
            Config(
                environment=Environment.PRODUCTION,
                database=DatabaseConfig(password=""),
                security=SecurityConfig(secret_key="test-key")
            )
    
    def test_validation_invalid_port(self):
        """Test configuration validation with invalid port."""
        with pytest.raises(ValueError, match="Invalid port"):
            Config(api=APIConfig(port=70000))
    
    def test_validation_invalid_rate_limit(self):
        """Test configuration validation with invalid rate limit."""
        with pytest.raises(ValueError, match="Registration rate limit"):
            Config(rate_limit=RateLimitConfig(registration_requests_per_minute=0))


class TestConfigManager:
    """Test ConfigManager class."""
    
    def test_detect_environment_default(self, monkeypatch):
        """Test environment detection defaults to development."""
        monkeypatch.delenv("CHARACTER_ENGINE_ENV", raising=False)
        manager = ConfigManager()
        assert manager._environment == Environment.DEVELOPMENT
    
    def test_detect_environment_from_env(self, monkeypatch):
        """Test environment detection from environment variable."""
        monkeypatch.setenv("CHARACTER_ENGINE_ENV", "test")
        manager = ConfigManager()
        assert manager._environment == Environment.TEST
    
    def test_detect_environment_invalid_defaults(self, monkeypatch):
        """Test invalid environment defaults to development."""
        monkeypatch.setenv("CHARACTER_ENGINE_ENV", "invalid")
        manager = ConfigManager()
        assert manager._environment == Environment.DEVELOPMENT
    
    def test_load_base_config_missing(self, tmp_path):
        """Test loading configuration when base config is missing."""
        manager = ConfigManager(config_dir=tmp_path)
        config = manager._load_base_config()
        assert config == {}
    
    def test_load_base_config_exists(self, tmp_path):
        """Test loading configuration when base config exists."""
        base_config_path = tmp_path / "base.json"
        base_config_path.write_text('{"test_key": "test_value"}')
        
        manager = ConfigManager(config_dir=tmp_path)
        config = manager._load_base_config()
        assert config == {"test_key": "test_value"}
    
    def test_load_environment_config_missing(self, tmp_path):
        """Test loading configuration when environment config is missing."""
        manager = ConfigManager(config_dir=tmp_path)
        config = manager._load_environment_config()
        assert config == {}
    
    def test_load_environment_config_exists(self, tmp_path):
        """Test loading configuration when environment config exists."""
        env_config_path = tmp_path / "development.json"
        env_config_path.write_text('{"env_key": "env_value"}')
        
        manager = ConfigManager(config_dir=tmp_path)
        config = manager._load_environment_config()
        assert config == {"env_key": "env_value"}
    
    def test_load_secrets_from_env(self, monkeypatch):
        """Test loading secrets from environment variables."""
        monkeypatch.setenv("DATABASE_PASSWORD", "test-db-pass")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        
        manager = ConfigManager()
        secrets = manager._load_secrets()
        assert secrets["database_password"] == "test-db-pass"
        assert secrets["secret_key"] == "test-secret-key"
    
    def test_load_secrets_missing(self, monkeypatch):
        """Test loading secrets when environment variables are missing."""
        monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        
        manager = ConfigManager()
        secrets = manager._load_secrets()
        assert secrets == {}
    
    def test_merge_configs(self, tmp_path):
        """Test merging configuration sources."""
        # Create base config
        base_config_path = tmp_path / "base.json"
        base_config_path.write_text('{"database_name": "base-db", "api_port": 8000}')
        
        # Create environment config
        env_config_path = tmp_path / "development.json"
        env_config_path.write_text('{"database_name": "dev-db", "api_debug": true}')
        
        manager = ConfigManager(config_dir=tmp_path)
        config = manager._merge_configs(
            manager._load_base_config(),
            manager._load_environment_config(),
            {}
        )
        
        assert config.database.database == "dev-db"  # Environment overrides base
        assert config.api.port == 8000  # Base value preserved
        assert config.api.debug is True  # Environment value
    
    def test_load_config_complete(self, tmp_path, monkeypatch):
        """Test complete configuration loading."""
        # Create base config
        base_config_path = tmp_path / "base.json"
        base_config_path.write_text('{"database_name": "base-db"}')
        
        # Create environment config
        env_config_path = tmp_path / "development.json"
        env_config_path.write_text('{"database_name": "dev-db"}')
        
        # Set secrets
        monkeypatch.setenv("DATABASE_PASSWORD", "test-pass")
        monkeypatch.setenv("SECRET_KEY", "test-key")
        
        manager = ConfigManager(config_dir=tmp_path)
        config = manager.load_config()
        
        assert config.environment == Environment.DEVELOPMENT
        assert config.database.database == "dev-db"
        assert config.database.password == "test-pass"
        assert config.security.secret_key == "test-key"


class TestGetConfig:
    """Test get_config function."""
    
    def test_get_config_default(self, monkeypatch):
        """Test get_config with default configuration directory."""
        monkeypatch.delenv("CHARACTER_ENGINE_ENV", raising=False)
        config = get_config()
        assert config.environment == Environment.DEVELOPMENT
    
    def test_get_config_custom_dir(self, tmp_path, monkeypatch):
        """Test get_config with custom configuration directory."""
        # Create environment config
        env_config_path = tmp_path / "development.json"
        env_config_path.write_text('{"database_name": "custom-db"}')
        
        config = get_config(config_dir=tmp_path)
        assert config.database.database == "custom-db"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])