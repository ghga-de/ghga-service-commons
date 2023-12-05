# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from contextlib import nullcontext

import pytest
from fastapi import FastAPI
from hexkit.correlation import InvalidCorrelationIdError

from ghga_service_commons.api.api import (
    CORRELATION_ID_HEADER_NAME,
    ApiConfigBase,
    configure_app,
)
from ghga_service_commons.api.testing import AsyncTestClient, get_free_port

VALID_CORRELATION_ID = "5deb0e61-5058-4e96-92d4-0529d045832e"


@pytest.mark.parametrize(
    "preset_id,generate_correlation_id,exception",
    [
        (VALID_CORRELATION_ID, False, None),  # happy path
        (VALID_CORRELATION_ID, True, None),  # also fine
        ("invalid", False, InvalidCorrelationIdError),  # error for bad cid header
        ("invalid", True, InvalidCorrelationIdError),  # the generate flag is irrelevant
        ("", False, InvalidCorrelationIdError),  # error for empty string cid header
        ("", True, None),  # empty string with generate flag is fine
    ],
)
@pytest.mark.asyncio
async def test_middleware(
    preset_id: str,
    generate_correlation_id: bool,
    exception,
):
    """Test that the right errors are raised for varying conditions in the middleware."""
    app = FastAPI()

    config = ApiConfigBase(generate_correlation_id=generate_correlation_id)  # type: ignore
    config.port = get_free_port()
    configure_app(app, config)

    async with AsyncTestClient(app=app) as rest_client:
        with pytest.raises(exception) if exception else nullcontext():
            await rest_client.get("/", headers={CORRELATION_ID_HEADER_NAME: preset_id})
