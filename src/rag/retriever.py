"""RAG 检索器 — 整合切分、编码、向量检索"""

from pathlib import Path

from .chunker import DocumentChunker, Chunk
from .embeddings import Embedder
from .vector_store import VectorStore, ScoredChunk


class RAGRetriever:
    """完整的 RAG 检索管线"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        top_k: int = 10,
        threshold: float = 0.0,
    ):
        self.chunker = DocumentChunker(chunk_size, chunk_overlap)
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.top_k = top_k
        self.threshold = threshold
        self._source_files: set[str] = set()

    def index_documents(self, doc_dir: Path | str):
        """索引目录下所有 .md 文件"""
        doc_dir = Path(doc_dir)
        all_chunks: list[Chunk] = []
        all_texts: list[str] = []

        for md_file in sorted(doc_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            chunks = self.chunker.chunk_text(text, source_file=md_file.name)
            all_chunks.extend(chunks)
            all_texts.extend(c.text for c in chunks)
            self._source_files.add(md_file.name)

        # 先 fit 构建 TF-IDF 词汇表
        self.embedder.fit(all_texts)
        # 再 encode
        vectors = self.embedder.encode_batch(all_texts)
        self.vector_store.add(all_chunks, vectors)

    def index_text(self, text: str, source_name: str = "inline"):
        """索引单段文本"""
        chunks = self.chunker.chunk_text(text, source_file=source_name)
        texts = [c.text for c in chunks]
        self.embedder.fit(texts)
        vectors = self.embedder.encode_batch(texts)
        self.vector_store.add(chunks, vectors)

    def search(self, query: str) -> list[ScoredChunk]:
        """检索 top_k 个相关 Chunk"""
        vec = self.embedder.encode(query)
        return self.vector_store.search(vec, top_k=self.top_k, threshold=self.threshold)

    @property
    def source_count(self) -> int:
        return len(self._source_files)
