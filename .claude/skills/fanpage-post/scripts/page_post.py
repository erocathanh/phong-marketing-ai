#!/usr/bin/env python3
"""Publish posts to a Facebook Page with preview mode when missing --dong-y.

Usage:
  python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --trang "<name-or-id>" --noi-dung "Post content"
  python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --trang "<name-or-id>" --tep-noi-dung content.md
  python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --trang "<name-or-id>" --noi-dung "..." --dong-y
  python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --liet-ke
  python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --tu-kiem
"""
import argparse
import datetime
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://graph.facebook.com/v21.0"
DEFAULT_TOKEN_FILE = os.path.expanduser("~/.config/opc-business-harness/meta-page-token")


def find_repo_root() -> pathlib.Path:
    """Find the marketing workspace root directory by walking up."""
    p = pathlib.Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "scripts" / "check_setup.py").is_file() and (parent / "MANIFEST.md").is_file():
            return parent
    return p.parents[3] if len(p.parents) > 3 else p.parent


def get_token_file_path() -> str:
    """Resolve token file path from environment or default OPC location."""
    env_file = os.environ.get("META_PAGE_TOKEN_FILE")
    if env_file:
        return os.path.expanduser(env_file)
    return DEFAULT_TOKEN_FILE


def sanitize_error(msg: str, token: str = "") -> str:
    """Mask token, EAA prefixes, and Authorization header values from error messages."""
    if not isinstance(msg, str):
        msg = str(msg)
    if token:
        msg = msg.replace(token, "<CHE>")
    msg = re.sub(r'EAA[a-zA-Z0-9_\-\.]+', '<CHE>', msg)
    msg = re.sub(r'(Bearer\s+)[^\s\'",]+', r'\1<CHE>', msg, flags=re.IGNORECASE)
    msg = re.sub(r'(Authorization[:=]\s*[\'\"]?)[^\s\'",]+', r'\1<CHE>', msg, flags=re.IGNORECASE)
    return msg


def validate_token_shape(raw_token: str) -> str:
    """Validate token format: strip ends, reject if length < 30 or whitespace/newline/invalid char inside.
    Never prints token value on failure.
    """
    token = raw_token.strip()
    if not token:
        print("Tệp chìa rỗng.")
        print("Hãy dùng tools/inbox-reader/save_token.py của kho OPC để cất chìa mới.")
        sys.exit(2)

    if len(token) < 30:
        print("Chìa truy cập không hợp lệ: độ dài quá ngắn (yêu cầu từ 30 ký tự trở lên).")
        print("Hãy dùng tools/inbox-reader/save_token.py của kho OPC để cất lại chìa.")
        sys.exit(2)

    if any(c.isspace() for c in token) or not re.fullmatch(r"^[A-Za-z0-9_.-]+$", token):
        print("Chìa truy cập không đúng định dạng (chứa khoảng trắng, ký tự xuống dòng hoặc ký tự không hợp lệ).")
        print("Hãy dùng tools/inbox-reader/save_token.py của kho OPC để cất lại chìa.")
        sys.exit(2)

    return token


def load_token(token_file: str) -> str:
    """Load token securely. Exit code 2 if token file is missing, empty, or malformed."""
    if not os.path.exists(token_file):
        print(f"Chưa có chìa truy cập tại {token_file}.")
        print("Hãy dùng tools/inbox-reader/save_token.py của kho OPC để cất chìa, hoặc chạy skill fb-chia-khoa để kiểm tra.")
        sys.exit(2)

    try:
        with open(token_file, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as err:
        print(f"Không thể đọc tệp chìa tại {token_file}: {sanitize_error(str(err))}")
        print("Hãy kiểm tra quyền tệp (cần quyền 600) hoặc dùng kho OPC để cất lại chìa.")
        sys.exit(2)

    return validate_token_shape(raw)


def api_request(path: str, token: str, params: dict = None, method: str = "GET", data: dict = None) -> dict:
    """Execute Graph API request securely."""
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "MarketingWorkspace/1.0"
    }
    query_str = ""
    if params:
        query_str = "?" + urllib.parse.urlencode(params)

    url = f"{API_BASE}/{path.lstrip('/')}{query_str}"
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)
    except urllib.error.HTTPError as err:
        try:
            err_body = json.loads(err.read().decode("utf-8"))
            if isinstance(err_body, dict) and "error" in err_body:
                if isinstance(err_body["error"], dict) and "message" in err_body["error"]:
                    err_body["error"]["message"] = sanitize_error(err_body["error"]["message"], token)
            return err_body
        except Exception:
            return {"error": {"message": sanitize_error(f"HTTP error {err.code}: {err.reason}", token)}}
    except Exception as err:
        return {"error": {"message": sanitize_error(f"Network error: {str(err)}", token)}}


def check_output_dir(out_dir: pathlib.Path) -> bool:
    """Verify that output directory/file is ignored by git and not tracked before writing. Does not create dir."""
    root = find_repo_root()
    target_file = pathlib.Path(out_dir) / "posted.json"
    try:
        track_proc = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(target_file)],
            cwd=str(root),
            capture_output=True
        )
        if track_proc.returncode == 0:
            return False

        proc = subprocess.run(
            ["git", "check-ignore", "-q", str(target_file)],
            cwd=str(root),
            capture_output=True
        )
        return proc.returncode == 0
    except Exception:
        return False


def get_pages(token: str) -> list:
    """Fetch all pages managed by the user/system account."""
    resp = api_request("me/accounts", token, {"fields": "id,name,access_token,tasks", "limit": "50"})
    if "error" in resp:
        me = api_request("me", token, {"fields": "id,name"})
        if "error" not in me and "name" in me:
            return [{"id": me["id"], "name": me["name"], "access_token": token}]
        err_msg = sanitize_error(resp['error'].get('message', 'Không rõ'), token)
        print(f"Lỗi truy vấn danh sách Trang: {err_msg}")
        return []
    return resp.get("data", [])


def resolve_page_from_list(pages: list, target: str):
    """Find specific page by exact ID or exact Name from a list.
    If substring matches 2+ pages: print matching pages and exit with code 1.
    If substring matches exactly 1 page: return that page.
    If no matches: return None.
    """
    if not pages:
        return None

    target_clean = target.strip()
    target_lower = target_clean.lower()

    # 1. Exact ID match
    for p in pages:
        if str(p.get("id")).strip() == target_clean:
            return p

    # 2. Exact Name match (case-insensitive)
    exact_name_matches = [
        p for p in pages
        if p.get("name", "").strip().lower() == target_lower
    ]
    if len(exact_name_matches) == 1:
        return exact_name_matches[0]
    elif len(exact_name_matches) > 1:
        print(f"Trùng tên: có {len(exact_name_matches)} Trang trùng khớp tên «{target_clean}»:")
        for idx, p in enumerate(exact_name_matches, 1):
            print(f"  {idx}. {p.get('name', '')} (Mã Trang: {p.get('id', '')})")
        print("Hãy chỉ định rõ Mã Trang qua --trang <mã-Trang> để tránh nhầm lẫn.")
        sys.exit(1)

    # 3. Partial substring name match
    partial_matches = [
        p for p in pages
        if target_lower in p.get("name", "").strip().lower()
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]
    elif len(partial_matches) > 1:
        print(f"Không rõ ràng: có {len(partial_matches)} Trang khớp một phần với «{target_clean}»:")
        for idx, p in enumerate(partial_matches, 1):
            print(f"  {idx}. {p.get('name', '')} (Mã Trang: {p.get('id', '')})")
        print("Hãy chỉ định chính xác tên Trang hoặc dùng Mã Trang (--trang <mã-Trang>) để tránh đăng nhầm.")
        sys.exit(1)

    return None


def resolve_page(token: str, target: str):
    """Find specific page by name or id."""
    pages = get_pages(token)
    return resolve_page_from_list(pages, target)


def print_preview(page_name: str, page_id: str, content: str, link: str = None):
    """Display post preview safely to stdout."""
    border = "═" * 60
    print("\n" + border)
    print("  XEM TRƯỚC BÀI ĐĂNG FACEBOOK PAGE (CHƯA ĐĂNG THẬT)")
    print(border)
    print(f"  Trang đích : {page_name} (Mã Trang: {page_id})")
    if link:
        print(f"  Liên kết   : {link}")
    print("  Nội dung   :")
    print("  " + "-" * 56)
    for line in content.splitlines():
        print(f"  {line}")
    print("  " + "-" * 56)
    print("  [CỔNG PUBLISH] Đăng bài là công khai cho tất cả mọi người.")
    print("  Quy trình duyệt: In thử bản này -> đưa chủ doanh nghiệp duyệt -> chỉ chạy lại với cờ --dong-y khi chủ gật.")
    print(border + "\n")


def post_to_page(page: dict, content: str, link: str = None, confirmed: bool = False) -> int:
    """Execute live publishing to Facebook Page and verify immediately.
    Safety gate: confirmed must be True, otherwise abort without making network calls.
    """
    if not confirmed:
        print("LỖI AN TOÀN: Thiếu xác nhận confirmed=True trong hàm post_to_page. Không gọi mạng.")
        return 1

    page_id = page["id"]
    page_name = page.get("name", "Trang Facebook")
    page_token = page.get("access_token")

    if not page_token:
        print(f"Không lấy được token riêng cho Trang {page_name} ({page_id}).")
        return 1

    post_data = {"message": content}
    if link:
        post_data["link"] = link

    print(f"Đang gửi bài đăng lên Trang: {page_name} ({page_id})...")
    resp = api_request(f"{page_id}/feed", page_token, method="POST", data=post_data)

    if "error" in resp:
        err_msg = sanitize_error(resp["error"].get("message", "Lỗi không xác định"), page_token)
        print(f"Đăng bài thất bại: {err_msg}")
        return 1

    new_id = resp.get("id")
    print(f"Đăng bài thành công! Mã bài viết: {new_id}")

    # Read back from Facebook to verify
    print("Đang đọc ngược từ Facebook để xác nhận bài viết đã có mặt...")
    verify_resp = api_request(f"{new_id}", page_token, {"fields": "id,created_time,message,permalink_url"})
    if "error" in verify_resp:
        v_err = sanitize_error(verify_resp['error'].get('message', 'Lỗi'), page_token)
        print(f"Cảnh báo: Đã đăng nhưng không đọc lại được bài viết: {v_err}")
    else:
        created_time = verify_resp.get("created_time", "N/A")
        permalink = verify_resp.get("permalink_url", f"https://facebook.com/{new_id}")
        print(f"Xác nhận thành công: Bài viết đã trực tuyến lúc {created_time}.")
        print(f"Liên kết bài viết: {permalink}")

    # Record to out/posted.json
    root = find_repo_root()
    out_dir = root / "out"
    if check_output_dir(out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        record_file = out_dir / "posted.json"
        existing = []
        if record_file.is_file():
            try:
                with open(record_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.append({
            "post_id": new_id,
            "page_id": page_id,
            "page_name": page_name,
            "posted_at": datetime.datetime.now().isoformat(),
            "snippet": content[:80]
        })
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    else:
        print("Cảnh báo: Thư mục out/ không được git bỏ qua, từ chối ghi nhật ký bài đăng.")

    return 0


def run_self_test() -> int:
    """Run offline self-test suite without external network calls or modifying out/."""
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Test 1: Page resolution matching logic
            mock_pages = [
                {"id": "999000111", "name": "Dự Án Xanh", "access_token": "mock-t1"},
                {"id": "999000222", "name": "Dịch Vụ Tư Vấn", "access_token": "mock-t2"},
                {"id": "999000333", "name": "Dịch Vụ Tư Vấn Chiến Lược", "access_token": "mock-t3"}
            ]
            # By exact ID
            p_id = resolve_page_from_list(mock_pages, "999000111")
            assert p_id is not None and p_id["name"] == "Dự Án Xanh"

            # By exact name
            p_exact = resolve_page_from_list(mock_pages, "Dự Án Xanh")
            assert p_exact is not None and p_exact["id"] == "999000111"

            # By unique partial name
            p_unique = resolve_page_from_list(mock_pages, "Chiến Lược")
            assert p_unique is not None and p_unique["id"] == "999000333"

            # Ambiguous partial match -> must exit code 1
            captured_io = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured_io
            ambig_code = None
            try:
                resolve_page_from_list(mock_pages, "Tư Vấn")
            except SystemExit as exc:
                ambig_code = exc.code
            finally:
                sys.stdout = old_stdout
            assert ambig_code == 1, f"Ambiguous page match must exit code 1, got {ambig_code}"
            assert "Không rõ ràng: có 2 Trang" in captured_io.getvalue(), "Must list matching pages"

            # Test 2: Check missing token exit code 2
            dummy_missing = os.path.join(tmp_dir, "khong-ton-tai-kiem-thu-token")
            cap_miss = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = cap_miss
            try:
                load_token(dummy_missing)
                assert False, "Should have exited with code 2"
            except SystemExit as exc:
                assert exc.code == 2, f"Expected exit code 2, got {exc.code}"
            finally:
                sys.stdout = old_stdout

            # Test 3a: Fake short token (< 30 chars) -> exits code 2 without leaking token
            fake_short = "EAAshort"
            cap_short = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = cap_short
            exit_short = None
            try:
                validate_token_shape(fake_short)
            except SystemExit as exc:
                exit_short = exc.code
            finally:
                sys.stdout = old_stdout
            assert exit_short == 2, "Short token must exit code 2"
            assert "EAAshort" not in cap_short.getvalue(), "Short token must not leak"

            # Test 3b: Fake token with newline -> exits code 2 without leaking token
            fake_token = "EAAB99988812345678901234567890\n777xyz"
            cap_io = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = cap_io
            t_exit = None
            try:
                validate_token_shape(fake_token)
            except SystemExit as exc:
                t_exit = exc.code
            finally:
                sys.stdout = old_stdout
            assert t_exit == 2, f"Expected exit code 2, got {t_exit}"
            assert "EAAB999888" not in cap_io.getvalue(), "Fake token must not leak in error"

            # Test 4: Write gate inside post_to_page function
            cap_gate = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = cap_gate
            try:
                gate_res = post_to_page(mock_pages[0], "Sample content", confirmed=False)
            finally:
                sys.stdout = old_stdout
            assert gate_res == 1, "post_to_page without confirmed=True must abort with 1"
            assert "LỖI AN TOÀN" in cap_gate.getvalue(), "Must print safety error"

            # Test 5: Path resolution logic
            old_env = os.environ.get("META_PAGE_TOKEN_FILE")
            test_env_path = os.path.join(tmp_dir, "env-token")
            try:
                os.environ["META_PAGE_TOKEN_FILE"] = test_env_path
                assert get_token_file_path() == test_env_path
            finally:
                if old_env is not None:
                    os.environ["META_PAGE_TOKEN_FILE"] = old_env
                else:
                    os.environ.pop("META_PAGE_TOKEN_FILE", None)

        # Test 6: Output dir verification (checks git ignore status without creating any disk folders)
        root = find_repo_root()
        out_dir = root / "out"
        assert check_output_dir(out_dir), "out/ directory must be ignored by git"

        print("ĐẠT  khớp Trang chính xác và từ chối chọn khi khớp một phần ra từ 2 Trang trở lên")
        print("ĐẠT  phát hiện thiếu chìa và thoát mã 2 có câu hướng dẫn")
        print("ĐẠT  chìa giả dưới 30 ký tự bị từ chối mã 2 và không in chìa")
        print("ĐẠT  chìa giả có xuống dòng ở giữa bị chặn mã 2 và không in chìa")
        print("ĐẠT  cổng an toàn nằm trong hàm post_to_page (chặn khi thiếu confirmed=True)")
        print("ĐẠT  thư mục out/ được git bảo vệ không đưa lên kho (tự kiểm không tạo tệp)")
        print("ĐẠT  phân giải đường dẫn chìa qua biến môi trường")
        print("7/7 đạt")
        return 0
    except (AssertionError, Exception) as err:
        msg = str(err) if str(err) else "điều kiện kiểm thử không đạt"
        print(f"HỎNG  tự kiểm tra: {msg}")
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trang", help="Tên hoặc mã Trang Facebook cần đăng")
    parser.add_argument("--noi-dung", help="Nội dung bài viết")
    parser.add_argument("--tep-noi-dung", help="Đường dẫn tệp chứa nội dung bài viết")
    parser.add_argument("--link", help="Đường dẫn URL đính kèm bài viết (tuỳ chọn)")
    parser.add_argument("--dong-y", action="store_true", help="Xác nhận đăng bài thật lên Trang")
    parser.add_argument("--liet-ke", action="store_true", help="Liệt kê danh sách Trang mà chìa quản lý")
    parser.add_argument("--tu-kiem", action="store_true", help="Chạy tự kiểm tra nội bộ (không cần mạng)")
    args = parser.parse_args()

    if args.tu_kiem:
        return run_self_test()

    token_file = get_token_file_path()
    token = load_token(token_file)

    if args.liet_ke:
        pages = get_pages(token)
        print(f"Danh sách Trang quản lý ({len(pages)} Trang):")
        for idx, p in enumerate(pages, 1):
            print(f"  {idx:>2}. {p.get('name', 'Không rõ'):<32} (Mã Trang: {p.get('id', '0')})")
        return 0

    if not args.trang:
        print("Thiếu tham số --trang. Dùng --liet-ke để xem danh sách Trang, hoặc --help để xem hướng dẫn.")
        return 1

    content = ""
    if args.noi_dung:
        content = args.noi_dung
    elif args.tep_noi_dung:
        tep_path = pathlib.Path(args.tep_noi_dung)
        if not tep_path.is_file():
            print(f"Không tìm thấy tệp nội dung: {args.tep_noi_dung}")
            return 1
        content = tep_path.read_text(encoding="utf-8")
    else:
        print("Thiếu nội dung bài đăng. Hãy dùng --noi-dung hoặc --tep-noi-dung.")
        return 1

    page = resolve_page(token, args.trang)
    if not page:
        print(f"Không tìm thấy Trang nào khớp với: «{args.trang}». Dùng --liet-ke để kiểm tra tên chính xác.")
        return 1

    # Safety gate: if not --dong-y, display preview and exit
    if not args.dong_y:
        print_preview(page.get("name", "Trang"), str(page.get("id")), content, args.link)
        return 0

    return post_to_page(page, content, args.link, confirmed=args.dong_y)


if __name__ == "__main__":
    sys.exit(main())
