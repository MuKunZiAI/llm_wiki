"""RAG + Wiki 混合架构 — 主入口

基于「RAG vs Wiki 实战篇」第三阶段设计。
Wiki 优先作为答案骨架，RAG 兜底覆盖盲区。

用法：
    python app.py                          # 交互模式
    python app.py --demo                   # 运行预设演示场景
    python app.py --query "你的问题"         # 单次查询
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

# Windows GBK 控制台兼容：强制使用 UTF-8 输出
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 确保 src 在 path 中
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR.parent))

from src.config import (
    WIKI_DATA_DIR, WEEKLY_REPORTS_DIR,
    CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_CHUNKS, SIMILARITY_THRESHOLD,
)
from src.wiki import WikiStore, WikiSearcher
from src.rag import RAGRetriever
from src.hybrid import HybridEngine


# 预设演示场景（全部来自周报）
DEMO_QUESTIONS = [
    # 场景 A：Wiki 盲区 → RAG 兜底
    "SSL 证书什么时候到期？",
    # 场景 B：Wiki 已覆盖 → Wiki 骨架 + RAG 补充
    "连接池超时排查进展如何？",
    # 场景 C：Wiki 存在矛盾 → 主动暴露分歧
    "Redis 用集群版还是哨兵？",
    # 追加：跨文档推理
    "支付中心迁移后连接池配置怎么调整？",
    # 追加：知识积累验证
    "Hikari 连接池超时的根因是什么？",
]


def build_engine() -> HybridEngine:
    """构建混合引擎：加载 Wiki + 索引 RAG"""
    print("[1/3] 加载 Wiki 知识图谱 ...")
    wiki_store = WikiStore(WIKI_DATA_DIR)
    print(f"      已加载 {len(wiki_store.concepts)} 个概念 | "
          f"{len(wiki_store.sources)} 个来源 | "
          f"{len(wiki_store.entities)} 个实体")

    print("[2/3] 初始化 RAG 检索引擎 ...")
    rag = RAGRetriever(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        top_k=TOP_K_CHUNKS,
        threshold=SIMILARITY_THRESHOLD,
    )
    print(f"      嵌入模型: {'sentence-transformers' if rag.embedder._st_model else 'TF-IDF（零依赖）'}")

    print("[3/3] 索引周报文档 ...")
    rag.index_documents(WEEKLY_REPORTS_DIR)
    print(f"      已索引 {rag.source_count} 份文档, {rag.vector_store.size} 个 Chunk")

    return HybridEngine(wiki_store, rag)


def print_result(result):
    """格式化输出混合查询结果"""
    print()
    print("=" * 68)
    print(f"  问题：{result.question}")
    print(f"  合并策略：{result.merge_strategy}")
    print(f"  Wiki 覆盖：{result.wiki_coverage}  |  "
          f"Wiki 命中 {len(result.wiki_hits)}  |  "
          f"RAG 命中 {len(result.rag_hits)}")
    print("-" * 68)
    print(result.formatted_answer)
    print("-" * 68)

    # 盲区提示
    if result.merge_strategy == "rag_fallback":
        print("  !! 该主题未在 Wiki 知识图谱中，建议纳入 INGEST 队列。")
    if result.wiki_coverage == "blind":
        blind = result.wiki_hits[0] if result.wiki_hits else None
    print("=" * 68)
    print()


def run_demo(engine: HybridEngine):
    """运行预设演示场景"""
    print("\n" + "=" * 68)
    print("  RAG + Wiki 混合架构 — 演示（基于周报场景）")
    print("=" * 68)

    for i, question in enumerate(DEMO_QUESTIONS, 1):
        input(f"\n>>> 按 Enter 运行场景 {i}/{len(DEMO_QUESTIONS)} ...")

        if i == 1:
            print("\n  [场景 A] Wiki 盲区 → RAG 兜底")
        elif i == 2:
            print("\n  [场景 B] Wiki 已覆盖 → Wiki 骨架 + RAG 补充")
        elif i == 3:
            print("\n  [场景 C] Wiki 存在矛盾 → 主动暴露分歧")
        elif i == 4:
            print("\n  [场景 D] 跨文档推理")
        elif i == 5:
            print("\n  [场景 E] 知识积累验证（Evolution Log）")

        result = engine.query(question)
        print_result(result)

    print("\n  演示完成。所有场景均基于同一份周报：backend-weekly-2026-04-20.md")


def run_interactive(engine: HybridEngine):
    """交互模式"""
    print("\n  输入问题开始查询，输入 /demo 运行预设场景，输入 /quit 退出。")
    print("  " + "-" * 60)

    while True:
        try:
            question = input("\n>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  再见。")
            break

        if not question:
            continue
        if question.lower() in ("/quit", "/exit", "/q"):
            print("  再见。")
            break
        if question.lower() == "/demo":
            run_demo(engine)
            continue

        result = engine.query(question)
        print_result(result)


def main():
    parser = argparse.ArgumentParser(
        description="RAG + Wiki 混合知识查询系统"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="运行预设演示场景"
    )
    parser.add_argument(
        "--query", "-q", type=str,
        help="单次查询"
    )
    args = parser.parse_args()

    engine = build_engine()

    if args.demo:
        run_demo(engine)
    elif args.query:
        result = engine.query(args.query)
        print_result(result)
    else:
        run_interactive(engine)


if __name__ == "__main__":
    main()
