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

"""An inbound port for the demo application."""

from __future__ import annotations

from abc import ABC, abstractmethod


class HangoutPort(ABC):
    """An inbound port for a demo application showing personalized welcome messages."""

    @abstractmethod
    async def reception(self, name: str | None = None) -> str:
        """A method that is not protected at all."""
        ...

    @abstractmethod
    async def lobby(self, name: str) -> str:
        """A method that can be accessed only by authenticated users."""
        ...

    @abstractmethod
    async def lounge(self, name: str) -> str:
        """A method that can be accessed only by VIP users."""
        ...
