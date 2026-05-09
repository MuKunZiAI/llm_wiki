"""RAG + Wiki 混合架构 — 非交互式演示脚本

运行：python -X utf8 demo.py
"""

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

from src.config import WIKI_DATA_DIR, WEEKLY_REPORTS_DIR
from src.wiki import WikiStore
from src.rag import RAGRetriever
from src.hybrid import HybridEngine

DEMO_QUESTIONS = [
    ("A", "Wiki 盲区 -> RAG 兜底",
     "SSL 证书什么时候到期？",
     "该主题在 Wiki 中没有独立概念页，系统回退到 RAG 从原始周报中检索。"),
    ("B", "Wiki 骨架 + RAG 补充",
     "连接池超时排查进展如何？",
     "Wiki 返回 Evolution Log（三周排查演进）+ Contradictions（备选根因），RAG 补充最新细节。"),
    ("C", "主动暴露分歧",
     "Redis 用集群版还是哨兵？",
     "Wiki Contradictions 节直接展示「架构组推荐 Cluster」vs「运维组推荐 Sentinel」。"),
    ("D", "跨文档推理",
     "支付中心迁移后连接池配置怎么调整？",
     "Wiki 通过 connection-pool-timeout -> hikari -> payment-center-migration 关系链串联因果。"),
    ("E", "知识积累验证",
     "Hikari 版本升级后连接池超时的根因是什么？",
     "验证 Evolution Log 积累效果：第17周怀疑 -> 第18周确认 -> 第19周解决。"),
]


def build_engine():
    print("[1/3] 加载 Wiki 知识图谱 ...")
    wiki_store = WikiStore(WIKI_DATA_DIR)
    print(f"      概念={len(wiki_store.concepts)}  来源={len(wiki_store.sources)}  实体={len(wiki_store.entities)}")

    print("[2/3] 初始化 RAG 检索引擎 ...")
    rag = RAGRetriever(chunk_size=500, chunk_overlap=100, top_k=10)
    model_type = "sentence-transformers" if rag.embedder._st_model else "TF-IDF（零依赖）"
    print(f"      嵌入模型: {model_type}")

    print("[3/3] 索引周报文档 ...")
    rag.index_documents(WEEKLY_REPORTS_DIR)
    print(f"      已索引 {rag.source_count} 份文档, {rag.vector_store.size} 个 Chunk")

    return HybridEngine(wiki_store, rag)


def print_separator(char="="):
    print(char * 68)


def main():
    print_separator()
    print("  RAG + Wiki 混合架构 — 演示（第三阶段，基于周报场景）")
    print_separator()

    engine = build_engine()

    print(f"\n  Wiki 中已摄入的概念（{len(engine.wiki_searcher.store.concepts)} 个）：")
    for slug, c in engine.wiki_searcher.store.concepts.items():
        conf_mark = {"low": "[L]", "medium": "[M]", "high": "[H]"}.get(c.confidence, "")
        print(f"    - {c.title}  {conf_mark}  sources={c.source_count}")

    print(f"\n  Wiki 中未摄入（盲区测试目标）：SSL 证书到期")

    print("\n")
    print_separator()
    print("  开始查询演示")
    print_separator()

    for idx, (label, strategy_name, question, desc) in enumerate(DEMO_QUESTIONS, 1):
        print(f"\n{'=' * 68}")
        print(f"  [{idx}/{len(DEMO_QUESTIONS)}] 场景 {label}：{strategy_name}")
        print(f"  问题：{question}")
        print(f"  预期：{desc}")
        print(f"{'-' * 68}")

        result = engine.query(question)

        print(f"  实际策略: {result.merge_strategy}")
        print(f"  Wiki 覆盖: {result.wiki_coverage}  |  "
              f"Wiki 命中: {len(result.wiki_hits)}  |  "
              f"RAG 命中: {len(result.rag_hits)}")
        print(f"{'-' * 68}")

        # 只打印关键段落（非完整）
        for seg in result.segments[:5]:
            text_preview = seg.text[:120].replace("\n", " ")
            label_str = seg.source_label
            if seg.is_contradiction:
                label_str += " [分歧]"
            print(f"  [{label_str}] {text_preview}...")

        if len(result.segments) > 5:
            print(f"  ... （共 {len(result.segments)} 个段落，已截断）")

    print(f"\n{'=' * 68}")
    print("  演示完成。所有场景均基于同一份周报：backend-weekly-2026-04-20.md")
    print(f"{'=' * 68}\n")


if __name__ == "__main__":
    main()
