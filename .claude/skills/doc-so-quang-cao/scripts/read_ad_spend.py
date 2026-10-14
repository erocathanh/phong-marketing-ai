#!/usr/bin/env python3
"""Daily ad report from CSV files: ad spend (from ad manager export) and optional sign-ups.

Usage:
  python3 scripts/read_ad_spend.py                      # runs on bundled sample spend data
  python3 scripts/read_ad_spend.py --spend my-spend.csv --signups my-signups.csv --daily-cap 400000

Spend CSV columns:   ngay, quang_cao, utm_campaign, chi_vnd, hien_thi, bam_link
Sign-up CSV columns: ngay, ma_nguoi, utm_campaign   (no names, no phone numbers needed)

Prints a plain-Vietnamese report and writes it to out/bao-cao-quang-cao_vNN_YYYYMMDD.md.
It only reads files: it never touches an ad account and never spends money.
Self-check: python3 scripts/read_ad_spend.py --tu-kiem
"""
import argparse, csv, datetime, pathlib, sys
from collections import defaultdict


def find_repo_root() -> pathlib.Path:
    """Find the marketing workspace root directory by walking up."""
    p = pathlib.Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "scripts" / "check_setup.py").is_file() and (parent / "MANIFEST.md").is_file():
            return parent
    return p.parents[3] if len(p.parents) > 3 else p.parent


ROOT = find_repo_root()
SAMPLE = ROOT / 'references' / 'du-lieu-mau'


def load(spend_path, signup_path=None):
    spend = list(csv.DictReader(open(spend_path, encoding='utf-8')))
    signups = []
    if signup_path and pathlib.Path(signup_path).is_file():
        signups = list(csv.DictReader(open(signup_path, encoding='utf-8')))
    return spend, signups


def report(spend, signups=None, daily_cap=250000):
    signups = signups or []
    by_ad = defaultdict(lambda: {'chi': 0, 'hien': 0, 'bam': 0, 'utm': ''})
    by_day = defaultdict(int)
    for r in spend:
        a = by_ad[r['quang_cao']]
        a['chi'] += int(r['chi_vnd']); a['hien'] += int(r['hien_thi']); a['bam'] += int(r['bam_link']); a['utm'] = r['utm_campaign']
        by_day[r['ngay']] += int(r['chi_vnd'])
    sign_by_utm = defaultdict(int)
    for s in signups:
        sign_by_utm[s['utm_campaign'] or 'khong-utm'] += 1
    total_spend = sum(a['chi'] for a in by_ad.values())
    total_clicks = sum(a['bam'] for a in by_ad.values())
    tracked = sum(n for u, n in sign_by_utm.items() if u != 'khong-utm')

    if signups:
        header_summary = f'Tổng chi: {total_spend:,}đ · tổng đăng ký có mã theo dõi: {tracked} · đăng ký không rõ nguồn: {sign_by_utm.get("khong-utm", 0)}'.replace(',', '.')
    else:
        header_summary = f'Tổng chi: {total_spend:,}đ · tổng lượt bấm link: {total_clicks} · số mẫu quảng cáo: {len(by_ad)}'.replace(',', '.')

    lines = ['# Báo cáo quảng cáo', '', header_summary, '', '## Từng mẫu quảng cáo']
    rows = []
    for name, a in sorted(by_ad.items()):
        if signups:
            n = sign_by_utm.get(a['utm'], 0)
            cpl = a['chi'] // n if n else None
            rows.append((name, a, n, cpl))
            lines.append(f'- {name}: chi {a["chi"]:,}đ · {a["hien"]} lượt hiển thị · {a["bam"]} lượt bấm · {n} đăng ký · '.replace(',', '.')
                         + (f'{cpl:,}đ mỗi đăng ký'.replace(',', '.') if cpl else 'chưa có đăng ký'))
        else:
            cpc = a['chi'] // a['bam'] if a['bam'] else None
            rows.append((name, a, a['bam'], cpc))
            lines.append(f'- {name}: chi {a["chi"]:,}đ · {a["hien"]} lượt hiển thị · {a["bam"]} lượt bấm · '.replace(',', '.')
                         + (f'CPC {cpc:,}đ/lượt bấm'.replace(',', '.') if cpc else 'chưa có lượt bấm'))

    lines += ['', '## Đề xuất (chỉ đề xuất — tắt, bật, đổi tiền là việc của chủ doanh nghiệp)']
    with_cost = [r for r in rows if r[3]]
    if with_cost:
        best = min(with_cost, key=lambda r: r[3])
        unit = "chi phí mỗi đăng ký thấp nhất" if signups else "chi phí mỗi lượt bấm thấp nhất"
        lines.append(f'- Giữ hoặc tăng: {best[0]} ({unit}).')
    for name, a, n, metric in rows:
        if not n:
            label = "chưa có đăng ký" if signups else "chưa có lượt bấm"
            lines.append(f'- Xem lại: {name} — đã chi {a["chi"]:,}đ mà {label}.'.replace(',', '.'))
    over = [d for d, v in sorted(by_day.items()) if daily_cap and v > daily_cap]
    lines.append(f'- Ngày vượt trần {daily_cap:,}đ: '.replace(',', '.') + (', '.join(over) if over else 'không có'))

    kq_num = tracked if signups else total_clicks
    src_str = "CSV chi tiêu + CSV đăng ký" if signups else "CSV chi tiêu"
    lines += ['', f'SỐ: chi={total_spend} · kq={kq_num} · nguon={src_str} (dữ liệu mẫu nếu không truyền tệp)']
    return '\n'.join(lines) + '\n', total_spend, kq_num


def write_report(text: str, out_dir=None) -> pathlib.Path:
    target_dir = pathlib.Path(out_dir) if out_dir else (ROOT / 'out')
    target_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y%m%d")
    for version in range(1, 100):
        candidate = target_dir / f"bao-cao-quang-cao_v{version:02d}_{today}.md"
        try:
            with open(candidate, 'x', encoding='utf-8') as f:
                try:
                    f.write(text)
                except Exception:
                    candidate.unlink(missing_ok=True)
                    raise
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError("Vượt quá 99 bản nháp trong một ngày.")


def self_check():
    try:
        return _self_check_body()
    except (AssertionError, Exception) as err:
        msg = str(err) if str(err) else "điều kiện kiểm thử không đạt"
        print(f"HỎNG  tự kiểm tra: {msg}")
        return 1


def _self_check_body():
    import concurrent.futures
    import tempfile
    spend, _ = load(SAMPLE / 'chi-quang-cao-7-ngay.csv')
    text, total, kq = report(spend, None, 250000)
    csv_total = sum(int(r['chi_vnd']) for r in spend)
    csv_clicks = sum(int(r['bam_link']) for r in spend)
    today = datetime.datetime.now().strftime("%Y%m%d")
    with tempfile.TemporaryDirectory() as tmp_dir:
        out1 = write_report(text, out_dir=tmp_dir)
        content1 = out1.read_text(encoding='utf-8')
        out2 = write_report(text, out_dir=tmp_dir)
        ok5_seq = (
            out1.is_file()
            and out2.is_file()
            and out1 != out2
            and '_v01_' in out1.name
            and '_v02_' in out2.name
            and out1.read_text(encoding='utf-8') == content1
        )

        def worker(idx):
            return write_report(f"{text}\nluong_{idx}\n", out_dir=tmp_dir)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            conc_results = list(ex.map(worker, range(4)))

        conc_files = sorted(pathlib.Path(tmp_dir).glob(f"bao-cao-quang-cao_v*_{today}.md"))
        ok5_conc = (
            len(conc_results) == 4
            and len(set(conc_results)) == 4
            and len(conc_files) == 6
            and all(f.is_file() and f.stat().st_size > 0 for f in conc_files)
        )

        # Ca tự kiểm: đầu vào hỏng -> không để lại tệp rỗng trong thư mục ra
        corrupt_dir = pathlib.Path(tmp_dir) / 'corrupt_test'
        bad_csv = pathlib.Path(tmp_dir) / 'bad_spend.csv'
        bad_csv.write_text("invalid,data\n1,2\n", encoding='utf-8')
        try:
            spend_bad, signups_bad = load(bad_csv)
            text_bad, _, _ = report(spend_bad, signups_bad, 250000)
            write_report(text_bad, out_dir=corrupt_dir)
            ok5_no_empty = False
        except Exception:
            ok5_no_empty = not corrupt_dir.exists() or len(list(corrupt_dir.glob("*.md"))) == 0

        ok5 = ok5_seq and ok5_conc and ok5_no_empty

    checks = [('tổng chi khớp tổng cột chi_vnd', total == csv_total),
              ('số kết quả khớp tổng lượt bấm trong CSV chi tiêu', kq == csv_clicks),
              ('có dòng SỐ:', '\nSỐ: chi=' in text),
              ('đối chứng âm: CSV rỗng ra 0', report([], [], 0)[1:] == (0, 0)),
              ('hỗ trợ cờ --ra, tự tăng phiên bản độc quyền, không để lại tệp rỗng khi lỗi', ok5)]
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(('ĐẠT ' if ok else 'HỎNG'), n)
    print(f'{len(checks) - len(bad)}/{len(checks)} đạt')
    return 0 if not bad else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--spend', default=str(SAMPLE / 'chi-quang-cao-7-ngay.csv'))
    ap.add_argument('--signups', default=None)
    ap.add_argument('--daily-cap', type=int, default=250000)
    ap.add_argument('--ra', help="Thư mục ghi kết quả bản nháp (mặc định: out/)")
    ap.add_argument('--tu-kiem', action='store_true')
    a = ap.parse_args()
    if a.tu_kiem:
        sys.exit(self_check())
    text, _, _ = report(*load(a.spend, a.signups), a.daily_cap)
    out = write_report(text, out_dir=a.ra)
    print(text)
    print(f'Đã ghi: {out}')
