#!/usr/bin/env python3
"""重排語感練功坊手冊（gokan/）的行事曆。

語感的行事曆跟起步系列不同：沒有固定班別，而是「按月預約」。

規則（2027 版，Eli 2026-11-17 決定改成每月 15 號選課）
------------------------------------------------------
- 每個月 15 號 20:00 開放「下一個月」整個月的選課。
  例：1/15 開放 2 月的課；2026/12/15 開放 2027 年 1 月的課。
- 休假整段不上課，月曆上標紅字。
- 每週五 10:00 公開下一週的預告與預習影片（休假日不標）。

怎麼跑
------
    python3 tools/build_gokan_calendar.py

會改寫 gokan/index.html 裡兩段標記之間的內容：
    <!-- GOKAN-CAL:START --> ... <!-- GOKAN-CAL:END -->        十二個月的月曆頁
    <!-- GOKAN-KEY:START --> ... <!-- GOKAN-KEY:END -->        「行事曆重點」頁的選課日與休假表
跑幾次結果都一樣，不會疊加。跑完會印出每個選課日與休假，並自動驗證。

新年度要改哪裡
--------------
只動下面「年度設定」這一區。
"""
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'gokan' / 'index.html'

# ── 年度設定 ────────────────────────────────────────────
YEAR = 2027
SELECT_DAY = 15          # 每月幾號開放選課
SELECT_TIME = '20:00'    # 開放時間
# 休假（含頭含尾）。名稱會直接顯示在月曆上
HOLIDAYS = [
    (dt.date(2026, 12, 29), dt.date(2027, 1, 4), '新年休假'),
    (dt.date(2027, 2, 4), dt.date(2027, 2, 10), '春節休假'),
    (dt.date(2027, 6, 8), dt.date(2027, 6, 13), '端午休假'),
    (dt.date(2027, 9, 14), dt.date(2027, 9, 19), '中秋休假'),
    (dt.date(2027, 10, 5), dt.date(2027, 10, 10), '國慶休假'),
    (dt.date(2027, 12, 28), dt.date(2028, 1, 3), '新年休假'),
]
# ────────────────────────────────────────────────────────

MONTH_ZH = ['', '一月', '二月', '三月', '四月', '五月', '六月',
            '七月', '八月', '九月', '十月', '十一月', '十二月']
WD_ZH = '一二三四五六日'


def holiday_of(d):
    for a, b, name in HOLIDAYS:
        if a <= d <= b:
            return name
    return None


def next_month(d):
    return (d.month % 12) + 1


def select_days():
    """回傳選課日清單：前一年 12 月那次（開放 1 月）＋今年 1～12 月。"""
    days = [dt.date(YEAR - 1, 12, SELECT_DAY)]
    days += [dt.date(YEAR, m, SELECT_DAY) for m in range(1, 13)]
    return days


def month_grid(year, month):
    first = dt.date(year, month, 1)
    start = first - dt.timedelta(days=first.weekday())
    last = (dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1))
    end = last + dt.timedelta(days=6 - last.weekday())
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    return days


def cell(d, month, sel):
    out = d.month != month
    cls = 'cal-cell' + (' cal-out' if out else '')
    hol = holiday_of(d)
    style = ''
    inner = f'<div class="cal-date">{d.day}</div>'
    if hol:
        style = ' style="background:#FDF4FF"'
        inner += f'<div class="cal-evt" style="color:#DC2626;font-weight:700">{hol}</div>'
    if d in sel:
        style = ' style="background:var(--a50);border-left:3px solid var(--a500);padding-left:4px"'
        inner += (f'<div class="cal-evt cal-keep" style="color:var(--a500);font-weight:700">'
                  f'⭐ {SELECT_TIME} 開放選課<br>（{next_month(d)} 月課程）</div>')
    if d.weekday() == 4 and not hol:
        inner += '<div class="cal-evt cal-evt-hi">10:00 下週預習影片</div>'
    return f'    <div class="{cls}"{style}>{inner}</div>'


def month_section(month, sel):
    days = month_grid(YEAR, month)
    rows = len(days) // 7
    head = '\n'.join(
        f'    <div style="background:var(--p500);color:#fff;padding:5px 6px;font-size:13px;font-weight:700;display:flex;align-items:center">{w}</div>'
        for w in WD_ZH)
    cells = '\n'.join(cell(d, month, sel) for d in days)
    name = MONTH_ZH[month]
    return f'''<!-- 月曆 ▪ {name} -->
<section class="slide" data-title="{name}行事曆" data-tag="課程架構" data-icon="📆">
<div class="card th-white">
<div class="si" style="padding:8px 22px calc(var(--ctrl-h) + 4px)">
  <div style="flex-shrink:0;display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px">
    <div style="font-size:clamp(20px,3vw,32px);font-weight:800;color:var(--n800)">{name}</div>
    <div style="font-size:14px;color:var(--text-muted)">每月 {SELECT_DAY} 號 {SELECT_TIME} 開放下個月選課　<span style="font-size:clamp(18px,2.6vw,28px);font-weight:800;color:var(--p500);margin-left:8px">{YEAR}</span></div>
  </div>
  <div style="flex:1;min-height:0;overflow:hidden;display:grid;grid-template-columns:repeat(7,1fr);grid-template-rows:auto repeat({rows},1fr);gap:1px;background:var(--border);padding:1px;border-radius:4px">
{head}
{cells}
  </div>
</div></div></section>
'''


def fmt(d):
    return f'{d.month}/{d.day}（{WD_ZH[d.weekday()]}）'


def key_block(sel):
    sel_li = '\n'.join(
        f'          <div style="background:var(--n100);border-radius:6px;padding:5px 8px;font-size:14px;color:var(--text);border-left:3px solid var(--a300)">'
        f'{(str(d.year) + "/") if d.year != YEAR else ""}{fmt(d)} → <strong>{next_month(d)} 月</strong></div>'
        for d in sel)
    hol_li = '\n'.join(
        f'        <li><span class="ri">🏖️</span><div><strong>{name}</strong>　{a.month}/{a.day} – {b.month}/{b.day}</div></li>'
        for a, b, name in HOLIDAYS if b.year >= YEAR and a.year <= YEAR)
    return f'''    <div class="col">
      <h3>⭐ 選課開放日（每月 {SELECT_DAY} 號 {SELECT_TIME}）</h3>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px">
{sel_li}
      </div>
      <div class="note" style="margin-top:8px">每月 {SELECT_DAY} 號開放後，可一次預約下一個月整個月的口說課</div>
    </div>
    <div class="col">
      <h3>🏖️ 休假（這幾天不上課）</h3>
      <ul class="rlist tight" style="margin-top:0">
{hol_li}
      </ul>
      <div class="note" style="margin-top:8px">🎬 每週五 10:00 公開下一週的預告與預習影片</div>
    </div>'''


def replace(src, tag, body):
    pat = re.compile(rf'(<!-- {tag}:START -->\n).*?(<!-- {tag}:END -->)', re.S)
    if not pat.search(src):
        sys.exit(f'❌ 找不到 <!-- {tag}:START/END --> 標記')
    return pat.sub(lambda m: m.group(1) + body + '\n' + m.group(2), src)


def verify(src, sel):
    errs = []
    if len(sel) != 13:
        errs.append(f'選課日應有 13 個（前一年 12 月＋今年 12 個月），實際 {len(sel)}')
    for d in sel:
        if d.day != SELECT_DAY:
            errs.append(f'選課日 {d} 不是 {SELECT_DAY} 號')
    if src.count('行事曆" data-tag="課程架構"') != 12:
        errs.append('月曆頁不是 12 張')
    if '｜W' in src:
        errs.append('月曆裡還有舊的 W 週次標示')
    return errs


def main():
    sel = select_days()
    src = HTML.read_text(encoding='utf-8')
    months = '\n'.join(month_section(m, sel) for m in range(1, 13))
    src = replace(src, 'GOKAN-CAL', months)
    src = replace(src, 'GOKAN-KEY', key_block(sel))
    HTML.write_text(src, encoding='utf-8')

    print(f'{YEAR} 語感練功坊行事曆｜每月 {SELECT_DAY} 號 {SELECT_TIME} 開放下個月選課')
    for d in sel:
        warn = f'　⚠️ 落在{holiday_of(d)}' if holiday_of(d) else ''
        print(f'  選課　{d}（{WD_ZH[d.weekday()]}）→ {next_month(d)} 月{warn}')
    for a, b, name in HOLIDAYS:
        print(f'  休假　{name}　{a} – {b}')
    errs = verify(src, sel)
    if errs:
        print('\n'.join('❌ ' + e for e in errs))
        sys.exit(1)
    print('🎉 全部驗證通過')


if __name__ == '__main__':
    main()
