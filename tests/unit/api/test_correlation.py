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
"""Tests for the correlation ID functionality."""

from fastapi import Request

from ghga_service_commons.api.api import (
    CORRELATION_ID_HEADER_NAME,
    set_header_correlation_id,
)


def test_header_update_function():
    """Verify that the header update function works."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
    }

    request = Request(scope=scope)
    set_header_correlation_id(request, "id123")
    assert request.headers.get(CORRELATION_ID_HEADER_NAME) == "id123"
