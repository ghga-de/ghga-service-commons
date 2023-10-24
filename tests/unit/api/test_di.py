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

"""Testing the di utils from the api subpackage."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from ghga_service_commons.api.di import DependencyDummy

dummy_dependency = DependencyDummy("dummy")


def get_test_app() -> FastAPI:
    """Get a FastAPI app that uses a DependencyDummy."""
    app = FastAPI()

    @app.get("/")
    def get_dummy(dummy: Annotated[str, Depends(dummy_dependency)]):
        """Dummy view function that uses a DependencyDummy."""
        return dummy

    return app


def test_dependency_dummy_no_override():
    """Test that using a DependencyDummy in a FastAPI app raises an error if it is not
    overridden.
    """
    app = get_test_app()
    client = TestClient(app)
    with pytest.raises(RuntimeError, match="'dummy' was not replaced"):
        client.get("/")


def test_dependency_dummy_override():
    """Test that using a DependencyDummy in a FastAPI app does not raise an error if it
    is overridden.
    """
    app = get_test_app()
    app.dependency_overrides[dummy_dependency] = lambda: "dummy"
    client = TestClient(app)
    response = client.get("/")

    assert response.json() == "dummy"
