#!/usr/bin/env python3
"""Build tracking links (UTM) for marketing posts and ads.

Usage:
  python3 scripts/make_utm_links.py                      # runs on sample plan
  python3 scripts/make_utm_links.py --plan my-plan.csv
  python3 scripts/make_utm_links.py --url https://example.com/landing --campaign tuan-01 --source facebook --medium organic

Plan CSV columns: trang_dich, nguon, kenh, dot, mau, noi_dung
  trang_dich  landing page URL (https://...)
  nguon       utm_source  (facebook, instagram, email...)
  kenh        utm_medium  (organic for normal posts [default], paid for ads)
  dot         utm_campaign (name of campaign or week)
  mau         utm_content (optional variant or post angle)
  noi_dung    utm_term    (optional headline or keyword)

Writes out/link-utm_vNN_YYYYMMDD.csv and prints one line per link. Reads and writes local files only.
Self-check: python3 scripts/make_utm_links.py --tu-kiem
"""
import argparse, csv, datetime, pathlib, re, sys
from urllib.parse import urlencode, urlparse, parse_qs


def find_repo_root() -> pathlib.Path:
    """Find the marketing workspace root directory by walking up."""
    p = pathlib.Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "scripts" / "check_setup.py").is_file() and (parent / "MANIFEST.md").is_file():
            return parent
    return p.parents[3] if len(p.parents) > 3 else p.parent


ROOT = find_repo_root()
SAMPLE = ROOT / 'references' / 'du-lieu-mau' / 'ke-hoach-utm.csv'
SLUG = re.compile(r'^[a-z0-9][a-z0-9-]*$')


def build(row):
    nguon = row.get('nguon') or 'facebook'
    dot = row.get('dot') or 'tuan-01'
    kenh = row.get('kenh') or 'organic'

    for k, val in [('nguon', nguon), ('kenh', kenh), ('dot', dot)]:
        if not SLUG.match(val):
            raise ValueError(f'«{val}» ở cột {k}: chỉ dùng chữ thường không dấu, số, gạch nối')

    if kenh not in ('paid', 'organic'):
        raise ValueError(f'cột kenh phải là paid hoặc organic, đang là «{kenh}»')

    params = {'utm_source': nguon, 'utm_medium': kenh, 'utm_campaign': dot}
    if row.get('mau'):
        params['utm_content'] = row['mau']
    if row.get('noi_dung'):
        params['utm_term'] = row['noi_dung']
    sep = '&' if '?' in row['trang_dich'] else '?'
    return row['trang_dich'] + sep + urlencode(params)


def run(plan_path, out_dir=None, verbose=True):
    rows = list(csv.DictReader(open(plan_path, encoding='utf-8')))
    built = [(r['dot'], r.get('mau', ''), build(r)) for r in rows]
    target_dir = pathlib.Path(out_dir) if out_dir else (ROOT / 'out')
    target_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y%m%d")
    for version in range(1, 100):
        candidate = target_dir / f"link-utm_v{version:02d}_{today}.csv"
        try:
            with open(candidate, 'x', newline='', encoding='utf-8') as f:
                try:
                    w = csv.writer(f, lineterminator='\n')
                    w.writerow(['dot', 'mau', 'link'])
                    for dot, mau, link in built:
                        w.writerow([dot, mau, link])
                        if verbose:
                            print(f'{dot:<28} {link}')
                except Exception:
                    candidate.unlink(missing_ok=True)
                    raise
            if verbose:
                print(f'Đã ghi {len(rows)} link: {candidate}')
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
    rows = list(csv.DictReader(open(SAMPLE, encoding='utf-8')))
    links = [build(r) for r in rows]
    ok1 = all(parse_qs(urlparse(l).query)['utm_campaign'][0] == r['dot'] for l, r in zip(links, rows))
    ok2 = len(set(links)) == len(links)
    try:
        build({'trang_dich': 'https://example.com/', 'nguon': 'Facebook', 'kenh': 'paid', 'dot': 'x'})
        ok3 = False
    except ValueError:
        ok3 = True
    link_default = build({'trang_dich': 'https://example.com/', 'nguon': 'facebook', 'dot': 'tuan-01'})
    ok4 = parse_qs(urlparse(link_default).query)['utm_medium'][0] == 'organic'

    today = datetime.datetime.now().strftime("%Y%m%d")
    with tempfile.TemporaryDirectory() as tmp_dir:
        out1 = run(SAMPLE, out_dir=tmp_dir, verbose=False)
        content1 = out1.read_text(encoding='utf-8')
        out2 = run(SAMPLE, out_dir=tmp_dir, verbose=False)
        ok5_seq = (
            out1.is_file()
            and out2.is_file()
            and out1 != out2
            and '_v01_' in out1.name
            and '_v02_' in out2.name
            and out1.read_text(encoding='utf-8') == content1
        )

        def worker(idx):
            return run(SAMPLE, out_dir=tmp_dir, verbose=False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            conc_results = list(ex.map(worker, range(4)))

        conc_files = sorted(pathlib.Path(tmp_dir).glob(f"link-utm_v*_{today}.csv"))
        ok5_conc = (
            len(conc_results) == 4
            and len(set(conc_results)) == 4
            and len(conc_files) == 6
            and all(f.is_file() and f.stat().st_size > 0 for f in conc_files)
        )

        # Ca tự kiểm: đầu vào hỏng -> không để lại tệp rỗng trong thư mục ra
        corrupt_dir = pathlib.Path(tmp_dir) / 'corrupt_test'
        bad_plan = pathlib.Path(tmp_dir) / 'bad_plan.csv'
        bad_plan.write_text("trang_dich,nguon,kenh,dot,mau,noi_dung\nhttps://example.com/,Facebook,organic,d1,,,\n", encoding='utf-8')
        try:
            run(bad_plan, out_dir=corrupt_dir, verbose=False)
            ok5_no_empty = False
        except ValueError:
            ok5_no_empty = not corrupt_dir.exists() or len(list(corrupt_dir.glob("*.csv"))) == 0

        ok5 = ok5_seq and ok5_conc and ok5_no_empty

    checks = [('mỗi link mang đúng utm_campaign của dòng kế hoạch', ok1),
              ('không có hai link trùng nhau', ok2),
              ('đối chứng âm: chữ hoa trong cột nguon bị chặn', ok3),
              ('mặc định utm_medium là organic khi không truyền', ok4),
              ('hỗ trợ cờ --ra, tự tăng phiên bản độc quyền, không để lại tệp rỗng khi lỗi', ok5)]
    for n, ok in checks:
        print(('ĐẠT ' if ok else 'HỎNG'), n)
    print(f'{sum(ok for _, ok in checks)}/{len(checks)} đạt')
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default=str(SAMPLE))
    ap.add_argument('--ra', help="Thư mục ghi kết quả bản nháp (mặc định: out/)")
    ap.add_argument('--url')
    ap.add_argument('--campaign')
    ap.add_argument('--source', default='facebook')
    ap.add_argument('--medium', default='organic')
    ap.add_argument('--content')
    ap.add_argument('--term')
    ap.add_argument('--tu-kiem', action='store_true')
    a = ap.parse_args()
    if a.tu_kiem:
        sys.exit(self_check())
    if a.url and a.campaign:
        row = {
            'trang_dich': a.url,
            'nguon': a.source,
            'kenh': a.medium,
            'dot': a.campaign,
            'mau': a.content or '',
            'noi_dung': a.term or ''
        }
        print(build(row))
    else:
        run(a.plan, out_dir=a.ra)
