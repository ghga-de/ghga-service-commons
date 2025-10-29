# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""TODO"""

from pydantic import Field, NonNegativeFloat, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings


class CacheTransportConfig(BaseSettings):
    """TODO"""

    cache_ttl: NonNegativeInt = Field(
        default=60,
        description="Number of seconds after which a stored response is considered stale.",
    )
    cache_capacity: PositiveInt = Field(
        default=128,
        description="Maximum number of entries to store in the cache. Older entries are evicted once this limit is reached.",
    )


class RatelimitingTransportConfig(BaseSettings):
    """TODO"""

    jitter: NonNegativeFloat = Field(
        default=0.001, description="Max amount of jitter to add to each request"
    )
    reset_after: int = Field(
        default=1,
        description="Amount of requests after which the stored delay from a 429 response is ignored again. If set to `None`, it's never forgotten.",
    )


class RetryTransportConfig(BaseSettings):
    """TODO"""

    exponential_backoff_max: NonNegativeInt = Field(
        default=60,
        description="Maximum number of seconds to wait for when using exponential backoff retry strategies.",
    )
    log_retries: bool = Field(
        default=False, description="If true, retry informtion will be logged"
    )
    max_retries: NonNegativeInt = Field(
        default=3, description="Number of times to retry failed API calls."
    )
    retry_status_codes: list[NonNegativeInt] = Field(
        default=[408, 429, 500, 502, 503, 504],
        description="List of status codes that should trigger retrying a request.",
    )


class CompositeConfig(RatelimitingTransportConfig, RetryTransportConfig):
    """TOOD"""


class CompositeCacheConfig(CompositeConfig, CacheTransportConfig):
    """TOOD"""
