### CloudStego (Python)

Encrypt data with AES-GCM, hide it inside a PNG using LSB steganography, and store/retrieve the image from AWS S3.

#### Install

```bash
python3 -m pip install -r requirements.txt
```

#### CLI Usage

- Embed + Upload:
```bash
python3 -m cloudstego.cli embed-upload \
  --cover cover.png \
  --input secret.bin \
  --output stego.png \
  --password "StrongPassw0rd" \
  --s3-bucket your-bucket \
  --s3-key path/in/bucket/stego.png
```

- Download + Extract:
```bash
python3 -m cloudstego.cli download-extract \
  --input stego.png \
  --output recovered.bin \
  --password "StrongPassw0rd" \
  --s3-bucket your-bucket \
  --s3-key path/in/bucket/stego.png
```

- Omit the S3 flags to work locally only.

#### Notes
- Uses PBKDF2-SHA256 to derive a 256-bit key and AES-GCM for authenticated encryption.
- Steganography uses 1 LSB per channel in RGB/RGBA PNGs. Capacity ≈ width × height × channels bits.
- Ensure the cover image has enough capacity for the encrypted payload (payload size = 4 bytes length + ciphertext+tag).