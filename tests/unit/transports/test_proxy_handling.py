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

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from hishel import AsyncCacheTransport

from ghga_service_commons.transports.config import CompositeCacheConfig, CompositeConfig
from ghga_service_commons.transports.proxy_handling import (
    cached_ratelimiting_retry_proxies,
    ratelimiting_retry_proxies,
)
from ghga_service_commons.transports.retry import AsyncRetryTransport


class TestRateLimitingRetryProxies:
    """Tests for ratelimiting_retry_proxies function."""

    @pytest.mark.parametrize(
        "protocol_key,proxy_url",
        [
            ("http://", "http://proxy.example.com:8080"),
            ("https://", "https://secure-proxy.example.com:8443"),
            ("all://", "http://fallback-proxy.example.com:8080"),
        ],
    )
    def test_with_single_proxy(self, protocol_key, proxy_url):
        """Test that proxy is correctly configured for each protocol."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: proxy_url},
        ):
            mounts = ratelimiting_retry_proxies(config)

            assert protocol_key in mounts
            assert isinstance(mounts[protocol_key], AsyncRetryTransport)

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

    @pytest.mark.parametrize(
        "protocol_key,proxy_url",
        [
            ("http://", "http://proxy.example.com:8080"),
            ("https://", "https://secure-proxy.example.com:8443"),
            ("all://", "http://fallback-proxy.example.com:8080"),
        ],
    )
    def test_with_single_proxy(self, protocol_key, proxy_url):
        """Test that proxy is correctly configured with caching for each protocol."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: proxy_url},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            assert protocol_key in mounts
            assert isinstance(mounts[protocol_key], AsyncCacheTransport)

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


class TestRateLimitingRetryProxiesIntegration:
    """Integration tests using mounts with httpx.AsyncClient."""

    @pytest.mark.parametrize(
        "protocol_key,proxy_url,request_url,status_code,response_content",
        [
            (
                "http://",
                "http://proxy.example.com:8080",
                "http://example.com/test",
                200,
                b'{"result": "success"}',
            ),
            (
                "https://",
                "https://secure-proxy.example.com:8443",
                "https://secure.example.com/api",
                200,
                b'{"secure": true}',
            ),
            (
                "all://",
                "http://fallback-proxy.example.com:8080",
                "ftp://files.example.com/data",
                204,
                None,
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_ratelimiting_retry_with_proxy_mount(
        self, protocol_key, proxy_url, request_url, status_code, response_content
    ):
        """Test that ratelimiting_retry_proxies mounts work with AsyncClient."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: proxy_url},
        ):
            mounts = ratelimiting_retry_proxies(config)

            mock_response = httpx.Response(
                status_code=status_code,
                content=response_content or b"",
            )

            with patch.object(
                mounts[protocol_key],
                "handle_async_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    response = await client.get(request_url)

                    assert response.status_code == status_code
                    if response_content:
                        assert response.json() is not None
                    mounts[protocol_key].handle_async_request.assert_called()

    @pytest.mark.asyncio
    async def test_ratelimiting_retry_with_multiple_proxies_mount(self):
        """Test that multiple proxy mounts work correctly with AsyncClient."""
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

            http_response = httpx.Response(
                status_code=200,
                content=b'{"protocol": "http"}',
            )
            https_response = httpx.Response(
                status_code=200,
                content=b'{"protocol": "https"}',
            )

            # Mock transports for different protocols
            with (
                patch.object(
                    mounts["http://"],
                    "handle_async_request",
                    new_callable=AsyncMock,
                    return_value=http_response,
                ),
                patch.object(
                    mounts["https://"],
                    "handle_async_request",
                    new_callable=AsyncMock,
                    return_value=https_response,
                ),
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    http_resp = await client.get("http://example.com")
                    https_resp = await client.get("https://example.com")

                    assert http_resp.status_code == 200
                    assert http_resp.json() == {"protocol": "http"}
                    assert https_resp.status_code == 200
                    assert https_resp.json() == {"protocol": "https"}


class TestCachedRateLimitingRetryProxiesIntegration:
    """Integration tests using cached mounts with httpx.AsyncClient."""

    @pytest.mark.parametrize(
        "protocol_key,proxy_url,request_url,status_code,response_content",
        [
            (
                "http://",
                "http://proxy.example.com:8080",
                "http://example.com/data",
                200,
                b'{"cached": false}',
            ),
            (
                "https://",
                "https://secure-proxy.example.com:8443",
                "https://api.example.com/v1/data",
                200,
                b'{"cached": true}',
            ),
            (
                "all://",
                "http://fallback-proxy.example.com:8080",
                "gopher://files.example.com/resource",
                201,
                b'{"id": 123}',
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_cached_ratelimiting_retry_with_proxy_mount(
        self, protocol_key, proxy_url, request_url, status_code, response_content
    ):
        """Test that cached_ratelimiting_retry_proxies mounts work with AsyncClient."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: proxy_url},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            mock_response = httpx.Response(
                status_code=status_code,
                content=response_content,
            )

            with patch.object(
                mounts[protocol_key],
                "handle_async_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    response = await client.post(request_url)

                    assert response.status_code == status_code
                    assert response.json() is not None
                    mounts[protocol_key].handle_async_request.assert_called()

    @pytest.mark.asyncio
    async def test_cached_ratelimiting_retry_with_multiple_proxies_mount(self):
        """Test that multiple cached proxy mounts work correctly with AsyncClient."""
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

            http_response = httpx.Response(
                status_code=200,
                content=b'{"protocol": "http", "cached": true}',
            )
            https_response = httpx.Response(
                status_code=200,
                content=b'{"protocol": "https", "cached": true}',
            )
            all_response = httpx.Response(
                status_code=200,
                content=b'{"protocol": "fallback", "cached": true}',
            )

            # Mock transports for different protocols
            with (
                patch.object(
                    mounts["http://"],
                    "handle_async_request",
                    new_callable=AsyncMock,
                    return_value=http_response,
                ),
                patch.object(
                    mounts["https://"],
                    "handle_async_request",
                    new_callable=AsyncMock,
                    return_value=https_response,
                ),
                patch.object(
                    mounts["all://"],
                    "handle_async_request",
                    new_callable=AsyncMock,
                    return_value=all_response,
                ),
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    http_resp = await client.get("http://example.com")
                    https_resp = await client.get("https://example.com")
                    all_resp = await client.get("custom://example.com")

                    assert http_resp.status_code == 200
                    assert http_resp.json()["protocol"] == "http"
                    assert https_resp.status_code == 200
                    assert https_resp.json()["protocol"] == "https"
                    assert all_resp.status_code == 200
                    assert all_resp.json()["protocol"] == "fallback"


class TestTransportTypeVerification:
    """Verify transport types are correctly used in the mounts."""

    @pytest.mark.parametrize(
        "protocol_key,proxy_url,config_class,expected_transport",
        [
            (
                "http://",
                "http://proxy.example.com:8080",
                CompositeConfig,
                AsyncRetryTransport,
            ),
            (
                "https://",
                "https://secure-proxy.example.com:8443",
                CompositeConfig,
                AsyncRetryTransport,
            ),
            (
                "all://",
                "http://fallback-proxy.example.com:8080",
                CompositeConfig,
                AsyncRetryTransport,
            ),
            (
                "http://",
                "http://proxy.example.com:8080",
                CompositeCacheConfig,
                AsyncCacheTransport,
            ),
            (
                "https://",
                "https://secure-proxy.example.com:8443",
                CompositeCacheConfig,
                AsyncCacheTransport,
            ),
            (
                "all://",
                "http://fallback-proxy.example.com:8080",
                CompositeCacheConfig,
                AsyncCacheTransport,
            ),
        ],
    )
    def test_transport_type_verification(
        self, protocol_key, proxy_url, config_class, expected_transport
    ):
        """Verify transport types are correctly used for all protocol/config combinations."""
        config = config_class()
        proxy_function = (
            ratelimiting_retry_proxies
            if config_class == CompositeConfig
            else cached_ratelimiting_retry_proxies
        )

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: proxy_url},
        ):
            mounts = proxy_function(config)

            transport = mounts[protocol_key]
            assert isinstance(transport, expected_transport)
            # Verify it has the underlying transport layers
            assert hasattr(transport, "_transport")
            assert transport._transport is not None
