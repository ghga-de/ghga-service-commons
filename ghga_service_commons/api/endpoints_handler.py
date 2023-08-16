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
"""A class for mocking API endpoints when testing with the httpx_mock fixture"""

import re
from functools import partial
from inspect import signature
from typing import Any, Callable, Optional, get_type_hints

import httpx
import pytest
from pydantic import BaseModel

from ghga_service_commons.httpyexpect.server.exceptions import HttpException


def _compile_regex_url(path: str) -> str:
    """Given a path, compile a url pattern regex that matches named groups where specified.

    e.g. "/work-packages/{package_id}" would become "/work-packages/(?P<package_id>[^/]+)$"
    And when a request URL like /work-packages/12 is matched against the regex-url above,
    the match object will have a .groupdict() of {"package_id": "12"}

    This function is not intended to be used outside the module.
    """

    brackets_to_strip = "{}"
    parameter_pattern = re.compile(r"{.*?}")  # match fewest possible chars inside

    url = re.sub(
        parameter_pattern,
        repl=lambda name: f"(?P<{name.group().strip(brackets_to_strip)}>[^/]+)",
        string=path,
    )
    return f"{url}$"


def _get_signature_info(endpoint_function: Callable) -> dict[str, Any]:
    """Retrieves the typed parameter info from function signature minus return type.

    This function is not intended to be used outside the module.
    """
    signature_parameters: dict[str, Any] = get_type_hints(endpoint_function)
    if "return" in signature_parameters:
        signature_parameters.pop("return")
    return signature_parameters


@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    """Whether httpx checks that all registered responses are sent back."""
    # Not all responses must be requested here.
    return False


class MatchableEndpoint(BaseModel):
    """Endpoint data with the url turned into regex string to get parameters in path"""

    url_pattern: str
    endpoint_function: Callable
    signature_parameters: dict[str, Any]


class EndpointsHandler:
    """
    A class used to register mock endpoints with decorators similar to FastAPI.

    Tag endpoint functions with EndpointHandler.[method]("/some/url-with/{variables}").
    The regex compiler function will turn the url specified in the decorator function
    into a regex string capable of capturing the variables in the url (curly brackets)
    with named groups. That in turn enables linking the named path variables to the
    variables in the endpoint function itself.

    Note that the only parameter types allowed in the endpoint functions are primitives
    that can be stored in the url string: int, float, str, bool, None, and complex.
    The one exception is "request", which will be passed in automatically if specified.
    """

    def __init__(
        self,
        http_exception_handler: Optional[
            Callable[[httpx.Request, HttpException], Any]
        ] = None,
    ):
        """Initialize the EndpointsHandler with an optional HttpException handler.

        Args:
            http_exception_handler:
                custom exception handler function that takes the request and exception
                as arguments, in that order.
        """

        self.http_exception_handler: Optional[
            Callable[[httpx.Request, HttpException], Any]
        ] = (http_exception_handler if http_exception_handler else None)

        self._methods: dict[str, list[MatchableEndpoint]] = {
            "GET": [],
            "DELETE": [],
            "POST": [],
            "PATCH": [],
            "PUT": [],
        }

    @staticmethod
    def _ensure_all_parameters_are_typed(
        endpoint_function: Callable, signature_parameters: dict[str, Any]
    ):
        """Verify that all the endpoint function parameters are typed.

        This will not apply to the request parameter because we don't perform any
        type conversion on that.

        Args:
            endpoint_function: the function associated with the endpoint.
            signature_parameters:
                A dict containing type information for the endpoint function's parameters.

        Raises:
            TypeError: When one or more parameters are missing type-hint information.
        """

        all_parameters = signature(endpoint_function).parameters

        for parameter in all_parameters:
            if parameter not in signature_parameters:
                raise TypeError(
                    f"Parameter '{parameter}' in '{endpoint_function.__name__}' is "
                    + "missing a type hint"
                )

    def _add_endpoint(
        self, method: str, path: str, endpoint_function: Callable
    ) -> None:
        """Register an endpoint.

        Process the `path` and store the resulting endpoint according to `method`.
        """
        signature_parameters: dict[str, Any] = _get_signature_info(endpoint_function)

        url_pattern = _compile_regex_url(path)

        matchable_endpoint = MatchableEndpoint(
            url_pattern=url_pattern,
            endpoint_function=endpoint_function,
            signature_parameters=signature_parameters,
        )

        self._methods[method].append(matchable_endpoint)

    def _validate_endpoint(self, endpoint_function: Callable):
        """Perform validation on the endpoint before adding it

        Verify that all the `endpoint_function` parameters are typed.
        """
        signature_parameters: dict[str, Any] = _get_signature_info(endpoint_function)
        self._ensure_all_parameters_are_typed(endpoint_function, signature_parameters)

    def _base_endpoint_wrapper(
        self, path: str, method: str, endpoint_function: Callable
    ) -> Callable:
        """Used by endpoint decorators to validate and register the target function"""
        self._validate_endpoint(endpoint_function)
        self._add_endpoint(
            method=method, path=path, endpoint_function=endpoint_function
        )
        return endpoint_function

    def get(self, path: str) -> Callable:
        """Decorator function to add endpoint to Handler with `GET` method"""

        return partial(self._base_endpoint_wrapper, path, "GET")

    def delete(self, path: str) -> Callable:
        """Decorator function to add endpoint to Handler with `DELETE` method"""

        return partial(self._base_endpoint_wrapper, path, "DELETE")

    def post(self, path: str) -> Callable:
        """Decorator function to add endpoint to Handler with `POST` method"""

        return partial(self._base_endpoint_wrapper, path, "POST")

    def patch(self, path: str) -> Callable:
        """Decorator function to add endpoint to Handler with `PATCH` method"""

        return partial(self._base_endpoint_wrapper, path, "PATCH")

    def put(self, path: str) -> Callable:
        """Decorator function to add endpoint to Handler with `PUT` method"""

        return partial(self._base_endpoint_wrapper, path, "PUT")

    @staticmethod
    def _convert_parameter_types(
        endpoint_function: Callable,
        string_parameters: dict[str, str],
        request: httpx.Request,
    ) -> dict[str, Any]:
        """Get type info for function parameters.

        Since the values parsed from the URL
        are still in string format, cast them to the types specified in the signature.
        If the request is needed, include that in the returned parameters.
        """

        # Get the parameter information from the endpoint function signature
        signature_parameters = get_type_hints(endpoint_function)

        # type-cast based on type-hinting info
        typed_parameters: dict[str, Any] = {}
        for parameter_name, value in string_parameters.items():
            try:
                parameter_type = signature_parameters[parameter_name]

            # all parameters should be typed, raise exception otherwise
            except KeyError as err:
                raise TypeError(
                    f"Parameter '{parameter_name}' in function "
                    + f"'{endpoint_function.__name__}' is missing type information!"
                ) from err

            if parameter_type is not str:
                try:
                    value = parameter_type(value)
                except ValueError as err:
                    raise HttpException(
                        status_code=422,
                        exception_id="malformedUrl",
                        description=(
                            f"Unable to cast '{value}' to {parameter_type} for "
                            + f"path '{request.url.path}'"
                        ),
                        data={
                            "value": value,
                            "parameter_type": parameter_type,
                            "path": request.url.path,
                        },
                    ) from err
            typed_parameters[parameter_name] = value

        # include request itself if needed (e.g. for header or auth info),
        if "request" in signature_parameters:
            typed_parameters["request"] = request

        return typed_parameters

    def _get_function_and_parameters(
        self, url: str, method: str
    ) -> tuple[Callable, dict[str, str]]:
        """Iterate through the registered endpoints for the given method.

        For each registered endpoint, try to match the request's url to the endpoint pattern.
        Upon matching, return the function and parsed variables from the url (if applicable).
        """
        for endpoint in self._methods[method]:
            matched_url = re.search(endpoint.url_pattern, url)
            if matched_url:
                endpoint_function = endpoint.endpoint_function

                # return endpoint function with url-string parameters
                return (
                    endpoint_function,
                    matched_url.groupdict(),
                )

        raise HttpException(
            status_code=404,
            exception_id="pageNotFound",
            description=f"No registered path found for url '{url}' and method '{method}'",
            data={"url": url, "method": method},
        )

    def _build_loaded_endpoint_function(self, request: httpx.Request) -> partial:
        """Match a request to the correct endpoint, build typed parameter dictionary,
        and return loaded partial function.
        """

        # get endpoint function and the parsed string parameters from the url
        endpoint_function, string_parameters = self._get_function_and_parameters(
            url=str(request.url), method=request.method
        )

        # convert string parameters into the types specified in function signature
        typed_parameters = self._convert_parameter_types(
            endpoint_function=endpoint_function,
            string_parameters=string_parameters,
            request=request,
        )

        # return function with the typed parameters
        return partial(endpoint_function, **typed_parameters)

    def handle_request(self, request: httpx.Request):
        """Route intercepted request to the registered endpoint and return response

        If using this with httpx_mock, then this function should be the callback.
        e.g.: httpx_mock.add_callback(callback=endpoints_handler.handle_request)"""
        try:
            endpoint_function = self._build_loaded_endpoint_function(request)
            return endpoint_function()
        except HttpException as exc:
            if self.http_exception_handler is not None:
                return self.http_exception_handler(request, exc)
            raise
