#!/usr/bin/env python3
"""Download ephemeris files for Skyfield usage.

This script downloads JPL ephemeris files and uploads them to configured storage backend:
- S3: Upload to S3 bucket using chuk-virtual-fs
- Local: Save to local directory
- Memory: Save to in-memory storage (for testing)

Usage:
    python scripts/download_ephemeris.py [--file de440s.bsp] [--backend s3]
"""

import argparse
import asyncio
import sys
import tempfile
from enum import Enum
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✓ Loaded environment variables from .env file")
except ImportError:
    print("ℹ️  python-dotenv not installed, using system environment variables")
    print("  Install with: pip install python-dotenv")


# Storage backend types (matches chuk-virtual-fs provider names)
class StorageBackend(str, Enum):
    """Available storage backends.

    Values match chuk-virtual-fs provider names exactly.
    """

    FILESYSTEM = "filesystem"  # Local filesystem storage
    S3 = "s3"  # AWS S3 storage
    MEMORY = "memory"  # In-memory storage

    # Convenience aliases
    @classmethod
    def from_name(cls, name: str) -> "StorageBackend":
        """Get backend from user-friendly name."""
        name_lower = name.lower()
        if name_lower in ("local", "filesystem"):
            return cls.FILESYSTEM
        elif name_lower == "s3":
            return cls.S3
        elif name_lower == "memory":
            return cls.MEMORY
        else:
            raise ValueError(f"Unknown storage backend: {name}")


# AWS regions
class AWSRegion(str, Enum):
    """AWS regions."""

    US_EAST_1 = "us-east-1"


try:
    from skyfield.iokit import Loader
except ImportError:
    print("Error: Skyfield not installed. Install with: pip install skyfield")
    sys.exit(1)

try:
    from chuk_virtual_fs import AsyncVirtualFileSystem
except ImportError:
    print("Error: chuk-virtual-fs not installed. Install with: pip install chuk-virtual-fs")
    sys.exit(1)

# Import config to get S3 settings
try:
    # Add parent directory to path to import from src
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from chuk_mcp_celestial.config import SkyfieldConfig
except ImportError:
    print("Warning: Could not import config, using defaults")

    class SkyfieldConfig:
        S3_BUCKET = "chuk-celestial-ephemeris"
        S3_REGION = "us-east-1"
        S3_PREFIX = "ephemeris/"
        S3_PROFILE = None
        DATA_DIR = "~/.skyfield"


# Available ephemeris files with descriptions
EPHEMERIS_FILES = {
    "de440s.bsp": {
        "description": "JPL DE440s - 32 MB, covers 1849-2150 (recommended for 2020+)",
        "size_mb": 32,
        "years": "1849-2150",
        "recommended": True,
    },
    "de421.bsp": {
        "description": "JPL DE421 - 17 MB, covers 1900-2050 (smaller, older)",
        "size_mb": 17,
        "years": "1900-2050",
        "recommended": False,
    },
    "de440.bsp": {
        "description": "JPL DE440 - 114 MB, covers 1550-2650 (most comprehensive)",
        "size_mb": 114,
        "years": "1550-2650",
        "recommended": False,
    },
}


async def check_and_create_bucket(bucket_name: str, region: str) -> None:
    """Check if S3 bucket exists and create if it doesn't.

    Args:
        bucket_name: Name of the S3 bucket
        region: AWS region for the bucket
    """
    try:
        import aioboto3
    except ImportError:
        print("❌ Error: aioboto3 required for S3. Install with: pip install aioboto3")
        sys.exit(1)

    session = aioboto3.Session()

    try:
        async with session.client("s3", region_name=region) as s3:
            # Check if bucket exists
            try:
                await s3.head_bucket(Bucket=bucket_name)
                print(f"✓ Bucket '{bucket_name}' exists")
            except s3.exceptions.NoSuchBucket:
                # Bucket doesn't exist, create it
                print(f"📦 Bucket '{bucket_name}' not found, creating...")

                # Create bucket with proper configuration based on region
                if region == "us-east-1":
                    # us-east-1 doesn't support LocationConstraint
                    await s3.create_bucket(Bucket=bucket_name)
                else:
                    await s3.create_bucket(
                        Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region}
                    )

                print(f"✅ Created bucket '{bucket_name}' in region '{region}'")
            except Exception as e:
                # If we get a 404 or Forbidden, try to create
                if "404" in str(e) or "NoSuchBucket" in str(e):
                    print(f"📦 Bucket '{bucket_name}' not found, creating...")

                    if region == "us-east-1":
                        await s3.create_bucket(Bucket=bucket_name)
                    else:
                        await s3.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": region},
                        )

                    print(f"✅ Created bucket '{bucket_name}' in region '{region}'")
                else:
                    raise
    except Exception as e:
        print(f"⚠️  Warning: Could not check/create bucket: {e}")
        print("   Proceeding anyway - VFS will handle initialization")


async def check_file_exists_in_storage(vfs, file_path: str) -> bool:
    """Check if file exists in VFS storage.

    Args:
        vfs: Virtual filesystem instance
        file_path: Path to check

    Returns:
        True if file exists, False otherwise
    """
    try:
        return await vfs.exists(file_path)
    except Exception:
        return False


async def download_ephemeris(
    ephemeris_file: str, backend: StorageBackend, force: bool = False
) -> None:
    """Download ephemeris file and upload to storage backend.

    Args:
        ephemeris_file: Name of ephemeris file (e.g., 'de440s.bsp')
        backend: Storage backend (LOCAL, S3, or MEMORY)
        force: Force download even if file exists
    """
    print(f"📥 Downloading ephemeris file: {ephemeris_file}")
    print(f"🗄️  Storage backend: {backend.value}")

    if ephemeris_file in EPHEMERIS_FILES:
        info = EPHEMERIS_FILES[ephemeris_file]
        print(f"ℹ️  {info['description']}")
        print(f"📊 Size: ~{info['size_mb']} MB")
        print(f"📅 Coverage: {info['years']}")
        print()

    # Check if file already exists in storage (unless forced)
    if not force:
        # Initialize VFS to check existence
        temp_vfs = None
        try:
            if backend == StorageBackend.FILESYSTEM:
                data_dir = Path(SkyfieldConfig.DATA_DIR).expanduser()
                temp_vfs = AsyncVirtualFileSystem(
                    provider=StorageBackend.FILESYSTEM.value, root_path=str(data_dir)
                )
            elif backend == StorageBackend.S3:
                await check_and_create_bucket(SkyfieldConfig.S3_BUCKET, SkyfieldConfig.S3_REGION)
                temp_vfs = AsyncVirtualFileSystem(
                    provider=StorageBackend.S3.value,
                    bucket_name=SkyfieldConfig.S3_BUCKET,
                    prefix=SkyfieldConfig.S3_PREFIX,
                    region_name=SkyfieldConfig.S3_REGION,
                )
            elif backend == StorageBackend.MEMORY:
                temp_vfs = AsyncVirtualFileSystem(provider=StorageBackend.MEMORY.value)

            if temp_vfs:
                await temp_vfs.initialize()
                vfs_path = f"/{ephemeris_file}"

                if await check_file_exists_in_storage(temp_vfs, vfs_path):
                    print(f"✓ File '{ephemeris_file}' already exists in {backend.value} storage")
                    print("  Skipping download (use --force to re-download)")
                    await temp_vfs.close()
                    return

                await temp_vfs.close()
        except Exception as e:
            # If we can't check, proceed with download
            print(f"  Warning: Could not check file existence: {e}")
            print("  Proceeding with download...")

    # Download to temp directory first
    temp_dir = Path(tempfile.mkdtemp(prefix="ephemeris_download_"))
    print(f"📁 Temporary directory: {temp_dir}")

    try:
        # Create Skyfield loader
        loader = Loader(str(temp_dir), verbose=True)

        # Download the file
        print("⏳ Downloading from JPL... (this may take a few minutes)")
        eph = loader(ephemeris_file)
        print(f"\n✅ Downloaded to: {temp_dir / ephemeris_file}")

        # Also download timescale files (small)
        print("\n📥 Downloading timescale data files...")
        loader.timescale()
        print("✅ Timescale files downloaded")

        # Verify the file works
        print("\n🔍 Verifying ephemeris file...")
        _ = eph["earth"]
        _ = eph["sun"]
        _ = eph["moon"]
        print("✅ Ephemeris verified - can access celestial bodies (earth, sun, moon)")

        # Upload to storage backend
        print(f"\n☁️  Uploading to {backend} storage...")

        # Initialize virtual filesystem
        if backend == StorageBackend.FILESYSTEM:
            data_dir = Path(SkyfieldConfig.DATA_DIR).expanduser()
            print(f"📁 Local directory: {data_dir}")
            vfs = AsyncVirtualFileSystem(provider="filesystem", root_path=str(data_dir))
        elif backend == StorageBackend.S3:
            print(f"📦 S3 Bucket: {SkyfieldConfig.S3_BUCKET}")
            print(f"📍 Region: {SkyfieldConfig.S3_REGION}")
            print(f"📂 Prefix: {SkyfieldConfig.S3_PREFIX}")

            # Check if bucket exists, create if not
            await check_and_create_bucket(SkyfieldConfig.S3_BUCKET, SkyfieldConfig.S3_REGION)

            vfs = AsyncVirtualFileSystem(
                provider="s3",
                bucket_name=SkyfieldConfig.S3_BUCKET,
                prefix=SkyfieldConfig.S3_PREFIX,
                region_name=SkyfieldConfig.S3_REGION,
            )
        elif backend == StorageBackend.MEMORY:
            print("💾 In-memory storage (for testing)")
            vfs = AsyncVirtualFileSystem(provider="memory")
        else:
            raise ValueError(f"Unknown backend: {backend}")

        await vfs.initialize()

        # Upload ephemeris file
        ephemeris_path = temp_dir / ephemeris_file
        vfs_path = f"/{ephemeris_file}"

        print(f"⬆️  Uploading {ephemeris_file}...")
        content = ephemeris_path.read_bytes()
        await vfs.write_file(vfs_path, content)
        print(f"✅ Uploaded to: {vfs_path}")

        # Upload timescale files
        for timescale_file in ["Leap_Second.dat", "deltat.data", "deltat.preds"]:
            ts_path = temp_dir / timescale_file
            if ts_path.exists():
                print(f"⬆️  Uploading {timescale_file}...")
                ts_content = ts_path.read_bytes()
                await vfs.write_file(f"/{timescale_file}", ts_content)
                print(f"✅ Uploaded: {timescale_file}")

        await vfs.close()

        print("\n🎉 All files uploaded successfully!")

        if backend == StorageBackend.S3:
            print("\n💡 Files are now available in S3:")
            print(f"   s3://{SkyfieldConfig.S3_BUCKET}/{SkyfieldConfig.S3_PREFIX}{ephemeris_file}")
        elif backend == StorageBackend.FILESYSTEM:
            print("\n💡 Files are available at:")
            print(f"   {data_dir / ephemeris_file}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        # Clean up temp directory
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        print("\n🧹 Cleaned up temporary directory")


def list_ephemeris_files() -> None:
    """List available ephemeris files with details."""
    print("📚 Available Ephemeris Files:\n")

    for filename, info in EPHEMERIS_FILES.items():
        marker = "⭐" if info["recommended"] else "  "
        print(f"{marker} {filename}")
        print(f"   {info['description']}")
        print(f"   Size: {info['size_mb']} MB | Years: {info['years']}")
        print()

    print("⭐ = Recommended for most users")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download JPL ephemeris files and upload to storage backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download recommended ephemeris (de440s.bsp) to S3
  python scripts/download_ephemeris.py

  # Download all ephemeris files to S3
  python scripts/download_ephemeris.py --all

  # Download specific ephemeris to S3
  python scripts/download_ephemeris.py --file de421.bsp

  # Download to local storage
  python scripts/download_ephemeris.py --backend local

  # Download all files to local storage
  python scripts/download_ephemeris.py --all --backend local

  # List available files
  python scripts/download_ephemeris.py --list
        """,
    )

    parser.add_argument(
        "--file",
        "-f",
        default=None,
        help="Ephemeris file to download (default: auto-select recommended)",
    )

    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Download all available ephemeris files",
    )

    parser.add_argument(
        "--backend",
        "-b",
        default="s3",
        choices=["local", "s3", "memory"],
        help="Storage backend (default: s3)",
    )

    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available ephemeris files",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force download even if files already exist in storage",
    )

    args = parser.parse_args()

    # List files and exit
    if args.list:
        list_ephemeris_files()
        return

    # Convert backend string to enum
    backend = StorageBackend.from_name(args.backend)

    # Determine which files to download
    if args.all:
        # Download all ephemeris files
        files_to_download = list(EPHEMERIS_FILES.keys())
    elif args.file:
        # Download specific file
        files_to_download = [args.file]
    else:
        # Auto-select recommended file
        recommended = [f for f, info in EPHEMERIS_FILES.items() if info["recommended"]]
        files_to_download = recommended if recommended else ["de440s.bsp"]

    # Download files
    async def download_all():
        for i, file in enumerate(files_to_download, 1):
            if len(files_to_download) > 1:
                print(f"\n{'=' * 60}")
                print(f"Downloading {i}/{len(files_to_download)}: {file}")
                print(f"{'=' * 60}\n")
            await download_ephemeris(file, backend, force=args.force)

    asyncio.run(download_all())


if __name__ == "__main__":
    main()
