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

"""Provides factories for different flavors of httpx.AsyncHTTPTransport."""

from hishel import AsyncCacheTransport, AsyncInMemoryStorage
from httpx import AsyncHTTPTransport, Limits

from .config import CompositeCacheConfig, CompositeConfig
from .ratelimiting import AsyncRatelimitingTransport
from .retry import AsyncRetryTransport


class CompositeTransportFactory:
    """TODO"""

    @classmethod
    def _create_common_transport_layers(
        cls, config: CompositeConfig, limits: Limits | None = None
    ):
        """TODO"""
        base_transport = (
            AsyncHTTPTransport(limits=limits) if limits else AsyncHTTPTransport()
        )
        ratelimiting_transport = AsyncRatelimitingTransport(
            config=config, transport=base_transport
        )
        retry_transport = AsyncRetryTransport(
            config=config, transport=ratelimiting_transport
        )
        return retry_transport

    @classmethod
    def create_ratelimiting_retry_transport(
        cls, config: CompositeConfig, limits: Limits | None = None
    ) -> AsyncRetryTransport:
        """TODO"""
        return cls._create_common_transport_layers(config)

    @classmethod
    def create_ratelimiting_retry_transport_with_cache(
        cls, config: CompositeCacheConfig, limits: Limits | None = None
    ) -> AsyncCacheTransport:
        """TODO"""
        storage = AsyncInMemoryStorage(ttl=config.cache_ttl)
        retry_transport = cls._create_common_transport_layers(config)
        return AsyncCacheTransport(transport=retry_transport, storage=storage)
