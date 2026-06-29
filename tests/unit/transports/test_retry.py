# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Tests for the retry transport, focusing on connection handling across retries."""

from unittest.mock import AsyncMock

import httpx
import pytest
from tenacity import RetryError

from ghga_service_commons.transports.config import RetryTransportConfig
from ghga_service_commons.transports.retry import AsyncRetryTransport

# 429 responses without a `Should-Wait` header use a zero wait, keeping the tests fast.
RETRYABLE_STATUS_CODE = 429


def _tracked_response(status_code: int) -> httpx.Response:
    """Build a response whose ``aclose`` is wrapped so it can be asserted on."""
    response = httpx.Response(status_code=status_code)
    response.aclose = AsyncMock(wraps=response.aclose)  # type: ignore[method-assign]
    return response


def _retry_transport(responses: list[httpx.Response]) -> AsyncRetryTransport:
    """Wrap a mock transport that yields the given responses in turn."""
    transport = AsyncMock(spec=httpx.AsyncBaseTransport)
    transport.handle_async_request = AsyncMock(side_effect=responses)
    return AsyncRetryTransport(
        config=RetryTransportConfig(client_num_retries=len(responses)),
        transport=transport,
    )


@pytest.mark.asyncio
async def test_retried_responses_are_closed():
    """Ensure discarded responses from retried attempts are closed, the returned one is not.

    Each retried response holds a connection from the pool until it is read or closed,
    so all but the final, returned response must be closed to avoid leaking connections.
    """
    responses = [
        _tracked_response(RETRYABLE_STATUS_CODE),
        _tracked_response(RETRYABLE_STATUS_CODE),
        _tracked_response(httpx.codes.OK),
    ]
    retry_transport = _retry_transport(responses)

    result = await retry_transport.handle_async_request(
        httpx.Request("GET", "http://test")
    )

    *retried, returned = responses
    assert result is returned
    assert all(response.aclose.called for response in retried)
    assert not returned.aclose.called


@pytest.mark.asyncio
async def test_exhausted_retries_close_last_response():
    """When retries are exhausted, the final unreturned response is closed too.

    A result-based exhaustion raises ``RetryError`` instead of returning the response,
    so that last response would also leak its connection if it were not closed.
    """
    responses = [_tracked_response(RETRYABLE_STATUS_CODE) for _ in range(3)]
    retry_transport = _retry_transport(responses)

    with pytest.raises(RetryError):
        await retry_transport.handle_async_request(httpx.Request("GET", "http://test"))

    assert all(response.aclose.called for response in responses)
