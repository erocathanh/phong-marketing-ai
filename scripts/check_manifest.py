#!/usr/bin/env python3
"""Check or rebuild MANIFEST.md for the marketing workspace.

Usage:
  python3 scripts/check_manifest.py           # Check all files against MANIFEST.md
  python3 scripts/check_manifest.py --write   # Generate MANIFEST.md from disk files
On Windows:
  py scripts\\check_manifest.py
  py scripts\\check_manifest.py --write
"""
import argparse
import hashlib
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST_FILE = ROOT / 'MANIFEST.md'


def is_ignored(rel_path):
    parts = rel_path.parts if isinstance(rel_path, pathlib.Path) else pathlib.Path(rel_path).parts
    if not parts:
        return True
    if parts[0] in ('out', '.git'):
        return True
    for part in parts:
        if part in ('__pycache__', '.DS_Store', 'MANIFEST.md'):
            return True
    return False


def collect_disk_files(root):
    collected = []
    for item in root.rglob('*'):
        if item.is_file():
            rel = item.relative_to(root)
            if not is_ignored(rel):
                collected.append(rel.as_posix())
    collected.sort()
    return collected


def is_git_root(root):
    if not (root / '.git').is_dir():
        return False
    try:
        verify_proc = subprocess.run(
            ['git', 'rev-parse', '--verify', '-q', 'HEAD'],
            cwd=str(root),
            capture_output=True,
            text=True
        )
        if verify_proc.returncode != 0:
            return False
        prefix_proc = subprocess.run(
            ['git', 'rev-parse', '--show-prefix'],
            cwd=str(root),
            capture_output=True,
            text=True
        )
        return prefix_proc.stdout.strip() == ''
    except Exception:
        return False


def get_london_time():
    try:
        out = subprocess.check_output(
            ['date', '+%Y-%m-%d %H:%M'],
            env={**os.environ, 'TZ': 'Europe/London'},
            text=True
        )
        return out.strip()
    except Exception:
        from datetime import datetime, timezone, timedelta
        return datetime.now(timezone(timedelta(hours=1))).strftime('%Y-%m-%d %H:%M')


def write_manifest(root):
    files = collect_disk_files(root)

    crlf_files = []
    for rel_path in files:
        file_path = root / rel_path
        content = file_path.read_bytes()
        if b'\x00' not in content[:8192] and b'\r\n' in content:
            print(f"HỎNG xuống dòng kiểu Windows: {rel_path} — đổi sang LF rồi chạy lại")
            crlf_files.append(rel_path)
    if crlf_files:
        return 1

    london_time = get_london_time()

    lines = [
        f"# MANIFEST — phong-marketing-ai ({london_time} London · băm từ tệp trên đĩa)",
        "",
        "md5(8)    cỡ(byte)  tệp"
    ]

    for rel_path in files:
        file_path = root / rel_path
        content = file_path.read_bytes()
        md5_8 = hashlib.md5(content).hexdigest()[:8]
        size = len(content)
        lines.append(f"{md5_8}  {size:>10}  {rel_path}")

    tmp_manifest = root / 'MANIFEST.md.tmp'
    tmp_manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    tmp_manifest.replace(MANIFEST_FILE)
    print(f"Đã ghi MANIFEST.md ({len(files)} tệp).")
    return 0


def check_manifest(root):
    if not MANIFEST_FILE.is_file():
        print("HỎNG MANIFEST — không tìm thấy MANIFEST.md trong kho.")
        return 1

    manifest_text = MANIFEST_FILE.read_text(encoding='utf-8')
    entry_pattern = re.compile(r'^([0-9a-f]{8})\s+(\d+)\s+(.+)$')

    listed_entries = {}
    for raw_line in manifest_text.splitlines():
        line = raw_line.strip()
        match = entry_pattern.match(line)
        if match:
            want_md5 = match.group(1)
            want_size = int(match.group(2))
            file_name = match.group(3).strip()
            listed_entries[file_name] = (want_md5, want_size)

    use_git = is_git_root(root)
    src_desc = "nội dung đã commit" if use_git else "tệp trên đĩa"

    ok = 0
    bad = 0

    for rel_path, (want_md5, want_size) in listed_entries.items():
        if use_git:
            check_proc = subprocess.run(
                ['git', 'cat-file', '-e', f'HEAD:{rel_path}'],
                cwd=str(root)
            )
            if check_proc.returncode != 0:
                print(f"HỎNG thiếu: {rel_path}")
                bad += 1
                continue
            show_proc = subprocess.run(
                ['git', 'show', f'HEAD:{rel_path}'],
                cwd=str(root),
                capture_output=True
            )
            content = show_proc.stdout
        else:
            file_path = root / rel_path
            if not file_path.is_file():
                print(f"HỎNG thiếu: {rel_path}")
                bad += 1
                continue
            content = file_path.read_bytes()

        actual_size = len(content)
        actual_md5 = hashlib.md5(content).hexdigest()[:8]

        has_error = False
        if actual_size != want_size:
            print(f"HỎNG lệch cỡ: {rel_path} (danh sách {want_size}, thật {actual_size})")
            has_error = True
        if actual_md5 != want_md5:
            print(f"HỎNG lệch md5: {rel_path} (danh sách {want_md5}, thật {actual_md5})")
            has_error = True

        if has_error:
            bad += 1
        else:
            ok += 1

    # Check for extra files in workspace
    if use_git:
        ls_proc = subprocess.run(
            ['git', 'ls-files'],
            cwd=str(root),
            capture_output=True,
            text=True
        )
        extra_files = []
        for line in ls_proc.stdout.splitlines():
            f = line.strip()
            if f and not is_ignored(pathlib.Path(f)) and f not in listed_entries:
                extra_files.append(f)
    else:
        disk_files = collect_disk_files(root)
        extra_files = [f for f in disk_files if f not in listed_entries]

    for extra in extra_files:
        print(f"HỎNG có trong kho nhưng không có trong MANIFEST: {extra}")
        bad += 1

    print(f"Khớp {ok} tệp · lệch {bad} (so bằng {src_desc})")
    if bad == 0:
        print("KẾT QUẢ: MANIFEST hợp lệ")
        return 0
    else:
        print("KẾT QUẢ: MANIFEST không khớp — hãy kiểm tra lại tệp")
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', '--sinh', dest='write', action='store_true', help='Rebuild MANIFEST.md from disk')
    args = parser.parse_args()

    if args.write:
        return write_manifest(ROOT)
    return check_manifest(ROOT)


if __name__ == '__main__':
    sys.exit(main())
