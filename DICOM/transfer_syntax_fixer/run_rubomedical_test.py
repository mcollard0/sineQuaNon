#!/usr/bin/env python3
import os, sys, argparse, logging, shutil, zipfile, tarfile, tempfile, json, time, webbrowser
from pathlib import Path
from typing import List, Dict, Any
import urllib.request
import urllib.parse
import re
from subprocess import run, PIPE
try:
    from pydicom import dcmread
    from pydicom.dataset import Dataset
except Exception as e:
    print('pydicom required, apt install python3-pydicom or pip install pydicom', file=sys.stderr); sys.exit(1)

RUBO_BASE = 'https://www.rubomedical.com/dicom_files/'
ZIP_PATTERN = re.compile(r'href=\"([^\"]+\.(?:zip|tar\.gz|tgz))\"', re.I)

# Common transfer syntax UIDs considered valid
COMMON_TS = {
    '1.2.840.10008.1.2',
    '1.2.840.10008.1.2.1',
    '1.2.840.10008.1.2.2',
    '1.2.840.10008.1.2.4.50',
    '1.2.840.10008.1.2.4.51',
    '1.2.840.10008.1.2.4.70',
    '1.2.840.10008.1.2.4.80',
    '1.2.840.10008.1.2.4.81',
    '1.2.840.10008.1.2.4.90',
    '1.2.840.10008.1.2.4.91',
    '1.2.840.10008.1.2.4.92',
    '1.2.840.10008.1.2.4.93',
    '1.2.840.10008.1.2.5',
}

def fetch_listing() -> List[str]:
    with urllib.request.urlopen(RUBO_BASE) as resp:
        html = resp.read().decode('utf-8', 'ignore')
    links = []
    for m in ZIP_PATTERN.finditer(html):
        url = m.group(1)
        if not url.startswith('http'):
            url = urllib.parse.urljoin(RUBO_BASE, url)
        links.append(url)
    return sorted(set(links))

def download_file(url: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / Path(urllib.parse.urlparse(url).path).name
    if out.exists():
        return out
    urllib.request.urlretrieve(url, out)
    return out

def extract_archive(archive: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == '.zip':
        with zipfile.ZipFile(archive, 'r') as zf:
            zf.extractall(dest)
    elif archive.suffixes[-2:] == ['.tar','.gz'] or archive.suffix.lower()=='.tgz':
        with tarfile.open(archive, 'r:gz') as tf:
            tf.extractall(dest)
    else:
        raise ValueError(f'Unsupported archive: {archive}')
    return dest

def find_dicom_files(root: Path) -> List[Path]:
    files = []
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        try:
            with open(p, 'rb') as f:
                f.seek(128)
                if f.read(4) == b'DICM':
                    files.append(p)
        except Exception:
            pass
    return files

def read_ts_and_study(ds) -> Dict[str, Any]:
    ts = None
    if getattr(ds, 'file_meta', None):
        ts = str(getattr(ds.file_meta, 'TransferSyntaxUID', '') or '')
    study = str(getattr(ds, 'StudyInstanceUID', '') or '')
    return {'study_uid': study, 'transfer_syntax': ts}

def clear_transfer_syntax(filepath: Path) -> bool:
    try:
        ds = dcmread(filepath, force=True)
        if not getattr(ds, 'file_meta', None):
            ds.file_meta = Dataset()
        # Clear the TransferSyntaxUID value
        setattr(ds.file_meta, 'TransferSyntaxUID', '')
        # Save the dataset with explicit rewriting of meta header
        ds.save_as(filepath, write_like_original=False)
        return True
    except Exception:
        return False

def run_fixer(fixer_path: Path, root: Path, dry: bool=False) -> int:
    cmd = ['python3', str(fixer_path), str(root)] + (['--dry-run'] if dry else [])
    proc = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    return proc.returncode

def open_in_chrome(path: Path):
    for candidate in ['google-chrome', 'chromium', 'chromium-browser']:
        try:
            run([candidate, str(path)], check=False)
            return
        except Exception:
            pass
    webbrowser.open(str(path))

def main():
    ap = argparse.ArgumentParser(description='Download RuboMedical DICOM sample archives, run fixer, and report results')
    ap.add_argument('--dest', default=str(Path.home()/'.cache/rubo_dicom'), help='Download/extract destination')
    ap.add_argument('--limit', type=int, default=5, help='Limit number of archives to process (0 = all)')
    ap.add_argument('--fixer', default='/media/michael/FASTESTARCHIVE/Archive/Programming/?python?/sinequonon/DICOM/fixer.py', help='Path to fixer.py')
    ap.add_argument('--report-dir', default=str(Path.home()/'.cache/rubo_dicom_report'), help='Where to write reports')
    args = ap.parse_args()

    dest = Path(args.dest)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    fixer = Path(args.fixer)
    if not fixer.exists():
        print(f'fixer not found: {fixer}', file=sys.stderr)
        sys.exit(1)

    links = fetch_listing()
    if args.limit > 0:
        links = links[:args.limit]

    archives: List[Path] = []
    for url in links:
        try:
            archives.append(download_file(url, dest))
        except Exception as e:
            print(f'Failed download {url}: {e}', file=sys.stderr)

    results = []
    total = 0
    success = 0
    for arc in archives:
        out_dir = dest / (arc.stem + '_extracted')
        try:
            extract_archive(arc, out_dir)
        except Exception as e:
            print(f'Failed extract {arc}: {e}', file=sys.stderr)
            continue
        # Make a working copy where we will clear TS ("during")
        work_dir = dest / (arc.stem + '_work')
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        shutil.copytree(out_dir, work_dir)

        dcm_files = find_dicom_files(out_dir)
        if not dcm_files:
            continue
        file_infos = []
        for fp in dcm_files:
            try:
                ds = dcmread(fp, force=True)
                info_before = read_ts_and_study(ds)
            except Exception:
                info_before = {'study_uid':'','transfer_syntax':''}
            # Corresponding path in work_dir
            rel = fp.relative_to(out_dir)
            wfp = work_dir / rel
            # Clear TS in working copy
            cleared_ok = clear_transfer_syntax(wfp)
            # Read during value from working copy
            try:
                ds_during = dcmread(wfp, force=True)
                info_during = read_ts_and_study(ds_during)
            except Exception:
                info_during = {'study_uid':'','transfer_syntax':''}
            file_infos.append({'path': str(fp), 'work_path': str(wfp), 'before': info_before, 'during': info_during})

        # Run fixer on working copy
        run_fixer(fixer, work_dir, dry=False)

        # After values from working copy
        for entry in file_infos:
            wfp = Path(entry['work_path'])
            try:
                ds = dcmread(wfp, force=True)
                entry['after'] = read_ts_and_study(ds)
            except Exception:
                entry['after'] = {'study_uid':'','transfer_syntax':''}
            b = entry['before'].get('transfer_syntax') or ''
            d = entry['during'].get('transfer_syntax') or ''
            a = entry['after'].get('transfer_syntax') or ''
            total += 1
            # Success criteria: if during was empty/missing OR before invalid, and after is valid
            before_valid = b in COMMON_TS
            after_valid = a in COMMON_TS
            during_empty = (d == '') or (d is None)
            if (during_empty or not before_valid) and after_valid:
                success += 1
        results.append({'archive': str(arc), 'dir': str(out_dir), 'work_dir': str(work_dir), 'files': file_infos})

    success_rate = (success/total*100.0) if total else 0.0
    json_path = report_dir / 'rubomedical_results.json'
    json_path.write_text(json.dumps({'total': total, 'success': success, 'success_rate': success_rate, 'results': results}, indent=2))

    md_lines = []
    md_lines.append(f'# RuboMedical DICOM Fixer Report')
    md_lines.append('')
    md_lines.append(f'- Total files: **{total}**')
    md_lines.append(f'- Success: **{success}** ✅')
    color = 'green' if success_rate>=90 else ('orange' if success_rate>=60 else 'red')
    md_lines.append(f'- Success rate: <span style=\"color:{color};font-weight:bold\">{success_rate:.2f}%</span> {"🎉" if success_rate>=90 else ("⚠️" if success_rate>=60 else "❌")}')
    md_lines.append('')
    for item in results:
        md_lines.append(f'## Archive: `{os.path.basename(item["archive"])}`')
        for f in item['files'][:10]:
            bts = f['before'].get('transfer_syntax') or '(missing/empty)'
            dts = f.get('during',{}).get('transfer_syntax') or '(missing/empty)'
            ats = f.get('after',{}).get('transfer_syntax') or '(missing/empty)'
            study = f['before'].get('study_uid') or f.get('after',{}).get('study_uid') or ''
            emoji = '✅' if (ats not in ('', '(missing/empty)')) else '➖'
            md_lines.append(f'- {emoji} `{os.path.basename(f["path"])}`  ')
            md_lines.append(f'  - StudyInstanceUID: `{study}`')
            md_lines.append(f'  - Before TS: `{bts}`')
            md_lines.append(f'  - During TS: `{dts}`')
            md_lines.append(f'  - After TS: `{ats}`')
        if len(item['files'])>10:
            md_lines.append(f'- ...and {len(item["files"])-10} more files')
        md_lines.append('')
    md_path = report_dir / 'rubomedical_report.md'
    md_path.write_text('\n'.join(md_lines))

    html = f'''<!doctype html><html><head><meta charset=\"utf-8\"><title>RuboMedical Report</title><style>body{{font-family:system-ui,Segoe UI,Arial;max-width:980px;margin:24px auto;line-height:1.5}} code{{background:#f6f8fa;padding:2px 4px;border-radius:4px}} pre{{background:#f6f8fa;padding:12px;border-radius:6px;overflow:auto}} h1,h2{{color:#333}} .ok{{color:green}} .warn{{color:orange}} .bad{{color:red}}</style></head><body><pre>''' + (md_path.read_text()) + '''</pre></body></html>'''
    html_path = report_dir / 'rubomedical_report.html'
    html_path.write_text(html)
    open_in_chrome(html_path)
    print(f'Report written to: {html_path}')

if __name__ == '__main__':
    main()
