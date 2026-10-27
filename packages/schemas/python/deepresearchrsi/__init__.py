"""DeepResearchRSI 契约层。

只放数据类与校验函数，不放业务逻辑。服务实现从 `services/*` 反向依赖本包，
本包不得依赖任何 service 模块。
"""

from .models import Brief, Claim, Evidence, Source, SubQuestion
from .validate import ValidationError, validate_research_dir

__all__ = [
    "Brief",
    "Claim",
    "Evidence",
    "Source",
    "SubQuestion",
    "ValidationError",
    "validate_research_dir",
]
__version__ = "0.1.0"
