#!/usr/bin/env python3
"""
Repo-wide replacement of unsupported clang warning flag.

Replaces '-Wno-nontrivial-memcall' with '-Wno-nontrivial-memaccess' in all
text files in the repository, excluding .git, out directories, and binary files.

Usage:
    python scripts/fix-warning-flag.py           # Dry-run (default)
    python scripts/fix-warning-flag.py --apply   # Apply changes
    python scripts/fix-warning-flag.py --commit  # Apply and commit changes
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

BAD_FLAG = "-Wno-nontrivial-memcall"
GOOD_FLAG = "-Wno-nontrivial-memaccess"
MAX_LINE_DISPLAY = 80  # Maximum line length to display before truncating

# Type alias for file match results: (filepath, [(line_number, line_content), ...])
FileMatch = tuple[Path, list[tuple[int, str]]]

# Directories to skip
SKIP_DIRS = {".git", "out", "__pycache__", ".cache", "node_modules"}

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp",
    ".exe", ".dll", ".so", ".dylib", ".a", ".o",
    ".zip", ".tar", ".gz", ".bz2", ".xz",
    ".pdf", ".doc", ".docx",
    ".pyc", ".pyo", ".class",
    ".woff", ".woff2", ".ttf", ".eot",
}


def is_binary_file(filepath: Path) -> bool:
    """Check if a file is binary by extension or content."""
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


def find_files_with_flag(root: Path) -> list[FileMatch]:
    """Find all files containing the bad flag.

    Returns a list of (filepath, [(line_number, line_content), ...])
    """
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out directories to skip
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            filepath = Path(dirpath) / filename
            if is_binary_file(filepath):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    matches = []
                    for i, line in enumerate(lines, 1):
                        if BAD_FLAG in line:
                            matches.append((i, line.rstrip()))
                    if matches:
                        results.append((filepath, matches))
            except (IOError, OSError):
                continue
    return results


def apply_replacements(root: Path, files: list[FileMatch]) -> list[Path]:
    """Apply replacements to files. Returns list of modified files."""
    modified = []
    for filepath, _ in files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            new_content = content.replace(BAD_FLAG, GOOD_FLAG)
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                modified.append(filepath)
        except (IOError, OSError) as e:
            print(f"Error modifying {filepath}: {e}", file=sys.stderr)
    return modified


def git_commit(files: list[Path], message: str) -> bool:
    """Stage and commit the given files."""
    try:
        for f in files:
            subprocess.run(["git", "add", str(f)], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git commit failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Replace unsupported clang warning flag repo-wide."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply replacements (otherwise dry-run)",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Apply replacements and commit changes",
    )
    args = parser.parse_args()

    # Find repo root (where this script is located is scripts/, parent is root)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    print(f"Scanning repository: {repo_root}")
    print(f"Looking for: {BAD_FLAG}")
    print(f"Replacement: {GOOD_FLAG}")
    print()

    files_with_flag = find_files_with_flag(repo_root)

    if not files_with_flag:
        print("No occurrences found.")
        return 0

    print(f"Found {len(files_with_flag)} file(s) with occurrences:")
    print()
    for filepath, matches in files_with_flag:
        rel_path = filepath.relative_to(repo_root)
        print(f"  {rel_path}:")
        for line_num, line_content in matches:
            print(f"    Line {line_num}: {line_content[:MAX_LINE_DISPLAY]}{'...' if len(line_content) > MAX_LINE_DISPLAY else ''}")
        print()

    if args.apply or args.commit:
        print("Applying replacements...")
        modified = apply_replacements(repo_root, files_with_flag)
        print(f"Modified {len(modified)} file(s).")

        if args.commit and modified:
            print("Committing changes...")
            commit_msg = f"fix: replace {BAD_FLAG} -> {GOOD_FLAG}"
            if git_commit(modified, commit_msg):
                print("Changes committed successfully.")
            else:
                return 1
    else:
        print("Dry-run mode. Use --apply to write changes or --commit to write and commit.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
