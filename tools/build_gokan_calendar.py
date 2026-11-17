#!/usr/bin/env python3
"""重排語感練功坊手冊（gokan/）的行事曆。

語感的行事曆跟起步系列不同：沒有固定班別，而是「四週一輪」的預約循環。

規則（照 2026 版手冊推算，2027 版沿用；有改再改這支）
------------------------------------------------------
- 一週＝週二到週日（週一不排 W 號，2026 版月曆就是這樣畫的）。
- 每四週一輪：W1 → W2 → W3 → W4 → 下一輪 W1。
- 休假週整週不上課、不給 W 號，下一週接著編。
- 每一輪 W4 那週的「週一 20:00」開放下一輪 W1–W4 選課。
- 春節這種「休假橫跨兩個半週」的情況，兩個半週合成一個 W（MERGED）。

怎麼跑
------
    python3 tools/build_gokan_calendar.py

會改寫 gokan/index.html 裡兩段標記之間的內容：
    <!-- GOKAN-CAL:START --> ... <!-- GOKAN-CAL:END -->        十二個月的月曆頁
    <!-- GOKAN-KEY:START --> ... <!-- GOKAN-KEY:END -->        「行事曆重點」頁的選課日與休假表
跑幾次結果都一樣，不會疊加。跑完會印出每個選課日與休假週，並自動驗證。

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
# 這一年第一個 W1 的週二（前一輪 W4＝2026/12/22，選課日 2026/12/21）
FIRST_W1 = dt.date(2027, 1, 5)
# 休假（含頭含尾）。名稱會直接顯示在月曆上
HOLIDAYS = [
    (dt.date(2026, 12, 29), dt.date(2027, 1, 4), '新年休假'),
    (dt.date(2027, 2, 4), dt.date(2027, 2, 10), '春節休假'),
    (dt.date(2027, 6, 8), dt.date(2027, 6, 13), '端午休假'),
    (dt.date(2027, 9, 14), dt.date(2027, 9, 19), '中秋休假'),
    (dt.date(2027, 10, 5), dt.date(2027, 10, 10), '國慶休假'),
    (dt.date(2027, 12, 28), dt.date(2028, 1, 3), '新年休假'),
]
# 兩個「半週」合成一個 W：(第一個半週的週二, 第二個半週的週二)
MERGED = [
    (dt.date(2027, 2, 2), dt.date(2027, 2, 9)),
]
SELECT_TEXT = '20:00 開放選課<br>（下一輪 W1–4）'
# 前一年就開放的選課日（月曆上看不到，只列在「行事曆重點」）
PRE_SELECT = [dt.date(2026, 12, 21)]
# ────────────────────────────────────────────────────────

MONTH_ZH = ['', '一月', '二月', '三月', '四月', '五月', '六月',
            '七月', '八月', '九月', '十月', '十一月', '十二月']
WD_ZH = '一二三四五六日'


def holiday_of(d):
    for a, b, name in HOLIDAYS:
        if a <= d <= b:
            return name
    return None


def build_weeks():
    """回傳 {日期: W號}（只有週二～週日、有上課的日子）與選課日清單。"""
    label = {}
    select_days = []
    merged_second = {b for _, b in MERGED}
    merged_first = {a: b for a, b in MERGED}
    n = 0  # 已經編到第幾週（0 起算）
    tue = FIRST_W1
    end = dt.date(YEAR, 12, 31) + dt.timedelta(days=14)
    while tue <= end:
        days = [tue + dt.timedelta(days=i) for i in range(6)]  # 週二～週日
        open_days = [d for d in days if not holiday_of(d)]
        if tue in merged_second:
            # 跟前一個半週同一個 W
            for d in open_days:
                label[d] = w_prev
        elif open_days:
            w = n % 4 + 1
            for d in open_days:
                label[d] = w
            if w == 4:
                select_days.append(tue - dt.timedelta(days=1))
            w_prev = w
            n += 1
        tue += dt.timedelta(days=7)
    return label, select_days


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


def cell(d, month, label, select_days):
    out = d.month != month
    cls = 'cal-cell' + (' cal-out' if out else '')
    hol = holiday_of(d)
    style = ''
    inner = f'<div class="cal-date">{d.day}'
    if d in label:
        inner += f'<span class="cal-wk">｜W{label[d]}</span>'
    inner += '</div>'
    if hol:
        style = ' style="background:#FDF4FF"'
        inner += f'<div class="cal-evt" style="color:#DC2626;font-weight:700">{hol}</div>'
    if d in select_days:
        style = ' style="background:var(--a50);border-left:3px solid var(--a500);padding-left:4px"'
        inner += f'<div class="cal-evt cal-keep" style="color:var(--a500);font-weight:700">⭐ {SELECT_TEXT}</div>'
    if d.weekday() == 4 and d in label:
        inner += '<div class="cal-evt cal-evt-hi">10:00 下週預習影片</div>'
    return f'    <div class="{cls}"{style}>{inner}</div>'


def month_section(month, label, select_days):
    days = month_grid(YEAR, month)
    rows = len(days) // 7
    head = '\n'.join(
        f'    <div style="background:var(--p500);color:#fff;padding:5px 6px;font-size:13px;font-weight:700;display:flex;align-items:center">{w}</div>'
        for w in WD_ZH)
    cells = '\n'.join(cell(d, month, label, select_days) for d in days)
    name = MONTH_ZH[month]
    return f'''<!-- 月曆 ▪ {name} -->
<section class="slide" data-title="{name}行事曆" data-tag="課程架構" data-icon="📆">
<div class="card th-white">
<div class="si" style="padding:8px 22px calc(var(--ctrl-h) + 4px)">
  <div style="flex-shrink:0;display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px">
    <div style="font-size:clamp(20px,3vw,32px);font-weight:800;color:var(--n800)">{name}</div>
    <div style="font-size:14px;color:var(--text-muted)">每週五 10:00 公開下週預習影片　<span style="font-size:clamp(18px,2.6vw,28px);font-weight:800;color:var(--p500);margin-left:8px">{YEAR}</span></div>
  </div>
  <div style="flex:1;min-height:0;overflow:hidden;display:grid;grid-template-columns:repeat(7,1fr);grid-template-rows:auto repeat({rows},1fr);gap:1px;background:var(--border);padding:1px;border-radius:4px">
{head}
{cells}
  </div>
</div></div></section>
'''


def fmt(d):
    return f'{d.month}/{d.day}（{WD_ZH[d.weekday()]}）'


def key_block(select_days):
    sel = PRE_SELECT + [d for d in select_days if d.year == YEAR]
    sel_li = '\n'.join(
        f'          <div style="background:var(--n100);border-radius:6px;padding:5px 8px;font-size:14px;color:var(--text);border-left:3px solid var(--a300)">{(str(d.year) + "/") if d.year != YEAR else ""}{fmt(d)}</div>'
        for d in sel)
    hol_li = '\n'.join(
        f'        <li><span class="ri">🏖️</span><div><strong>{name}</strong>　{a.month}/{a.day} – {b.month}/{b.day}</div></li>'
        for a, b, name in HOLIDAYS if b.year >= YEAR and a.year <= YEAR)
    return f'''    <div class="col">
      <h3>⭐ 選課開放日（皆為週一 20:00）</h3>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px">
{sel_li}
      </div>
      <div class="note" style="margin-top:8px">每次開放後，可一次預約接下來 W1–W4 共四週的口說課</div>
    </div>
    <div class="col">
      <h3>🏖️ 休假週（不上課，週次順延）</h3>
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


def verify(label, select_days):
    errs = []
    for d, w in label.items():
        if d.weekday() == 0:
            errs.append(f'{d} 是週一卻有 W 號')
        if holiday_of(d):
            errs.append(f'{d} 是休假卻有 W 號')
    for d in select_days:
        if d.weekday() != 0:
            errs.append(f'選課日 {d} 不是週一')
        if label.get(d + dt.timedelta(days=1)) != 4:
            errs.append(f'選課日 {d} 的隔天不是 W4')
    # 每一輪 W1→W4 連續
    seq = [label[d] for d in sorted(label) if d.weekday() == 1 or (d - dt.timedelta(days=1)) not in label]
    for a, b in zip(seq, seq[1:]):
        if a != b and b != a % 4 + 1:
            errs.append(f'週次跳號：W{a} 之後是 W{b}')
    return errs


def main():
    label, select_days = build_weeks()
    src = HTML.read_text(encoding='utf-8')
    months = '\n'.join(month_section(m, label, select_days) for m in range(1, 13))
    src = replace(src, 'GOKAN-CAL', months)
    src = replace(src, 'GOKAN-KEY', key_block(select_days))
    HTML.write_text(src, encoding='utf-8')

    print(f'{YEAR} 語感練功坊行事曆｜第一個 W1：{fmt(FIRST_W1)}')
    print('選課開放日：' + '、'.join(fmt(d) for d in select_days if d.year == YEAR))
    for a, b, name in HOLIDAYS:
        print(f'  休假　{name}　{a} – {b}')
    errs = verify(label, select_days)
    if errs:
        print('\n'.join('❌ ' + e for e in errs))
        sys.exit(1)
    print('🎉 全部驗證通過')


if __name__ == '__main__':
    main()
