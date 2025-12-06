#!/usr/bin/env python3
"""
Repo-wide replacement of -Wno-nontrivial-memcall -> -Wno-nontrivial-memaccess.

This script scans the repository for occurrences of the unsupported clang flag
'-Wno-nontrivial-memcall' and replaces it with '-Wno-nontrivial-memaccess'.

Usage:
    python scripts/fix-warning-flag.py           # Dry-run: show files that would be changed
    python scripts/fix-warning-flag.py --apply   # Apply changes to files
    python scripts/fix-warning-flag.py --commit  # Apply changes and commit them
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

BAD_FLAG = "-Wno-nontrivial-memcall"
GOOD_FLAG = "-Wno-nontrivial-memaccess"

# Directories to skip
SKIP_DIRS = {".git", "out", "node_modules", "__pycache__", ".cache"}

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".a", ".o", ".obj",
    ".pyc", ".pyo", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav",
    ".db", ".sqlite", ".sqlite3",
}


def is_binary_file(filepath: Path) -> bool:
    """Check if a file is likely binary based on extension or content."""
    if filepath.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
    except (IOError, OSError):
        return True
    return False


def find_files_with_bad_flag(root: Path) -> List[Tuple[Path, int]]:
    """Find all files containing the bad flag and count occurrences."""
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip certain directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        
        for filename in filenames:
            filepath = Path(dirpath) / filename
            
            if is_binary_file(filepath):
                continue
            
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    count = content.count(BAD_FLAG)
                    if count > 0:
                        results.append((filepath, count))
            except (IOError, OSError) as e:
                print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
    
    return results


def replace_in_file(filepath: Path) -> bool:
    """Replace bad flag with good flag in a file. Returns True if changes were made."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        if BAD_FLAG not in content:
            return False
        
        new_content = content.replace(BAD_FLAG, GOOD_FLAG)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return True
    except (IOError, OSError) as e:
        print(f"Error: Could not modify {filepath}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Replace -Wno-nontrivial-memcall with -Wno-nontrivial-memaccess repo-wide."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to files (default is dry-run)",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Apply changes and commit them (implies --apply)",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Root directory to scan (default: repository root)",
    )
    args = parser.parse_args()

    # If --commit is specified, it implies --apply
    if args.commit:
        args.apply = True

    # Determine root directory
    if args.root:
        root = Path(args.root).resolve()
    else:
        # Try to find the repository root
        root = Path(__file__).parent.parent.resolve()
    
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {root} for '{BAD_FLAG}'...")
    print()

    files_with_flag = find_files_with_bad_flag(root)

    if not files_with_flag:
        print("No files found containing the bad flag.")
        sys.exit(0)

    print(f"Found {len(files_with_flag)} file(s) with '{BAD_FLAG}':")
    total_occurrences = 0
    for filepath, count in files_with_flag:
        rel_path = filepath.relative_to(root)
        print(f"  {rel_path}: {count} occurrence(s)")
        total_occurrences += count
    print()
    print(f"Total: {total_occurrences} occurrence(s) in {len(files_with_flag)} file(s)")
    print()

    if not args.apply:
        print("Dry-run mode: no changes made. Use --apply to apply changes.")
        sys.exit(0)

    # Apply changes
    print("Applying changes...")
    changed_files = []
    for filepath, _ in files_with_flag:
        if replace_in_file(filepath):
            rel_path = filepath.relative_to(root)
            print(f"  Modified: {rel_path}")
            changed_files.append(filepath)

    if not changed_files:
        print("No files were modified.")
        sys.exit(0)

    print()
    print(f"Modified {len(changed_files)} file(s).")

    if args.commit:
        print()
        print("Committing changes...")
        try:
            # Stage changes
            subprocess.run(
                ["git", "add"] + [str(f) for f in changed_files],
                cwd=root,
                check=True,
                capture_output=True,
            )
            # Commit
            commit_msg = "fix: replace -Wno-nontrivial-memcall -> -Wno-nontrivial-memaccess"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"Committed: {commit_msg}")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error committing changes: {e}", file=sys.stderr)
            if e.stderr:
                print(e.stderr, file=sys.stderr)
            sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
