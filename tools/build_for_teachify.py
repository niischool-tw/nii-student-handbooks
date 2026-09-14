#!/usr/bin/env python3
"""產生「開課快手（Teachify）部署專用版」HTML。

為什麼需要這一步
----------------
手冊在 repo 裡用相對路徑引用圖片與影片（`assets/xxx.png`），本機預覽與
Cloudflare Pages 都靠這個。但 Teachify 上沒有 assets 目錄，直接把 repo
的檔案丟上去，12 個圖片影片會全破。

這支腳本把 `assets/...` 換成 GitHub Pages 的絕對網址，輸出到 dist/，
再由那份輸出上傳到 Teachify。repo 本身不會被改到。

    src="assets/logo-color.png"
    → src="https://niischool-tw.github.io/nii-student-handbooks/walking/assets/logo-color.png"

⚠️ `src=` 和 `href=` 都要換。favicon 是用 `href` 引用的，只換 `src`
會讓分頁圖示破掉——這個坑踩過一次。

用法
----
    python3 tools/build_for_teachify.py              # 產生 dist/teachify/
    python3 tools/build_for_teachify.py --check      # 另外連線確認 assets 都取得到

輸出完會印出每份的位元組數與部署目標，接著照 README 的「部署到開課快手」
步驟走 MCP 上傳。

圖片來源的依賴（重要）
----------------------
圖片是 hot-link `main` 分支的 GitHub Pages，因為 Teachify MCP 目前缺
`storage:write` scope，圖片傳不進 Teachify 自己的 CDN。

所以**換圖時必須先讓新圖進 `main`**，否則線上手冊會抓不到。腳本的
--check 會實際連線驗證每個 asset 是否 200，換圖後務必跑一次。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'dist' / 'teachify'

# 圖片來源：main 分支的 GitHub Pages
ASSET_BASE = 'https://niischool-tw.github.io/nii-student-handbooks'

# 部署目標：資料夾 → (Teachify slug, 正式網址, page_id)
TARGETS = {
    'walking': ('walking-s9', 'https://nii.school/walking-s9/',
                '3715f11b-763b-4997-a92e-945f7be5377d'),
    'running': ('running-s8', 'https://nii.school/running-s8/',
                '4e8f346a-96a3-49f3-ba6e-fc8a33ebb5c2'),
    'flying': ('flying-s7', 'https://nii.school/flying-s7/',
               'ab131e0f-9730-4458-b485-ee40aa6dce76'),
}

ASSET_REF = re.compile(r'(src|href)="assets/')


def build(name):
    src = (ROOT / name / 'index.html').read_text(encoding='utf-8')
    before = len(ASSET_REF.findall(src))
    out = ASSET_REF.sub(lambda m: f'{m.group(1)}="{ASSET_BASE}/{name}/assets/', src)
    left = len(ASSET_REF.findall(out))
    if left:
        sys.exit(f'{name}: 轉換後仍有 {left} 處相對路徑，請檢查')
    if before == 0:
        sys.exit(f'{name}: 找不到任何 assets 引用，來源檔案可能不對')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / f'{name}.html'
    dest.write_text(out, encoding='utf-8')
    return dest, before, len(out.encode('utf-8'))


def asset_urls(name):
    src = (ROOT / name / 'index.html').read_text(encoding='utf-8')
    return sorted({f'{ASSET_BASE}/{name}/assets/{p}'
                   for p in re.findall(r'(?:src|href)="assets/([^"]+)"', src)})


def check_assets(name):
    """實際連線確認每個 asset 都取得到。換圖後一定要跑。"""
    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError
    bad = []
    for url in asset_urls(name):
        try:
            with urlopen(url, timeout=20) as r:
                if r.status != 200:
                    bad.append((url.rsplit('/', 1)[-1], r.status))
        except HTTPError as e:
            bad.append((url.rsplit('/', 1)[-1], e.code))
        except URLError as e:
            bad.append((url.rsplit('/', 1)[-1], str(e.reason)))
    return bad


def main():
    do_check = '--check' in sys.argv
    print(f'圖片來源：{ASSET_BASE}\n輸出目錄：{OUT_DIR}\n')
    failed = False
    for name, (slug, live, page_id) in TARGETS.items():
        dest, n, size = build(name)
        print(f'✅ {name} → {dest.name}｜{n} 處 assets 轉為絕對網址｜{size:,} bytes')
        print(f'      slug {slug}｜page_id {page_id}')
        print(f'      正式網址 {live}')
        if do_check:
            bad = check_assets(name)
            if bad:
                failed = True
                print(f'      ❌ 有 {len(bad)} 個 asset 取不到：')
                for f, why in bad:
                    print(f'         {f} → {why}')
            else:
                print(f'      ✅ {len(asset_urls(name))} 個 asset 全部可取得')
        print()
    if not do_check:
        print('提示：加上 --check 可實際連線驗證所有圖片影片是否取得得到。\n')
    print('接著依 tools/README.md「部署到開課快手」的步驟上傳 dist/teachify/*.html。')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
