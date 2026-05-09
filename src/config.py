"""RAG + Wiki 混合架构 — 全局配置"""

from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Wiki 知识图谱数据目录
WIKI_DATA_DIR = PROJECT_ROOT / "demo_data" / "wiki"

# 周报原始文档目录
WEEKLY_REPORTS_DIR = PROJECT_ROOT / "demo_data" / "weekly_reports"

# RAG 向量参数
CHUNK_SIZE = 500          # 每个 Chunk 最大字符数
CHUNK_OVERLAP = 100       # Chunk 间重叠字符数
TOP_K_CHUNKS = 10         # RAG 召回数量
SIMILARITY_THRESHOLD = 0.05  # 向量相似度最低阈值

# Wiki 图谱参数
WIKI_TOP_K = 5            # Wiki 检索返回数量

# 结果合并策略
ENABLE_RAG_FALLBACK = True  # 是否启用 RAG 兜底
