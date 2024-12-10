# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Tools to enhance traceability of HTTP requests across microservices."""

import logging
from functools import partial
from typing import Union

import httpx
from hexkit.correlation import (
    CorrelationIdContextError,
    get_correlation_id,
    new_correlation_id,
)

CORRELATION_ID_HEADER_NAME = "X-Request-Id"
log = logging.getLogger(__name__)


def add_correlation_id_to_request(request, generate_correlation_id: bool):
    """Include the correlation ID in the request header so it is propagated.

    If the correlation ID isn't set, one will be generated if `generate_correlation_id`
    is set. Otherwise, an error will be raised.

    Raises:
        CorrelationIdContextError: when the correlation ID ContextVar is not set.
        InvalidCorrelationIdError: when the correlation ID is invalid.
    """
    try:
        correlation_id = get_correlation_id()
    except CorrelationIdContextError:
        if generate_correlation_id:
            correlation_id = new_correlation_id()
        else:
            raise
    request.headers[CORRELATION_ID_HEADER_NAME] = correlation_id


async def add_correlation_id_to_request_async(request, generate_correlation_id: bool):
    """Async version of `add_correlation_id_to_request`"""
    add_correlation_id_to_request(request, generate_correlation_id)


def attach_correlation_id_to_requests(
    client: Union[httpx.Client, httpx.AsyncClient],
    *,
    generate_correlation_id: bool,
):
    """Add an event hook to an httpx Client that includes the correlation ID header."""
    if "request" not in client.event_hooks:
        client.event_hooks["request"] = []

    event_hook = partial(
        add_correlation_id_to_request,
        generate_correlation_id=generate_correlation_id,
    )

    if isinstance(client, httpx.AsyncClient):
        event_hook = partial(
            add_correlation_id_to_request_async,
            generate_correlation_id=generate_correlation_id,
        )
    client.event_hooks["request"].append(event_hook)
