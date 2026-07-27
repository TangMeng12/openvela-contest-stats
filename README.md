# openvela AI 大赛仓库统计

自动统计 [open-vela](https://github.com/open-vela) 组织下大赛相关仓库的活跃度数据。

## �� 统计内容

### 1. contest2026 参赛仓库统计
- 所有 `contest2026_xxx` 仓库的 PR、Issue、AI Log 提交情况
- 详见 [REPORT.md](./REPORT.md)

### 2. 公共仓库 dev-ai-contest-2026 分支 PR 统计
- 公共仓库（nuttx, vendor_xxx 等）中 `dev-ai-contest-2026` 分支的 PR 合入情况
- 包括待合入 PR 链接，方便跟踪 review 进度
- 详见 [PUBLIC_BRANCH_REPORT.md](./PUBLIC_BRANCH_REPORT.md)

## 📈 数据文件

| 文件 | 说明 |
|------|------|
| `REPORT.md` | contest2026 仓库统计报告 |
| `PUBLIC_BRANCH_REPORT.md` | 公共仓库分支 PR 报告 |
| `history.json` | contest2026 历史数据 |
| `public_branch_history.json` | 公共仓库 PR 历史数据 |
| `charts/` | 趋势图 (SVG) |
| `query_and_record.py` | 统计脚本 |

## 🔄 如何更新

```bash
# 需要设置 GitHub Token
export GITHUB_TOKEN="your_token"

# 运行统计（会自动查询 + 生成报告 + 推送到本仓库）
python3 query_and_record.py
```

## 📅 更新频率

每日通过 Kiro Hook 自动触发更新。

---

*数据来源: [GitHub API](https://api.github.com) / 组织: [open-vela](https://github.com/open-vela)*
