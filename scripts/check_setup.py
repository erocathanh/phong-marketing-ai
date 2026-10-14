#!/usr/bin/env python3
"""Kiểm tra môi trường hệ thống và tính sẵn sàng của kho marketing.

Cách dùng:
  python3 scripts/check_setup.py
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent

AGENT_NAMES = [
    'marketing-lead',
    'content-writer',
    'social-community',
    'email-crm',
    'paid-media',
    'video-creative',
    'funnel-offer',
    'marketing-reviewer'
]

INSTALLED_SKILLS = [
    'caption-fanpage',
    'doc-so-quang-cao',
    'lich-dang-7-ngay',
    'fb-chia-khoa',
    'fanpage-post',
    'doc-comment-fanpage',
    'tra-loi-inbox-fanpage'
]

INSTALLED_AGENTS = [
    f'{name}.md' for name in AGENT_NAMES
]

REQUIRED_FILES = [
    'CLAUDE.md',
    'README.md',
    'LICENSE',
    *[f'.claude/agents/{name}.md' for name in AGENT_NAMES],
    '.claude/skills/caption-fanpage/SKILL.md',
    '.claude/skills/doc-so-quang-cao/SKILL.md',
    '.claude/skills/doc-so-quang-cao/scripts/read_ad_spend.py',
    '.claude/skills/lich-dang-7-ngay/SKILL.md',
    '.claude/skills/lich-dang-7-ngay/scripts/make_utm_links.py',
    '.claude/skills/lich-dang-7-ngay/scripts/build_schedule.py',
    '.claude/skills/fb-chia-khoa/SKILL.md',
    '.claude/skills/fb-chia-khoa/scripts/page_token.py',
    '.claude/skills/fanpage-post/SKILL.md',
    '.claude/skills/fanpage-post/scripts/page_post.py',
    '.claude/skills/doc-comment-fanpage/SKILL.md',
    '.claude/skills/doc-comment-fanpage/scripts/page_comments.py',
    '.claude/skills/tra-loi-inbox-fanpage/SKILL.md',
    '.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py',
    'scripts/check_setup.py',
    'scripts/check_manifest.py',
    'scripts/install.sh',
    'scripts/uninstall.sh',
    'references/du-lieu-mau/chi-quang-cao-7-ngay.csv',
    'references/du-lieu-mau/ke-hoach-tuan-mau.json',
    'references/du-lieu-mau/ke-hoach-utm.csv',
    'references/du-lieu-mau/loi-doc-video-mau.md',
    'references/ban-mau/bao-cao-quang-cao-mau.md',
    'references/ban-mau/caption-mau.md',
    'references/ban-mau/lich-dang-7-ngay-mau.md',
    'references/ban-mau/link-utm-mau.csv'
]


def check_python_version() -> bool:
    version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 8):
        print(f"ĐẠT Python — phiên bản {version_str} đáp ứng yêu cầu (từ 3.8 trở lên).")
        return True
    print(f"HỎNG Python — phiên bản hiện tại là {version_str}, cần từ 3.8 trở lên.")
    return False


def check_claude_command() -> bool:
    claude_bin = shutil.which('claude')
    if claude_bin:
        print("ĐẠT Lệnh claude — đã có lệnh claude trên máy, sẵn sàng dùng trong Terminal.")
        return True
    print("HỎNG Lệnh claude — chưa thấy lệnh claude trong Terminal. Cần cài đặt Claude Code để vận hành.")
    return False


def check_main_files() -> bool:
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    if not missing:
        print(f"ĐẠT Tệp chính — đủ {len(REQUIRED_FILES)} tệp cần thiết trong kho.")
        return True
    missing_str = ', '.join(missing)
    print(f"HỎNG Tệp chính — thiếu: {missing_str}, hãy tải lại kho.")
    return False


def check_agents_metadata() -> bool:
    name_re = re.compile(r'^name:\s*([a-z0-9-]+)\s*$', re.MULTILINE)
    desc_re = re.compile(r'^description:\s*(.+)$', re.MULTILINE)
    errors = []

    for name in AGENT_NAMES:
        path = ROOT / '.claude' / 'agents' / f'{name}.md'
        if not path.is_file():
            errors.append(f"thiếu tệp {name}.md")
            continue
        text = path.read_text(encoding='utf-8')
        m_name = name_re.search(text)
        m_desc = desc_re.search(text)
        if not m_name or m_name.group(1).strip() != name:
            errors.append(f"{name}.md sai trường name")
        if not m_desc or not m_desc.group(1).strip():
            errors.append(f"{name}.md thiếu trường description")

    if not errors:
        print(f"ĐẠT Tệp vai 8 ghế — đủ 8 ghế với định danh name và description hợp lệ.")
        return True
    print(f"HỎNG Tệp vai 8 ghế — {', '.join(errors)}.")
    return False


def check_symlinks() -> bool:
    """Verify that 7 skills and 8 agent roles in ~/.claude/ exist and point to this repo."""
    home = pathlib.Path.home()
    claude_skills = home / '.claude' / 'skills'
    claude_agents = home / '.claude' / 'agents'

    repo_skills = ROOT / '.claude' / 'skills'
    repo_agents = ROOT / '.claude' / 'agents'

    missing = []
    collisions = []

    # Check 7 skills
    for skill in INSTALLED_SKILLS:
        dest = claude_skills / skill
        expected_src = (repo_skills / skill).resolve()
        if not dest.exists() and not dest.is_symlink():
            missing.append(f"skill {skill}")
        elif dest.is_symlink():
            target_str = os.readlink(dest)
            target = pathlib.Path(target_str)
            if not target.is_absolute():
                target = (dest.parent / target).resolve()
            else:
                target = target.resolve()
            if target != expected_src:
                collisions.append(f"skill {skill} (đang trỏ sang: {target})")
        else:
            collisions.append(f"skill {skill} (là tệp/thư mục thật của học viên, không phải lối tắt kho này)")

    # Check 8 agent files
    for agent in INSTALLED_AGENTS:
        dest = claude_agents / agent
        expected_src = (repo_agents / agent).resolve()
        if not dest.exists() and not dest.is_symlink():
            missing.append(f"vai {agent}")
        elif dest.is_symlink():
            target_str = os.readlink(dest)
            target = pathlib.Path(target_str)
            if not target.is_absolute():
                target = (dest.parent / target).resolve()
            else:
                target = target.resolve()
            if target != expected_src:
                collisions.append(f"vai {agent} (đang trỏ sang: {target})")
        else:
            collisions.append(f"vai {agent} (là tệp thật của học viên, không phải lối tắt kho này)")

    if collisions:
        print("HỎNG Lối tắt — trùng với thứ khác của học viên:")
        for col in collisions:
            print(f"  · {col}")
        return False

    if missing:
        missing_str = ', '.join(missing)
        print(f"HỎNG Lối tắt — chưa cài đủ 7 skill và 8 vai vào ~/.claude/ (thiếu: {missing_str}).")
        print("  Hãy chạy: bash scripts/install.sh")
        return False

    print("ĐẠT Lối tắt — đủ 7 skill và 8 tệp vai trong ~/.claude/ trỏ đúng vào kho này.")
    return True


def run_script_self_check(rel_script_path: str, label: str) -> bool:
    script_path = ROOT / rel_script_path
    if not script_path.is_file():
        print(f"HỎNG {label} — không thấy {rel_script_path}, hãy tải lại kho.")
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), '--tu-kiem'],
            cwd=str(ROOT),
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            print(f"ĐẠT {label} — tự kiểm tra hoạt động đúng.")
            return True
        print(f"HỎNG {label} — tự kiểm tra không đạt (mã {proc.returncode}).")
        return False
    except Exception as err:
        print(f"HỎNG {label} — lỗi chạy script: {err}.")
        return False


def check_read_ad_spend() -> bool:
    return run_script_self_check('.claude/skills/doc-so-quang-cao/scripts/read_ad_spend.py', 'Đọc số quảng cáo')


def check_make_utm_links() -> bool:
    return run_script_self_check('.claude/skills/lich-dang-7-ngay/scripts/make_utm_links.py', 'Tạo link UTM')


def check_build_schedule() -> bool:
    return run_script_self_check('.claude/skills/lich-dang-7-ngay/scripts/build_schedule.py', 'Khung lịch 7 ngày')


def check_page_token() -> bool:
    return run_script_self_check('.claude/skills/fb-chia-khoa/scripts/page_token.py', 'Kiểm chìa Facebook')


def check_page_post() -> bool:
    return run_script_self_check('.claude/skills/fanpage-post/scripts/page_post.py', 'Đăng bài Trang')


def check_page_comments() -> bool:
    return run_script_self_check('.claude/skills/doc-comment-fanpage/scripts/page_comments.py', 'Bình luận Trang')


def check_page_inbox() -> bool:
    return run_script_self_check('.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py', 'Hộp thư Trang')


def check_out_directory() -> bool:
    out_dir = ROOT / 'out'
    test_file = out_dir / f".test_setup_write_{uuid.uuid4().hex}"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        test_file.write_text('ok', encoding='utf-8')
        content = test_file.read_text(encoding='utf-8')
        if test_file.exists():
            test_file.unlink()
        if content == 'ok':
            print("ĐẠT Thư mục out — thư mục out/ tạo được và ghi được.")
            return True
        print("HỎNG Thư mục out — nội dung ghi thử không khớp, hãy kiểm tra quyền ghi thư mục out/.")
        return False
    except Exception as err:
        print(f"HỎNG Thư mục out — không tạo hoặc ghi được vào thư mục out/: {err}.")
        return False


def main():
    checks = [
        check_python_version,
        check_claude_command,
        check_main_files,
        check_agents_metadata,
        check_symlinks,
        check_read_ad_spend,
        check_make_utm_links,
        check_build_schedule,
        check_page_token,
        check_page_post,
        check_page_comments,
        check_page_inbox,
        check_out_directory
    ]

    passed_count = sum(1 for chk in checks if chk())
    total_count = len(checks)

    if passed_count == total_count:
        print(f"KẾT QUẢ: {passed_count}/{total_count} đạt — bộ cài sẵn sàng")
        return 0
    else:
        print(f"KẾT QUẢ: {passed_count}/{total_count} đạt — sửa dòng HỎNG rồi chạy lại")
        return 1


if __name__ == '__main__':
    sys.exit(main())
