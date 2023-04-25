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

"""Test the cryptographic utilities."""


import base64

from pytest import raises

from ghga_service_commons.utils.crypt import (
    decode_private_key,
    decode_public_key,
    decrypt,
    encode_private_key,
    encode_public_key,
    encrypt,
    generate_key_pair,
)


def test_generate_key_pair():
    """Test that random key pairs can be generated."""
    key_pair = generate_key_pair()
    assert hasattr(key_pair, "public_key")
    another_key_pair = generate_key_pair()
    assert key_pair != another_key_pair
    assert bytes(key_pair) != bytes(another_key_pair)
    assert bytes(key_pair.public_key) != bytes(another_key_pair.public_key)


def test_encode_key_pair():
    """Test that key pairs can be base64 encoded."""
    key_pair = generate_key_pair()
    encoded_private_key = encode_private_key(key_pair)
    assert isinstance(encoded_private_key, str)
    assert encoded_private_key.isascii()
    assert len(encoded_private_key) == 44
    encoded_public_key = encode_public_key(key_pair)
    assert isinstance(encoded_public_key, str)
    assert encoded_public_key.isascii()
    assert len(encoded_public_key) == 44
    assert encode_public_key != encode_private_key


def test_decode_valid_private_key():
    """Test that valid base64 encoded private keys can be decoded."""
    key = decode_private_key(base64.b64encode(b"foo4" * 8).decode("ascii"))
    assert bytes(key) == b"foo4" * 8


def test_decode_invalid_private_key():
    """Test that invalid private keys can be detected."""
    with raises(ValueError, match="Incorrect padding"):
        decode_private_key("foo")
    with raises(ValueError, match="raw private key must be 32 bytes long"):
        decode_private_key(base64.b64encode(b"foo").decode("ascii"))


def test_decode_valid_public_key():
    """Test that valid base64 encoded public keys can be decoded."""
    key = decode_public_key(base64.b64encode(b"foo4" * 8).decode("ascii"))
    assert bytes(key) == b"foo4" * 8


def test_decode_invalid_public_key():
    """Test that invalid public keys can be detected."""
    with raises(ValueError, match="Incorrect padding"):
        decode_public_key("foo")
    with raises(ValueError, match="raw public key must be 32 bytes long"):
        decode_public_key(base64.b64encode(b"foo").decode("ascii"))
    decode_public_key(base64.b64encode(b"foo4" * 8).decode("ascii"))


def test_decode_generated_key_pair():
    """Test that a generated key pair can be encoded and decoded."""
    key_pair = generate_key_pair()
    decode_private_key(encode_private_key(key_pair))
    decode_public_key(encode_public_key(key_pair))


def test_encryption_and_decryption():
    """Test encrypting and decrypting a message."""
    key_pair = generate_key_pair()
    private_key = encode_private_key(key_pair)
    assert isinstance(private_key, str)
    public_key = encode_public_key(key_pair)
    assert isinstance(public_key, str)

    message = "Foo bar baz!"
    encrypted = encrypt(message, public_key)
    assert isinstance(encrypted, str)
    assert encrypted != message
    decrypted = decrypt(encrypted, private_key)
    assert isinstance(decrypted, str)
    assert decrypted == message
