#!/usr/bin/env python3
"""
openvela contest2026 仓库统计工具
- 查询 GitHub API 获取所有 contest2026_xxx 仓库的 PR、Issue、AI Log 数据
- 将每次查询结果追加到历史记录文件 (history.json)
- 生成 Markdown 报告文档 (REPORT.md)
- 生成数据变化趋势图 (charts/)
"""

import json
import urllib.request
import urllib.error
import time
import sys
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(SCRIPT_DIR, "history.json")
REPORT_FILE = os.path.join(SCRIPT_DIR, "REPORT.md")
CHARTS_DIR = os.path.join(SCRIPT_DIR, "charts")

ORG = "open-vela"
BASE_URL = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def fetch_json(url):
    """Fetch JSON from GitHub API with auth."""
    try:
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "openvela-contest-query")
        req.add_header("Authorization", f"token {TOKEN}")
        with urllib.request.urlopen(req, timeout=15) as resp:
            remaining = resp.headers.get("X-RateLimit-Remaining", "?")
            data = json.loads(resp.read().decode())
            return data, remaining
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, "?"
        elif e.code == 403:
            return "RATE_LIMITED", "0"
        else:
            return None, "?"
    except Exception as e:
        return None, "?"


def check_has_ai_log(repo):
    """Check if repo has real AI logs submitted."""
    url = f"{BASE_URL}/repos/{ORG}/{repo}/contents/logs"
    data, _ = fetch_json(url)
    if not data or data == "RATE_LIMITED":
        return False
    real_entries = [item["name"] for item in data
                   if item["name"] not in ("README.md", "your-github-login", ".gitkeep")]
    return len(real_entries) > 0


def query_all_repos():
    """Query all contest2026 repos and return structured data."""
    print("获取仓库列表...", file=sys.stderr)
    repos = []
    for page in range(1, 15):
        url = f"{BASE_URL}/orgs/{ORG}/repos?per_page=100&page={page}"
        data, _ = fetch_json(url)
        if not data or data == "RATE_LIMITED" or len(data) == 0:
            break
        for r in data:
            if "contest2026" in r["name"]:
                repos.append(r["name"])
        if len(data) < 100:
            break
        time.sleep(0.1)

    repos.sort()
    print(f"共 {len(repos)} 个 contest2026 仓库", file=sys.stderr)

    results = []
    for i, repo in enumerate(repos):
        pr_count = 0
        issue_count = 0
        page = 1
        while True:
            url = f"{BASE_URL}/repos/{ORG}/{repo}/issues?state=all&per_page=100&page={page}"
            data, remaining = fetch_json(url)
            if not data or data == "RATE_LIMITED" or len(data) == 0:
                break
            for item in data:
                if "pull_request" in item:
                    pr_count += 1
                else:
                    issue_count += 1
            if len(data) < 100:
                break
            page += 1

        has_ai_log = check_has_ai_log(repo)

        results.append({
            "repo": repo,
            "issues": issue_count,
            "prs": pr_count,
            "ai_log": has_ai_log,
        })

        ai_mark = "📝" if has_ai_log else "  "
        print(f"[{i+1}/{len(repos)}] {repo}: issues={issue_count}, prs={pr_count} {ai_mark}", file=sys.stderr)
        time.sleep(0.05)

    return results


def load_history():
    """Load history from file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history):
    """Save history to file."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def append_to_history(results):
    """Append current query results to history."""
    history = load_history()

    today = datetime.now().strftime("%Y-%m-%d")
    total_repos = len(results)
    total_issues = sum(r["issues"] for r in results)
    total_prs = sum(r["prs"] for r in results)
    active_repos = sum(1 for r in results if r["issues"] > 0 or r["prs"] > 0)
    ai_log_repos = sum(1 for r in results if r["ai_log"])

    entry = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_repos": total_repos,
            "active_repos": active_repos,
            "total_issues": total_issues,
            "total_prs": total_prs,
            "ai_log_repos": ai_log_repos,
        },
        "repos": results,
    }

    # Replace today's entry if already exists, otherwise append
    existing_idx = next((i for i, h in enumerate(history) if h["date"] == today), None)
    if existing_idx is not None:
        history[existing_idx] = entry
    else:
        history.append(entry)

    save_history(history)
    return history


def generate_report(history):
    """Generate Markdown report with current data and historical trends."""
    if not history:
        return

    latest = history[-1]
    summary = latest["summary"]
    repos = latest["repos"]
    date = latest["date"]

    lines = []
    lines.append("# openvela 大赛仓库统计报告")
    lines.append("")
    lines.append(f"> 最后更新时间: {latest['timestamp']}")
    lines.append("")

    # Summary section
    lines.append("## 📊 总体统计")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| 总仓库数 | **{summary['total_repos']}** |")
    lines.append(f"| 有活跃 Issue/PR 的仓库 | **{summary['active_repos']}** |")
    lines.append(f"| 总 Issue 数（纯 issue，不含 PR） | **{summary['total_issues']}** |")
    lines.append(f"| 总 PR 数 | **{summary['total_prs']}** |")
    lines.append(f"| 提交了 AI Log 的仓库 | **{summary['ai_log_repos']}** |")
    lines.append("")

    # Active repos table
    active = [r for r in repos if r["issues"] > 0 or r["prs"] > 0]
    active.sort(key=lambda x: x["prs"], reverse=True)

    lines.append("## 🏆 有活跃 PR/Issue 的仓库明细")
    lines.append("")
    lines.append("| # | 仓库 | Issue | PR | AI Log |")
    lines.append("|---|------|-------|----|--------|")
    for i, r in enumerate(active, 1):
        ai = "✅" if r["ai_log"] else "❌"
        repo_link = f"[{r['repo']}](https://github.com/{ORG}/{r['repo']})"
        lines.append(f"| {i} | {repo_link} | {r['issues']} | {r['prs']} | {ai} |")
    lines.append("")

    # AI Log repos
    ai_repos = [r for r in repos if r["ai_log"]]
    lines.append("## 📝 提交了 AI Log 的仓库")
    lines.append("")
    if ai_repos:
        for i, r in enumerate(ai_repos, 1):
            repo_link = f"[{r['repo']}](https://github.com/{ORG}/{r['repo']})"
            lines.append(f"{i}. {repo_link} (PR: {r['prs']}, Issue: {r['issues']})")
    else:
        lines.append("暂无仓库提交 AI Log。")
    lines.append("")

    # Historical trends
    if len(history) > 1:
        lines.append("## 📈 历史趋势")
        lines.append("")
        lines.append("| 日期 | 总仓库 | 活跃仓库 | Issue | PR | AI Log仓库 |")
        lines.append("|------|--------|----------|-------|-----|-----------|")
        for h in history:
            s = h["summary"]
            lines.append(f"| {h['date']} | {s['total_repos']} | {s['active_repos']} | {s['total_issues']} | {s['total_prs']} | {s['ai_log_repos']} |")
        lines.append("")

        # Daily changes
        if len(history) >= 2:
            prev = history[-2]["summary"]
            curr = history[-1]["summary"]
            lines.append("### 较上次变化")
            lines.append("")
            changes = []
            for key, label in [
                ("total_repos", "总仓库"),
                ("active_repos", "活跃仓库"),
                ("total_issues", "Issue"),
                ("total_prs", "PR"),
                ("ai_log_repos", "AI Log仓库"),
            ]:
                diff = curr[key] - prev[key]
                if diff != 0:
                    sign = "+" if diff > 0 else ""
                    changes.append(f"- {label}: {sign}{diff}")
            if changes:
                lines.extend(changes)
            else:
                lines.append("- 无变化")
            lines.append("")

        # ASCII chart for PR trend
        lines.append("### PR 数量趋势")
        lines.append("")
        lines.append("```")
        max_prs = max(h["summary"]["total_prs"] for h in history)
        chart_width = 40
        for h in history:
            prs = h["summary"]["total_prs"]
            bar_len = int(prs / max(max_prs, 1) * chart_width) if max_prs > 0 else 0
            bar = "█" * bar_len
            lines.append(f"{h['date']} | {bar} {prs}")
        lines.append("```")
        lines.append("")

        # ASCII chart for AI Log repos trend
        lines.append("### AI Log 提交仓库趋势")
        lines.append("")
        lines.append("```")
        max_ai = max(h["summary"]["ai_log_repos"] for h in history)
        for h in history:
            ai = h["summary"]["ai_log_repos"]
            bar_len = int(ai / max(max_ai, 1) * chart_width) if max_ai > 0 else 0
            bar = "█" * bar_len
            lines.append(f"{h['date']} | {bar} {ai}")
        lines.append("```")
        lines.append("")

    # Per-repo PR ranking chart
    lines.append("## 🏅 仓库 PR 排行榜")
    lines.append("")
    lines.append("```")
    top_repos = sorted(repos, key=lambda x: x["prs"], reverse=True)[:15]
    top_repos = [r for r in top_repos if r["prs"] > 0]
    if top_repos:
        max_pr = top_repos[0]["prs"]
        for r in top_repos:
            # Shorten repo name for display
            name = r["repo"].replace("contest2026_", "")
            bar_len = int(r["prs"] / max(max_pr, 1) * 30)
            bar = "█" * bar_len
            ai = " 📝" if r["ai_log"] else ""
            lines.append(f"{name:40s} | {bar} {r['prs']}{ai}")
    lines.append("```")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*本报告由 `contest_stats/query_and_record.py` 自动生成*")
    lines.append(f"*数据来源: GitHub API (https://github.com/{ORG})*")
    lines.append("")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"报告已生成: {REPORT_FILE}", file=sys.stderr)


def generate_charts(history):
    """Generate SVG charts for data trends."""
    os.makedirs(CHARTS_DIR, exist_ok=True)

    if len(history) < 2:
        print("历史数据不足2天，跳过图表生成", file=sys.stderr)
        return

    # Generate a simple SVG line chart
    dates = [h["date"] for h in history]
    prs = [h["summary"]["total_prs"] for h in history]
    issues = [h["summary"]["total_issues"] for h in history]
    ai_logs = [h["summary"]["ai_log_repos"] for h in history]
    active = [h["summary"]["active_repos"] for h in history]

    def make_svg_chart(title, datasets, filename):
        """Generate a simple SVG line chart."""
        width = 800
        height = 400
        margin = {"top": 50, "right": 150, "bottom": 80, "left": 60}
        chart_w = width - margin["left"] - margin["right"]
        chart_h = height - margin["top"] - margin["bottom"]

        all_values = []
        for ds in datasets:
            all_values.extend(ds["values"])
        max_val = max(all_values) if all_values else 1
        min_val = 0

        n = len(dates)
        if n < 2:
            return

        colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c"]

        svg_lines = []
        svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">')
        svg_lines.append(f'<rect width="{width}" height="{height}" fill="white"/>')

        # Title
        svg_lines.append(f'<text x="{width//2}" y="30" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>')

        # Y axis grid
        for i in range(5):
            y = margin["top"] + chart_h - (i / 4 * chart_h)
            val = int(min_val + (max_val - min_val) * i / 4)
            svg_lines.append(f'<line x1="{margin["left"]}" y1="{y}" x2="{margin["left"]+chart_w}" y2="{y}" stroke="#e5e7eb" stroke-width="1"/>')
            svg_lines.append(f'<text x="{margin["left"]-10}" y="{y+4}" text-anchor="end" font-size="11" fill="#6b7280">{val}</text>')

        # X axis labels
        for i, date in enumerate(dates):
            x = margin["left"] + (i / max(n - 1, 1) * chart_w)
            y = margin["top"] + chart_h + 20
            svg_lines.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="10" fill="#6b7280" transform="rotate(-45 {x} {y})">{date}</text>')

        # Data lines
        for di, ds in enumerate(datasets):
            color = colors[di % len(colors)]
            points = []
            for i, v in enumerate(ds["values"]):
                x = margin["left"] + (i / max(n - 1, 1) * chart_w)
                y = margin["top"] + chart_h - ((v - min_val) / max(max_val - min_val, 1) * chart_h)
                points.append(f"{x},{y}")

            # Line
            svg_lines.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')

            # Points
            for i, v in enumerate(ds["values"]):
                x = margin["left"] + (i / max(n - 1, 1) * chart_w)
                y = margin["top"] + chart_h - ((v - min_val) / max(max_val - min_val, 1) * chart_h)
                svg_lines.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')
                svg_lines.append(f'<text x="{x}" y="{y-8}" text-anchor="middle" font-size="9" fill="{color}">{v}</text>')

            # Legend
            ly = margin["top"] + 20 + di * 20
            lx = margin["left"] + chart_w + 20
            svg_lines.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+20}" y2="{ly}" stroke="{color}" stroke-width="2"/>')
            svg_lines.append(f'<text x="{lx+25}" y="{ly+4}" font-size="11" fill="{color}">{ds["label"]}</text>')

        svg_lines.append('</svg>')

        filepath = os.path.join(CHARTS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(svg_lines))
        print(f"图表已生成: {filepath}", file=sys.stderr)

    # Chart 1: PR and Issue trends
    make_svg_chart(
        "PR & Issue 数量趋势",
        [
            {"label": "PR", "values": prs},
            {"label": "Issue", "values": issues},
        ],
        "pr_issue_trend.svg"
    )

    # Chart 2: Active repos and AI log trends
    make_svg_chart(
        "活跃仓库 & AI Log 趋势",
        [
            {"label": "活跃仓库", "values": active},
            {"label": "AI Log仓库", "values": ai_logs},
        ],
        "active_ailog_trend.svg"
    )


def main():
    # Check rate limit
    data, _ = fetch_json(f"{BASE_URL}/rate_limit")
    if data and data != "RATE_LIMITED":
        core = data["resources"]["core"]
        print(f"API Rate Limit: {core['remaining']}/{core['limit']}", file=sys.stderr)
        if core["remaining"] < 100:
            print("⚠️ API 配额不足，请稍后再试", file=sys.stderr)
            sys.exit(1)
    else:
        print("无法获取 rate limit", file=sys.stderr)
        sys.exit(1)

    # Query repos
    results = query_all_repos()

    # Record history
    history = append_to_history(results)
    print(f"\n历史记录已更新，共 {len(history)} 条记录", file=sys.stderr)

    # Generate report
    generate_report(history)

    # Generate charts
    generate_charts(history)

    # Print summary
    s = history[-1]["summary"]
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"统计完成 - {history[-1]['date']}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"总仓库: {s['total_repos']} | 活跃: {s['active_repos']} | Issue: {s['total_issues']} | PR: {s['total_prs']} | AI Log: {s['ai_log_repos']}", file=sys.stderr)


if __name__ == "__main__":
    main()
