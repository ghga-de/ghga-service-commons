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

"""Helper functions for Crypt4GH compliant encryption."""

import base64

from nacl.public import PrivateKey, PublicKey, SealedBox

__all__ = [
    "generate_key_pair",
    "encode_private_key",
    "encode_public_key",
    "decode_private_key",
    "decode_public_key",
    "decrypt",
    "encrypt",
]


def generate_key_pair() -> PrivateKey:
    """Generate a Curve25519 key pair (as used in Crypt4GH)."""
    return PrivateKey.generate()


def encode_private_key(key_pair: PrivateKey) -> str:
    """Get base64 encoded private key from the given key pair."""
    return base64.b64encode(bytes(key_pair)).decode("ascii")


def encode_public_key(key_pair: PrivateKey) -> str:
    """Get base64 encoded public key from the given key pair."""
    return base64.b64encode(bytes(key_pair.public_key)).decode("ascii")


def decode_private_key(key: str) -> PrivateKey:
    """Get the given base64 encoded private key as a PrivateKey object.

    This function can be used to check whether this is a valid base64 encoded string
    of the right length; it raises a ValueError if this is not the case.
    """
    try:
        decoded_key = base64.b64decode(key)
    except base64.binascii.Error as error:  # type: ignore
        raise ValueError(str(error)) from error
    if len(decoded_key) != 32:
        raise ValueError("The raw private key must be 32 bytes long.")
    return PrivateKey(decoded_key)


def decode_public_key(key: str) -> PublicKey:
    """Get the given base64 encoded public key as a PublicKey object.

    This function can be used to check whether this is a valid base64 encoded string
    of the right length; it raises a ValueError if this is not the case.
    """
    try:
        decoded_key = base64.b64decode(key)
    except base64.binascii.Error as error:  # type: ignore
        raise ValueError(str(error)) from error
    if len(decoded_key) != 32:
        raise ValueError("The raw public key must be 32 bytes long.")
    return PublicKey(decoded_key)


def decrypt(data: str, key: str) -> str:
    """Decrypt a str of ASCII characters with a base64 encoded private Crypt4GH key."""
    sealed_box = SealedBox(decode_private_key(key))
    encrypted_bytes = base64.b64decode(data)
    decrypted_bytes = sealed_box.decrypt(encrypted_bytes)
    return decrypted_bytes.decode("ascii")


def encrypt(data: str, key: str) -> str:
    """Encrypt a str of ASCII characters with a base64 encoded public Crypt4GH key.

    The result will be base64 encoded again.
    """
    sealed_box = SealedBox(decode_public_key(key))
    decoded_data = bytes(data, encoding="ascii")
    encrypted = sealed_box.encrypt(decoded_data)
    return base64.b64encode(encrypted).decode("ascii")
