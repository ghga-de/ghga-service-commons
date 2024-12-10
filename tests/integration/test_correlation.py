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
#

"""Test the correlation ID middleware."""

import pytest
from fastapi import FastAPI
from hexkit.correlation import (
    CorrelationIdContextError,
    get_correlation_id,
    set_new_correlation_id,
)

from ghga_service_commons.api.api import (
    CORRELATION_ID_HEADER_NAME,
    ApiConfigBase,
    configure_app,
)
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.http.correlation import attach_correlation_id_to_requests

VALID_CORRELATION_ID = "5deb0e61-5058-4e96-92d4-0529d045832e"
pytestmark = pytest.mark.asyncio()


@pytest.mark.parametrize(
    "preset_id,generate_correlation_id,status_code",
    [
        (VALID_CORRELATION_ID, False, 200),  # happy path
        (VALID_CORRELATION_ID, True, 200),  # also fine
        ("invalid", False, 400),  # error for bad cid header
        ("invalid", True, 400),  # the generate flag is irrelevant
        ("", False, 400),  # No error for empty string cid header
        ("", True, 200),  # empty string with generate flag is fine
    ],
)
async def test_middleware(
    preset_id: str,
    generate_correlation_id: bool,
    status_code: int,
):
    """Test that the InvalidCorrelationIdErrors are returned as 400 status-code responses."""
    app = FastAPI()

    config = ApiConfigBase(generate_correlation_id=generate_correlation_id)
    configure_app(app, config)

    # dummy endpoint to get a 200 status code
    app.get("/")(lambda: "some response")

    async with AsyncTestClient(app=app) as rest_client:
        response = await rest_client.get(
            "/", headers={CORRELATION_ID_HEADER_NAME: preset_id}
        )

        assert response.status_code == status_code


async def test_correlation_id_request_hook():
    """Test to see if the correlation ID is correctly propagated between services.

    Both of the defined endpoints will not raise an error when calling
    `get_correlation_id` because the default `ApiConfigBase` specifies that we
    generate and use a new correlation ID in the API middleware if one is not found in
    the ContextVar.
    """
    some_other_service = FastAPI()
    configure_app(some_other_service, ApiConfigBase())

    # Define a second/final endpoint that returns the current correlation ID
    some_other_service.get("/test")(lambda: get_correlation_id())

    this_service = FastAPI()
    configure_app(this_service, ApiConfigBase())

    @this_service.get("/")
    async def first_endpoint():
        """Call the other endpoint"""
        correlation_id = get_correlation_id()

        async with AsyncTestClient(app=some_other_service) as client:
            # Make a call to the other API and verify that the CID isn't passed on
            response = await client.get("/test")
            assert response.json() != correlation_id

            # Add tracing, and make sure it fails if there's not a CID already set
            attach_correlation_id_to_requests(client, generate_correlation_id=False)

            # Make another call to the other API, passing on the correlation ID
            response = await client.get("/test")
            assert response.json() == correlation_id
        return correlation_id

    # Kick off the request flow
    async with AsyncTestClient(app=this_service) as rest_client:
        attach_correlation_id_to_requests(rest_client, generate_correlation_id=True)
        # Verify that no CID is currently set
        with pytest.raises(CorrelationIdContextError):
            _ = get_correlation_id()

        # Verify that the CID is propagated from here to the final API endpoint and back
        async with set_new_correlation_id() as correlation_id:
            response = await rest_client.get("/")
            assert response.json() == correlation_id


async def test_hook_errors():
    """Assert that we raise an error when making requests when generate_correlation_id
    is False.
    """
    app = FastAPI()

    config = ApiConfigBase()
    configure_app(app, config)

    app.get("/")(lambda: "hello world")

    async with AsyncTestClient(app=app) as client:
        attach_correlation_id_to_requests(client, generate_correlation_id=False)
        with pytest.raises(CorrelationIdContextError):
            await client.get("/")
