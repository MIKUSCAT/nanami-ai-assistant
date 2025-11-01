"""简单上传文件存储与读取。

不做复杂安全校验，文件保存到 data/uploads/ 目录，并使用随机ID索引。
支持图片文件的base64编码，用于LLM视觉理解。
"""
from __future__ import annotations

import os
import uuid
import base64
import mimetypes
from typing import Optional, Dict, Any


BASE_DIR = os.path.join(os.getcwd(), "data", "uploads")
INDEX_FILE = os.path.join(os.getcwd(), "data", "uploads.index")

# 支持的图片格式
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}


def _ensure_dirs() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)
    # 索引文件按行存储：id<TAB>path
    if not os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "w", encoding="utf-8"):
            pass


def _append_index(fid: str, path: str) -> None:
    with open(INDEX_FILE, "a", encoding="utf-8") as f:
        f.write(f"{fid}\t{path}\n")


def _load_index() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not os.path.exists(INDEX_FILE):
        return mapping
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fid, path = line.split("\t", 1)
            mapping[fid] = path
    return mapping


def save_upload(filename: str, content: bytes) -> str:
    _ensure_dirs()
    fid = str(uuid.uuid4())
    ext = os.path.splitext(filename)[1]
    path = os.path.join(BASE_DIR, fid + ext)
    with open(path, "wb") as f:
        f.write(content)
    _append_index(fid, path)
    return fid


def get_file_path_by_id(fid: str) -> Optional[str]:
    mapping = _load_index()
    return mapping.get(fid)


def is_image_file(path: str) -> bool:
    """检查文件是否是图片"""
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in IMAGE_EXTENSIONS


def get_file_content_by_id(fid: str) -> Optional[str]:
    """读取文件内容（文本文件）"""
    path = get_file_path_by_id(fid)
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def get_image_as_base64(fid: str) -> Optional[Dict[str, Any]]:
    """将图片文件转换为base64编码，用于LLM视觉理解

    Returns:
        {
            "base64": "...",
            "mime_type": "image/png",
            "url": "data:image/png;base64,..."
        }
    """
    path = get_file_path_by_id(fid)
    if not path or not os.path.exists(path):
        return None

    if not is_image_file(path):
        return None

    try:
        with open(path, "rb") as f:
            image_bytes = f.read()

        # 编码为base64
        base64_str = base64.b64encode(image_bytes).decode('utf-8')

        # 检测MIME类型
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type or not mime_type.startswith('image/'):
            # 默认使用文件扩展名推断
            ext = os.path.splitext(path)[1].lower()
            mime_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml'
            }
            mime_type = mime_map.get(ext, 'image/png')

        # 构造data URL
        data_url = f"data:{mime_type};base64,{base64_str}"

        return {
            "base64": base64_str,
            "mime_type": mime_type,
            "url": data_url
        }
    except Exception as e:
        print(f"⚠️ 读取图片失败: {e}")
        return None


def cache_base64_data(data: str, file_type: str = "unknown", metadata: Optional[Dict[str, Any]] = None) -> str:
    """缓存大型base64数据到临时文件

    用途：当工具返回大型base64数据（如PDF、截图）时，
    将数据缓存到文件系统，返回file_id供后续使用。

    Args:
        data: base64编码的数据
        file_type: 文件类型标识（pdf、screenshot、text等）
        metadata: 额外元数据（格式、大小等）

    Returns:
        file_id: 缓存文件的唯一标识符
    """
    _ensure_dirs()

    # 生成唯一ID
    fid = str(uuid.uuid4())

    # 根据文件类型确定扩展名
    ext_map = {
        "pdf": ".pdf",
        "screenshot": ".png",
        "image": ".png",
        "text": ".txt",
        "json": ".json"
    }
    ext = ext_map.get(file_type, ".bin")

    # 解码base64并保存
    try:
        # 尝试解码base64
        file_bytes = base64.b64decode(data)

        # 保存文件
        path = os.path.join(BASE_DIR, fid + ext)
        with open(path, "wb") as f:
            f.write(file_bytes)

        # 更新索引
        _append_index(fid, path)

        # 保存元数据（如果提供）
        if metadata:
            meta_path = os.path.join(BASE_DIR, fid + ".meta.json")
            import json
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

        return fid

    except Exception as e:
        print(f"⚠️ 缓存base64数据失败: {e}")
        # 如果解码失败，直接保存原始数据
        path = os.path.join(BASE_DIR, fid + ".raw")
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        _append_index(fid, path)
        return fid


def get_cached_data(fid: str) -> Optional[Dict[str, Any]]:
    """获取缓存的文件数据

    Returns:
        {
            "file_id": "...",
            "file_path": "...",
            "file_size": 123456,
            "file_type": "pdf",
            "base64": "..." (可选，如果文件不太大),
            "metadata": {...} (如果存在)
        }
    """
    path = get_file_path_by_id(fid)
    if not path or not os.path.exists(path):
        return None

    try:
        file_size = os.path.getsize(path)
        ext = os.path.splitext(path)[1].lower()

        # 猜测文件类型
        type_map = {
            ".pdf": "pdf",
            ".png": "screenshot",
            ".jpg": "image",
            ".jpeg": "image",
            ".txt": "text",
            ".json": "json"
        }
        file_type = type_map.get(ext, "unknown")

        result = {
            "file_id": fid,
            "file_path": path,
            "file_size": file_size,
            "file_type": file_type
        }

        # 如果文件不太大（<1MB），提供base64编码
        if file_size < 1024 * 1024:
            with open(path, "rb") as f:
                file_bytes = f.read()
            result["base64"] = base64.b64encode(file_bytes).decode('utf-8')

        # 读取元数据（如果存在）
        meta_path = os.path.join(os.path.dirname(path), fid + ".meta.json")
        if os.path.exists(meta_path):
            import json
            with open(meta_path, "r", encoding="utf-8") as f:
                result["metadata"] = json.load(f)

        return result

    except Exception as e:
        print(f"⚠️ 读取缓存数据失败: {e}")
        return None


def get_storage_stats() -> Dict[str, Any]:
    """获取存储统计信息

    Returns:
        {
            "total_files": 总文件数,
            "total_size": 总大小(bytes),
            "total_size_mb": 总大小(MB),
            "by_type": {类型: 数量},
            "oldest_file": 最旧文件信息,
            "newest_file": 最新文件信息
        }
    """
    _ensure_dirs()

    try:
        import time

        files = []
        total_size = 0
        type_counts = {}

        # 遍历所有文件
        for filename in os.listdir(BASE_DIR):
            file_path = os.path.join(BASE_DIR, filename)
            if not os.path.isfile(file_path):
                continue

            # 跳过元数据文件
            if filename.endswith('.meta.json'):
                continue

            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            file_mtime = file_stat.st_mtime

            ext = os.path.splitext(filename)[1].lower()

            files.append({
                "path": file_path,
                "name": filename,
                "size": file_size,
                "mtime": file_mtime,
                "ext": ext
            })

            total_size += file_size
            type_counts[ext] = type_counts.get(ext, 0) + 1

        # 排序
        files.sort(key=lambda x: x['mtime'])

        result = {
            "total_files": len(files),
            "total_size": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "by_type": type_counts
        }

        if files:
            result["oldest_file"] = {
                "name": files[0]["name"],
                "age_hours": round((time.time() - files[0]["mtime"]) / 3600, 1),
                "size_kb": round(files[0]["size"] / 1024, 1)
            }
            result["newest_file"] = {
                "name": files[-1]["name"],
                "age_hours": round((time.time() - files[-1]["mtime"]) / 3600, 1),
                "size_kb": round(files[-1]["size"] / 1024, 1)
            }

        return result

    except Exception as e:
        print(f"⚠️ 统计存储信息失败: {e}")
        return {"error": str(e)}


def cleanup_old_files(max_age_hours: int = 24, max_total_size_mb: int = 100) -> Dict[str, Any]:
    """清理旧文件

    Args:
        max_age_hours: 文件最大保存时间（小时）
        max_total_size_mb: 总大小上限（MB）

    Returns:
        {
            "deleted_count": 删除文件数,
            "freed_space_mb": 释放空间(MB),
            "deleted_files": [...],
            "remaining_files": 剩余文件数
        }
    """
    _ensure_dirs()

    try:
        import time

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        max_total_size = max_total_size_mb * 1024 * 1024

        files = []
        total_size = 0

        # 收集所有文件信息
        for filename in os.listdir(BASE_DIR):
            file_path = os.path.join(BASE_DIR, filename)
            if not os.path.isfile(file_path):
                continue

            # 跳过索引文件和元数据文件
            if filename == 'uploads.index' or filename.endswith('.meta.json'):
                continue

            file_stat = os.stat(file_path)
            files.append({
                "path": file_path,
                "name": filename,
                "size": file_stat.st_size,
                "mtime": file_stat.st_mtime,
                "age": current_time - file_stat.st_mtime
            })
            total_size += file_stat.st_size

        # 按时间排序（旧的在前）
        files.sort(key=lambda x: x['mtime'])

        deleted_files = []
        freed_space = 0

        # 策略1：删除超过时间限制的文件
        for file_info in files[:]:
            if file_info['age'] > max_age_seconds:
                try:
                    os.remove(file_info['path'])
                    # 同时删除元数据文件（如果存在）
                    meta_path = file_info['path'] + '.meta.json'
                    if os.path.exists(meta_path):
                        os.remove(meta_path)

                    deleted_files.append(file_info['name'])
                    freed_space += file_info['size']
                    total_size -= file_info['size']
                    files.remove(file_info)
                except Exception as e:
                    print(f"⚠️ 删除文件失败 {file_info['name']}: {e}")

        # 策略2：如果总大小仍超限，继续删除最旧的文件
        while total_size > max_total_size and files:
            file_info = files.pop(0)
            try:
                os.remove(file_info['path'])
                # 同时删除元数据文件
                meta_path = file_info['path'] + '.meta.json'
                if os.path.exists(meta_path):
                    os.remove(meta_path)

                deleted_files.append(file_info['name'])
                freed_space += file_info['size']
                total_size -= file_info['size']
            except Exception as e:
                print(f"⚠️ 删除文件失败 {file_info['name']}: {e}")

        # 重建索引（移除已删除文件的记录）
        if deleted_files:
            _rebuild_index()

        return {
            "deleted_count": len(deleted_files),
            "freed_space_mb": round(freed_space / 1024 / 1024, 2),
            "deleted_files": deleted_files[:10],  # 只返回前10个
            "remaining_files": len(files),
            "remaining_size_mb": round(total_size / 1024 / 1024, 2)
        }

    except Exception as e:
        print(f"⚠️ 清理文件失败: {e}")
        return {"error": str(e)}


def _rebuild_index() -> None:
    """重建索引文件，移除不存在的文件记录"""
    mapping = _load_index()

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        for fid, path in mapping.items():
            if os.path.exists(path):
                f.write(f"{fid}\t{path}\n")


