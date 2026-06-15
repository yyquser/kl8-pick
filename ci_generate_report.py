#!/usr/bin/env python3
"""
GitHub Actions 包装脚本
1. 运行 daily_pick.py 生成推荐
2. 生成 TODAY_PICK.md 供手机查看
3. 返回退出码 (0=有新推荐, 1=跳过/无变化)
"""
import subprocess, sys, json, os
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKER_FILE = os.path.join(SCRIPT_DIR, "daily_tracker.json")

def main():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    today_str = now.strftime("%Y-%m-%d %H:%M")
    
    # 运行 daily_pick.py
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "daily_pick.py")],
        capture_output=True, text=True, cwd=SCRIPT_DIR, timeout=120
    )
    
    output = result.stdout
    print(output)
    if result.stderr:
        print("[STDERR]", result.stderr, file=sys.stderr)
    
    # 读取 tracker 获取最新推荐
    if not os.path.exists(TRACKER_FILE):
        print("[SKIP] tracker 不存在", file=sys.stderr)
        sys.exit(1)
    
    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        tracker = json.load(f)
    
    recs = tracker.get("recommendations", [])
    if not recs:
        print("[SKIP] 无推荐记录", file=sys.stderr)
        sys.exit(1)
    
    # 找最新的待开奖推荐 (hit=None, 按target_issue数值排序)
    def issue_int(r):
        ti = r.get("target_issue", "0")
        try:
            return int(ti)
        except ValueError:
            return 0
    
    pending = [r for r in recs if r.get("hit") is None]
    if pending:
        pending.sort(key=issue_int, reverse=True)
        latest_issue = pending[0]["target_issue"]
        today_recs = [r for r in pending if r["target_issue"] == latest_issue]
    else:
        # 没有待开奖的, 显示最近已开奖的
        recs.sort(key=issue_int, reverse=True)
        latest_issue = recs[0]["target_issue"]
        today_recs = [r for r in recs if r["target_issue"] == latest_issue]
    
    if not today_recs:
        print("[SKIP] 今日无新推荐", file=sys.stderr)
        sys.exit(1)
    
    # 生成 TODAY_PICK.md
    lines = []
    lines.append(f"# KL8 每日选二推荐")
    lines.append(f"")
    lines.append(f"**生成时间**: {today_str} (北京时间)")
    lines.append(f"**目标期号**: {latest_issue}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    
    for i, rec in enumerate(today_recs):
        pair = rec["pair"]
        strategy = rec["strategy"]
        reason = rec.get("reason", "")
        group = rec.get("group", "")
        
        if pair[0] is None:
            lines.append(f"## 策略: {strategy}")
            lines.append(f"")
            lines.append(f"> {reason}")
        elif len(pair) == 4:
            lines.append(f"## 4号复式 (6注12元)")
            lines.append(f"")
            lines.append(f"| 号码 |  |  |  |")
            lines.append(f"|------|--|--|--|")
            lines.append(f"| **{pair[0]:02d}** | **{pair[1]:02d}** | **{pair[2]:02d}** | **{pair[3]:02d}** |")
            lines.append(f"")
            lines.append(f"> {reason}")
            lines.append(f"")
            lines.append(f"- 投入: 6注 × 2元 = **12元**")
            lines.append(f"- 中2个: 1注 × 28元 = **净赚16元**")
            lines.append(f"- 中3个: 3注 × 28元 = **赚72元**")
        elif len(pair) == 2:
            lines.append(f"## 单注选二 [{group}组]" if group else "## 单注选二")
            lines.append(f"")
            lines.append(f"### {pair[0]:02d} + {pair[1]:02d}")
            lines.append(f"")
            lines.append(f"> {reason}")
            lines.append(f"")
            lines.append(f"- 投入: **2元**")
            lines.append(f"- 中奖: **28元** (净赚26元)")
        
        lines.append(f"")
    
    # 历史战绩汇总
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 历史战绩")
    lines.append(f"")
    
    total = len(recs)
    settled = [r for r in recs if r.get("hit") is not None]
    hit_recs = [r for r in settled if r.get("hit")]
    unset = [r for r in recs if r.get("hit") is None]
    
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 累计推荐 | {total} 期 |")
    lines.append(f"| 已开奖 | {len(settled)} 期 |")
    if settled:
        lines.append(f"| 命中 | {len(hit_recs)} 期 ({len(hit_recs)/len(settled)*100:.0f}%) |")
    lines.append(f"| 待开奖 | {len(unset)} 期 |")
    lines.append(f"")
    
    lines.append(f"| 日期 | 期号 | 推荐 | 结果 |")
    lines.append(f"|------|------|------|------|")
    for rec in sorted(recs, key=lambda r: r["target_issue"], reverse=True)[:20]:
        status = "⏳"
        if rec.get("hit") is True:
            status = "✅ 命中"
        elif rec.get("hit") is False:
            status = f"❌ MISS(中{rec.get('hit_count', 0)}个)"
        
        pair_str = "+".join(f"{n:02d}" for n in rec["pair"])
        lines.append(f"| {rec['date']} | {rec['target_issue']} | {pair_str} | {status} |")
    
    report_path = os.path.join(SCRIPT_DIR, "TODAY_PICK.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"\n[报告] 已生成 {report_path}")
    sys.exit(0)

if __name__ == "__main__":
    main()
