# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Tests for proxy handling functions."""

import os
from unittest.mock import patch

import pytest
from hishel import AsyncCacheTransport
from httpx import Limits

from ghga_service_commons.transports.config import CompositeCacheConfig, CompositeConfig
from ghga_service_commons.transports.proxy_handling import (
    cached_ratelimiting_retry_proxies,
    ratelimiting_retry_proxies,
)
from ghga_service_commons.transports.retry import AsyncRetryTransport


class TestRateLimitingRetryProxies:
    """Tests for ratelimiting_retry_proxies function."""

    def test_with_http_proxy(self):
        """Test that http proxy is correctly configured."""
        config = CompositeConfig()

        with patch.dict(os.environ, {"http_proxy": "http://proxy.example.com:8080"}):
            with patch(
                "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
                return_value={"http://": "http://proxy.example.com:8080"},
            ):
                mounts = ratelimiting_retry_proxies(config)

                assert "http://" in mounts
                assert isinstance(mounts["http://"], AsyncRetryTransport)

    def test_with_https_proxy(self):
        """Test that https proxy is correctly configured."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"https://": "https://secure-proxy.example.com:8443"},
        ):
            mounts = ratelimiting_retry_proxies(config)

            assert "https://" in mounts
            assert isinstance(mounts["https://"], AsyncRetryTransport)

    def test_with_all_proxy(self):
        """Test that 'all' proxy fallback is correctly configured."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"all://": "http://fallback-proxy.example.com:8080"},
        ):
            mounts = ratelimiting_retry_proxies(config)

            assert "all://" in mounts
            assert isinstance(mounts["all://"], AsyncRetryTransport)

    def test_with_multiple_proxies(self):
        """Test that multiple proxy protocols are configured together."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={
                "http://": "http://proxy.example.com:8080",
                "https://": "https://secure-proxy.example.com:8443",
                "all://": "http://fallback-proxy.example.com:8080",
            },
        ):
            mounts = ratelimiting_retry_proxies(config)

            assert len(mounts) == 3
            assert "http://" in mounts
            assert "https://" in mounts
            assert "all://" in mounts
            assert all(isinstance(t, AsyncRetryTransport) for t in mounts.values())

    def test_with_no_proxies(self):
        """Test that empty dict is returned when no proxies are configured."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={},
        ):
            mounts = ratelimiting_retry_proxies(config)

            assert mounts == {}

    def test_with_limits(self):
        """Test that limits are passed to the transport factory."""
        config = CompositeConfig()
        limits = Limits(max_connections=10, max_keepalive_connections=5)

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"http://": "http://proxy.example.com:8080"},
        ):
            mounts = ratelimiting_retry_proxies(config, limits=limits)

            assert "http://" in mounts
            assert isinstance(mounts["http://"], AsyncRetryTransport)

    def test_filters_none_proxy_values(self):
        """Test that None proxy values are filtered out."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={
                "http://": "http://proxy.example.com:8080",
                "https://": None,
                "all://": "http://fallback-proxy.example.com:8080",
            },
        ):
            mounts = ratelimiting_retry_proxies(config)

            # The function should filter out None values
            assert len(mounts) == 2
            assert "http://" in mounts
            assert "all://" in mounts
            assert "https://" not in mounts


class TestCachedRateLimitingRetryProxies:
    """Tests for cached_ratelimiting_retry_proxies function."""

    def test_with_http_proxy(self):
        """Test that http proxy is correctly configured with caching."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"http://": "http://proxy.example.com:8080"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            assert "http://" in mounts
            assert isinstance(mounts["http://"], AsyncCacheTransport)

    def test_with_https_proxy(self):
        """Test that https proxy is correctly configured with caching."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"https://": "https://secure-proxy.example.com:8443"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            assert "https://" in mounts
            assert isinstance(mounts["https://"], AsyncCacheTransport)

    def test_with_all_proxy(self):
        """Test that 'all' proxy fallback is correctly configured with caching."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"all://": "http://fallback-proxy.example.com:8080"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            assert "all://" in mounts
            assert isinstance(mounts["all://"], AsyncCacheTransport)

    def test_with_multiple_proxies(self):
        """Test that multiple proxy protocols are configured together with caching."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={
                "http://": "http://proxy.example.com:8080",
                "https://": "https://secure-proxy.example.com:8443",
                "all://": "http://fallback-proxy.example.com:8080",
            },
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            assert len(mounts) == 3
            assert "http://" in mounts
            assert "https://" in mounts
            assert "all://" in mounts
            assert all(isinstance(t, AsyncCacheTransport) for t in mounts.values())

    def test_with_no_proxies(self):
        """Test that empty dict is returned when no proxies are configured."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            assert mounts == {}

    def test_with_limits(self):
        """Test that limits are passed to the transport factory."""
        config = CompositeCacheConfig()
        limits = Limits(max_connections=20, max_keepalive_connections=10)

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"https://": "https://secure-proxy.example.com:8443"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config, limits=limits)

            assert "https://" in mounts
            assert isinstance(mounts["https://"], AsyncCacheTransport)

    def test_filters_none_proxy_values(self):
        """Test that None proxy values are filtered out."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={
                "http://": "http://proxy.example.com:8080",
                "https://": None,
                "all://": "http://fallback-proxy.example.com:8080",
            },
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            # The function should filter out None values
            assert len(mounts) == 2
            assert "http://" in mounts
            assert "all://" in mounts
            assert "https://" not in mounts


class TestProxyProtocolSupport:
    """Tests to verify all supported proxy protocols are handled correctly."""

    @pytest.mark.parametrize(
        "protocol_key",
        [
            "http://",
            "https://",
            "all://",
        ],
    )
    def test_ratelimiting_retry_all_protocols(self, protocol_key):
        """Test that ratelimiting_retry_proxies supports all protocol keys."""
        config = CompositeConfig()
        proxy_url = "http://proxy.example.com:8080"

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: proxy_url},
        ):
            mounts = ratelimiting_retry_proxies(config)

            assert protocol_key in mounts
            assert isinstance(mounts[protocol_key], AsyncRetryTransport)

    @pytest.mark.parametrize(
        "protocol_key",
        [
            "http://",
            "https://",
            "all://",
        ],
    )
    def test_cached_ratelimiting_retry_all_protocols(self, protocol_key):
        """Test that cached_ratelimiting_retry_proxies supports all protocol keys."""
        config = CompositeCacheConfig()
        proxy_url = "http://proxy.example.com:8080"

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: proxy_url},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            assert protocol_key in mounts
            assert isinstance(mounts[protocol_key], AsyncCacheTransport)
