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
from typing import Any, Callable, Optional, get_type_hints

import httpx
import pytest
from pydantic import BaseModel


@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    """Whether httpx checks that all registered responses are sent back."""
    # Not all responses must be requested here.
    return False


class MatchableEndpoint(BaseModel):
    """Endpoint data with the url turned into regex string to get parameters in path"""

    url_pattern: str
    endpoint_function: Callable


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

    class NoMatchingUrl(RuntimeError):
        """Raised upon exhausting list of urls under matching method without match"""

        def __init__(self, url: str, method: str) -> None:
            message = (
                f"No mock endpoint registered for url '{url}' and method '{method}'"
            )
            super().__init__(message)

    def __init__(self, exception_handler: Optional[Callable] = None):
        """Initialize the handler.

        Args:
            exception_handler - custom exception handler function
        """

        self.exception_handler: Optional[Callable] = (
            exception_handler if exception_handler else None
        )

        self._methods: dict[str, list[MatchableEndpoint]] = {
            "GET": [],
            "DELETE": [],
            "POST": [],
            "PATCH": [],
            "PUT": [],
        }

    @staticmethod
    def _compile_regex_url(url_pattern: str) -> str:
        """Given a url pattern, compile a regex that matches named groups where specified.

        e.g. "/work-packages/{package_id}" would become "/work-packages/(?P<package_id>[^/]+)"
        And when a request URL like /work-packages/12 is matched against the regex-url above,
        the match object will have a .groupdict() of {"package_id": "12"}
        """

        strip = "{}"
        parameter_pattern = re.compile(r"{.*?}")  # match fewest possible chars inside

        url = re.sub(
            parameter_pattern,
            repl=lambda name: f"(?P<{name.group().strip(strip)}>[^/]+)",
            string=url_pattern,
        )
        return url

    def _add_endpoint(self, method: str, url: str, endpoint_function: Callable) -> None:
        """Process the url and store the resulting endpoint according to method type"""
        url_pattern = self._compile_regex_url(url)
        matchable_endpoint = MatchableEndpoint(
            url_pattern=url_pattern,
            endpoint_function=endpoint_function,
        )

        self._methods[method].append(matchable_endpoint)
        self._methods[method].sort(
            key=lambda endpoint: len(endpoint.url_pattern), reverse=True
        )

    def _base_endpoint_wrapper(
        self, url: str, method: str, endpoint_function: Callable
    ) -> Callable:
        """Used by endpoint decorators to wrap and register the target function"""
        self._add_endpoint(method=method, url=url, endpoint_function=endpoint_function)
        return endpoint_function

    def get(self, url: str) -> Callable:
        """Decorator function to add endpoint to Handler"""

        return partial(self._base_endpoint_wrapper, url, "GET")

    def delete(self, url: str) -> Callable:
        """Decorator function to add endpoint to Handler"""

        return partial(self._base_endpoint_wrapper, url, "DELETE")

    def post(self, url: str) -> Callable:
        """Decorator function to add endpoint to Handler"""

        return partial(self._base_endpoint_wrapper, url, "POST")

    def patch(self, url: str) -> Callable:
        """Decorator function to add endpoint to Handler"""

        return partial(self._base_endpoint_wrapper, url, "PATCH")

    def put(self, url: str) -> Callable:
        """Decorator function to add endpoint to Handler"""

        return partial(self._base_endpoint_wrapper, url, "PUT")

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
                value = parameter_type(value)
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

        raise self.NoMatchingUrl(url=url, method=method)

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
        except BaseException as exc:
            if self.exception_handler is not None:
                return self.exception_handler(exc)
            raise
