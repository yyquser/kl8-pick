#!/usr/bin/env python3
"""
KL8 每日选二推荐系统
策略：
  基于回测结果，只推荐靠谱分数高的信号列
  靠谱分数 = 信号延续率 × 号码延续率 / 100
追踪: daily_tracker.json 记录每期推荐及命中结果
"""
import urllib.request, gzip, re, json, os
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))
today = datetime.now(tz).strftime("%Y-%m-%d")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKER_FILE = os.path.join(SCRIPT_DIR, "daily_tracker.json")
BACKTEST_FILE = os.path.join(SCRIPT_DIR, "backtest_result.json")
TAIL_PATTERN_FILE = os.path.join(SCRIPT_DIR, "tail_pattern_backtest.json")

# 加载回测结果
def load_backtest():
    """加载回测结果，如果不存在则返回空字典"""
    if os.path.exists(BACKTEST_FILE):
        with open(BACKTEST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'col_continuation': {}, 'pattern_continuation': {}, 'col_hit_rate': {}}

# 加载尾数+pattern位置分布回测
def load_tail_pattern_backtest():
    """加载尾数+pattern位置分布回测结果"""
    if os.path.exists(TAIL_PATTERN_FILE):
        with open(TAIL_PATTERN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

BACKTEST = load_backtest()
TAIL_PATTERN = load_tail_pattern_backtest()

# ============ 数据获取 ============
def fetch_latest_data():
    url = "https://www.51879.com/kaijiang/kl8/"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Encoding": "gzip",
        "Accept": "text/html,application/xhtml+xml"
    })
    resp = urllib.request.urlopen(req, timeout=15)
    data = resp.read()
    if resp.getheader("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    html = data.decode("utf-8", errors="replace")
    
    rows = re.findall(
        r"<tr>\s*<td>\s*(\d+)\s*</td>\s*<td>.*?</td>\s*<td class=\"hm\">(.*?)</td>",
        html, re.DOTALL
    )
    result = {}
    for issue, nums_html in rows:
        nums = [int(n) for n in re.findall(r">(\d+)<", nums_html)]
        if len(nums) == 20:
            result[issue] = sorted(nums)
    return result


# ============ 信号检测 ============
def get_number_by_position(col, row):
    """根据列和行计算具体号码
    col: 0-19 (对应尾数1-0)
    row: 1-4 (R1-R4)
    返回: 号码 (1-80)
    """
    return (row - 1) * 20 + col + 1


def find_signals(nums_set):
    signals = []
    for col in range(20):
        cn = [col + 1, col + 21, col + 41, col + 61]
        row1 = cn[0]
        below = cn[1:]
        if row1 in nums_set:
            bp = [n for n in below if n in nums_set]
            if len(bp) == 1:
                below_row = (bp[0] - 1) // 20 + 1
                signals.append({
                    "col": col,
                    "tail": bp[0] % 10,
                    "row1": row1,
                    "below": bp[0],
                    "below_row": below_row,
                    "pattern": f"R1+R{below_row}"
                })
    return signals


# ============ 尾数分析 ============
def get_tail_distribution(nums):
    """返回 {tail: [numbers]}"""
    dist = {}
    for n in nums:
        t = n % 10
        dist.setdefault(t, []).append(n)
    return dist


# ============ 回测数据(内置26期) ============
HISTORY = {
    "115": [5,6,7,12,14,25,26,30,31,33,36,43,44,48,51,57,70,75,77,80],
    "116": [3,11,16,22,27,31,32,36,40,47,48,58,62,65,67,69,70,74,75,80],
    "117": [4,15,19,20,24,26,29,39,42,44,45,48,49,55,56,60,61,66,75,77],
    "118": [2,7,8,9,12,17,18,33,36,39,44,46,61,66,68,69,71,72,75,80],
    "119": [3,12,14,15,17,22,23,27,31,39,43,46,48,53,54,64,66,69,77,78],
    "120": [2,3,6,10,16,21,35,37,43,45,52,54,57,63,67,68,70,76,78,80],
    "121": [2,16,18,19,26,32,33,38,39,42,49,50,52,54,60,61,63,65,72,78],
    "122": [1,7,9,15,19,26,27,28,30,36,45,50,56,57,58,61,63,66,76,78],
    "123": [11,14,17,21,23,24,30,34,41,43,50,51,52,58,62,71,74,75,78,80],
    "124": [3,7,8,9,14,23,31,34,35,37,38,40,43,47,61,63,66,71,76,78],
    "125": [9,30,38,39,40,41,43,44,45,46,47,51,53,54,56,58,60,67,76,77],
    "126": [1,4,10,11,12,16,22,23,29,36,39,43,52,57,59,60,61,62,64,74],
    "127": [1,5,10,14,15,27,31,33,34,47,51,54,57,63,65,66,69,73,77,78],
    "128": [4,5,11,13,17,19,26,28,38,39,41,43,45,46,47,51,53,60,75,76],
    "129": [3,8,9,12,17,25,28,29,33,36,38,43,49,59,60,62,63,66,76,78],
    "130": [2,7,8,10,18,21,22,26,28,30,31,32,33,39,41,49,52,62,64,67],
    "131": [7,19,25,28,32,33,36,38,43,44,46,50,55,61,65,70,71,72,73,79],
    "132": [8,9,11,12,13,16,18,19,32,37,38,40,42,53,56,57,63,68,77,78],
    "133": [1,6,9,16,18,19,21,26,27,29,55,58,59,60,62,66,73,74,76,80],
    "134": [6,12,19,20,21,22,27,30,31,32,34,42,51,54,57,66,70,71,72,75],
    "135": [8,13,20,23,24,27,29,37,42,48,49,50,51,57,59,60,64,65,67,77],
    "136": [2,6,11,14,17,20,24,33,35,40,42,45,49,50,51,52,57,60,64,75],
    "137": [4,8,9,13,14,15,16,17,18,23,28,39,47,48,53,56,63,66,77,79],
    "138": [2,6,8,10,11,14,19,22,26,30,31,33,47,53,56,62,63,73,76,77],
    "139": [2,6,7,9,10,11,14,19,22,23,26,30,36,40,41,44,47,51,53,60],
    "140": [1,3,11,12,16,18,23,24,31,35,37,39,40,54,61,64,65,69,71,79],
    "141": [6,9,10,20,21,28,33,38,48,49,52,54,57,64,66,70,72,74,75,77],
    "142": [2,4,10,14,18,21,26,35,39,40,41,48,50,53,57,59,65,73,75,76],
    "143": [2,3,7,11,14,23,30,31,34,38,39,41,47,51,52,60,63,68,72,78],
    "144": [3,4,12,24,27,30,34,50,53,55,61,63,65,69,70,72,74,75,76,77],
    "145": [2,4,5,15,19,24,27,29,32,33,36,38,50,52,60,64,66,69,74,75],
    "146": [4,7,9,10,14,27,38,39,40,43,44,45,48,50,54,56,66,70,77,78],
    "147": [3,6,7,10,11,12,14,17,22,24,28,35,37,38,45,50,52,67,77,79],
    "148": [1,2,7,11,17,18,26,28,30,38,41,42,43,54,59,62,69,71,74,79],
    "149": [2,4,10,12,13,17,23,30,31,33,37,43,47,55,58,62,65,72,75,77],
    "150": [7,8,12,18,19,23,24,27,53,54,56,57,59,60,62,70,74,77,78,79],
    "151": [3,4,6,10,12,21,24,36,37,38,41,42,44,45,49,52,70,73,77,78],
    "152": [1,3,13,16,18,25,32,35,37,44,45,47,58,59,60,63,66,68,72,75],
    "153": [1,7,17,19,20,21,22,23,35,37,43,44,49,51,53,59,66,71,77,78],
    "154": [7, 10, 12, 13, 17, 18, 26, 29, 33, 38, 41, 47, 50, 54, 56, 57, 58, 62, 68, 73],
    "155": [7, 10, 11, 12, 17, 18, 24, 27, 30, 31, 32, 34, 42, 49, 54, 59, 64, 65, 71, 72],
}


def compute_tail_continuation_rate(history):
    """计算每个尾数的历史延续率（当某尾>=2个时，下期至少出1个的概率）"""
    issues = sorted(history.keys())
    tail_stats = {}  # {tail: {"hit": N, "total": N}}
    for i in range(len(issues) - 1):
        cur = set(history[issues[i]])
        nxt = set(history[issues[i + 1]])
        cur_dist = get_tail_distribution(history[issues[i]])
        for t, nums in cur_dist.items():
            if len(nums) >= 2:
                nxt_has = any(n % 10 == t for n in history[issues[i + 1]])
                tail_stats.setdefault(t, {"hit": 0, "total": 0})
                tail_stats[t]["total"] += 1
                if nxt_has:
                    tail_stats[t]["hit"] += 1
    return tail_stats


def compute_number_frequency(history):
    """统计历史各号码出现次数"""
    freq = {}
    for nums in history.values():
        for n in nums:
            freq[n] = freq.get(n, 0) + 1
    return freq


# ============ 降温机制 ============
def count_recent_appearances(num, history, window=10):
    """统计某号码在最近N期内出现的次数"""
    issues = sorted(history.keys())[-window:]
    return sum(1 for iss in issues if num in history.get(iss, []))

def apply_cooling_off(signals, history, window=10):
    """降温机制: recommended号近N期出现≥4次 → 标记overheated=True
    在排序时，过热号会打折（分数*0.5）
    支持 (score, sig) 元组列表或纯 sig 列表
    """
    # 兼容 (score, sig) 元组列表
    if signals and isinstance(signals[0], tuple):
        sigs = [s[1] for s in signals]
    else:
        sigs = signals
    
    for s in sigs:
        num = s.get("recommended", s["below"])
        count = count_recent_appearances(num, history, window)
        if count >= 4:
            s["overheated"] = True
            s["overheated_count"] = count
        else:
            s["overheated"] = False
            s["overheated_count"] = 0
    return [s for s in sigs if s.get("overheated")]


# ============ 纯R1列（信号不足3列时的补充） ============
def find_r1_alone_columns(nums_set):
    """找纯R1列: R1恰好1个号 + 下方0个号
    回测延续率72.8%, 比信号列(68.4%)还高
    返回: [(col, r1_num), ...] 按历史延续率排序
    """
    rows = {
        1: [n for n in nums_set if 1 <= n <= 20],
        2: [n for n in nums_set if 21 <= n <= 40],
        3: [n for n in nums_set if 41 <= n <= 60],
        4: [n for n in nums_set if 61 <= n <= 80],
    }
    
    candidates = []
    for col in range(20):
        r1 = [n for n in rows[1] if (n-1) % 20 == col]
        r2 = [n for n in rows[2] if (n-21) % 20 == col]
        r3 = [n for n in rows[3] if (n-41) % 20 == col]
        r4 = [n for n in rows[4] if (n-61) % 20 == col]
        
        has_r1 = len(r1) == 1
        below_any = sum([len(r2)>=1, len(r3)>=1, len(r4)>=1])
        
        if has_r1 and below_any == 0:
            candidates.append((col, r1[0]))
    
    # 无额外排序依据，按列号排序即可
    candidates.sort(key=lambda x: x[0])
    return candidates


# ============ 推荐策略 ============
def get_recommended_number(signal, tail_pattern_data):
    """根据尾数+pattern历史位置分布，决定推荐哪个位置的号
    返回: (推荐号, 推荐理由)
    """
    col = signal['col']
    tail = (col + 1) % 10
    pattern = signal['pattern']
    key = f'{tail}+{pattern}'
    
    if key not in tail_pattern_data:
        return signal['below'], f'无历史数据,回退到below({signal["below"]:02d})'
    
    data = tail_pattern_data[key]
    total = data['total']
    
    if total < 5:
        return signal['below'], f'样本不足({total}<5),回退到below({signal["below"]:02d})'
    
    # 找最优位置
    best_row = max(['R1', 'R2', 'R3', 'R4'], key=lambda r: data[f'{r}_pct'])
    best_pct = data[f'{best_row}_pct']
    below_row_name = f'R{signal["below_row"]}'
    below_pct = data.get(f'{below_row_name}_pct', 0)
    
    # 如果最优位置就是below号位置，不用改
    if best_row == below_row_name:
        return signal['below'], f'below号自身最优({best_pct:.1f}%,样本{total})'
    
    # 最优位置概率比below号高≥5个百分点才改推荐
    if best_pct - below_pct < 5:
        return signal['below'], f'差距不足5%({best_pct:.1f}%vs{below_pct:.1f}%),回退below'
    
    # 推荐最优位置的号
    row_num = int(best_row[1])
    recommended = get_number_by_position(col, row_num)
    
    return recommended, f'历史{best_row}={best_pct:.1f}%>>below={below_pct:.1f}%(样本{total})'


def generate_recommendation(latest_issue, latest_nums, history):
    """返回推荐列表 [(pair, strategy, reason, group_label), ...]
    改进: 基于尾数+pattern历史位置分布推荐号
    """
    nums_set = set(latest_nums)
    signals = find_signals(nums_set)
    tail_stats = compute_tail_continuation_rate(history)
    freq = compute_number_frequency(history)
    tail_dist = get_tail_distribution(latest_nums)
    
    # 为每个信号列决定推荐哪个位置的号 + 计算排序分
    # 排序依据: 位置概率差距(最优-次优) → 越大越可靠, 样本量作为平局裁决
    scored_signals = []
    for s in signals:
        recommended, reason = get_recommended_number(s, TAIL_PATTERN)
        s['recommended'] = recommended
        s['recommend_reason'] = reason
        
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
    
    # 按 差距↓ → 样本量↓ 排序
    scored_signals.sort(key=lambda x: (-x[0], -x[1]))

    # ★ 尾数去重: 同尾数只保留差距最大的那个信号作为 primary
    # 被去重的信号保留为 reserve（补号优先使用），避免"同生共死"
    # 如155期col16(尾7)被去重但37虽未中，reserve机制保留了col11的12纯R1兜底
    seen_tails = set()
    primary_signals = []
    reserve_signals = []
    for gap, total, s in scored_signals:
        tail = s['tail']
        if tail not in seen_tails:
            seen_tails.add(tail)
            primary_signals.append((gap, total, s))
        else:
            reserve_signals.append((gap, total, s))
    scored_signals = primary_signals

    # 策略: 按信号数列数分级
    #    ≥3列 → 出2组单注 + 4号复式(6注12元)
    #    =2列 → 正常推荐2个号单注
    #    ≤1列 → 观望不出手
    
    def fmt_info(sig):
        rec = sig['recommended']
        reason = sig['recommend_reason']
        return f'col{sig["col"]}→{rec:02d}({reason})'
    
    if len(scored_signals) >= 3:
        # 3+信号 → A组 + B组 + 4号复式
        best = scored_signals[0][2]
        second = scored_signals[1][2]
        third = scored_signals[2][2]
        n_best = best['recommended']
        n_second = second['recommended']
        n_third = third['recommended']
        
        results = []
        results.append((
            (n_best, n_second), 'signal',
            f'A组: {fmt_info(best)} | {fmt_info(second)}',
            'A'
        ))
        results.append((
            (n_best, n_third), 'signal',
            f'B组: {fmt_info(best)} | {fmt_info(third)}',
            'B'
        ))
        
        # 4号复式(C4,2=6注12元): 信号Top3 + 第4号(第4信号/below号/纯R1)
        if len(scored_signals) >= 4:
            n_fourth = scored_signals[3][2]['recommended']
            results.append((
                (n_best, n_second, n_third, n_fourth), 'signal+4号复式',
                f'4号复式: {n_best:02d}+{n_second:02d}+{n_third:02d}+{n_fourth:02d} (4列信号, 6注12元)',
                '4号复式'
            ))
        else:
            # 只有3信号, 第4号优先顺序: reserve信号 → below号 → 纯R1
            n_fourth = None
            fourth_source = ''
            
            # 1. 尝试被去重的reserve信号
            for _, _, rs in reserve_signals:
                rn = rs['recommended']
                if rn not in (n_best, n_second, n_third):
                    n_fourth = rn
                    fourth_source = f'reserve col{rs["col"]}'
                    break
            
            # 2. 尝试below号
            if n_fourth is None:
                below_candidates = [third['below'], second['below'], best['below']]
                for bc in below_candidates:
                    if bc not in (n_best, n_second, n_third):
                        n_fourth = bc
                        fourth_source = 'below补'
                        break
            
            # 3. 纯R1兜底
            if n_fourth is None:
                r1_cols = find_r1_alone_columns(nums_set)
                signal_cols = {s['col'] for s in signals}
                r1_cols = [(c, n) for c, n in r1_cols if c not in signal_cols]
                if r1_cols:
                    n_fourth = r1_cols[0][1]
                    fourth_source = f'纯R1 col{r1_cols[0][0]}'
            if n_fourth:
                results.append((
                    (n_best, n_second, n_third, n_fourth), 'signal+4号复式',
                    f'4号复式: {n_best:02d}+{n_second:02d}+{n_third:02d}+{n_fourth:02d} (3信号+{fourth_source}, 6注12元)',
                    '4号复式'
                ))
        return results
    
    if len(scored_signals) == 2:
        # 2信号 → 单注2号 + 推荐号→4号复式(6注12元)
        # 补号优先级: reserve信号 > below号 > 纯R1
        n1 = scored_signals[0][2]['recommended']
        n2 = scored_signals[1][2]['recommended']
        s1, s2 = scored_signals[0][2], scored_signals[1][2]
        
        results = []
        reason_a = f'信号2列: {fmt_info(s1)} | {fmt_info(s2)}'
        results.append(((n1, n2), 'signal', reason_a, None))
        
        # 4号复式: 推荐号 + reserve/below/纯R1
        rec_nums = [n1, n2]
        fill_desc = []
        
        # 1. 尝试reserve信号
        for _, _, rs in reserve_signals:
            rn = rs['recommended']
            if rn not in rec_nums:
                rec_nums.append(rn)
                fill_desc.append(f'reserve col{rs["col"]}')
                if len(rec_nums) >= 4:
                    break
        
        # 2. 尝试below号
        if len(rec_nums) < 4:
            for bn in [s1['below'], s2['below']]:
                if bn not in rec_nums:
                    rec_nums.append(bn)
                    fill_desc.append('below')
                    if len(rec_nums) >= 4:
                        break
        
        # 3. 纯R1兜底
        if len(rec_nums) < 4:
            r1_cols = find_r1_alone_columns(nums_set)
            signal_cols = {s['col'] for s in signals}
            r1_cols = [(c, n) for c, n in r1_cols if c not in signal_cols and n not in rec_nums]
            if r1_cols:
                col4, n4 = r1_cols[0]
                rec_nums.append(n4)
                fill_desc.append(f'纯R1 col{col4}')
        
        if len(rec_nums) >= 4:
            desc = '+'.join(fill_desc[:2]) if fill_desc else '推荐+below'
            results.append((
                tuple(rec_nums[:4]), 'signal+4号复式',
                f'4号复式(推荐+{desc}): col{s1["col"]}→{n1:02d} + col{s2["col"]}→{n2:02d} (6注12元, 2列信号回测命中33.8%)',
                '4号复式'
            ))
        elif len(rec_nums) == 3:
            results.append((
                tuple(rec_nums), 'signal+3号复式',
                f'3号复式(推荐+{"/".join(fill_desc)}): col{s1["col"]}→{n1:02d} + col{s2["col"]}→{n2:02d} (3注6元)',
                '3号复式'
            ))
        return results
    
    # ≤1信号 → 观望不出手
    if signals:
        sig_desc = ", ".join(f'col{s["col"]}' for s in signals)
        return [((None, None), '观望', f'信号仅{len(signals)}列({sig_desc}), ≤1列不出手', None)]
    return [((None, None), '观望', '无满足列信号, ≤1列不出手', None)]
    
    # 所有情况已在上方return, 此处不应到达
    return [((None, None), 'fallback', '未知错误', None)]


# ============ 追踪系统 ============
def load_tracker():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"recommendations": []}


def save_tracker(tracker):
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)


def check_previous_hits(tracker, latest_data):
    """用最新开奖数据核验之前未命中的推荐"""
    issues = sorted(latest_data.keys())
    for rec in tracker["recommendations"]:
        if rec.get("hit") is not None:
            continue  # 已结算
        target = rec["target_issue"]
        if target in latest_data:
            nums = set(latest_data[target])
            pair = rec["pair"]
            hits = [n for n in pair if n in nums]
            rec["hit"] = len(hits) >= 2
            rec["hit_count"] = len(hits)
            rec["hit_nums"] = hits
            rec["checked_date"] = today


# ============ 主流程 ============
def main():
    print(f"=== KL8 每日选二推荐 {today} ===\n")
    
    # 1. 获取最新数据
    try:
        live_data = fetch_latest_data()
        print(f"[数据] 从51879获取到{len(live_data)}期")
    except Exception as e:
        print(f"[警告] 在线获取失败: {e}")
        print("[数据] 使用内置历史数据")
        live_data = HISTORY
    
    # 2. 合并数据
    all_data = {**HISTORY, **live_data}
    issues = sorted(all_data.keys())
    latest_issue = issues[-1]
    latest_nums = all_data[latest_issue]
    print(f"[最新] {latest_issue}期: {latest_nums}")
    
    # 3. 加载追踪器, 核验历史推荐
    tracker = load_tracker()
    check_previous_hits(tracker, all_data)
    
    # 4. 打印历史战绩
    if tracker["recommendations"]:
        print(f"\n=== 历史战绩 ===")
        total = len(tracker["recommendations"])
        checked = sum(1 for r in tracker["recommendations"] if r.get("hit") is not None)
        hit_count = sum(1 for r in tracker["recommendations"] if r.get("hit"))
        print(f"  总计{total}期 | 已结算{checked}期 | 命中{hit_count}期")
        for rec in tracker["recommendations"]:
            status = ""
            if rec.get("hit") is True:
                status = " HIT"
            elif rec.get("hit") is False:
                status = f" MISS(中{rec.get('hit_count', 0)}个)"
            else:
                status = " 待开奖"
            grp = f" [{rec['group']}组]" if rec.get("group") else ""
            print(f"  {rec['date']} [{rec['target_issue']}期] {rec['pair']} ({rec['strategy']}{grp}){status}")
    
    # 5. 生成新推荐
    results = generate_recommendation(latest_issue, latest_nums, all_data)
    
    if results[0][0][0] is None:
        print(f"\n[推荐] 本期数据不足以生成推荐")
        return
    
    target_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "unknown"
    
    # 防重复: 如果目标期号已有推荐，跳过
    existing_targets = {r["target_issue"] for r in tracker["recommendations"]}
    if target_issue in existing_targets:
        print(f"\n[跳过] {target_issue}期已有推荐，无需重复生成")
        return
    
    print(f"\n=== 今日推荐 [{target_issue}期] ===")
    if len(results) > 1:
        has_duplex = any(r[2] == '4号复式' for r in results)
        if has_duplex:
            print(f"  (信号≥3，出{len(results)}组，含4号复式)")
        else:
            print(f"  (信号≥3，出{len(results)}组)")
    
    # 6. 保存推荐
    for i, (pair, strategy, reason, group) in enumerate(results):
        label = f" [{group}]" if group else ""
        if pair[0] is None:
            print(f"  {strategy}{label}: {reason}")
        elif len(pair) == 4:
            print(f"  {strategy}{label}: {pair[0]:02d}+{pair[1]:02d}+{pair[2]:02d}+{pair[3]:02d}  |  {reason}")
        elif len(pair) >= 2:
            print(f"  {strategy}{label}: {pair[0]:02d} + {pair[1]:02d}  |  {reason}")
        else:
            print(f"  {strategy}{label}: {pair}  |  {reason}")
        
        rec = {
            "date": today,
            "from_issue": latest_issue,
            "target_issue": target_issue,
            "pair": pair,
            "strategy": strategy,
            "reason": reason,
            "group": group,
            "hit": None
        }
        tracker["recommendations"].append(rec)
    save_tracker(tracker)
    print(f"\n[保存] {len(results)}组推荐已写入 {TRACKER_FILE}")
    
    # 7. 输出当前状态摘要
    print(f"\n=== 当前统计 ===")
    total = len(tracker["recommendations"])
    settled = [r for r in tracker["recommendations"] if r.get("hit") is not None]
    hit_recs = [r for r in settled if r.get("hit")]
    unset = [r for r in tracker["recommendations"] if r.get("hit") is None]
    print(f"  累计推荐: {total}期")
    print(f"  已开奖: {len(settled)}期 | 命中: {len(hit_recs)}期 ({len(hit_recs)/len(settled)*100:.0f}%)" if settled else "  尚无开奖结果")
    print(f"  待开奖: {len(unset)}期")
    
    return pair

if __name__ == "__main__":
    main()
