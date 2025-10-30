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

"""Provides an httpx.AsyncTransport that handles rate limiting responses."""

import random
import time
from logging import getLogger
from types import TracebackType
from typing import Self

import httpx

from ghga_service_commons.transports.config import RatelimitingTransportConfig

log = getLogger(__name__)


class AsyncRatelimitingTransport(httpx.AsyncBaseTransport):
    """TODO"""

    def __init__(
        self, config: RatelimitingTransportConfig, transport: httpx.AsyncBaseTransport
    ) -> None:
        self._jitter = config.jitter
        self._transport = transport
        self._num_requests = 0
        self._reset_after: int = config.reset_after
        self._last_request_time = time.monotonic()
        self._wait_time: float = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """
        Handles HTTP requests while also implementing HTTP caching.

        :param request: An HTTP request
        :type request: httpx.Request
        :return: An HTTP response
        :rtype: httpx.Response
        """
        # Caculate seconds since the last request has been fired and corresponding wait time
        time_elapsed = time.monotonic() - self._last_request_time
        remaining_wait = max(0, self._wait_time - time_elapsed)
        log.info("Configured base wait time: %.3f s", self._wait_time)
        log.info(
            "Time elapsed since last request:%.3f.\nWaiting for at least %.3f s",
            time_elapsed,
            remaining_wait,
        )

        # Add jitter to both cases and sleep
        if remaining_wait < self._jitter:
            time.sleep(random.uniform(remaining_wait, self._jitter))  # noqa: S311
        else:
            time.sleep(
                random.uniform(remaining_wait, remaining_wait + self._jitter)  # noqa: S311
            )

        # Delegate call and update timestamp
        response = await self._transport.handle_async_request(request=request)
        self._last_request_time = time.monotonic()
        log.info("Last request fired at: %.3f", self._last_request_time)

        # Update state
        self._num_requests += 1
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                self._wait_time = float(retry_after)
                log.info("Received retry after response: %.3f s", self._wait_time)
            else:
                log.warning(
                    "Retry-After header not present in 429 response, using fallback instead."
                )
                self._wait_time = self._jitter
            self._num_requests = 0
        elif self._reset_after and self._reset_after <= self._num_requests:
            self._wait_time = 0
            self._num_requests = 0

        return response

    async def aclose(self) -> None:  # noqa: D102
        await self._transport.aclose()

    async def __aenter__(self) -> Self:  # noqa: D105
        return self

    async def __aexit__(  # noqa: D105
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self.aclose()
