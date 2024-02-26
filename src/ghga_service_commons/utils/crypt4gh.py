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

import base64
import io
import os
from pathlib import Path
from tempfile import mkstemp
from typing import Callable, NamedTuple, Union

import crypt4gh.header
import crypt4gh.lib
from crypt4gh.keys import c4gh, get_private_key, get_public_key

from ghga_service_commons.utils.temp_files import big_temp_file


class Crypt4GHKeyPair(NamedTuple):
    """Crypt4GH keypair"""

    private: bytes
    public: bytes


def string_decoder(function: Callable):
    """Decorator decoding string arguments from base64 to bytes"""

    def wrapper(**kwargs):
        """Decode all string arguments to byte representation"""
        for key, value in kwargs.items():
            if isinstance(value, str):
                kwargs[key] = base64.b64decode(value)
        function(**kwargs)

    return wrapper


@string_decoder
def extract_file_secret(
    *,
    encrypted_header: Union[str, bytes],
    private_key: Union[str, bytes],
    public_key: Union[str, bytes],
) -> bytes:
    """TODO"""
    # (method - only 0 supported for now, private_key, public_key)
    keys = [(0, private_key, None)]
    session_keys, _ = crypt4gh.header.deconstruct(
        infile=encrypted_header, keys=keys, sender_pubkey=public_key
    )

    return session_keys[0]


@string_decoder
def decrypt_file(
    *, input_path: Path, output_path: Path, private_key: Union[str, bytes]
) -> None:
    """TODO"""
    keys = [(0, private_key, None)]
    with input_path.open("rb") as infile, output_path.open("wb") as outfile:
        crypt4gh.lib.decrypt(keys=keys, infile=infile, outfile=outfile)


@string_decoder
def create_envelope(
    *,
    file_secret: Union[str, bytes],
    private_key: Union[str, bytes],
    public_key: Union[str, bytes],
) -> bytes:
    """TODO"""
    keys = [(0, private_key, public_key)]
    header_content = crypt4gh.header.make_packet_data_enc(0, file_secret)
    header_packets = crypt4gh.header.encrypt(header_content, keys)
    return crypt4gh.header.serialize(header_packets)


@string_decoder
def random_encrypted_content(
    file_size: int, private_key: Union[str, bytes], public_key: Union[str, bytes]
):
    """TODO"""
    with big_temp_file(file_size) as raw_file, io.BytesIO() as encrypted_file:
        # rewind input file for reading
        raw_file.seek(0)
        keys = [(0, private_key, public_key)]
        crypt4gh.lib.encrypt(keys=keys, infile=raw_file, outfile=encrypted_file)
        # rewind output file for reading
        encrypted_file.seek(0)
        yield encrypted_file


def generate_keypair() -> Crypt4GHKeyPair:
    """TODO"""
    sk_file, sk_path = mkstemp(prefix="private", suffix=".key")
    pk_file, pk_path = mkstemp(prefix="public", suffix=".key")

    # Crypt4GH does not reset the umask it sets, so we need to deal with it
    original_umask = os.umask(0o022)
    c4gh.generate(seckey=sk_file, pubkey=pk_file)
    public_key = get_public_key(pk_path)
    private_key = get_private_key(sk_path, lambda: None)
    os.umask(original_umask)

    Path(pk_path).unlink()
    Path(sk_path).unlink()

    return Crypt4GHKeyPair(private=private_key, public=public_key)
