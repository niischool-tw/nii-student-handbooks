#!/usr/bin/env python3
"""重建三份學生手冊的行事曆頁與「口說課時段」表。

用法
----
    python3 tools/build_calendar.py

會直接改寫 walking/ running/ flying/ 的 index.html。
可重複執行：每次都整段替換，不會疊加，所以跑幾次結果都一樣。
跑完會自動驗證每一格，有錯會印出來並以非 0 結束。

新學期要改什麼
--------------
只要動下面「學期設定」與「各班設定」兩區：

  START / END   學期第一天、最後一天
  BREAKS        停課區間（起訖日，含頭含尾）
  CLASSES       每班的文法課星期、週次起點、口說時段、開學前日程

其餘（星期、週次編號、月曆列數、鄰月補齊、跨年）都會自己算。

注意
----
* 週次會自動跳過停課週，例如停課一整週後，下一週才接續 W2。
* 月曆頁數＝學期橫跨的月份數。若改動後頁數與手冊裡現有的
  section 數不符，腳本會直接報錯而不是寫出壞檔案。
* 口說時段留空 {} 時，時段表會輸出紅色待填提示，行事曆也不會
  排口說課——用於資料還沒到齊的階段。
"""
import calendar
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── 學期設定 ────────────────────────────────────────────────
START = dt.date(2026, 9, 14)    # 學期第一天
END = dt.date(2026, 12, 20)     # 學期最後一天
BREAKS = [                      # 停課區間（含頭含尾）
    (dt.date(2026, 9, 21), dt.date(2026, 9, 27)),
    (dt.date(2026, 10, 5), dt.date(2026, 10, 11)),
]

# ── 各班設定 ────────────────────────────────────────────────
# 口說班別對應上課時間
AM = ('09:00–11:00', '午前班')
NOON = ('12:00–14:00', '正午班')
PM = ('15:00–17:00', '午後班')
EVE = ('19:00–21:00', '晚間班')
MON, TUE, WED, THU, FRI, SAT, SUN = range(7)

GRAMMAR_TXT = '20:00–21:30 文法課'

CLASSES = {
    # 起步班 S9 — W1–W12，文法課週一，開學前有開課說明直播
    'walking': dict(
        grammar=MON, week0=0,
        pre={dt.date(2026, 9, 7): (True, '⭐ 20:00 開課說明直播')},
        speak={THU: [EVE],
               FRI: [AM, NOON, PM, EVE],
               SAT: [AM, NOON, EVE],
               SUN: [AM, NOON, PM, EVE]},
    ),
    # 起跑班 S8 — W13–W24，文法課週二
    'running': dict(
        grammar=TUE, week0=12, pre={},
        speak={THU: [EVE],
               FRI: [AM, NOON, EVE],
               SAT: [NOON, EVE],
               SUN: [AM, PM, EVE]},
    ),
    # 起飛班 S7 — W25–W36，文法課週二
    'flying': dict(
        grammar=TUE, week0=24, pre={},
        speak={THU: [EVE],
               FRI: [AM, PM, EVE],
               SAT: [AM, NOON],
               SUN: [AM, PM, EVE]},
    ),
}

# ── 以下為實作，正常情況不需要修改 ──────────────────────────
CN_NUM = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
WD_CN = '一二三四五六日'
CARD = ('background:var(--n100);border-radius:8px;padding:8px 10px;'
        'border-left:3px solid var(--p300)')


def months_in_range():
    """學期（含開學前日程）橫跨的 (年, 月) 清單。"""
    earliest = min([START] + [d for c in CLASSES.values() for d in c['pre']])
    out, y, m = [], earliest.year, earliest.month
    while (y, m) <= (END.year, END.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


MONTHS = months_in_range()


def in_break(d):
    return any(a <= d <= b for a, b in BREAKS)


def week_of(d, week0):
    """該日期的累計週次；學期外或停課期間回 None。"""
    if not (START <= d <= END) or in_break(d):
        return None
    n, cur = 0, START
    while cur <= END:
        if not in_break(cur):
            n += 1
            if cur <= d < cur + dt.timedelta(7):
                return week0 + n
        cur += dt.timedelta(7)
    return None


def cell(d, cfg, out=False):
    """單一日期格。out=True 表示這格屬於前後鄰月，會淡化顯示。"""
    wk = week_of(d, cfg['week0'])
    date_html = f'<div class="cal-date">{d.day}'
    if wk:
        date_html += f'<span class="cal-wk">｜W{wk}</span>'
    date_html += '</div>'
    evts, style = [], ''
    cls = 'cal-cell cal-out' if out else 'cal-cell'

    if in_break(d):
        style = '' if out else ' style="background:#FDF4FF"'
        evts.append('<div class="cal-evt" style="color:#DC2626;font-weight:700">休校停課</div>')
    else:
        if d == START:
            if not out:
                style = (' style="background:var(--a50);border-left:3px solid var(--a500);'
                         'padding-left:4px"')
                date_html = date_html.replace(
                    '<div class="cal-date">',
                    '<div class="cal-date" style="color:var(--a500)">')
            evts.append('<div class="cal-evt" style="color:var(--a500);font-weight:700">'
                        '🎉 學期開始</div>')
        if d in cfg['pre']:
            hi, txt = cfg['pre'][d]
            if hi and not out:
                style = ' style="background:var(--p50)"'
            evts.append(f'<div class="cal-evt cal-evt-hi">{txt}</div>')
        if wk and d.weekday() == cfg['grammar']:
            evts.append(f'<div class="cal-evt cal-evt-hi">{GRAMMAR_TXT}</div>')
        if wk:
            slots = cfg['speak'].get(d.weekday(), [])
            if slots:
                body = '<br>'.join(f'{t} {n}' for t, n in slots)
                evts.append(f'<div class="cal-evt">{body}</div>')

    return f'    <div class="{cls}"{style}>{date_html}{"".join(evts)}</div>'


def month_section(idx, y, m, cfg):
    name = f'{CN_NUM[m]}月'
    first = dt.date(y, m, 1)
    lead = first.weekday()
    rows = -(-(lead + calendar.monthrange(y, m)[1]) // 7)

    L = [f'<!-- {idx} ▪ {name}行事曆 -->',
         f'<section class="slide" data-title="{name}行事曆" data-tag="課程架構" data-icon="📆">',
         '<div class="card th-white">',
         '<div class="si" style="padding:8px 22px calc(var(--ctrl-h) + 4px)">',
         '  <div style="flex-shrink:0;display:flex;justify-content:space-between;'
         'align-items:baseline;margin-bottom:8px">',
         f'    <div style="font-size:clamp(20px,3vw,32px);font-weight:800;'
         f'color:var(--n800)">{name}</div>',
         f'    <div style="font-size:clamp(18px,2.6vw,28px);font-weight:800;'
         f'color:var(--p500)">{y}</div>',
         '  </div>',
         f'  <div style="flex:1;min-height:0;overflow:hidden;display:grid;'
         f'grid-template-columns:repeat(7,1fr);grid-template-rows:auto repeat({rows},1fr);'
         f'gap:1px;background:var(--border);padding:1px;border-radius:4px">']
    for wd in WD_CN:
        L.append('    <div style="background:var(--p500);color:#fff;padding:5px 6px;'
                 f'font-size:13px;font-weight:700;display:flex;align-items:center">{wd}</div>')
    grid_start = first - dt.timedelta(lead)
    for i in range(rows * 7):
        d = grid_start + dt.timedelta(i)
        L.append(cell(d, cfg, out=(d.month != m)))
    L += ['  </div>', '</div></div></section>']
    return '\n'.join(L)


def slot_table(cfg):
    """「📆 口說課時段」卡片區塊；speak 為空時輸出待填提示。"""
    head = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;flex:1">'
    if not cfg['speak']:
        return (head + '\n        <div style="' + CARD +
                ';grid-column:1 / -1;border-left-color:#DC2626">'
                '<strong style="color:#DC2626;font-size:15px">口說課時段_TODO</strong>'
                '<div style="font-size:14px;color:var(--text-muted);margin-top:3px;'
                'line-height:1.6">新學期時段尚未提供，待補上後這裡與行事曆會一起更新。</div>'
                '</div>\n      </div>')
    L = [head]
    for wd in sorted(cfg['speak']):
        body = '<br>'.join(f'{n} {t}' for t, n in cfg['speak'][wd])
        L.append(f'        <div style="{CARD}">'
                 f'<strong style="color:var(--text);font-size:15px">週{WD_CN[wd]}</strong>'
                 f'<div style="font-size:14px;color:var(--text-muted);margin-top:3px;'
                 f'line-height:1.6">{body}</div></div>')
    L.append('      </div>')
    return '\n'.join(L)


CAL_PAT = re.compile(r'<!-- \d+ ▪ [^\n]*行事曆 -->\s*<section class="slide" '
                     r'data-title="[^"]*行事曆".*?</section>', re.S)
SLOT_PAT = re.compile(r'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;'
                      r'flex:1">.*?</div>\s*(?=<div class="note")', re.S)


def rebuild(name):
    path = ROOT / name / 'index.html'
    html = path.read_text(encoding='utf-8')
    cfg = CLASSES[name]

    found = CAL_PAT.findall(html)
    if len(found) != len(MONTHS):
        sys.exit(f'{name}: 手冊有 {len(found)} 頁行事曆，但學期橫跨 {len(MONTHS)} 個月。'
                 f'請先手動增減 section 數量再重跑。')
    if len(SLOT_PAT.findall(html)) != 1:
        sys.exit(f'{name}: 口說時段區塊定位失敗')

    new = [month_section(10 + i, y, m, cfg) for i, (y, m) in enumerate(MONTHS)]
    out, pos, i = [], 0, 0
    for mt in CAL_PAT.finditer(html):
        out.append(html[pos:mt.start()])
        out.append(new[i])
        pos, i = mt.end(), i + 1
    out.append(html[pos:])
    html = ''.join(out)
    html = SLOT_PAT.sub(lambda _: slot_table(cfg) + '\n      ', html, count=1)
    path.write_text(html, encoding='utf-8')


def verify(name):
    """重新讀檔，逐格比對真實日期。回傳錯誤清單。"""
    cfg = CLASSES[name]
    html = (ROOT / name / 'index.html').read_text(encoding='utf-8')
    errs, cells_seen = [], 0

    sec = re.search(r'口說課時段(.*?)</div>\s*<div class="note"', html, re.S)
    decl = {}
    if sec:
        for wd, body in re.findall(r'>週([一二三四五六日])</strong><div[^>]*>(.*?)</div>',
                                   sec.group(1)):
            decl[WD_CN.index(wd)] = [n for n, _ in re.findall(
                r'([午晚正][前後間午]班)\s*(\d{2}:\d{2}–\d{2}:\d{2})', body)]
    want_decl = {wd: [n for _, n in s] for wd, s in cfg['speak'].items()}
    if decl != want_decl:
        errs.append(f'時段表與設定不符: {decl} ≠ {want_decl}')

    blocks = re.findall(r'data-title="([^"]*)月行事曆"(.*?)</section>', html, re.S)
    for (label, body), (y, m) in zip(blocks, MONTHS):
        if label != CN_NUM[m]:
            errs.append(f'第 {m} 月頁標題為「{label}月」')
        first = dt.date(y, m, 1)
        lead = first.weekday()
        rows = -(-(lead + calendar.monthrange(y, m)[1]) // 7)
        gs = first - dt.timedelta(lead)
        found = re.findall(r'<div class="(cal-cell(?: cal-out)?)"[^>]*>'
                           r'(.*?)(?=<div class="cal-cell|\Z)', body, re.S)
        if len(found) != rows * 7:
            errs.append(f'{m} 月格數 {len(found)} ≠ {rows * 7}')
        for i, (cls, p) in enumerate(found):
            d = gs + dt.timedelta(i)
            cells_seen += 1
            if (d.month != m) != (' cal-out' in cls):
                errs.append(f'{d} 鄰月標記錯誤')
            dm = re.search(r'<div class="cal-date"[^>]*>(\d{1,2})', p)
            if not dm or int(dm.group(1)) != d.day:
                errs.append(f'{m} 月第 {i} 格應為 {d.day} 日')
                continue
            wk = week_of(d, cfg['week0'])
            if wk and f'｜W{wk}<' not in p:
                errs.append(f'{d} 週次應為 W{wk}')
            if not wk and '｜W' in p:
                errs.append(f'{d} 不應有週次')
            if in_break(d) and '休校停課' not in p:
                errs.append(f'{d} 缺少休校標記')
            got = [n for _, n in re.findall(
                r'(\d{2}:\d{2}–\d{2}:\d{2})\s*([午晚正][前後間午]班)', p)]
            want = [n for _, n in cfg['speak'].get(d.weekday(), [])] if wk else []
            if got != want:
                errs.append(f'{d}（週{WD_CN[d.weekday()]}）口說 {got} ≠ {want}')
            if ('文法課' in p) != (bool(wk) and d.weekday() == cfg['grammar']):
                errs.append(f'{d} 文法課標記錯誤')
    return errs, cells_seen


def main():
    weeks = sum(1 for _ in iter_weeks())
    print(f'學期 {START} – {END}｜停課 {len(BREAKS)} 段｜上課 {weeks} 週｜'
          f'月曆 {len(MONTHS)} 頁\n')
    bad = False
    for name, cfg in CLASSES.items():
        rebuild(name)
        errs, cells = verify(name)
        per = sum(len(v) for v in cfg['speak'].values())
        mark = '✅' if not errs else '❌'
        print(f'{mark} {name}: {cells} 格｜文法課週{WD_CN[cfg["grammar"]]}｜'
              f'口說每週 {per} 堂 × {weeks} = {per * weeks} 堂')
        for e in errs[:10]:
            print(f'      {e}')
        bad = bad or bool(errs)
    print('\n' + ('❌ 驗證未通過，請檢查上面的訊息' if bad else '🎉 全部驗證通過'))
    return 1 if bad else 0


def iter_weeks():
    cur = START
    while cur <= END:
        if not in_break(cur):
            yield cur
        cur += dt.timedelta(7)


if __name__ == '__main__':
    sys.exit(main())
