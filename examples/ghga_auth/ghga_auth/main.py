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

"""Implement global logic for running the application."""

import asyncio

from fastapi import FastAPI
from ghga_auth.config import Config
from ghga_auth.container import Container  # type: ignore
from ghga_auth.router import router

from ghga_service_commons.api import configure_app, run_server
from ghga_service_commons.utils.utc_dates import assert_tz_is_utc


def get_configured_container(config: Config) -> Container:
    """Create and configure the DI container."""
    container = Container()
    container.config.load_config(config)
    return container


def get_configured_app(config: Config) -> FastAPI:
    """Create and configure the FastAPI app"""
    app = FastAPI()
    app.include_router(router)
    configure_app(app, config=config)
    return app


async def configure_and_run_server():
    """Run the HTTP API."""
    config = Config()  # pyright: ignore
    async with get_configured_container(config) as container:
        container.wire(modules=["ghga_auth.router"])
        app = get_configured_app(config)
        await run_server(app=app, config=config)


def run():
    """Main entry point for running the server."""
    assert_tz_is_utc()
    asyncio.run(configure_and_run_server())