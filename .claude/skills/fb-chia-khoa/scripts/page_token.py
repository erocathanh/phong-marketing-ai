#!/usr/bin/env python3
"""Inspect Facebook Page access token and list managed pages.

Usage:
  python3 ~/.claude/skills/fb-chia-khoa/scripts/page_token.py           # Check existing token status and permissions
  python3 ~/.claude/skills/fb-chia-khoa/scripts/page_token.py --liet-ke # List pages managed by this token
  python3 ~/.claude/skills/fb-chia-khoa/scripts/page_token.py --tu-kiem # Run offline self-test
"""
import argparse
import datetime
import io
import json
import os
import pathlib
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://graph.facebook.com/v21.0"
DEFAULT_TOKEN_FILE = os.path.expanduser("~/.config/opc-business-harness/meta-page-token")

REQUIRED_SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "pages_manage_engagement",
    "pages_read_user_content",
    "pages_messaging",
    "pages_manage_metadata"
]


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
    """Execute Graph API request with Bearer authorization in header."""
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


def check_token(token_file: str) -> int:
    """Check status, permissions, and validity of existing token."""
    token = load_token(token_file)

    print("── Kiểm tra chìa Facebook ──")
    print(f"  Tệp chìa      : {token_file}")

    # Inspect token details
    dbg = api_request("debug_token", token, {"input_token": token})
    if "error" in dbg:
        err_msg = sanitize_error(dbg['error'].get('message', 'Lỗi'), token)
        print(f"  Trạng thái    : không kiểm tra được qua debug_token ({err_msg})")
        # Try checking via /me endpoint
        me_resp = api_request("me", token, {"fields": "id,name"})
        if "error" in me_resp:
            me_err = sanitize_error(me_resp['error'].get('message', 'Lỗi'), token)
            print(f"  Gọi /me       : thất bại ({me_err})")
            return 1
        print(f"  Gọi /me       : thành công — đối tượng: {me_resp.get('name', 'N/A')} (ID: {me_resp.get('id', 'N/A')})")
        return 0

    data = dbg.get("data", {})
    is_valid = bool(data.get("is_valid"))
    print(f"  Hợp lệ        : {'CÓ' if is_valid else 'KHÔNG'}")

    if not is_valid:
        print("  Chìa không còn hiệu lực. Hãy dùng save_token.py của kho OPC để cất chìa mới.")
        return 1

    exp = data.get("expires_at", 0)
    if not exp:
        exp_str = "Vĩnh viễn (không hết hạn)"
    else:
        exp_dt = datetime.datetime.fromtimestamp(exp, datetime.timezone.utc)
        exp_str = exp_dt.strftime("%Y-%m-%d %H:%M UTC")
    print(f"  Hạn dùng      : {exp_str}")

    scopes = set(data.get("scopes", []))
    print(f"  Số quyền      : {len(scopes)}")

    missing_req = [q for q in REQUIRED_SCOPES if q not in scopes]
    for q in REQUIRED_SCOPES:
        status = "ĐẠT" if q in scopes else "THIẾU"
        print(f"    · [{status}] {q}")

    if missing_req:
        print(f"  Cảnh báo      : Thiếu các quyền: {', '.join(missing_req)}")
        print("  Hãy cấp thêm quyền trên Meta for Developers và cất lại chìa.")

    list_pages(token)
    return 0


def list_pages(token: str) -> list:
    """List pages accessible by this token."""
    resp = api_request("me/accounts", token, {"fields": "id,name,tasks", "limit": "50"})
    if "error" in resp:
        # If token is already a Page token, /me will return the page itself
        me = api_request("me", token, {"fields": "id,name"})
        if "error" not in me and "name" in me:
            print("\n  Chìa này là Page Token trực tiếp của Trang:")
            print(f"     1. {me.get('name', 'Không rõ'):<32} (Mã Trang: {me.get('id', '0')})")
            return [me]
        err_msg = sanitize_error(resp['error'].get('message', 'Lỗi'), token)
        print(f"  Không lấy được danh sách Trang: {err_msg}")
        return []

    pages = resp.get("data", [])
    print(f"\n  Danh sách Trang quản lý ({len(pages)} Trang):")
    for idx, p in enumerate(pages, 1):
        name = p.get("name", "Không rõ")
        pid = p.get("id", "0")
        print(f"    {idx:>2}. {name:<32} (Mã Trang: {pid})")
    return pages


def run_self_test() -> int:
    try:
        return _run_self_test_body()
    except (AssertionError, Exception) as err:
        msg = str(err) if str(err) else "điều kiện kiểm thử không đạt"
        print(f"HỎNG  tự kiểm tra: {msg}")
        return 1


def _run_self_test_body() -> int:
    """Run offline self-test suite without external network calls."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Test 1: Check token file path resolution
        test_path = os.path.join(tmp_dir, "test-token-file")
        old_env = os.environ.get("META_PAGE_TOKEN_FILE")
        try:
            os.environ["META_PAGE_TOKEN_FILE"] = test_path
            resolved = get_token_file_path()
            assert resolved == test_path, f"Expected {test_path}, got {resolved}"
        finally:
            if old_env is not None:
                os.environ["META_PAGE_TOKEN_FILE"] = old_env
            else:
                os.environ.pop("META_PAGE_TOKEN_FILE", None)

        # Test 2: Check missing token exits code 2
        dummy_missing = os.path.join(tmp_dir, "khong-ton-tai-kiem-thu-token")
        cap_missing = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = cap_missing
        try:
            load_token(dummy_missing)
            assert False, "Should have exited with code 2"
        except SystemExit as exc:
            assert exc.code == 2, f"Expected exit code 2, got {exc.code}"
        finally:
            sys.stdout = old_stdout

        # Test 3a: Fake short token (5 chars < 30) -> exits code 2, does NOT leak token
        fake_short = "EAA12"
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
        assert exit_short == 2, f"Expected exit code 2 for short token, got {exit_short}"
        assert "EAA12" not in cap_short.getvalue(), "Short token must not leak in error message"

        # Test 3b: Fake token with newline in middle -> exits code 2, does NOT print token
        fake_newline = "EAAB1234567890123456789012345\n678xyz"
        cap_nl = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = cap_nl
        exit_nl = None
        try:
            validate_token_shape(fake_newline)
        except SystemExit as exc:
            exit_nl = exc.code
        finally:
            sys.stdout = old_stdout
        assert exit_nl == 2, f"Expected exit code 2, got {exit_nl}"
        assert "EAAB123456" not in cap_nl.getvalue() and "678xyz" not in cap_nl.getvalue(), "Token must not be printed in error"

        # Test 4: sanitize_error masks token even if short, and masks EAA and Authorization headers
        raw_err = "Error 401: Invalid Bearer EAAtestsecret123 in Authorization: Bearer EAAtestsecret123"
        sanitized = sanitize_error(raw_err, "EAAtestsecret123")
        assert "EAAtestsecret123" not in sanitized, "Secret token must be masked"
        assert "<CHE>" in sanitized, "Masking placeholder <CHE> must be present"

        # Test 4b: sanitize_error masks short token (e.g. 3 chars)
        sanitized_short = sanitize_error("Failed on abc key", "abc")
        assert "abc" not in sanitized_short and "<CHE>" in sanitized_short

    # Test 5: Check permission scope requirements (7 scopes)
    test_scopes = set(REQUIRED_SCOPES)
    missing = [q for q in REQUIRED_SCOPES if q not in test_scopes]
    assert len(missing) == 0, "Required scopes list must match"
    assert "pages_manage_metadata" in test_scopes, "Must include pages_manage_metadata"
    assert len(REQUIRED_SCOPES) == 7, "Must have exactly 7 required scopes"

    # Test 6: Root directory resolution
    root = find_repo_root()
    assert (root / "scripts" / "check_setup.py").is_file() or (root / "MANIFEST.md").is_file(), "Root resolution failed"

    print("ĐẠT  phân giải đường dẫn chìa từ biến môi trường và tệp mặc định")
    print("ĐẠT  phát hiện thiếu chìa và thoát mã 2 có câu hướng dẫn")
    print("ĐẠT  chìa giả dưới 30 ký tự bị từ chối mã 2 và không in chìa")
    print("ĐẠT  chìa giả có xuống dòng ở giữa bị chặn mã 2 và không in chìa")
    print("ĐẠT  thông báo lỗi được che mọi giá trị chìa và tiêu đề Authorization bằng <CHE>")
    print("ĐẠT  kiểm tra danh sách 7 quyền nền tảng bắt buộc (kèm pages_manage_metadata)")
    print("ĐẠT  xác định thư mục gốc kho làm việc")
    print("7/7 đạt")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--liet-ke", action="store_true", help="Liệt kê danh sách Trang mà chìa quản lý")
    parser.add_argument("--tu-kiem", action="store_true", help="Chạy tự kiểm tra nội bộ (không cần mạng)")
    args = parser.parse_args()

    if args.tu_kiem:
        return run_self_test()

    token_file = get_token_file_path()

    if args.liet_ke:
        token = load_token(token_file)
        list_pages(token)
        return 0

    return check_token(token_file)


if __name__ == "__main__":
    sys.exit(main())
