#!/usr/bin/env python3
"""KL8 分布图生成器 — 精确版"""
import json
import os

# ============================================================
# 最新5期数据 (从 51879.com 抓取)
# ============================================================
ISSUES = [
    ("2026151", [3,4,6,10,12,21,24,36,37,38,41,42,44,45,49,52,70,73,77,78]),
    ("2026152", [1,3,13,16,18,25,32,35,37,44,45,47,58,59,60,63,66,68,72,75]),
    ("2026153", [1,7,17,19,20,21,22,23,35,37,43,44,49,51,53,59,66,71,77,78]),
    ("2026154", [7,10,12,13,17,18,26,29,33,38,41,47,50,54,56,57,58,62,68,73]),
    ("2026155", [7,10,11,12,17,18,24,27,30,31,32,34,42,49,54,59,64,65,71,72]),
]

def get_row(n):
    if 1 <= n <= 20: return 1
    if 21 <= n <= 40: return 2
    if 41 <= n <= 60: return 3
    return 4

def get_row_range(r):
    return {1: (1,20), 2: (21,40), 3: (41,60), 4: (61,80)}[r]

def find_signals(nums_set):
    """检测满足列信号: R1有且仅有1个 + 下方恰好1行有且仅有1个"""
    signals = []
    for col in range(20):
        candidates = [col+1, col+21, col+41, col+61]  # R1~R4
        row1_num = candidates[0]
        below = candidates[1:]
        if row1_num in nums_set:
            below_hits = [n for n in below if n in nums_set]
            if len(below_hits) == 1:
                below_row = get_row(below_hits[0])
                signals.append({
                    'col': col,
                    'row1': row1_num,
                    'below': below_hits[0],
                    'below_row': below_row,
                    'pattern': f'R1+R{below_row}'
                })
    return signals

def detect_tail_heat(nums_set, threshold=3):
    """检测尾数热态: 同尾出现>=threshold个"""
    tail_count = {}
    for n in nums_set:
        t = n % 10
        tail_count[t] = tail_count.get(t, 0) + 1
    return {t: cnt for t, cnt in tail_count.items() if cnt >= threshold}

def build_grid_row(nums_set, row, signals, verify_set, tail_hot_tails):
    """为指定行生成20个格子的HTML"""
    rmin, rmax = get_row_range(row)
    cells_html = []
    for col in range(20):
        n = rmin + col
        if n > rmax:
            break
        cls = "cell"
        if n in nums_set:
            cls += " hit"
        else:
            cls += " empty"

        # 信号列高亮
        for sig in signals:
            if n == sig['row1']:
                cls += " signal-r1"
            elif n == sig['below']:
                cls += " signal-below"

        # 验证高亮 (上期信号延续命中)
        if n in verify_set:
            cls += " verify-hit"
            if "empty" in cls:
                cls = cls.replace(" empty", "")

        # 尾数热态
        tail = n % 10
        if tail in tail_hot_tails and n in nums_set:
            cls += " tail-hot"

        display = f"{n:02d}" if n in nums_set else ".."
        cells_html.append(f'<div class="{cls}">{display}</div>')

    return "".join(cells_html)

# ============================================================
# 计算各期信号
# ============================================================
issue_data = []
for issue, nums in ISSUES:
    nums_set = set(nums)
    signals = find_signals(nums_set)
    tail_hot = detect_tail_heat(nums_set)
    issue_data.append({
        'issue': issue,
        'nums': nums_set,
        'signals': signals,
        'tail_hot': tail_hot,
        'tail_hot_tails': set(tail_hot.keys()),
    })

# 计算验证 (上一期信号在当期的命中)
for i in range(1, len(issue_data)):
    prev_signals = issue_data[i-1]['signals']
    curr_nums = issue_data[i]['nums']
    verify_hits = set()
    for sig in prev_signals:
        if sig['row1'] in curr_nums:
            verify_hits.add(sig['row1'])
        if sig['below'] in curr_nums:
            verify_hits.add(sig['below'])
    issue_data[i]['verify'] = verify_hits
    # 统计验证命中数
    verify_count = len(verify_hits)
    total_sig = len(prev_signals) * 2  # 每信号2个号
    issue_data[i]['verify_count'] = verify_count
    issue_data[i]['verify_total'] = total_sig

# ============================================================
# 生成 HTML
# ============================================================
COL_HEADERS = "1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0".split()

html_parts = []

html_parts.append('''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>KL8 尾号对齐分布图</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#1a1a2e; color:#e0e0e0; font-family:'Consolas','Courier New',monospace; padding:20px; }
h1 { text-align:center; color:#ffd700; margin-bottom:5px; font-size:1.3em; }
.subtitle { text-align:center; color:#aaa; font-size:0.75em; margin-bottom:15px; }
.dist-block { margin-bottom:32px; padding:12px; background:#1e1e35; border-radius:8px; }
.issue-tag { color:#ffd700; font-weight:bold; font-size:0.95em; margin-bottom:6px; }
.cell { padding:4px 2px; text-align:center; font-size:0.85em; border-radius:3px; min-width:34px; }
.cell.hit { background:#2d5a2d; color:#7dff7d; font-weight:bold; }
.cell.empty { background:#252535; color:#444; }
.cell.signal-r1 { background:#6b3a00; color:#ffaa00; font-weight:bold; border:1px solid #ff8800; }
.cell.signal-below { background:#5a2a00; color:#ffcc00; font-weight:bold; border:1px solid #ff9900; }
.cell.verify-hit { background:#1a5a1a; color:#00ff88; font-weight:bold; border:1px solid #00ff88; }
.cell.tail-hot { background:#3a1a3a; color:#ff66ff; font-weight:bold; border:1px solid #ff66ff; }
.cell.empty.verify-hit { background:#1a4a1a; color:#00ff88; font-weight:bold; }
.cell.hit.verify-hit { background:#1a6a1a; color:#00ff88; font-weight:bold; border:2px solid #00ff88; }
.col-header { text-align:center; font-size:0.8em; color:#666; }
.row-label { font-size:0.8em; color:#777; display:flex; align-items:center; justify-content:flex-end; padding-right:8px; }
.grid { display:grid; grid-template-columns:50px repeat(20,1fr); gap:2px; margin-bottom:2px; }
.signal-bar { margin-top:8px; padding:6px 12px; background:#252540; border-radius:5px; font-size:0.82em; }
.signal-item { color:#ffaa00; }
.verify-item { color:#00ff88; }
.tail-hot-item { color:#ff66ff; }
.legend { font-size:0.75em; color:#777; margin-top:20px; padding:10px; background:#222236; border-radius:5px; }
.legend span { margin-right:15px; }
.l-hit{color:#7dff7d;}.l-r1{color:#ffaa00;}.l-below{color:#ffcc00;}.l-verify{color:#00ff88;}.l-tailhot{color:#ff66ff;}
.rec-box { margin-top:20px; padding:12px 16px; background:#1a2a1a; border:1px solid #ffd700; border-radius:6px; font-size:0.9em; }
.rec-title { color:#ffd700; font-weight:bold; }
.rec-nums { color:#00ff88; font-size:1.3em; font-weight:bold; margin:8px 0; }
.rec-warn { color:#ff6666; font-size:0.75em; }
</style>
</head>
<body>
<h1>KL8 尾号对齐分布图 (最近5期)</h1>
<div class="subtitle">列: 1 2 3 4 5 6 7 8 9 0 | 1 2 3 4 5 6 7 8 9 0</div>
''')

# 按时间倒序 (最新在前)
for idx in range(len(issue_data)-1, -1, -1):
    d = issue_data[idx]
    nums_set = d['nums']
    signals = d['signals']
    tail_hot = d['tail_hot']
    tail_hot_tails = d['tail_hot_tails']
    verify_set = d.get('verify', set())
    verify_count = d.get('verify_count', 0)
    verify_total = d.get('verify_total', 0)

    issue_label = f"{d['issue']}期"
    if idx == len(issue_data) - 1:
        issue_label += " (最新)"

    # 附加信息
    extras = []
    if verify_count > 0:
        extras.append(f"上期验证: {verify_count}/{verify_total}命中")
    if tail_hot:
        hot_desc = ", ".join(f"尾{t}出{c}个" for t, c in tail_hot.items())
        extras.append(f"尾数热态: {hot_desc}")

    extra_html = ""
    if extras:
        extra_html = ' <span style="color:#ff66ff;font-size:0.8em;">| ' + " | ".join(extras) + '</span>'

    html_parts.append(f'''
<div class="dist-block">
  <div class="issue-tag">{issue_label}{extra_html}</div>
  <div class="grid">
    <div class="row-label"></div>
''')

    # 列头
    for h in COL_HEADERS:
        html_parts.append(f'    <div class="col-header">{h}</div>\n')
    html_parts.append('\n')

    # 4行数据
    for row in range(1, 5):
        row_html = build_grid_row(nums_set, row, signals, verify_set, tail_hot_tails)
        html_parts.append(f'    <div class="row-label">R{row}</div>\n')
        html_parts.append(f'    {row_html}\n')

    html_parts.append('  </div>')  # close grid

    # 信号栏
    html_parts.append('  <div class="signal-bar">')
    if signals:
        sig_desc = " | ".join(
            f"col{s['col']}(尾{(s['col']%10+1)%10 or '0'}): {s['row1']:02d}(R1)+{s['below']:02d}(R{s['below_row']})"
            for s in signals
        )
        html_parts.append(f'    <span class="signal-item">信号({len(signals)}): {sig_desc}</span>')
    else:
        html_parts.append(f'    <span class="signal-item">信号: 无</span>')

    if verify_set:
        vnums = sorted(verify_set)
        vnums_str = ", ".join(f"{n:02d}" for n in vnums)
        html_parts.append(f'    <br><span class="verify-item">验证命中({verify_count}/{verify_total}): {vnums_str}</span>')

    html_parts.append('  </div>')
    html_parts.append('</div>')

# ============================================================
# 推荐区: 基于最新一期信号推荐下一期
# 使用尾数+pattern位置分布回测结果，推荐历史最优位置的号
# ============================================================
import json as json_mod
BACKTEST_FILE = os.path.join(os.path.dirname(__file__), "backtest_result.json")
TAIL_PATTERN_FILE = os.path.join(os.path.dirname(__file__), "tail_pattern_backtest.json")
BACKTEST = {}
TAIL_PATTERN = {}
if os.path.exists(BACKTEST_FILE):
    with open(BACKTEST_FILE, 'r', encoding='utf-8') as f:
        BACKTEST = json_mod.load(f)
if os.path.exists(TAIL_PATTERN_FILE):
    with open(TAIL_PATTERN_FILE, 'r', encoding='utf-8') as f:
        TAIL_PATTERN = json_mod.load(f)

def get_recommended_number(signal):
    """根据尾数+pattern历史位置分布，决定推荐哪个位置的号"""
    col = signal['col']
    tail = (col + 1) % 10
    pattern = signal['pattern']
    key = f'{tail}+{pattern}'
    
    if key not in TAIL_PATTERN:
        return signal['below'], f'无数据→below({signal["below"]:02d})'
    
    data = TAIL_PATTERN[key]
    total = data['total']
    
    if total < 5:
        return signal['below'], f'样本{total}<5→below({signal["below"]:02d})'
    
    best_row = max(['R1', 'R2', 'R3', 'R4'], key=lambda r: data[f'{r}_pct'])
    best_pct = data[f'{best_row}_pct']
    below_row_name = f'R{signal["below_row"]}'
    below_pct = data.get(f'{below_row_name}_pct', 0)
    
    # below号自身最优，不用改
    if best_row == below_row_name:
        return signal['below'], f'below最优{best_pct:.0f}%(n={total})'
    
    # 差距<5%不折腾
    if best_pct - below_pct < 5:
        return signal['below'], f'差距小({best_pct:.0f}%vs{below_pct:.0f}%),below'
    
    row_num = int(best_row[1])
    rmin = {1: 1, 2: 21, 3: 41, 4: 61}[row_num]
    recommended = rmin + col
    
    return recommended, f'{best_row}={best_pct:.0f}%>>below{below_pct:.0f}%(n={total})'

latest = issue_data[-1]  # 最新一期
signals = latest['signals']
tail_hot = latest['tail_hot']
latest_issue = latest['issue']
target_issue = str(int(latest_issue) + 1)

# 基于位置分布回测确定推荐号
signal_recs = []
for s in signals:
    rec, reason = get_recommended_number(s)
    s['recommended'] = rec
    s['rec_reason'] = reason
    signal_recs.append(s)

# 排序: 按位置概率差距（最优-次优）→ 差距越大越可靠, 样本量平局
scored_signals = []
for s in signal_recs:
    col = s['col']
    tail = (col + 1) % 10
    pattern = s['pattern']
    key = f'{tail}+{pattern}'
    
    if key in TAIL_PATTERN and TAIL_PATTERN[key]['total'] >= 5:
        data = TAIL_PATTERN[key]
        pcts = sorted([data['R1_pct'], data['R2_pct'], data['R3_pct'], data['R4_pct']], reverse=True)
        gap = pcts[0] - pcts[1]
        total = data['total']
    else:
        gap = 0
        total = 0
    
    scored_signals.append((gap, total, s))

scored_signals.sort(key=lambda x: (-x[0], -x[1]))

# ★ 尾数去重: 同尾数只保留差距最大的那个信号作为 primary
# 被去重的信号保留为 reserve（补号优先使用）
seen_tails = set()
primary_signals = []
reserve_signals = []
for gap, total, s in scored_signals:
    tail = (s['col'] + 1) % 10  # gen_dist.py 信号字典无tail字段, 从col计算
    if tail not in seen_tails:
        seen_tails.add(tail)
        primary_signals.append((gap, total, s))
    else:
        reserve_signals.append((gap, total, s))
scored_signals = primary_signals

if len(scored_signals) >= 3:
    # 3+信号 → 出2组单注 + 4号复式(6注12元)
    best = scored_signals[0][2]
    second = scored_signals[1][2]
    third = scored_signals[2][2]
    n_best = best['recommended']
    n_second = second['recommended']
    n_third = third['recommended']
    
    # 第4号: 优先 reserve信号 → below号 → 纯R1兜底
    fourth_info = ''
    if len(scored_signals) >= 4:
        n_fourth = scored_signals[3][2]['recommended']
        fourth_info = f'4列信号'
    else:
        n_fourth = None
        # 1. 尝试被去重的reserve信号
        for _, _, rs in reserve_signals:
            rn = rs['recommended']
            if rn not in (n_best, n_second, n_third):
                n_fourth = rn
                fourth_info = f'3信号+reserve col{rs["col"]}'
                break
        # 2. 尝试below号
        if n_fourth is None:
            below_candidates = [third['below'], second['below'], best['below']]
            for bc in below_candidates:
                if bc not in (n_best, n_second, n_third):
                    n_fourth = bc
                    fourth_info = '3信号+below补'
                    break
        # 3. 纯R1兜底
        if n_fourth is None:
            # 极端情况: 所有below号都与推荐号重复，用纯R1兜底
            r1_cols = []
            rows_r1 = {
                1: [n for n in latest['nums'] if 1 <= n <= 20],
                2: [n for n in latest['nums'] if 21 <= n <= 40],
                3: [n for n in latest['nums'] if 41 <= n <= 60],
                4: [n for n in latest['nums'] if 61 <= n <= 80],
            }
            signal_cols = {s['col'] for s in signals}
            for col in range(20):
                r1 = [n for n in rows_r1[1] if (n-1) % 20 == col]
                r2 = [n for n in rows_r1[2] if (n-21) % 20 == col]
                r3 = [n for n in rows_r1[3] if (n-41) % 20 == col]
                r4 = [n for n in rows_r1[4] if (n-61) % 20 == col]
                has_r1 = len(r1) == 1
                below_any = sum([len(r2)>=1, len(r3)>=1, len(r4)>=1])
                if has_r1 and below_any == 0 and col not in signal_cols:
                    r1_cols.append((col, r1[0]))
            r1_cols.sort(key=lambda x: x[0])
            if r1_cols:
                n_fourth = r1_cols[0][1]
                fourth_info = f'3信号+纯R1补col{r1_cols[0][0]}(兜底)'
            else:
                n_fourth = n_third
                fourth_info = f'3信号+兜底(下方号全重复)'
        else:
            fourth_info = f'3信号+below补'
    
    rec_html = f'''
<div class="rec-box">
  <div class="rec-title">{target_issue}期推荐 (基于{latest_issue}期{len(signals)}个信号)</div>
  <div class="rec-nums">{n_best:02d} + {n_second:02d} (A组) | {n_best:02d} + {n_third:02d} (B组)</div>
  <div style="font-size:0.8em;color:#aaa;margin-top:4px;">col{best['col']}→{best['rec_reason']} | col{second['col']}→{second['rec_reason']} | col{third['col']}→{third['rec_reason']}</div>
  <div style="margin-top:6px;color:#ffaa00;font-weight:bold;font-size:1.1em;">4号复式: {n_best:02d} + {n_second:02d} + {n_third:02d} + {n_fourth:02d} (6注12元, {fourth_info})</div>
  <div>策略: 选二复式C(4,2)=6注, 回测命中~36-40%</div>
</div>'''

elif len(scored_signals) == 2:
    # 2信号 → 单注2号 + 推荐号→4号复式
    # 补号优先级: reserve信号 > below号 > 纯R1
    n1 = scored_signals[0][2]['recommended']
    n2 = scored_signals[1][2]['recommended']
    
    # 从原始signals获取below号
    sig_map = {s['col']: s for s in signals}
    s1 = sig_map[scored_signals[0][2]['col']]
    s2 = sig_map[scored_signals[1][2]['col']]
    below1, below2 = s1['below'], s2['below']
    
    # 4号复式补号: reserve → below → 纯R1
    rec_nums_4 = [n1, n2]
    fill_desc = []
    for _, _, rs in reserve_signals:
        rn = rs['recommended']
        if rn not in rec_nums_4:
            rec_nums_4.append(rn)
            fill_desc.append(f'reserve col{rs["col"]}')
            if len(rec_nums_4) >= 4:
                break
    if len(rec_nums_4) < 4:
        for bn in [below1, below2]:
            if bn not in rec_nums_4:
                rec_nums_4.append(bn)
                if len(rec_nums_4) >= 4:
                    break
    rec_nums_4 = sorted(set(rec_nums_4))
    
    duplex_html = ''
    if len(rec_nums_4) >= 4:
        desc = '+'.join(fill_desc) if fill_desc else '推荐+below'
        duplex_html = f'<div style="margin-top:6px;color:#ffaa00;font-weight:bold;font-size:1.1em;">4号复式: {rec_nums_4[0]:02d} + {rec_nums_4[1]:02d} + {rec_nums_4[2]:02d} + {rec_nums_4[3]:02d} (推荐+{desc}, 6注12元)</div><div>策略: 推荐号+{desc}, 2列→4号复式回测命中33.8% vs 单注14.7%</div>'
    elif len(rec_nums_4) == 3:
        duplex_html = f'<div style="margin-top:6px;color:#ffaa00;font-weight:bold;font-size:1.1em;">3号复式: {rec_nums_4[0]:02d} + {rec_nums_4[1]:02d} + {rec_nums_4[2]:02d} (3注6元)</div>'
    
    rec_html = f'''
<div class="rec-box">
  <div class="rec-title">{target_issue}期推荐 (基于{latest_issue}期{len(signals)}个信号)</div>
  <div class="rec-nums">{n1:02d} + {n2:02d}</div>
  <div style="font-size:0.8em;color:#aaa;margin-top:4px;">col{s1['col']}→{scored_signals[0][2]['rec_reason']} | col{s2['col']}→{scored_signals[1][2]['rec_reason']}</div>
  {duplex_html}
</div>'''

else:
    # ≤1信号 → 观望
    if signals:
        rec_nums = " + ".join(f"{s['below']:02d}" for s in signals)
    else:
        rec_nums = "无信号"
    
    tail_tips = ""
    if tail_hot:
        hot_tails = sorted(tail_hot.keys())
        hot_tails_str = ", ".join(str(t) for t in hot_tails)
        tail_tips = f'<div style="margin-top:4px;color:#ff66ff;font-size:0.85em;">尾数热态关注: {hot_tails_str}</div>'
    
    rec_html = f'''
<div class="rec-box">
  <div class="rec-title">{target_issue}期推荐 (信号{len(signals)}个, ≤1列)</div>
  <div class="rec-nums">{rec_nums}</div>
  <div class="rec-warn" style="margin-top:8px;font-size:0.9em;">⚠ 信号≤1列, 本期不出手, 观望</div>
  {tail_tips}
</div>'''

html_parts.append(rec_html)

# 图例
html_parts.append('''
<div class="legend">
  <span class="l-tailhot">粉紫边框</span> 尾数热态(同尾≥3个)
  <span class="l-verify">亮绿边框</span> 上期信号延续命中
  <span class="l-r1">橙边框</span> 信号列R1号
  <span class="l-below">深橙</span> 信号列下方号
  <span class="l-hit">绿</span> 普通命中
  <span style="color:#444;">灰</span> 未出
</div>
</body>
</html>
''')

output = "".join(html_parts)

with open("d:/WechatBot/kl8_distribution.html", "w", encoding="utf-8") as f:
    f.write(output)

# ============================================================
# 验证输出
# ============================================================
print("=== 分布图已生成: kl8_distribution.html ===")
print()
for d in issue_data:
    print(f"{d['issue']}期: {len(d['signals'])}个信号")
    for s in d['signals']:
        print(f"  col{s['col']}(尾{(s['col']%10+1)%10 or '0'}): {s['row1']:02d}(R1)+{s['below']:02d}(R{s['below_row']})")
    if d.get('verify_set'):
        v = sorted(d['verify_set'])
        print(f"  验证命中: {', '.join(f'{n:02d}' for n in v)}")
    if d['tail_hot']:
        print(f"  尾数热态: {d['tail_hot']}")
    print()

latest_info = issue_data[-1]
print(f"=== {latest_info['issue']}期(最新) ===")
print(f"号码: {sorted(latest_info['nums'])}")
print(f"信号: {len(latest_info['signals'])}个")
for s in latest_info['signals']:
    print(f"  col{s['col']}: R1={s['row1']:02d} + R{s['below_row']}={s['below']:02d}")
print(f"尾数分布: {latest_info['tail_hot']}")
