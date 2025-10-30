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

"""Provides an httpx.AsyncTransport that handles retrying requests on failure."""

from collections.abc import Callable
from logging import getLogger
from types import TracebackType
from typing import Any, Self

import httpx
import tenacity
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    RetryError,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)

from ghga_service_commons.transports.config import RetryTransportConfig

log = getLogger(__name__)


def _default_wait_strategy(config: RetryTransportConfig):
    """TODO"""
    return wait_exponential(max=config.max_retries)


def _default_stop_strategy(config: RetryTransportConfig):
    """TODO"""
    return stop_after_attempt(config.max_retries)


def _log_retry_stats(retry_state: RetryCallState):
    """TODO"""
    if not retry_state.fn:
        log.debug("No wrapped function found in retry state.")
        return

    function_name = retry_state.fn.__qualname__
    attempt_number = retry_state.attempt_number

    retry_stats = {
        "function_name": function_name,
        "attempt_number": attempt_number,
    }

    if time_passed := retry_state.seconds_since_start:
        retry_stats["seconds_elapsed"] = round(time_passed, 3)

    log.info(
        "Retry attempt number %i for function %s.",
        attempt_number,
        function_name,
        extra=retry_stats,
    )


class AsyncRetryTransport(httpx.AsyncBaseTransport):
    """TODO"""

    def __init__(
        self,
        config: RetryTransportConfig,
        transport: httpx.AsyncBaseTransport,
        wait_strategy: Callable[[RetryTransportConfig], Any] = _default_wait_strategy,
        stop_strategy: Callable[[RetryTransportConfig], Any] = _default_stop_strategy,
        stats_logger: Callable[[RetryCallState], Any] = _log_retry_stats,
    ) -> None:
        self._transport = transport
        self._retry_handler = _configure_retry_handler(
            config,
            wait_strategy=wait_strategy,
            stop_strategy=stop_strategy,
            stats_logger=stats_logger,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """
        Handles HTTP requests while also implementing HTTP caching.

        :param request: An HTTP request
        :type request: httpx.Request
        :return: An HTTP response
        :rtype: httpx.Response
        """
        try:
            response = await self._retry_handler(
                fn=self._transport.handle_async_request, request=request
            )
        except RetryError as exc:
            if isinstance(exc.last_attempt, tenacity.Future):
                raise exc.last_attempt.result() from exc
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


def _configure_retry_handler(
    config: RetryTransportConfig,
    wait_strategy: Callable[[RetryTransportConfig], Any],
    stop_strategy: Callable[[RetryTransportConfig], Any],
    stats_logger: Callable[[RetryCallState], Any],
):
    """TODO"""
    return AsyncRetrying(
        reraise=True,
        retry=(
            retry_if_exception_type(
                (
                    httpx.ConnectError,
                    httpx.ConnectTimeout,
                    httpx.TimeoutException,
                )
            )
            | retry_if_result(
                lambda response: response.status_code in config.retry_status_codes
            )
        ),
        stop=stop_strategy(config),
        wait=wait_strategy(config),
        after=stats_logger if config.log_retries else lambda _: None,
    )
