"""文档切分器 — 将文档按语义边界切分为 Chunk"""

from dataclasses import dataclass


@dataclass
class Chunk:
    id: str
    text: str
    source_file: str      # 来源文件路径
    chunk_index: int       # 在文档中的序号
    metadata: dict = None

    def __post_init__(self):
        self.metadata = self.metadata or {}


class DocumentChunker:
    """基于段落 + 字符窗口的简单切分器"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, source_file: str = "") -> list[Chunk]:
        """将文本切分为 Chunk 列表"""
        paragraphs = self._split_paragraphs(text)
        chunks: list[Chunk] = []
        chunk_idx = 0

        for para in paragraphs:
            if not para.strip():
                continue
            if len(para) <= self.chunk_size:
                chunks.append(Chunk(
                    id=f"{source_file}__{chunk_idx}",
                    text=para.strip(),
                    source_file=source_file,
                    chunk_index=chunk_idx,
                ))
                chunk_idx += 1
            else:
                # 长段落按滑动窗口切分
                start = 0
                while start < len(para):
                    end = min(start + self.chunk_size, len(para))
                    sub = para[start:end]
                    # 尝试在标点处断句
                    if end < len(para):
                        for sep in ["\n\n", "\n", "。", "；", ". ", "; "]:
                            idx = sub.rfind(sep)
                            if idx > self.chunk_size // 2:
                                end = start + idx + len(sep)
                                break
                    chunks.append(Chunk(
                        id=f"{source_file}__{chunk_idx}",
                        text=para[start:end].strip(),
                        source_file=source_file,
                        chunk_index=chunk_idx,
                    ))
                    chunk_idx += 1
                    start = end - self.chunk_overlap
                    if start < 0:
                        start = 0

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """按双换行拆分段落"""
        return text.split("\n\n")
