"""文件操作工具集

包含：
1. SaveCachedFileTool - 将缓存的base64文件保存到本地
2. ListCachedFilesTool - 列出所有缓存的文件
3. StorageStatsTool - 查看存储统计信息
4. CleanupStorageTool - 清理旧文件
"""
from __future__ import annotations

import os
import shutil
from typing import Any, Dict

from .base import BaseTool
from services.file_store import get_cached_data, get_storage_stats, cleanup_old_files


class SaveCachedFileTool(BaseTool):
    """保存缓存文件到本地

    功能：
    - 将通过file_id引用的缓存文件保存到指定路径
    - 支持自动创建目录
    - 支持覆盖现有文件
    """
    name = "save_cached_file"
    description = "将缓存的文件（通过file_id引用）保存到本地路径。用于保存截图、PDF等工具生成的文件。"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        file_id = kwargs.get("file_id")
        target_path = kwargs.get("target_path")

        if not file_id:
            return {"error": True, "message": "缺少参数 file_id"}

        if not target_path:
            return {"error": True, "message": "缺少参数 target_path"}

        # 获取缓存的文件数据
        cached_data = get_cached_data(file_id)

        if not cached_data:
            return {
                "error": True,
                "message": f"未找到file_id: {file_id}。可能文件已过期或ID无效。"
            }

        source_path = cached_data["file_path"]

        # 确保目标目录存在
        target_dir = os.path.dirname(target_path)
        if target_dir and not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                return {
                    "error": True,
                    "message": f"创建目标目录失败: {e}"
                }

        # 复制文件
        try:
            shutil.copy2(source_path, target_path)

            return {
                "error": False,
                "data": {
                    "file_id": file_id,
                    "source_path": source_path,
                    "target_path": target_path,
                    "file_size": cached_data["file_size"],
                    "file_type": cached_data["file_type"],
                    "message": f"✅ 文件已成功保存到: {target_path}"
                }
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"保存文件失败: {e}"
            }


class ListCachedFilesTool(BaseTool):
    """列出所有缓存的文件

    功能：
    - 显示所有临时缓存的文件
    - 包含file_id、类型、大小等信息
    """
    name = "list_cached_files"
    description = "列出所有缓存的临时文件，显示file_id、类型、大小等信息。"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        from services.file_store import _load_index

        try:
            index = _load_index()

            files_info = []
            for fid, path in index.items():
                if os.path.exists(path):
                    # 获取文件信息
                    cached_data = get_cached_data(fid)
                    if cached_data:
                        files_info.append({
                            "file_id": fid,
                            "file_type": cached_data["file_type"],
                            "file_size": cached_data["file_size"],
                            "file_path": path
                        })

            return {
                "error": False,
                "data": {
                    "count": len(files_info),
                    "files": files_info
                }
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"列出缓存文件失败: {e}"
            }


class StorageStatsTool(BaseTool):
    """查看存储统计信息

    功能：
    - 显示总文件数和总大小
    - 按类型统计文件数量
    - 显示最旧和最新文件信息
    """
    name = "storage_stats"
    description = "查看文件存储统计信息，包括总大小、文件类型分布、最旧/最新文件等。用于监控存储使用情况。"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            stats = get_storage_stats()

            if "error" in stats:
                return {
                    "error": True,
                    "message": f"获取存储统计失败: {stats['error']}"
                }

            return {
                "error": False,
                "data": stats,
                "message": f"📊 当前缓存了 {stats['total_files']} 个文件，总大小 {stats['total_size_mb']} MB"
            }

        except Exception as e:
            return {
                "error": True,
                "message": f"获取存储统计失败: {e}"
            }


class CleanupStorageTool(BaseTool):
    """清理旧文件

    功能：
    - 删除超过指定时间的文件
    - 当总大小超限时删除最旧的文件
    - 自动重建索引
    """
    name = "cleanup_storage"
    description = """清理旧的缓存文件以释放空间。支持按时间和大小清理。

    使用场景：
    1. 定期维护：清理超过30天的旧文件
    2. 空间不足：清理文件使总大小不超过500MB
    3. 手动清理：用户要求清理缓存

    默认策略：删除30天前的文件，或当总大小超过500MB时删除最旧的文件。"""

    async def execute(self, max_age_hours: int = 720, max_total_size_mb: int = 500, **kwargs) -> Dict[str, Any]:
        try:
            result = cleanup_old_files(max_age_hours, max_total_size_mb)

            if "error" in result:
                return {
                    "error": True,
                    "message": f"清理文件失败: {result['error']}"
                }

            return {
                "error": False,
                "data": result,
                "message": f"🧹 清理完成：删除了 {result['deleted_count']} 个文件，释放 {result['freed_space_mb']} MB空间，剩余 {result['remaining_files']} 个文件（{result['remaining_size_mb']} MB）"
            }

        except Exception as e:
            import traceback
            return {
                "error": True,
                "message": f"清理文件失败: {e}\n{traceback.format_exc()}"
            }

