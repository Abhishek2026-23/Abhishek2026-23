from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from PIL import Image


@dataclass
class Capacity:
    width: int
    height: int
    channels: int

    @property
    def bits(self) -> int:
        return self.width * self.height * self.channels

    @property
    def bytes(self) -> int:
        return self.bits // 8


def _ensure_rgb(image: Image.Image) -> Image.Image:
    if image.mode not in ("RGB", "RGBA"):
        return image.convert("RGBA")
    return image


def get_capacity(image: Image.Image) -> Capacity:
    image = _ensure_rgb(image)
    channels = 4 if image.mode == "RGBA" else 3
    width, height = image.size
    return Capacity(width=width, height=height, channels=channels)


def embed_bytes_into_image(image: Image.Image, data: bytes) -> Image.Image:
    """
    Embed data into image using 1 LSB per channel.
    We prefix the data with a 32-bit big-endian length.
    """
    image = _ensure_rgb(image).copy()
    capacity_bits = get_capacity(image).bits
    required_bits = (len(data) + 4) * 8
    if required_bits > capacity_bits:
        raise ValueError("Data too large for image capacity")

    payload = len(data).to_bytes(4, "big") + data
    pixels = list(image.getdata())

    flat_channels = []
    for pixel in pixels:
        flat_channels.extend(pixel)

    bit_index = 0
    for byte in payload:
        for bit_pos in range(7, -1, -1):
            bit = (byte >> bit_pos) & 1
            channel_value = flat_channels[bit_index]
            flat_channels[bit_index] = (channel_value & 0xFE) | bit
            bit_index += 1

    channels_per_pixel = 4 if image.mode == "RGBA" else 3
    new_pixels = []
    for i in range(0, len(flat_channels), channels_per_pixel):
        new_pixels.append(tuple(flat_channels[i:i+channels_per_pixel]))

    image.putdata(new_pixels)
    return image


def extract_bytes_from_image(image: Image.Image) -> bytes:
    image = _ensure_rgb(image)
    pixels = list(image.getdata())
    flat_channels = []
    for pixel in pixels:
        flat_channels.extend(pixel)

    # Read first 32 bits for length
    bit_index = 0
    length_bytes = bytearray()
    current_byte = 0
    for i in range(32):
        current_byte = (current_byte << 1) | (flat_channels[bit_index] & 1)
        bit_index += 1
        if (i + 1) % 8 == 0:
            length_bytes.append(current_byte)
            current_byte = 0
    total_length = int.from_bytes(length_bytes, "big")

    # Read payload
    data = bytearray()
    current_byte = 0
    for i in range(total_length * 8):
        current_byte = (current_byte << 1) | (flat_channels[bit_index] & 1)
        bit_index += 1
        if (i + 1) % 8 == 0:
            data.append(current_byte)
            current_byte = 0
    return bytes(data)

