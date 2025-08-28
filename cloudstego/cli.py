from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from .crypto_utils import encrypt_bytes, decrypt_bytes
from .stego_png import embed_bytes_into_image, extract_bytes_from_image
from .s3_utils import upload_bytes, download_bytes


def cmd_embed_upload(args: argparse.Namespace) -> None:
    cover_path = Path(args.cover)
    data_path = Path(args.input)
    output_path = Path(args.output)

    data = data_path.read_bytes()
    encrypted = encrypt_bytes(data, args.password)

    with Image.open(cover_path) as img:
        stego = embed_bytes_into_image(img, encrypted)
        stego.save(output_path, format="PNG")

    # Upload to S3
    if args.s3_bucket and args.s3_key:
        upload_bytes(args.s3_bucket, args.s3_key, output_path.read_bytes(), content_type="image/png")


def cmd_download_extract(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_path = Path(args.output)

    # Download if S3 is provided
    if args.s3_bucket and args.s3_key:
        blob = download_bytes(args.s3_bucket, args.s3_key)
        input_path.write_bytes(blob)

    with Image.open(input_path) as img:
        encrypted = extract_bytes_from_image(img)
    data = decrypt_bytes(encrypted, args.password)
    output_path.write_bytes(data)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cloudstego", description="Encrypt data, hide in PNG, store in S3")
    sub = p.add_subparsers(dest="command", required=True)

    embed = sub.add_parser("embed-upload", help="Encrypt, embed into PNG, optionally upload to S3")
    embed.add_argument("--cover", required=True, help="Path to cover PNG (RGB/RGBA)")
    embed.add_argument("--input", required=True, help="Path to input data file")
    embed.add_argument("--output", required=True, help="Path to output stego PNG")
    embed.add_argument("--password", required=True, help="Password for encryption")
    embed.add_argument("--s3-bucket", help="S3 bucket to upload to")
    embed.add_argument("--s3-key", help="S3 key to upload as")
    embed.set_defaults(func=cmd_embed_upload)

    extract = sub.add_parser("download-extract", help="Download PNG from S3 or disk, extract and decrypt")
    extract.add_argument("--input", required=True, help="Path to stego PNG (or temp path if downloading)")
    extract.add_argument("--output", required=True, help="Path to write decrypted data")
    extract.add_argument("--password", required=True, help="Password for decryption")
    extract.add_argument("--s3-bucket", help="S3 bucket to download from")
    extract.add_argument("--s3-key", help="S3 key to download")
    extract.set_defaults(func=cmd_download_extract)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

