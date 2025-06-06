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

"""App specific policies using the AuthContext provider with FastAPI.

See the router.py module for how to use these policies in REST endpoints.
"""

from typing import Annotated, Optional

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_demo.auth.config import DemoAuthContext
from auth_demo.dummies import AuthProviderDummy
from ghga_service_commons.auth.policies import (
    get_auth_context_using_credentials,
    require_auth_context_using_credentials,
)

__all__ = ["OptionalAuthContext", "UserAuthContext", "VipAuthContext"]


async def get_auth_context(
    auth_provider: AuthProviderDummy,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> Optional[DemoAuthContext]:
    """Get an authentication and authorization context using FastAPI."""
    context = await get_auth_context_using_credentials(credentials, auth_provider)
    return context  # workaround mypy issue #12156


async def require_auth_context(
    auth_provider: AuthProviderDummy,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> DemoAuthContext:
    """Require an authentication and authorization context using FastAPI."""
    return await require_auth_context_using_credentials(credentials, auth_provider)


def check_vip(context: DemoAuthContext) -> bool:
    """Check if the given auth context belongs to a VIP."""
    return context.is_vip


async def require_vip_context(
    auth_provider: AuthProviderDummy,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> DemoAuthContext:
    """Require a VIP authentication and authorization context using FastAPI."""
    return await require_auth_context_using_credentials(
        credentials, auth_provider, check_vip
    )


# policy for getting an auth token without requiring its existence
OptionalAuthContext = Annotated[Optional[DemoAuthContext], Security(get_auth_context)]

# policy for requiring and getting a user auth token
UserAuthContext = Annotated[DemoAuthContext, Security(require_auth_context)]

# policy for requiring and getting a VIP user auth token
VipAuthContext = Annotated[DemoAuthContext, Security(require_vip_context)]
