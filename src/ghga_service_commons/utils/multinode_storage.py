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
"""Configuration for multiple object storage nodes"""

from hexkit.providers.s3 import S3Config, S3ObjectStorage
from pydantic_settings import BaseSettings


class ObjectStorageNodeConfig(BaseSettings):
    """Configuration for one specific object storage node"""

    bucket: str
    credentials: S3Config


class ObjectStorageConfig(BaseSettings):
    """Configuration for all available object storage nodes"""

    object_storages: dict[str, ObjectStorageNodeConfig]


class ObjectStorages:
    """Constructor to instantiate multiple object storage objects from config"""

    def __init__(self, *, config: ObjectStorageConfig) -> None:
        self._config = config
        self.object_storages: dict[str, S3ObjectStorage] = {}

    def __getitem__(self, key):
        """Lazily create storage configs on first access."""
        if not self.object_storages:
            self._create_object_storages()
        return self.object_storages[key]

    def _create_object_storages(self):
        """Create object storage instances from config"""
        for node_label, node_config in self._config.object_storages.items():
            self.object_storages[node_label] = S3ObjectStorage(
                config=node_config.credentials
            )
