#!/usr/bin/env python3
"""Read and reply to direct messages (inbox) on Facebook Page within 24h window.

Usage:
  python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --trang "<name-or-id>" --hop-thu                 # List conversations (read-only)
  python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --trang "<name-or-id>" --doc "<conv-id>"         # Read conversation messages
  python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --trang "<name-or-id>" --hoi-thoai "<id>" --tra-loi "..."          # Preview reply
  python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --trang "<name-or-id>" --hoi-thoai "<id>" --tra-loi "..." --dong-y # Send reply
  python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --liet-ke                                        # List managed pages
  python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --tu-kiem                                        # Run offline self-test
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
    """Validate token format: strip ends, reject if whitespace/newline/invalid char inside or < 30 chars.
    Never prints token value on failure.
    """
    token = raw_token.strip()
    if not token:
        print("Tệp chìa rỗng.")
        print("Hãy dùng tools/inbox-reader/save_token.py của kho OPC để cất chìa mới.")
        sys.exit(2)

    if len(token) < 30:
        print("Chìa truy cập quá ngắn (phải có ít nhất 30 ký tự).")
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


def api_request(path: str, token: str, params: dict = None, method: str = "GET", data: dict = None, is_json: bool = False) -> dict:
    """Execute Graph API request securely.
    Only allows requests to https://graph.facebook.com/ to prevent credential leakage.
    """
    if path.startswith("http://") or path.startswith("https://"):
        if not path.startswith("https://graph.facebook.com/"):
            return {"error": {"message": "Địa chỉ URL không hợp lệ (chỉ chấp nhận https://graph.facebook.com/)."}}
        url = path
    else:
        query_str = ""
        if params:
            query_str = "?" + urllib.parse.urlencode(params)
        url = f"{API_BASE}/{path.lstrip('/')}{query_str}"

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "MarketingWorkspace/1.0"
    }

    body = None
    if data is not None:
        if is_json:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
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


def parse_iso_time(time_str: str):
    """Parse ISO timestamp with timezone. Return None if missing, malformed, or missing timezone info."""
    if not time_str or not isinstance(time_str, str):
        return None
    clean = time_str.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            # Timestamp without timezone must be considered CLOSED, do NOT assume UTC
            return None
        return dt
    except Exception:
        return None


def check_24h_window(time_str: str) -> tuple:
    """Verify if timestamp is valid and within 24-hour window.
    Any uncertainty (missing time, invalid format, future time) => CLOSED (is_open=False).
    Returns (is_open: bool, hours: float).
    """
    if not time_str:
        return False, 999.0

    last_dt = parse_iso_time(time_str)
    if last_dt is None:
        return False, 999.0

    now_dt = datetime.datetime.now(datetime.timezone.utc)

    # Future time check: if time is in the future (> 60s skew allowance), reject
    if last_dt > now_dt + datetime.timedelta(seconds=60):
        return False, 999.0

    delta = now_dt - last_dt
    hours_ago = delta.total_seconds() / 3600.0

    if hours_ago < 0:
        return False, 999.0

    is_open = (hours_ago <= 24.0)
    return is_open, hours_ago


def get_customer_last_message_time(page_id: str, messages: list) -> tuple:
    """Find the latest message timestamp sent by customer (excluding Page's own replies).
    If missing timestamp, malformed, future timestamp, missing from.id, None, empty, or string "None":
    evaluates to CLOSED (is_open=False).
    Returns (is_open: bool, hours: float, message_detail: str).
    """
    if not messages:
        return False, 999.0, "Không có tin nhắn nào trong hội thoại"

    page_id_str = str(page_id).strip()
    customer_msgs = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        from_info = m.get("from")
        if not isinstance(from_info, dict):
            continue
        raw_id = from_info.get("id")
        if raw_id is None:
            continue
        sender_id = str(raw_id).strip()
        if not sender_id or sender_id.lower() == "none":
            # Missing from.id, None, empty, or string "None": cannot verify sender -> skip
            continue
        if sender_id != page_id_str:
            customer_msgs.append(m)

    if not customer_msgs:
        return False, 999.0, "Không tìm thấy tin nhắn nào của khách hàng"

    # Sort by created_time descending
    def _msg_sort_key(m):
        t = m.get("created_time")
        return t if isinstance(t, str) else ""

    customer_msgs.sort(key=_msg_sort_key, reverse=True)
    latest_msg = customer_msgs[0]
    latest_time = latest_msg.get("created_time")
    if not latest_time or not isinstance(latest_time, str):
        return False, 999.0, "Tin nhắn của khách thiếu thời gian tạo"

    is_open, hours = check_24h_window(latest_time)
    return is_open, hours, latest_time


def check_customer_24h_window(page: dict, conv_id: str) -> tuple:
    """Verify if the latest message sent by the CUSTOMER is within 24 hours.
    Paginates until customer message is found or messages are exhausted.
    Returns (is_open: bool, hours: float, message_detail: str).
    """
    page_id = str(page.get("id", "")).strip()
    page_token = page.get("access_token")

    url = f"{conv_id}/messages"
    params = {"fields": "from,created_time", "limit": "25"}

    while url:
        resp = api_request(url, page_token, params=params)
        params = None  # subsequent paging URLs already contain params
        if "error" in resp:
            err_msg = sanitize_error(resp["error"].get("message", "Lỗi đọc tin nhắn"), page_token)
            return False, 999.0, f"Lỗi đọc tin nhắn: {err_msg}"

        msgs = resp.get("data", [])
        if not msgs:
            break

        is_open, hours, detail = get_customer_last_message_time(page_id, msgs)
        if detail != "Không tìm thấy tin nhắn nào của khách hàng":
            return is_open, hours, detail

        paging = resp.get("paging", {})
        url = paging.get("next")
        if not url:
            break
        if not str(url).startswith("https://graph.facebook.com/"):
            return False, 999.0, "Địa chỉ phân trang không hợp lệ (không phải Graph API)"

    return False, 999.0, "Không tìm thấy tin nhắn nào của khách hàng"


def list_inbox(page: dict) -> int:
    """List recent conversations with latest activity time."""
    page_id = page["id"]
    page_name = page.get("name", "Trang Facebook")
    page_token = page.get("access_token")

    resp = api_request(f"{page_id}/conversations", page_token, {"fields": "id,updated_time,senders,unread_count", "limit": "20"})
    if "error" in resp:
        err_msg = sanitize_error(resp['error'].get('message', 'Lỗi'), page_token)
        print(f"Lỗi truy vấn hộp thư: {err_msg}")
        return 1

    convs = resp.get("data", [])
    print(f"\nHộp thư Trang {page_name} ({len(convs)} hội thoại gần nhất):")
    print(f"{'Mã hội thoại':<25} | {'Người gửi':<20} | {'Thời gian':<20} | {'Hoạt động cuối'}")
    print("-" * 80)

    for c in convs:
        cid = c.get("id", "N/A")
        updated = c.get("updated_time", "")
        senders = ", ".join(s.get("name", "Khách") for s in c.get("senders", {}).get("data", []))
        is_open, hours = check_24h_window(updated)
        status = f"Gần đây ({hours:.1f}h trước)" if is_open else f"Cách đây ({hours:.1f}h)"
        print(f"{cid:<25} | {senders:<20} | {updated[:19]:<20} | {status}")

    print("\nLưu ý: Bảng trên hiển thị «hoạt động cuối» của hội thoại.")
    print("Facebook chỉ cho phép gửi tin nhắn trong vòng 24 giờ kể từ tin nhắn cuối do CHÍNH KHÁCH HÀNG gửi.")
    print("Dùng lệnh in thử (--hoi-thoai <mã> --tra-loi <nội-dung>) để hệ thống quét tin nhắn và xác định chính xác cửa sổ 24 giờ của khách trước khi gửi.")
    return 0


def read_conversation(page: dict, conv_id: str) -> int:
    """Read all messages in a specific conversation and write to out/<page_id>/fanpage-inbox."""
    page_id = str(page.get("id", "0")).strip()
    page_name = page.get("name", "Trang Facebook")
    page_token = page.get("access_token")

    root = find_repo_root()
    out_dir = root / "out" / page_id / "fanpage-inbox"
    out_dir.mkdir(parents=True, exist_ok=True)

    clean_id = conv_id.replace("t_", "").replace("/", "_")
    conv_file = out_dir / f"hoi-thoai-{clean_id}.json"

    if not check_file_safe_to_write(conv_file):
        print("Lỗi an toàn: Tệp đầu ra không được git bỏ qua hoặc đang bị git theo dõi. Từ chối ghi dữ liệu khách hàng.")
        return 1

    resp = api_request(f"{conv_id}/messages", page_token, {"fields": "id,created_time,from,to,message", "limit": "50"})
    if "error" in resp:
        err_msg = sanitize_error(resp['error'].get('message', 'Lỗi'), page_token)
        print(f"Lỗi đọc nội dung hội thoại: {err_msg}")
        return 1

    msgs = resp.get("data", [])
    msgs.sort(key=lambda m: m.get("created_time", ""))

    print(f"\nChi tiết hội thoại {conv_id} trên Trang {page_name} ({len(msgs)} tin nhắn):")
    print("-" * 65)
    for m in msgs:
        sender = m.get("from", {}).get("name", "Người dùng")
        time_str = m.get("created_time", "")[:19]
        text = m.get("message", "")
        print(f"[{time_str}] {sender}: {text}")
    print("-" * 65)

    with open(conv_file, "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu bản sao lưu hội thoại vào: {conv_file}")
    return 0


def print_reply_preview(page_name: str, conv_id: str, reply_text: str, is_open: bool = None, hours: float = None):
    """Display reply preview safely to stdout."""
    border = "═" * 60
    print("\n" + border)
    print("  XEM TRƯỚC TIN NHẮN TRẢ LỜI KHÁCH HÀNG (CHƯA GỬI THẬT)")
    print(border)
    print(f"  Trang gửi      : {page_name}")
    print(f"  Mã hội thoại   : {conv_id}")
    if is_open is None or hours is None:
        window_status = "chưa kiểm cửa sổ 24 giờ"
    elif is_open:
        window_status = f"CÒN HẠN ({hours:.1f}h)"
    else:
        window_status = f"QUÁ HẠN ({hours:.1f}h) — KHÔNG ĐƯỢC GỬI"
    print(f"  Cửa sổ 24 giờ  : {window_status}")
    print("  Nội dung tin   :")
    print("  " + "-" * 56)
    for line in reply_text.splitlines():
        print(f"  {line}")
    print("  " + "-" * 56)
    print("  [CỔNG CUSTOMER-MESSAGE] Tin nhắn sẽ gửi trực tiếp vào hộp thư khách hàng.")
    print("  Quy trình duyệt: In thử bản này -> đưa chủ doanh nghiệp duyệt -> chỉ chạy lại với cờ --dong-y khi chủ gật.")
    if is_open is False:
        print("  CẢNH BÁO: Đã quá hạn 24 giờ kể từ tin nhắn của khách. Facebook sẽ từ chối gửi tin nhắn này.")
    print(border + "\n")


def send_reply(page: dict, conv_id: str, reply_text: str, confirmed: bool = False) -> int:
    """Send reply to conversation after verifying 24-hour window from customer's latest message.
    Safety gate: confirmed must be True, otherwise abort without making network calls.
    """
    if not confirmed:
        print("LỖI AN TOÀN: Thiếu xác nhận confirmed=True trong hàm send_reply. Không gọi mạng.")
        return 1

    page_name = page.get("name", "Trang Facebook")
    page_token = page.get("access_token")

    # Verify 24-hour window from customer's latest message
    is_open, hours, latest_time = check_customer_24h_window(page, conv_id)
    if not is_open:
        print(f"LỖI AN TOÀN: Tin nhắn gần nhất của khách hàng đã cách đây {hours:.1f} giờ (> 24 giờ hoặc không xác minh được).")
        print("Chính sách của Facebook nghiêm cấm gửi tin nhắn ngoài cửa sổ 24 giờ. Lệnh bị huỷ.")
        return 1

    print(f"Đang gửi tin nhắn tới hội thoại {conv_id} từ Trang {page_name}...")
    resp = api_request(
        f"{conv_id}/messages",
        page_token,
        method="POST",
        data={"message": reply_text}
    )

    if "error" in resp:
        err_msg = sanitize_error(resp['error'].get('message', 'Lỗi'), page_token)
        print(f"Gửi tin nhắn thất bại: {err_msg}")
        return 1

    msg_id = resp.get("id")
    print(f"Gửi tin nhắn thành công! Mã tin nhắn: {msg_id}")
    return 0


def run_self_test() -> int:
    try:
        return _run_self_test_body()
    except (AssertionError, Exception) as err:
        msg = str(err) if str(err) else "điều kiện kiểm thử không đạt"
        print(f"HỎNG  tự kiểm tra: {msg}")
        return 1


def _run_self_test_body() -> int:
    """Run offline self-test suite without external network calls."""
    now = datetime.datetime.now(datetime.timezone.utc)
    page_id = "999888777"

    # Test 1: Standard 24h window calculation
    recent_time = (now - datetime.timedelta(hours=2)).isoformat()
    expired_time = (now - datetime.timedelta(hours=26)).isoformat()

    is_open1, h1 = check_24h_window(recent_time)
    is_open2, h2 = check_24h_window(expired_time)
    assert is_open1 is True, "Recent conversation should be within 24h"
    assert is_open2 is False, "Expired conversation should exceed 24h"

    # Test 2: Các ca an toàn cửa sổ 24 giờ:
    # Ca 2a: Thiếu giờ => đóng
    mock_missing_time = [{"id": "m1", "from": {"id": "c1"}, "created_time": None}]
    is_open_m, _, _ = get_customer_last_message_time(page_id, mock_missing_time)
    assert is_open_m is False, "Ca 2a: Thiếu giờ phải coi là ĐÓNG"

    # Ca 2b: Giờ tương lai => đóng
    mock_future_time = [{"id": "m2", "from": {"id": "c1"}, "created_time": (now + datetime.timedelta(hours=5)).isoformat()}]
    is_open_f, _, _ = get_customer_last_message_time(page_id, mock_future_time)
    assert is_open_f is False, "Ca 2b: Giờ tương lai phải coi là ĐÓNG"

    # Ca 2c: Thiếu from.id / from.id=None / from.id='None' => đóng
    mock_no_from_id = [{"id": "m3", "from": {"name": "Khách ẩn danh"}, "created_time": recent_time}]
    is_open_nf, _, _ = get_customer_last_message_time(page_id, mock_no_from_id)
    assert is_open_nf is False, "Ca 2c: Thiếu from.id phải coi là ĐÓNG"

    mock_none_id = [{"id": "m3a", "from": {"id": None, "name": "Khách ẩn"}, "created_time": recent_time}]
    is_open_none, _, _ = get_customer_last_message_time(page_id, mock_none_id)
    assert is_open_none is False, "Ca 2c-bis: from.id=None phải coi là ĐÓNG"

    mock_str_none_id = [{"id": "m3b", "from": {"id": "None", "name": "Khách ẩn"}, "created_time": recent_time}]
    is_open_snone, _, _ = get_customer_last_message_time(page_id, mock_str_none_id)
    assert is_open_snone is False, "Ca 2c-ter: from.id='None' phải coi là ĐÓNG"

    # Ca 2d: Giờ thiếu múi giờ => coi là ĐÓNG, không tự gán UTC
    mock_no_tz = [{"id": "m3c", "from": {"id": "c1"}, "created_time": "2026-10-14T10:00:00"}]
    is_open_ntz, _, _ = get_customer_last_message_time(page_id, mock_no_tz)
    assert is_open_ntz is False, "Ca 2d: Giờ thiếu múi giờ phải coi là ĐÓNG"

    # Ca 2e: Không có tin nào của khách => đóng
    mock_no_customer = [{"id": "m4", "from": {"id": page_id}, "created_time": recent_time}]
    is_open_nc, _, _ = get_customer_last_message_time(page_id, mock_no_customer)
    assert is_open_nc is False, "Ca 2e: Không có tin của khách phải coi là ĐÓNG"

    # Test 3: Khách gửi quá hạn nhưng Trang mới gửi 1h trước => PHẢI CHẶN (đo theo khách)
    mock_msgs_expired = [
        {"id": "m5", "from": {"id": page_id, "name": "Trang ABC"}, "created_time": (now - datetime.timedelta(hours=1)).isoformat()},
        {"id": "m6", "from": {"id": "guest_001", "name": "Khách Nguyễn Văn A"}, "created_time": (now - datetime.timedelta(hours=30)).isoformat()}
    ]
    is_open_cust1, h_cust1, _ = get_customer_last_message_time(page_id, mock_msgs_expired)
    assert is_open_cust1 is False, "Trang nhắn 1 giờ trước nhưng khách nhắn 30 giờ trước ⇒ phải chặn"
    assert h_cust1 >= 29.9, f"Cửa sổ phải đo theo khách (~30h), nhận được {h_cust1}"

    # Test 4: Khách gửi hợp lệ trong 24h => ĐẠT
    mock_msgs_valid = [
        {"id": "m7", "from": {"id": page_id, "name": "Trang ABC"}, "created_time": (now - datetime.timedelta(hours=1)).isoformat()},
        {"id": "m8", "from": {"id": "guest_002", "name": "Khách Trần B"}, "created_time": (now - datetime.timedelta(hours=4)).isoformat()}
    ]
    is_open_cust2, h_cust2, _ = get_customer_last_message_time(page_id, mock_msgs_valid)
    assert is_open_cust2 is True, "Khách nhắn 4 giờ trước phải còn hạn"

    # Test 5: Phân trang - paging.next trỏ ra ngoài Graph API bị từ chối
    bad_req = api_request("https://evil.com/fake-graph", "mock-token")
    assert "error" in bad_req and "Địa chỉ URL không hợp lệ" in bad_req["error"]["message"]

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Test 6: Check missing token exit code 2
        dummy_missing = os.path.join(tmp_dir, "khong-ton-tai-kiem-thu-token")
        try:
            load_token(dummy_missing)
            assert False, "Should have exited with code 2"
        except SystemExit as exc:
            assert exc.code == 2, f"Expected exit code 2, got {exc.code}"

        # Test 7: Fake token with newline -> exits 2 without leaking
        fake_token = "EAAB444555\n666xyz"
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
        assert "EAAB444555" not in cap_io.getvalue()

        # Test 8: Short token (< 30 chars, e.g. 5 chars) -> exits 2 without leaking
        short_token = "EAAB4"
        cap_short = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = cap_short
        s_exit = None
        try:
            validate_token_shape(short_token)
        except SystemExit as exc:
            s_exit = exc.code
        finally:
            sys.stdout = old_stdout
        assert s_exit == 2
        assert short_token not in cap_short.getvalue()
        assert "quá ngắn" in cap_short.getvalue()

        # Test 9: sanitize_error masks any non-empty token
        assert sanitize_error("Lỗi với chìa EAAB4", "EAAB4") == "Lỗi với chìa <CHE>"
        assert sanitize_error("Lỗi abc", "abc") == "Lỗi <CHE>"

        # Test 10: Write gate inside send_reply function
        cap_gate = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = cap_gate
        try:
            gate_res = send_reply({"id": page_id, "name": "Mock"}, "t_123", "Nội dung", confirmed=False)
        finally:
            sys.stdout = old_stdout
        assert gate_res == 1, "send_reply without confirmed=True must abort with 1"
        assert "LỖI AN TOÀN" in cap_gate.getvalue()

        # Test 11: Page resolution strict matching
        mock_pages = [
            {"id": "999000111", "name": "Dự Án Xanh", "access_token": "mock-t1"},
            {"id": "999000222", "name": "Dịch Vụ Tư Vấn", "access_token": "mock-t2"},
            {"id": "999000333", "name": "Dịch Vụ Tư Vấn Khác", "access_token": "mock-t3"}
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

        # Test 12: Path resolution logic
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

    # Test 13: Output file git check-ignore verification (without creating directories in out/)
    root = find_repo_root()
    test_inbox_file = root / "out" / "mock_page_id" / "fanpage-inbox" / "hoi-thoai-123.json"
    existed_before = (root / "out" / "mock_page_id").exists()
    assert check_file_safe_to_write(test_inbox_file), "Output file in out/ must be ignored by git"
    existed_after = (root / "out" / "mock_page_id").exists()
    assert existed_before == existed_after, "Self-test must not change directory existence state in out/"

    print("ĐẠT  kiểm soát chính xác cửa sổ 24 giờ theo tin nhắn cuối của khách hàng")
    print("ĐẠT  các ca an toàn cửa sổ 24 giờ: thiếu giờ / giờ tương lai / thiếu from.id / from.id None / thiếu múi giờ / không có tin khách đều đóng")
    print("ĐẠT  khớp Trang chính xác và từ chối chọn khi khớp một phần ra từ 2 Trang trở lên")
    print("ĐẠT  phát hiện thiếu chìa và thoát mã 2 có câu hướng dẫn")
    print("ĐẠT  chìa giả có xuống dòng ở giữa hoặc quá ngắn (< 30 ký tự) bị chặn mã 2 và không in chìa")
    print("ĐẠT  che mọi giá trị chìa khác rỗng qua hàm sanitize_error")
    print("ĐẠT  phân trang và api_request chỉ đi theo https://graph.facebook.com/")
    print("ĐẠT  cổng an toàn nằm trong hàm send_reply (chặn khi thiếu confirmed=True)")
    print("ĐẠT  kiểm đúng tệp ghi dữ liệu khách hàng được git bảo vệ qua git check-ignore (không tạo thư mục trong out/)")
    print("ĐẠT  phân giải đường dẫn chìa qua biến môi trường")
    print("10/10 đạt")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trang", help="Tên hoặc mã Trang Facebook cần thao tác")
    parser.add_argument("--hop-thu", action="store_true", help="Xem danh sách các hội thoại trong hộp thư")
    parser.add_argument("--doc", help="Mã hội thoại cần đọc tin nhắn")
    parser.add_argument("--hoi-thoai", help="Mã hội thoại cần gửi tin nhắn trả lời")
    parser.add_argument("--tra-loi", help="Nội dung tin nhắn trả lời khách hàng")
    parser.add_argument("--dong-y", action="store_true", help="Xác nhận gửi tin nhắn thật tới khách hàng")
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

    # Sending reply
    if args.hoi_thoai or args.tra_loi:
        if not args.hoi_thoai or not args.tra_loi:
            print("Cần cung cấp cả --hoi-thoai <mã-hội-thoại> và --tra-loi <nội-dung>.")
            return 1

        if not args.dong_y:
            is_open, hours = None, None
            try:
                open_flag, h, _ = check_customer_24h_window(page, args.hoi_thoai)
                if h < 900:
                    is_open, hours = open_flag, h
            except Exception:
                pass
            print_reply_preview(page.get("name", "Trang"), args.hoi_thoai, args.tra_loi, is_open, hours)
            return 0

        return send_reply(page, args.hoi_thoai, args.tra_loi, confirmed=args.dong_y)

    # Read specific conversation
    if args.doc:
        return read_conversation(page, args.doc)

    # Default to inbox list
    return list_inbox(page)


if __name__ == "__main__":
    sys.exit(main())
