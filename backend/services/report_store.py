"""SearchSubAgent报告存储服务

功能：
- 保存SearchSubAgent生成的完整Markdown报告
- 按年月日分文件夹存储
- 支持report_id检索和列表查询
- 自动生成结构化报告格式

设计理念：
- 完整报告持久化到磁盘（data/reports/search/YYYY-MM-DD/）
- 主Agent只接收紧凑版报告 + report_id
- 主Agent可通过read_report工具读取完整报告
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# 报告存储根目录
REPORTS_DIR = os.path.join(os.getcwd(), "data", "reports")
SEARCH_REPORTS_DIR = os.path.join(REPORTS_DIR, "search")


def _ensure_reports_dir() -> None:
    """确保报告目录存在"""
    os.makedirs(SEARCH_REPORTS_DIR, exist_ok=True)


def _get_date_folder() -> str:
    """获取当前日期文件夹路径（YYYY-MM-DD格式）"""
    today = datetime.now().strftime("%Y-%m-%d")
    date_folder = os.path.join(SEARCH_REPORTS_DIR, today)
    os.makedirs(date_folder, exist_ok=True)
    return date_folder


def _generate_report_id(task_description: str) -> str:
    """生成报告ID（基于任务描述的哈希）

    格式：timestamp_hash8位
    例如：20251025_143022_abc12345
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_hash = hashlib.md5(task_description.encode()).hexdigest()[:8]
    return f"{timestamp}_{task_hash}"


def _generate_report_markdown(
    report_id: str,
    task_description: str,
    summary: str,
    todos: List[Dict[str, Any]],
    search_results: List[Dict[str, Any]],
    key_findings: List[str],
    artifacts: List[str],
    iterations: int,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """生成结构化Markdown报告

    Args:
        report_id: 报告ID
        task_description: 任务描述
        summary: 执行摘要
        todos: TODO执行记录
        search_results: 详细搜索结果
        key_findings: 关键发现
        artifacts: 相关附件ID列表
        iterations: 迭代次数
        metadata: 其他元数据

    Returns:
        完整的Markdown报告内容
    """
    # 提取任务摘要（用于标题）
    task_summary = task_description[:50] + "..." if len(task_description) > 50 else task_description

    # 生成报告时间
    report_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

    # 生成TODO执行记录
    todo_lines = []
    for todo in todos:
        status = todo.get("status", "pending")
        title = todo.get("title", "")
        status_icon = {"completed": "x", "in_progress": "~", "pending": " "}
        todo_lines.append(f"- [{status_icon.get(status, ' ')}] {title}")
    todo_section = "\n".join(todo_lines) if todo_lines else "（无TODO记录）"

    # 生成详细搜索结果
    search_section_lines = []
    for idx, result in enumerate(search_results, 1):
        tool_name = result.get("tool", "unknown")
        query = result.get("query", "")
        data = result.get("data", {})

        search_section_lines.append(f"### 搜索{idx}: {tool_name}")
        if query:
            search_section_lines.append(f"**查询**: {query}")

        # 处理搜索结果数据
        if isinstance(data, dict):
            if "results" in data:
                results_list = data["results"]
                if isinstance(results_list, list):
                    for r_idx, r in enumerate(results_list[:5], 1):  # 最多显示5条
                        if isinstance(r, dict):
                            title = r.get("title", "无标题")
                            url = r.get("url", "")
                            content = r.get("content", "")[:200]  # 截断到200字符
                            search_section_lines.append(f"\n**{r_idx}. {title}**")
                            if url:
                                search_section_lines.append(f"- URL: {url}")
                            if content:
                                search_section_lines.append(f"- 摘要: {content}...")

        search_section_lines.append("")  # 空行分隔

    search_section = "\n".join(search_section_lines) if search_section_lines else "（无详细搜索结果）"

    # 生成关键发现
    findings_section = "\n".join([f"{i}. {finding}" for i, finding in enumerate(key_findings, 1)]) \
                       if key_findings else "（无关键发现）"

    # 生成附件列表
    artifacts_section = "\n".join([f"- {artifact}" for artifact in artifacts]) \
                        if artifacts else "（无附件）"

    # 组装完整报告
    report = f"""# 深度搜索报告 - {task_summary}

**Report ID**: {report_id}
**执行时间**: {report_time}
**任务描述**: {task_description}
**迭代次数**: {iterations}轮
**SubAgent**: SearchSubAgent

---

## 执行摘要

{summary}

---

## TODO执行记录

{todo_section}

---

## 详细搜索结果

{search_section}

---

## 关键发现

{findings_section}

---

## 相关附件

{artifacts_section}

---

## 元数据

```json
{json.dumps(metadata or {}, ensure_ascii=False, indent=2)}
```

---

**报告生成时间**: {report_time}
**报告ID**: {report_id}
"""

    return report


def save_report(
    task_description: str,
    summary: str,
    todos: List[Dict[str, Any]] = None,
    search_results: List[Dict[str, Any]] = None,
    key_findings: List[str] = None,
    artifacts: List[str] = None,
    iterations: int = 0,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """保存SearchSubAgent报告

    Args:
        task_description: 任务描述
        summary: 执行摘要
        todos: TODO执行记录
        search_results: 详细搜索结果（包含工具调用和返回数据）
        key_findings: 关键发现列表
        artifacts: 附件ID列表
        iterations: 迭代次数
        metadata: 其他元数据

    Returns:
        report_id（报告ID）
    """
    _ensure_reports_dir()

    # 生成report_id
    report_id = _generate_report_id(task_description)

    # 生成Markdown报告内容
    report_content = _generate_report_markdown(
        report_id=report_id,
        task_description=task_description,
        summary=summary,
        todos=todos or [],
        search_results=search_results or [],
        key_findings=key_findings or [],
        artifacts=artifacts or [],
        iterations=iterations,
        metadata=metadata
    )

    # 保存报告文件
    date_folder = _get_date_folder()
    report_filename = f"{report_id}.md"
    report_path = os.path.join(date_folder, report_filename)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_id


def read_report(report_id: str) -> Optional[str]:
    """读取报告内容

    Args:
        report_id: 报告ID

    Returns:
        完整的Markdown报告内容，如果不存在则返回None
    """
    _ensure_reports_dir()

    # 遍历所有日期文件夹查找报告
    for date_folder in Path(SEARCH_REPORTS_DIR).iterdir():
        if date_folder.is_dir():
            report_path = date_folder / f"{report_id}.md"
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    return f.read()

    return None


def list_reports(limit: int = 10) -> List[Dict[str, Any]]:
    """列出最近的报告

    Args:
        limit: 最多返回的报告数量

    Returns:
        报告列表，每个报告包含：
        {
            "report_id": "...",
            "filename": "...",
            "date": "...",
            "created_at": timestamp,
            "path": "..."
        }
    """
    _ensure_reports_dir()

    reports = []

    # 遍历所有日期文件夹
    for date_folder in sorted(Path(SEARCH_REPORTS_DIR).iterdir(), reverse=True):
        if not date_folder.is_dir():
            continue

        # 遍历该日期下的所有报告
        for report_file in sorted(date_folder.glob("*.md"), reverse=True):
            report_id = report_file.stem
            created_at = report_file.stat().st_mtime

            reports.append({
                "report_id": report_id,
                "filename": report_file.name,
                "date": date_folder.name,
                "created_at": created_at,
                "path": str(report_file)
            })

            if len(reports) >= limit:
                return reports

    return reports


def delete_report(report_id: str) -> bool:
    """删除报告

    Args:
        report_id: 报告ID

    Returns:
        是否删除成功
    """
    _ensure_reports_dir()

    # 遍历所有日期文件夹查找并删除
    for date_folder in Path(SEARCH_REPORTS_DIR).iterdir():
        if date_folder.is_dir():
            report_path = date_folder / f"{report_id}.md"
            if report_path.exists():
                report_path.unlink()
                return True

    return False
