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

"""Dependency injection logic"""

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager, nullcontext
from typing import Optional

from auth_demo import dummies
from auth_demo.auth.config import DemoAuthContext
from auth_demo.config import Config
from auth_demo.core import Hangout
from auth_demo.ports.hangout import HangoutPort
from auth_demo.router_config import get_configured_app
from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.jwt_auth import JWTAuthContextProvider
from ghga_service_commons.utils.context import asyncnullcontext


@asynccontextmanager
async def prepare_auth_provider(
    *,
    config: Config,
) -> AsyncGenerator[AuthContextProtocol[DemoAuthContext], None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    async with JWTAuthContextProvider.construct(
        config=config, context_class=DemoAuthContext
    ) as auth_provider:
        yield auth_provider


def prepare_auth_with_override(
    *,
    config: Config,
    auth_provider_override: Optional[AuthContextProtocol[DemoAuthContext]] = None,
):
    """Resolve the auth_provider context manager based on config and override (if any)."""

    return (
        asyncnullcontext(auth_provider_override)
        if auth_provider_override
        else prepare_auth_provider(config=config)
    )


@contextmanager
def prepare_core(
    *,
    config: Config,
) -> Generator[HangoutPort, None, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    yield Hangout(config=config)


def prepare_core_with_override(
    *,
    config: Config,
    hangout_override: Optional[HangoutPort] = None,
):
    """Resolve the hangout context manager based on config and override (if any)."""

    return (
        nullcontext(hangout_override)
        if hangout_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    auth_provider_override: Optional[AuthContextProtocol[DemoAuthContext]] = None,
    hangout_override: Optional[HangoutPort] = None,
):
    """Construct and initialize an REST API app along with all its dependencies.

    By default, the core dependencies are automatically prepared but you can also
    provide them using the auth_provider_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_auth_with_override(
        config=config, auth_provider_override=auth_provider_override
    ) as auth_provider:
        with prepare_core_with_override(
            config=config, hangout_override=hangout_override
        ) as hangout:
            app.dependency_overrides[dummies.hangout_port] = lambda: hangout
            app.dependency_overrides[dummies.auth_provider_dummy] = (
                lambda: auth_provider
            )
            yield app
