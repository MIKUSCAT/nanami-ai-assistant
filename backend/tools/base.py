"""工具基类定义。"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """所有外部工具需实现的统一接口。"""

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具，返回统一结构的结果字典。"""
        raise NotImplementedError

