"""Tests for configuration module."""

import os
from unittest.mock import patch


from chuk_mcp_celestial.config import (
    ProviderConfig,
    SkyfieldConfig,
    load_yaml_config,
)


class TestLoadYamlConfig:
    """Test YAML configuration loading."""

    def test_no_yaml_available(self):
        """Test when PyYAML is not available."""
        with patch("chuk_mcp_celestial.config.YAML_AVAILABLE", False):
            result = load_yaml_config()
            assert result == {}

    def test_env_config_path(self, tmp_path):
        """Test loading config from CELESTIAL_CONFIG_PATH environment variable."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("default_provider: skyfield\n")

        with patch.dict(os.environ, {"CELESTIAL_CONFIG_PATH": str(config_file)}):
            # Clear any cached config
            from importlib import reload
            from chuk_mcp_celestial import config as config_module

            reload(config_module)
            result = load_yaml_config()
            assert result.get("default_provider") == "skyfield"

    def test_config_file_error(self, tmp_path):
        """Test handling of malformed YAML file."""
        config_file = tmp_path / "bad_config.yaml"
        config_file.write_text("invalid: yaml: syntax:")

        with patch.dict(os.environ, {"CELESTIAL_CONFIG_PATH": str(config_file)}):
            result = load_yaml_config()
            # Should return empty dict on error
            assert result == {}

    def test_no_config_file(self, tmp_path, monkeypatch):
        """Test when no config file exists."""
        # Change to a temp directory with no config
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CELESTIAL_CONFIG_PATH", raising=False)

        result = load_yaml_config()
        assert result == {}


class TestProviderConfig:
    """Test provider configuration."""

    def test_default_provider(self):
        """Test default provider setting."""
        assert ProviderConfig.DEFAULT_PROVIDER in ["navy_api", "skyfield"]

    def test_provider_config_attributes(self):
        """Test that provider config attributes exist."""
        # Should have DEFAULT_PROVIDER
        assert hasattr(ProviderConfig, "DEFAULT_PROVIDER")
        assert isinstance(ProviderConfig.DEFAULT_PROVIDER, str)

    def test_env_override(self, monkeypatch):
        """Test environment variable override."""
        monkeypatch.setenv("CELESTIAL_PROVIDER", "skyfield")

        # Reload config to pick up env var
        from importlib import reload
        from chuk_mcp_celestial import config as config_module

        reload(config_module)

        # Should use env var
        assert config_module.ProviderConfig.DEFAULT_PROVIDER == "skyfield"


class TestSkyfieldConfig:
    """Test Skyfield configuration."""

    def test_ephemeris_file(self):
        """Test ephemeris file configuration."""
        assert SkyfieldConfig.EPHEMERIS_FILE in [
            "de421.bsp",
            "de440s.bsp",
            "de440.bsp",
        ]

    def test_storage_backend(self):
        """Test storage backend configuration."""
        assert SkyfieldConfig.STORAGE_BACKEND in ["local", "s3", "memory"]

    def test_data_dir(self):
        """Test data directory configuration."""
        assert isinstance(SkyfieldConfig.DATA_DIR, str)
        assert len(SkyfieldConfig.DATA_DIR) > 0

    def test_auto_download(self):
        """Test auto download configuration."""
        assert isinstance(SkyfieldConfig.AUTO_DOWNLOAD, bool)

    def test_s3_configuration(self):
        """Test S3 configuration values."""
        assert isinstance(SkyfieldConfig.S3_BUCKET, str)
        assert isinstance(SkyfieldConfig.S3_REGION, str)
        assert isinstance(SkyfieldConfig.S3_PREFIX, str)

    def test_env_override_skyfield(self, monkeypatch):
        """Test Skyfield environment variable overrides."""
        monkeypatch.setenv("SKYFIELD_EPHEMERIS", "de440.bsp")
        monkeypatch.setenv("SKYFIELD_STORAGE_BACKEND", "local")
        monkeypatch.setenv("SKYFIELD_S3_BUCKET", "test-bucket")

        # Reload config
        from importlib import reload
        from chuk_mcp_celestial import config as config_module

        reload(config_module)

        assert config_module.SkyfieldConfig.EPHEMERIS_FILE == "de440.bsp"
        assert config_module.SkyfieldConfig.STORAGE_BACKEND == "local"
        assert config_module.SkyfieldConfig.S3_BUCKET == "test-bucket"
