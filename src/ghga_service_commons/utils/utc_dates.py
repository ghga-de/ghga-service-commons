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

"""Utilities for ensuring the consistent use of the UTC timezone."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import AwareDatetime, TypeAdapter
from pydantic.functional_validators import BeforeValidator

__all__ = ["DateTimeUTC", "set_tz_to_utc", "UTC", "assert_tz_is_utc", "now_as_utc"]

UTC = timezone.utc


def assert_tz_is_utc() -> None:
    """Verify that the default timezone is set to UTC.

    Raise a RuntimeError if the default timezone is set differently.
    """
    if datetime.now().astimezone().tzinfo != UTC:
        raise RuntimeError("System must be configured to use UTC.")


def set_tz_to_utc(date: datetime) -> datetime:
    """Force UTC timezone for date."""
    return date.astimezone(UTC) if date.tzinfo is not UTC else date


# A pydantic type for values that should have an UTC timezone.
# This behaves exactly like the normal datetime type, but requires that the value
# has a timezone and converts the timezone to UTC if necessary.
DateTimeUTC = Annotated[
    datetime,
    BeforeValidator(set_tz_to_utc),
    BeforeValidator(TypeAdapter(AwareDatetime).validate_python),
]


def construct_datetime_utc(*args, **kwargs) -> DateTimeUTC:
    """Construct a datetime with UTC timezone."""
    if kwargs.get("tzinfo") is None:
        kwargs["tzinfo"] = UTC
    return DateTimeUTC(*args, **kwargs)


def now_as_utc() -> DateTimeUTC:
    """Return the current datetime with UTC timezone.

    Note: This is different from datetime.utcnow() which has no timezone.
    """
    return DateTimeUTC.now(UTC)
