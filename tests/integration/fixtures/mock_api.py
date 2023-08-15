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
"""Simple set of endpoints designed to test the EndpointsHandler class"""
import json

import httpx

from ghga_service_commons.api.endpoints_handler import EndpointsHandler
from ghga_service_commons.httpyexpect.server.exceptions import HttpException

app = EndpointsHandler()


@app.get("/hello")
def basic() -> httpx.Response:
    """Basic endpoint"""
    return httpx.Response(status_code=200, json={"hello": "world"})


@app.get(url="/items/{item_name}")
def endpoint(item_name: str) -> httpx.Response:
    """Endpoint with only one path variable"""
    response = httpx.Response(status_code=200, json={"expected": item_name})
    return response


@app.get(url="/items/{item_name}/sizes/{item_size}")
def get_endpoint_2(item_name: str, item_size: int) -> httpx.Response:
    """Endpoint with multiple path variables, defined after simpler one with same start"""
    response = httpx.Response(
        status_code=200, json={"expected": (item_name, item_size)}
    )
    return response


@app.post(url="/items")
def posting_endpoint(request: httpx.Request) -> httpx.Response:
    """Mock endpoint to test getting data from the request body.

    Expects "detail" in body.
    """
    body = json.loads(request.content)

    if "detail" not in body:
        raise HttpException(
            status_code=422,
            exception_id="noDetail",
            description="No detail found in the request body",
            data={},
        )

    response = httpx.Response(status_code=201, json={"expected": body["detail"]})
    return response
