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

"""Context manager utils"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypeVar

__all__ = ["asyncnullcontext"]

YieldValue = TypeVar("YieldValue")


@asynccontextmanager
async def asyncnullcontext(
    yield_value: YieldValue,
) -> AsyncGenerator[YieldValue, None]:
    """Async version of contextlib.nullcontext but with a custom yield value.

    Note that you can just use contextlib.nullcontext instead since Python 3.10.
    """
    yield yield_value
