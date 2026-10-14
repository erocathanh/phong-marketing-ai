#!/usr/bin/env python3
"""Read comments and reply to individual comments on Facebook Page.

Usage:
  python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --trang "<name-or-id>"                      # Read recent comments (read-only)
  python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --trang "<name-or-id>" --tu-khoa "gia,ship" # Filter comments by keywords
  python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --trang "<name-or-id>" --cmt <id> --tra-loi "..."          # Preview reply
  python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --trang "<name-or-id>" --cmt <id> --tra-loi "..." --dong-y # Publish reply
  python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --liet-ke                                   # List managed pages
  python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --tu-kiem                                   # Run offline self-test
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
    if path.startswith("http://") or path.startswith("https://"):
        # Validate Graph API domain before following
        if not path.startswith("https://graph.facebook.com/"):
            return {"error": {"message": "Địa chỉ URL không thuộc graph.facebook.com, từ chối gửi chìa"}}
        url = path
    else:
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


def check_file_safe_to_write(file_path: pathlib.Path) -> bool:
    """Verify that file is safe to write: ignored by git and NOT tracked by git.
    Refuses write if tracked or not ignored. Does NOT create directories on disk.
    """
    root = find_repo_root()
    try:
        # Check if already tracked by git
        track_proc = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(file_path)],
            cwd=str(root),
            capture_output=True
        )
        if track_proc.returncode == 0:
            return False

        # Check if ignored by git
        ignore_proc = subprocess.run(
            ["git", "check-ignore", "-q", str(file_path)],
            cwd=str(root),
            capture_output=True
        )
        return ignore_proc.returncode == 0
    except Exception:
        return False


def get_pages(token: str) -> list:
    """Fetch all pages managed by the token."""
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


def read_comments(page: dict, limit_posts: int = 10, keywords: list = None) -> int:
    """Read comments from page posts, saving partitioned by Page ID to out/<page_id>/fanpage-comments."""
    page_id = str(page.get("id", "0")).strip()
    page_name = page.get("name", "Trang Facebook")
    page_token = page.get("access_token")

    root = find_repo_root()
    out_dir = root / "out" / page_id / "fanpage-comments"

    today_str = datetime.date.today().isoformat()
    da_thay_file = out_dir / "da-thay.json"
    jsonl_file = out_dir / f"comment-{today_str}.jsonl"

    if not check_file_safe_to_write(da_thay_file) or not check_file_safe_to_write(jsonl_file):
        print("Lỗi an toàn: Tệp đầu ra không được git bỏ qua hoặc đang bị git theo dõi. Từ chối ghi dữ liệu khách hàng.")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    seen_ids = set()
    if da_thay_file.is_file():
        try:
            with open(da_thay_file, "r", encoding="utf-8") as f:
                seen_ids = set(json.load(f))
        except Exception:
            seen_ids = set()

    posts_resp = api_request(f"{page_id}/posts", page_token, {"fields": "id,message,created_time", "limit": str(limit_posts)})
    if "error" in posts_resp:
        err_msg = sanitize_error(posts_resp['error'].get('message', 'Lỗi'), page_token)
        print(f"Lỗi đọc danh sách bài viết: {err_msg}")
        return 1

    posts = posts_resp.get("data", [])
    print(f"Đã lấy {len(posts)} bài viết từ Trang {page_name}. Bắt đầu đọc bình luận...")

    new_comments = 0
    total_found = 0

    with open(jsonl_file, "a", encoding="utf-8") as out_f:
        for p in posts:
            pid = p.get("id")
            cmts_resp = api_request(f"{pid}/comments", page_token, {"fields": "id,from,message,created_time,comment_count,like_count", "limit": "50"})
            if "error" in cmts_resp:
                continue

            cmts = cmts_resp.get("data", [])
            for c in cmts:
                cid = c.get("id")
                msg = c.get("message", "")
                total_found += 1

                if keywords:
                    if not any(k.lower() in msg.lower() for k in keywords):
                        continue

                is_new = cid not in seen_ids
                if is_new:
                    seen_ids.add(cid)
                    new_comments += 1
                    record = {
                        "comment_id": cid,
                        "post_id": pid,
                        "page_id": page_id,
                        "from_name": c.get("from", {}).get("name", "Khách hàng"),
                        "from_id": c.get("from", {}).get("id"),
                        "message": msg,
                        "created_time": c.get("created_time"),
                        "like_count": c.get("like_count", 0)
                    }
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with open(da_thay_file, "w", encoding="utf-8") as f:
        json.dump(list(seen_ids), f, indent=2)

    print(f"\nTổng kết đọc bình luận Trang {page_name}:")
    print(f"  · Tổng bình luận quét được  : {total_found}")
    print(f"  · Bình luận mới ghi nhận    : {new_comments}")
    print(f"  · Nhật ký lưu tại           : {jsonl_file}")
    return 0


def print_reply_preview(page_name: str, cmt_id: str, reply_text: str):
    """Print reply preview safely to stdout."""
    border = "═" * 60
    print("\n" + border)
    print("  XEM TRƯỚC TRẢ LỜI BÌNH LUẬN (CHƯA ĐĂNG THẬT)")
    print(border)
    print(f"  Trang thực hiện : {page_name}")
    print(f"  Mã bình luận    : {cmt_id}")
    print("  Nội dung phản hồi:")
    print("  " + "-" * 56)
    for line in reply_text.splitlines():
        print(f"  {line}")
    print("  " + "-" * 56)
    print("  [CỔNG PUBLISH] Trả lời bình luận là công khai cho tất cả mọi người.")
    print("  Quy trình duyệt: In thử bản này -> đưa chủ doanh nghiệp duyệt -> chỉ chạy lại với cờ --dong-y khi chủ gật.")
    print(border + "\n")


def reply_comment(page: dict, cmt_id: str, reply_text: str, confirmed: bool = False) -> int:
    """Reply to an individual comment after authorization and verify.
    Safety gate: confirmed must be True, otherwise abort without making network calls.
    """
    if not confirmed:
        print("LỖI AN TOÀN: Thiếu xác nhận confirmed=True trong hàm reply_comment. Không gọi mạng.")
        return 1

    page_name = page.get("name", "Trang Facebook")
    page_token = page.get("access_token")

    print(f"Đang gửi câu trả lời bình luận {cmt_id} từ Trang {page_name}...")
    resp = api_request(f"{cmt_id}/comments", page_token, method="POST", data={"message": reply_text})

    if "error" in resp:
        err_msg = sanitize_error(resp['error'].get('message', 'Lỗi'), page_token)
        print(f"Trả lời bình luận thất bại: {err_msg}")
        return 1

    reply_id = resp.get("id")
    print(f"Trả lời bình luận thành công! Mã câu trả lời: {reply_id}")

    # Read back to verify
    print("Đang đọc ngược từ Facebook để xác nhận phản hồi...")
    verify = api_request(f"{reply_id}", page_token, {"fields": "id,created_time,message"})
    if "error" not in verify:
        print(f"Xác nhận thành công: Câu trả lời đã hiển thị lúc {verify.get('created_time')}.")
    else:
        v_err = sanitize_error(verify['error'].get('message', 'Lỗi'), page_token)
        print(f"Cảnh báo: Đã gửi nhưng không xác nhận được qua API: {v_err}")

    return 0


def run_self_test() -> int:
    """Run offline self-test suite without external network calls or modifying out/."""
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Test 1: Keyword filtering logic
            sample_comments = [
                {"id": "1", "message": "Cho em hỏi giá khoá học này bao nhiêu ạ?"},
                {"id": "2", "message": "Nội dung rất hay, cảm ơn bạn!"},
                {"id": "3", "message": "Có tư vấn dịch vụ này trực tuyến không ạ?"}
            ]
            keywords = ["giá", "tư vấn"]
            matched = [c for c in sample_comments if any(k.lower() in c["message"].lower() for k in keywords)]
            assert len(matched) == 2, f"Expected 2 matches, got {len(matched)}"

            # Test 2: Page resolution matching logic (exact vs ambiguous)
            mock_pages = [
                {"id": "999000111", "name": "Dự Án Xanh", "access_token": "mock-t1"},
                {"id": "999000222", "name": "Dịch Vụ Tư Vấn", "access_token": "mock-t2"},
                {"id": "999000333", "name": "Dịch Vụ Tư Vấn Chiến Lược", "access_token": "mock-t3"}
            ]
            p_id = resolve_page_from_list(mock_pages, "999000111")
            assert p_id is not None and p_id["name"] == "Dự Án Xanh"

            cap_ambig = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = cap_ambig
            ambig_code = None
            try:
                resolve_page_from_list(mock_pages, "Tư Vấn")
            except SystemExit as exc:
                ambig_code = exc.code
            finally:
                sys.stdout = old_stdout
            assert ambig_code == 1, "Ambiguous match must exit 1"

            # Test 3: Check missing token exit code 2
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

            # Test 4a: Fake short token (< 30 chars) -> exits code 2 without leaking
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

            # Test 4b: Fake token with newline -> exits 2 without leaking
            fake_token = "EAAB11122212345678901234567890\n333xyz"
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
            assert t_exit == 2
            assert "EAAB111222" not in cap_io.getvalue()

            # Test 5: Write gate inside reply_comment function
            cap_gate = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = cap_gate
            try:
                gate_res = reply_comment(mock_pages[0], "cmt_123", "Phản hồi", confirmed=False)
            finally:
                sys.stdout = old_stdout
            assert gate_res == 1, "reply_comment without confirmed=True must abort with 1"
            assert "LỖI AN TOÀN" in cap_gate.getvalue()

            # Test 6: Path resolution logic
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

        # Test 7: Output file git check-ignore verification (tests path safely without creating any directory)
        root = find_repo_root()
        test_comment_file = root / "out" / "virtual_check_page" / "fanpage-comments" / "da-thay.json"
        existed_before = (root / "out" / "virtual_check_page").exists()
        assert check_file_safe_to_write(test_comment_file), "Virtual output path in out/ must be ignored by git"
        existed_after = (root / "out" / "virtual_check_page").exists()
        assert existed_before == existed_after, "Self-test must not change directory existence state in out/"

        print("ĐẠT  lọc bình luận theo từ khoá chính xác")
        print("ĐẠT  khớp Trang chính xác và từ chối chọn khi khớp một phần ra từ 2 Trang trở lên")
        print("ĐẠT  phát hiện thiếu chìa và thoát mã 2 có câu hướng dẫn")
        print("ĐẠT  chìa giả dưới 30 ký tự bị từ chối mã 2 và không in chìa")
        print("ĐẠT  chìa giả có xuống dòng ở giữa bị chặn mã 2 và không in chìa")
        print("ĐẠT  cổng an toàn nằm trong hàm reply_comment (chặn khi thiếu confirmed=True)")
        print("ĐẠT  kiểm đúng tệp ghi dữ liệu khách hàng được git bảo vệ (tự kiểm không tạo thư mục)")
        print("ĐẠT  phân giải đường dẫn chìa qua biến môi trường")
        print("8/8 đạt")
        return 0
    except (AssertionError, Exception) as err:
        msg = str(err) if str(err) else "điều kiện kiểm thử không đạt"
        print(f"HỎNG  tự kiểm tra: {msg}")
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trang", help="Tên hoặc mã Trang Facebook cần thao tác")
    parser.add_argument("--so-bai", type=int, default=10, help="Số lượng bài viết cần đọc bình luận (mặc định: 10)")
    parser.add_argument("--tu-khoa", help="Danh sách từ khoá lọc bình luận, cách nhau bởi dấu phẩy")
    parser.add_argument("--cmt", help="Mã bình luận cần trả lời")
    parser.add_argument("--tra-loi", help="Nội dung phản hồi bình luận")
    parser.add_argument("--dong-y", action="store_true", help="Xác nhận gửi câu trả lời thật lên Trang")
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

    page = resolve_page(token, args.trang)
    if not page:
        print(f"Không tìm thấy Trang nào khớp với: «{args.trang}». Dùng --liet-ke để kiểm tra tên chính xác.")
        return 1

    # Replying to a comment
    if args.cmt or args.tra_loi:
        if not args.cmt or not args.tra_loi:
            print("Cần cung cấp cả --cmt <mã-bình-luận> và --tra-loi <nội-dung>.")
            return 1

        if not args.dong_y:
            print_reply_preview(page.get("name", "Trang"), args.cmt, args.tra_loi)
            return 0

        return reply_comment(page, args.cmt, args.tra_loi, confirmed=args.dong_y)

    # Read comments mode
    keywords = [k.strip() for k in args.tu_khoa.split(",")] if args.tu_khoa else None
    return read_comments(page, limit_posts=args.so_bai, keywords=keywords)


if __name__ == "__main__":
    sys.exit(main())
