#!/usr/bin/env python3
"""Tạo khung lịch đăng 7 ngày cho Trang Facebook và Instagram.

Đầu vào: Mô tả ngắn doanh nghiệp, mục tiêu tuần, danh sách chủ đề, các ngày đăng.
Đầu ra:
  - out/lich-dang-7-ngay_vNN_YYYYMMDD.md: Bảng kế hoạch nội dung tuần dạng Markdown
  - out/lich-dang-7-ngay_vNN_YYYYMMDD.csv: Bảng dữ liệu 9 cột chi tiết

9 cột theo quy định:
  1. thứ trong tuần
  2. giờ đăng
  3. kênh (Trang Facebook hay Instagram)
  4. dạng bài
  5. chủ đề hoặc góc
  6. câu mở
  7. lời kêu gọi
  8. link gắn utm
  9. trạng thái (nháp / chờ duyệt / đã đăng)

Chạy không cần mạng.
Tự kiểm: python3 scripts/build_schedule.py --tu-kiem
"""
import argparse
import csv
import datetime
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, urlencode, urlparse


def find_repo_root() -> pathlib.Path:
    """Tìm thư mục gốc của kho marketing bằng cách dò ngược lên."""
    p = pathlib.Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "scripts" / "check_setup.py").is_file() and (parent / "MANIFEST.md").is_file():
            return parent
    return p.parents[3] if len(p.parents) > 3 else p.parent


ROOT = find_repo_root()
SAMPLE_INPUT = ROOT / 'references' / 'du-lieu-mau' / 'ke-hoach-tuan-mau.json'

COLUMNS_CSV = [
    'thu_trong_tuan',
    'gio_dang',
    'kenh',
    'dang_bai',
    'chu_de_goc',
    'cau_mo',
    'loi_keu_goi',
    'link_utm',
    'trang_thai'
]

COLUMNS_MD = [
    'Thứ trong tuần',
    'Giờ đăng',
    'Kênh',
    'Dạng bài',
    'Chủ đề hoặc góc',
    'Câu mở',
    'Lời kêu gọi',
    'Link gắn UTM',
    'Trạng thái'
]

DEFAULT_SCHEDULE_TEMPLATES = [
    {
        "thu": "Thứ Hai",
        "gio": "08:30",
        "kenh": "Trang Facebook",
        "dang_bai": "Chùm ảnh câu chuyện",
        "slug": "thu-hai-men-tro",
        "cau_mo": "Mỗi chiếc cốc mộc ra đời là một lần trò chuyện giữa đất sét và tro tự nhiên.",
        "loi_keu_goi": "Nhắn xưởng để chọn cho mình chiếc cốc ưng ý đầu tuần bạn nhé.",
        "trang_thai": "nháp"
    },
    {
        "thu": "Thứ Ba",
        "gio": "11:45",
        "kenh": "Instagram",
        "dang_bai": "Ảnh đơn cận cảnh",
        "slug": "thu-ba-am-tra",
        "cau_mo": "Một buổi trưa mát lành với tách trà hoa và mặt men rạn màu hạt dẻ.",
        "loi_keu_goi": "Lưu lại bài viết nếu bạn cũng mê những góc bàn trà mộc mạc.",
        "trang_thai": "nháp"
    },
    {
        "thu": "Thứ Tư",
        "gio": "19:30",
        "kenh": "Trang Facebook",
        "dang_bai": "Video ngắn hậu trường",
        "slug": "thu-tu-lo-cui",
        "cau_mo": "23 giờ đêm canh lửa bên lò củi đỏ rực: âm thanh củi lách tách thật bình yên.",
        "loi_keu_goi": "Bấm vào đường link để xem trọn bộ ảnh mẻ gốm vừa ra lò.",
        "trang_thai": "chờ duyệt"
    },
    {
        "thu": "Thứ Năm",
        "gio": "12:15",
        "kenh": "Trang Facebook",
        "dang_bai": "Mẹo hữu ích",
        "slug": "thu-nam-meo-gom",
        "cau_mo": "Cách dưỡng đồ gốm men tro để càng dùng càng lên nước bóng mịn tự nhiên.",
        "loi_keu_goi": "Chia sẻ cho bạn bè cùng yêu thích gốm thủ công.",
        "trang_thai": "nháp"
    },
    {
        "thu": "Thứ Sáu",
        "gio": "20:00",
        "kenh": "Instagram",
        "dang_bai": "Chùm ảnh phản hồi",
        "slug": "thu-sau-goc-khach",
        "cau_mo": "Góc đọc sách cuối tuần của một người bạn xưởng, giản dị mà an lòng.",
        "loi_keu_goi": "Gắn thẻ xưởng khi bạn khoe góc gốm của riêng mình nhé.",
        "trang_thai": "nháp"
    },
    {
        "thu": "Thứ Bảy",
        "gio": "09:00",
        "kenh": "Trang Facebook",
        "dang_bai": "Bài chia sẻ trải nghiệm",
        "slug": "thu-bay-workshop",
        "cau_mo": "Dành một sáng thứ Bảy buông điện thoại, chạm tay vào đất sét mát lành.",
        "loi_keu_goi": "Đăng ký workshop cuối tuần qua đường link bên dưới.",
        "trang_thai": "chờ duyệt"
    },
    {
        "thu": "Chủ Nhật",
        "gio": "15:00",
        "kenh": "Trang Facebook",
        "dang_bai": "Tâm tình cuối tuần",
        "slug": "chu-nhat-nhin-lai",
        "cau_mo": "Khép lại một tuần nhiều vội vã bằng một tách nước ấm trong lòng bàn tay.",
        "loi_keu_goi": "Hẹn gặp lại bạn vào tuần mới với những mẻ gốm mới.",
        "trang_thai": "nháp"
    }
]


def make_utm_link(target_url: str, source: str, campaign: str, content: str, medium: str = "organic") -> str:
    """Tạo link UTM theo chuẩn nội bộ."""
    clean_src = 'facebook' if 'facebook' in source.lower() else ('instagram' if 'instagram' in source.lower() else 'social')
    params = {
        'utm_source': clean_src,
        'utm_medium': medium,
        'utm_campaign': campaign,
        'utm_content': content
    }
    sep = '&' if '?' in target_url else '?'
    return target_url + sep + urlencode(params)


def build_schedule_data(plan_dict: dict) -> list:
    """Xây dựng 7 dòng lịch từ kế hoạch tuần."""
    target_url = plan_dict.get('trang_dich', 'https://example.com/workshop-gom')
    campaign = plan_dict.get('chien_dich', 'tuan-01')
    days = plan_dict.get('ngay_dang', ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"])
    topics = plan_dict.get('chu_de', [])

    schedule_rows = []
    for i, day in enumerate(days):
        tpl = DEFAULT_SCHEDULE_TEMPLATES[i % len(DEFAULT_SCHEDULE_TEMPLATES)]
        topic = topics[i] if i < len(topics) else tpl['cau_mo']
        link = make_utm_link(
            target_url=target_url,
            source=tpl['kenh'],
            campaign=campaign,
            content=tpl['slug'],
            medium="organic"
        )
        row = {
            'thu_trong_tuan': day,
            'gio_dang': tpl['gio'],
            'kenh': tpl['kenh'],
            'dang_bai': tpl['dang_bai'],
            'chu_de_goc': topic,
            'cau_mo': tpl['cau_mo'],
            'loi_keu_goi': tpl['loi_keu_goi'],
            'link_utm': link,
            'trang_thai': tpl['trang_thai']
        }
        schedule_rows.append(row)
    return schedule_rows


def export_markdown(rows: list, business_name: str, goal: str, out_path: pathlib.Path):
    """Xuất lịch đăng ra tệp Markdown với bảng đẹp và rõ ràng."""
    lines = [
        f"# Kế hoạch lịch đăng 7 ngày — {business_name}",
        "",
        f"**Mục tiêu tuần**: {goal}",
        "",
        "| " + " | ".join(COLUMNS_MD) + " |",
        "| " + " | ".join(["---"] * len(COLUMNS_MD)) + " |"
    ]
    for r in rows:
        row_cells = [
            r['thu_trong_tuan'],
            r['gio_dang'],
            r['kenh'],
            r['dang_bai'],
            r['chu_de_goc'].replace('|', '-'),
            r['cau_mo'].replace('|', '-'),
            r['loi_keu_goi'].replace('|', '-'),
            f"`{r['link_utm']}`",
            r['trang_thai']
        ]
        lines.append("| " + " | ".join(row_cells) + " |")

    lines.append("")
    lines.append("## Ghi chú triển khai")
    lines.append("- Trạng thái bài viết cần được cập nhật sau khi chủ doanh nghiệp duyệt.")
    lines.append("- Toàn bộ link đăng organic sử dụng tham số `utm_medium=organic` để phân biệt với quảng cáo trả phí.")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding='utf-8')


def export_csv(rows: list, out_path: pathlib.Path):
    """Xuất lịch đăng ra tệp CSV chuẩn UTF-8."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS_CSV, lineterminator='\n')
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def reserve_schedule_pair(target_dir: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """Giữ chỗ độc quyền đồng thời cả hai tệp Markdown và CSV cùng một số phiên bản."""
    target_dir = pathlib.Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y%m%d")
    for version in range(1, 100):
        v_str = f"v{version:02d}"
        md_candidate = target_dir / f"lich-dang-7-ngay_{v_str}_{today}.md"
        csv_candidate = target_dir / f"lich-dang-7-ngay_{v_str}_{today}.csv"
        try:
            fd_md = os.open(md_candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        try:
            fd_csv = os.open(csv_candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            os.close(fd_md)
            try:
                md_candidate.unlink()
            except OSError:
                pass
            continue
        os.close(fd_md)
        os.close(fd_csv)
        return md_candidate, csv_candidate
    raise RuntimeError("Vượt quá 99 bản nháp trong một ngày.")


def generate(input_path: pathlib.Path, out_dir: pathlib.Path = None) -> tuple[pathlib.Path, pathlib.Path]:
    """Đọc dữ liệu, kiểm tra hợp lệ, sau đó giữ chỗ độc quyền và xuất 2 tệp Markdown và CSV."""
    target_dir = pathlib.Path(out_dir) if out_dir else (ROOT / 'out')
    input_path = pathlib.Path(input_path)

    # 1. Đọc và kiểm tra dữ liệu đầu vào TRƯỚC khi giữ chỗ tệp
    raw_text = input_path.read_text(encoding='utf-8')
    data = json.loads(raw_text)
    rows = build_schedule_data(data)
    business = data.get('doanh_nghiep', 'Doanh nghiệp')
    goal = data.get('muc_tieu_tuan', 'Kế hoạch truyền thông tuần')

    # 2. Giữ chỗ độc quyền cặp tệp
    md_path, csv_path = reserve_schedule_pair(target_dir)

    # 3. Xuất lịch, nếu lỗi sau khi đã giữ chỗ thì xoá đúng cặp tệp do chính lượt đó vừa tạo
    try:
        export_markdown(rows, business, goal, md_path)
        export_csv(rows, csv_path)
        print(f"Đã tạo bảng Markdown: {md_path}")
        print(f"Đã tạo tệp CSV ({len(rows)} dòng, {len(COLUMNS_CSV)} cột): {csv_path}")
        return md_path, csv_path
    except Exception:
        for p in (md_path, csv_path):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def run_schedule(input_path: pathlib.Path, out_dir: pathlib.Path = None) -> tuple[pathlib.Path, pathlib.Path]:
    """Bí danh của generate phục vụ kiểm thử và gọi từ module khác."""
    return generate(input_path, out_dir)


def self_check() -> int:
    try:
        return _self_check_body()
    except (AssertionError, Exception) as err:
        msg = str(err) if str(err) else "điều kiện kiểm thử không đạt"
        print(f"HỎNG  tự kiểm tra: {msg}")
        return 1


def _self_check_body() -> int:
    """Tự kiểm tra offline không mạng."""
    import concurrent.futures

    if not SAMPLE_INPUT.is_file():
        print(f"HỎNG  không tìm thấy tệp mẫu {SAMPLE_INPUT}")
        return 1

    data = json.loads(SAMPLE_INPUT.read_text(encoding='utf-8'))
    rows = build_schedule_data(data)

    # 1. Đủ 7 dòng tương ứng 7 ngày
    ok1 = len(rows) == 7 and [r['thu_trong_tuan'] for r in rows] == data.get('ngay_dang')

    # 2. Đủ 9 cột dữ liệu
    ok2 = all(len(r.keys()) == 9 and all(k in r for k in COLUMNS_CSV) for r in rows)

    # 3. Mọi link UTM đều đúng tham số organic và chiến dịch
    ok3 = True
    for r in rows:
        parsed = urlparse(r['link_utm'])
        qs = parse_qs(parsed.query)
        if qs.get('utm_medium') != ['organic']:
            ok3 = False
        if qs.get('utm_campaign') != [data.get('chien_dich')]:
            ok3 = False
        if not qs.get('utm_source') or not qs.get('utm_content'):
            ok3 = False

    # 4. Xuất file kiểm tra thực tế trong thư mục tạm riêng
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_out = pathlib.Path(tmp_dir)
        md1, csv1 = run_schedule(SAMPLE_INPUT, tmp_out)
        content_md1 = md1.read_text(encoding='utf-8')
        content_csv1 = csv1.read_text(encoding='utf-8')

        md2, csv2 = run_schedule(SAMPLE_INPUT, tmp_out)

        ok4 = (
            md1.is_file() and csv1.is_file()
            and md2.is_file() and csv2.is_file()
            and md1 != md2 and csv1 != csv2
            and '_v01_' in md1.name and '_v02_' in md2.name
            and '_v01_' in csv1.name and '_v02_' in csv2.name
            and md1.read_text(encoding='utf-8') == content_md1
            and csv1.read_text(encoding='utf-8') == content_csv1
        )

        # 5. Kiểm tra cờ --ra ghi vào thư mục chỉ định
        ra_dir = tmp_out / 'custom_ra'
        ra_md, ra_csv = run_schedule(SAMPLE_INPUT, ra_dir)
        ok5 = ra_md.is_file() and ra_csv.is_file() and '_v01_' in ra_md.name

        # 6. Kiểm tra tạo độc quyền theo cặp: chạy 4 luồng song song không đè nhau, rollback khi csv đụng trước
        conc_dir = tmp_out / 'concurrent_test'
        def worker(idx):
            return run_schedule(SAMPLE_INPUT, conc_dir)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            conc_results = list(ex.map(worker, range(4)))

        conc_mds = sorted(conc_dir.glob("*.md"))
        conc_csvs = sorted(conc_dir.glob("*.csv"))
        ok6_conc = (
            len(conc_results) == 4
            and len(set(conc_results)) == 4
            and len(conc_mds) == 4
            and len(conc_csvs) == 4
            and all(m.stem == c.stem for m, c in conc_results)
            and all(m.stat().st_size > 0 for m in conc_mds)
            and all(c.stat().st_size > 0 for c in conc_csvs)
        )

        # Rollback check: csv đã tồn tại -> huỷ md thứ nhất, chuyển sang phiên bản kế tiếp
        rb_dir = tmp_out / 'rollback_test'
        rb_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.datetime.now().strftime("%Y%m%d")
        dummy_csv = rb_dir / f"lich-dang-7-ngay_v01_{today}.csv"
        dummy_csv.write_text("dummy", encoding='utf-8')
        rb_md, rb_csv = run_schedule(SAMPLE_INPUT, rb_dir)
        ok6_rb = (
            rb_md.name == f"lich-dang-7-ngay_v02_{today}.md"
            and rb_csv.name == f"lich-dang-7-ngay_v02_{today}.csv"
            and not (rb_dir / f"lich-dang-7-ngay_v01_{today}.md").exists()
            and dummy_csv.read_text(encoding='utf-8') == "dummy"
        )

        ok6 = ok6_conc and ok6_rb

        # 7. Ca tự kiểm: đầu vào hỏng không để lại tệp giữ chỗ rỗng trong thư mục ra
        corrupt_dir = tmp_out / 'corrupt_test'
        bad_json = tmp_out / 'bad_input.json'
        bad_json.write_text('{"muc_tieu": [du_lieu_sai', encoding='utf-8')
        try:
            generate(bad_json, corrupt_dir)
            ok7 = False
        except Exception:
            ok7 = not corrupt_dir.exists() or len(list(corrupt_dir.glob("*"))) == 0

    checks = [
        ('đủ 7 dòng lịch tương ứng 7 ngày trong tuần', ok1),
        ('đủ 9 cột dữ liệu theo đúng quy định', ok2),
        ('mọi link UTM đều mang chuẩn utm_medium=organic và chiến dịch tuần', ok3),
        ('xuất đầy đủ bảng Markdown và tệp CSV hợp lệ với tự tăng phiên bản không ghi đè', ok4),
        ('hỗ trợ cờ --ra ghi vào thư mục chỉ định', ok5),
        ('tạo độc quyền theo cặp (4 luồng song song không đè nhau) và rollback khi tệp trùng', ok6),
        ('đầu vào hỏng không để lại tệp giữ chỗ rỗng trong thư mục ra', ok7)
    ]

    for n, ok in checks:
        print(('ĐẠT ' if ok else 'HỎNG'), n)
    passed = sum(ok for _, ok in checks)
    print(f'{passed}/{len(checks)} đạt')
    return 0 if passed == len(checks) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tạo lịch đăng 7 ngày")
    parser.add_argument('--input', type=pathlib.Path, default=SAMPLE_INPUT, help="Tệp kế hoạch tuần JSON")
    parser.add_argument('--ra', type=pathlib.Path, help="Thư mục ghi kết quả bản nháp (mặc định: out/)")
    parser.add_argument('--tu-kiem', action='store_true', help="Chạy tự kiểm tra")

    args = parser.parse_args()

    if args.tu_kiem:
        sys.exit(self_check())

    generate(args.input, args.ra)
