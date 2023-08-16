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

"""Tests for the EndpointsHandler class"""

import httpx
import pytest
from pytest_httpx import HTTPXMock, httpx_mock  # noqa: F401

from ghga_service_commons.api.endpoints_handler import (  # noqa: F401
    EndpointsHandler,
    assert_all_responses_were_requested,
)
from ghga_service_commons.httpyexpect.server.exceptions import HttpException
from tests.integration.fixtures.mock_api import app

BASE_URL = "http://localhost"


def http_exception_handler(request: httpx.Request, exc: HttpException):
    """An exception handler that can be attached to the endpoints handler"""
    assert isinstance(exc, HttpException)
    return httpx.Response(
        status_code=exc.status_code,
        json=exc.body.dict(),
    )


def test_non_existent_path(httpx_mock: HTTPXMock):  # noqa: F811
    """Make a request with a path that isn't registered."""
    httpx_mock.add_callback(callback=app.handle_request)
    with pytest.raises(HttpException):
        with httpx.Client(base_url=BASE_URL) as client:
            client.get("/does/not/exist")


def test_url_with_wrong_method(httpx_mock: HTTPXMock):  # noqa: F811
    """Make a request to a url that is registered but with the wrong method"""
    httpx_mock.add_callback(callback=app.handle_request)
    with pytest.raises(HttpException):
        with httpx.Client(base_url=BASE_URL) as client:
            client.patch("/hello")


def test_simplest_get(httpx_mock: HTTPXMock):  # noqa: F811
    """Make sure there's nothing wrong with an endpoint path with no variables"""
    httpx_mock.add_callback(callback=app.handle_request)
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get("/hello")
        assert response is not None
        assert response.json() == {"hello": "world"}


def test_get_one_path_variable(httpx_mock: HTTPXMock):  # noqa: F811
    """Verify that a path terminating with one variable is okay"""
    httpx_mock.add_callback(callback=app.handle_request)

    expected = "beach_ball"

    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get(f"/items/{expected}")
        assert response is not None
        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_get_two_path_variables(httpx_mock: HTTPXMock):  # noqa: F811
    """Make sure the handler can parse paths with more than one variable"""
    httpx_mock.add_callback(callback=app.handle_request)

    expected = ["4", 9]  # pass str number as a sanity check that it stays a str

    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get(f"/items/{expected[0]}/sizes/{expected[1]}")
        assert response is not None
        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_get_with_bad_input(httpx_mock: HTTPXMock):  # noqa: F811
    """Look for error raised with invalid path variables"""
    httpx_mock.add_callback(callback=app.handle_request)

    expected = ["pass", "fail"]

    with pytest.raises(HttpException):
        with httpx.Client(base_url=BASE_URL) as client:
            client.get(f"/items/{expected[0]}/sizes/{expected[1]}")


def test_post_successful(httpx_mock: HTTPXMock):  # noqa: F811
    """Pass a vanilla POST request.

    Makes sure that the request parameter is correctly passed to the endpoint function.
    """
    httpx_mock.add_callback(callback=app.handle_request)

    request_body = {"detail": {"a key": "a value"}}
    expected = request_body["detail"]

    with httpx.Client(base_url=BASE_URL) as client:
        response = client.post("/items", json=request_body)
        assert response is not None

        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_post_failure(httpx_mock: HTTPXMock):  # noqa: F811
    """Cause the endpoint to raise an HttpException.

    Makes sure that endpoint-defined exceptions are passed up as expected when no
    exception handler is specified.
    """
    httpx_mock.add_callback(callback=app.handle_request)

    # cause a failure by omitting the "detail" key that the endpoint looks for
    with pytest.raises(HttpException):
        with httpx.Client(base_url=BASE_URL) as client:
            client.post("/items", json={})


def test_post_failure_with_handler(httpx_mock: HTTPXMock):  # noqa: F811
    """Cause the endpoint to raise an HttpException.

    Makes sure that exceptions are handled with the specified handler.
    """
    app.http_exception_handler = http_exception_handler
    httpx_mock.add_callback(callback=app.handle_request)

    # cause a failure by omitting the "detail" key that the endpoint looks for
    with httpx.Client(base_url=BASE_URL) as client:
        client.post("/items", json={})


def test_path_and_function_mismatch():
    """Make sure that we get an error if path variable names and decorated endpoint
    function parameter names are not identical.
    """

    # create a new EndpointsHandler so we don't modify 'app'
    throwaway = EndpointsHandler()

    with pytest.raises(
        TypeError,
        match="Path variables for path '/dummy/{pram1}' do not match the function it decorates",
    ):

        @throwaway.get("/dummy/{pram1}")
        def dummy(parameter1: int) -> None:
            """Dummy function with missing type-hint info"""


def test_endpoint_missing_typehint():
    """Make sure that we get an error when a registered endpoint lacks type hints"""

    # create a new EndpointsHandler so we don't modify 'app'
    throwaway = EndpointsHandler()

    with pytest.raises(
        TypeError,
        match="Parameter 'parameter1' in 'dummy' is missing a type hint",
    ):

        @throwaway.get("/dummy/{parameter1}")
        def dummy(parameter1) -> None:
            """Dummy function with missing type-hint info"""
