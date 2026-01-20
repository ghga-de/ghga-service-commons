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

    @pytest.mark.asyncio
    async def test_ratelimiting_retry_with_http_proxy_mount(self):
        """Test that ratelimiting_retry_proxies mounts work with AsyncClient for HTTP."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"http://": "http://proxy.example.com:8080"},
        ):
            mounts = ratelimiting_retry_proxies(config)

            # Create a mock response
            mock_response = httpx.Response(
                status_code=200,
                headers={"content-type": "application/json"},
                content=b'{"result": "success"}',
            )

            # Patch the transport's handle_async_request to verify it's called
            with patch.object(
                mounts["http://"],
                "handle_async_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    response = await client.get("http://example.com/test")

                    assert response.status_code == 200
                    assert response.json() == {"result": "success"}
                    # Verify the transport was used
                    mounts["http://"].handle_async_request.assert_called()

    @pytest.mark.asyncio
    async def test_ratelimiting_retry_with_https_proxy_mount(self):
        """Test that ratelimiting_retry_proxies mounts work with AsyncClient for HTTPS."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"https://": "https://secure-proxy.example.com:8443"},
        ):
            mounts = ratelimiting_retry_proxies(config)

            mock_response = httpx.Response(
                status_code=200,
                headers={"content-type": "application/json"},
                content=b'{"secure": true}',
            )

            with patch.object(
                mounts["https://"],
                "handle_async_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    response = await client.get("https://secure.example.com/api")

                    assert response.status_code == 200
                    assert response.json() == {"secure": True}
                    mounts["https://"].handle_async_request.assert_called()

    @pytest.mark.asyncio
    async def test_ratelimiting_retry_with_all_proxy_mount(self):
        """Test that ratelimiting_retry_proxies mounts work with AsyncClient for all protocol."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"all://": "http://fallback-proxy.example.com:8080"},
        ):
            mounts = ratelimiting_retry_proxies(config)

            mock_response = httpx.Response(
                status_code=204,
                headers={"x-fallback": "true"},
            )

            with patch.object(
                mounts["all://"],
                "handle_async_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    response = await client.get("ftp://files.example.com/data")

                    assert response.status_code == 204
                    assert response.headers["x-fallback"] == "true"
                    mounts["all://"].handle_async_request.assert_called()

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

    @pytest.mark.asyncio
    async def test_cached_ratelimiting_retry_with_http_proxy_mount(self):
        """Test that cached_ratelimiting_retry_proxies mounts work with AsyncClient for HTTP."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"http://": "http://proxy.example.com:8080"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            mock_response = httpx.Response(
                status_code=200,
                headers={"content-type": "application/json"},
                content=b'{"cached": false}',
            )

            with patch.object(
                mounts["http://"],
                "handle_async_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    response = await client.get("http://example.com/data")

                    assert response.status_code == 200
                    assert response.json() == {"cached": False}
                    mounts["http://"].handle_async_request.assert_called()

    @pytest.mark.asyncio
    async def test_cached_ratelimiting_retry_with_https_proxy_mount(self):
        """Test that cached_ratelimiting_retry_proxies mounts work with AsyncClient for HTTPS."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"https://": "https://secure-proxy.example.com:8443"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            mock_response = httpx.Response(
                status_code=200,
                headers={"cache-control": "max-age=3600"},
                content=b'{"cached": true}',
            )

            with patch.object(
                mounts["https://"],
                "handle_async_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    response = await client.get("https://api.example.com/v1/data")

                    assert response.status_code == 200
                    assert response.json() == {"cached": True}
                    mounts["https://"].handle_async_request.assert_called()

    @pytest.mark.asyncio
    async def test_cached_ratelimiting_retry_with_all_proxy_mount(self):
        """Test that cached_ratelimiting_retry_proxies mounts work with AsyncClient for all protocol."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"all://": "http://fallback-proxy.example.com:8080"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            mock_response = httpx.Response(
                status_code=201,
                headers={"x-created": "true"},
                content=b'{"id": 123}',
            )

            with patch.object(
                mounts["all://"],
                "handle_async_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                async with httpx.AsyncClient(mounts=mounts) as client:
                    response = await client.post("gopher://files.example.com/resource")

                    assert response.status_code == 201
                    assert response.json() == {"id": 123}
                    mounts["all://"].handle_async_request.assert_called()

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

    def test_ratelimiting_retry_transport_hierarchy_http(self):
        """Verify AsyncRetryTransport hierarchy for HTTP proxy."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"http://": "http://proxy.example.com:8080"},
        ):
            mounts = ratelimiting_retry_proxies(config)

            transport = mounts["http://"]
            assert isinstance(transport, AsyncRetryTransport)
            # Verify it has the underlying transport layers
            assert hasattr(transport, "_transport")
            assert transport._transport is not None

    def test_cached_ratelimiting_retry_transport_hierarchy_https(self):
        """Verify AsyncCacheTransport hierarchy for HTTPS proxy."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={"https://": "https://secure-proxy.example.com:8443"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            transport = mounts["https://"]
            assert isinstance(transport, AsyncCacheTransport)
            # Verify it has underlying transport
            assert hasattr(transport, "_transport")
            assert transport._transport is not None

    @pytest.mark.parametrize(
        "protocol_key",
        [
            "http://",
            "https://",
            "all://",
        ],
    )
    def test_ratelimiting_retry_transport_types_for_all_protocols(self, protocol_key):
        """Verify all protocols use AsyncRetryTransport in ratelimiting_retry_proxies."""
        config = CompositeConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: "http://proxy.example.com:8080"},
        ):
            mounts = ratelimiting_retry_proxies(config)

            transport = mounts[protocol_key]
            assert isinstance(transport, AsyncRetryTransport)

    @pytest.mark.parametrize(
        "protocol_key",
        [
            "http://",
            "https://",
            "all://",
        ],
    )
    def test_cached_ratelimiting_retry_transport_types_for_all_protocols(
        self, protocol_key
    ):
        """Verify all protocols use AsyncCacheTransport in cached_ratelimiting_retry_proxies."""
        config = CompositeCacheConfig()

        with patch(
            "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
            return_value={protocol_key: "http://proxy.example.com:8080"},
        ):
            mounts = cached_ratelimiting_retry_proxies(config)

            transport = mounts[protocol_key]
            assert isinstance(transport, AsyncCacheTransport)
