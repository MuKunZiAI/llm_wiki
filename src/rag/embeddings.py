"""向量嵌入层 — 支持 TF-IDF（零依赖）和 sentence-transformers（可选）"""

from __future__ import annotations

import math
import re
from collections import Counter


class Embedder:
    """
    嵌入模型抽象。
    - 默认使用 TF-IDF（零外部依赖）
    - 若安装 sentence-transformers 则自动切换
    """

    def __init__(self, model_name: str = ""):
        self._tfidf_idf: dict[str, float] = {}
        self._tfidf_docs: list[list[str]] = []
        self._st_model = None

        if model_name:
            self._init_sentence_transformer(model_name)
        else:
            self._try_init_sentence_transformer()

    def _init_sentence_transformer(self, name: str):
        try:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer(name)
        except ImportError:
            pass

    def _try_init_sentence_transformer(self):
        # 尝试常见模型
        for name in [
            "paraphrase-multilingual-MiniLM-L12-v2",
            "all-MiniLM-L6-v2",
        ]:
            self._init_sentence_transformer(name)
            if self._st_model:
                break

    @property
    def dim(self) -> int:
        if self._st_model:
            return self._st_model.get_sentence_embedding_dimension()
        return len(self._tfidf_idf) or 1

    # ------------------------------------------------------------------
    # 批量索引
    # ------------------------------------------------------------------

    def fit(self, documents: list[str]):
        """为 TF-IDF 构建倒排文档频率（仅 TF-IDF 模式）"""
        if self._st_model:
            return
        tokenized = [self._tokenize(d) for d in documents]
        self._tfidf_docs = tokenized
        doc_count = len(tokenized)
        df: Counter = Counter()
        for tokens in tokenized:
            df.update(set(tokens))
        self._tfidf_idf = {
            word: math.log((doc_count + 1) / (freq + 1)) + 1
            for word, freq in df.items()
        }

    # ------------------------------------------------------------------
    # 编码
    # ------------------------------------------------------------------

    def encode(self, text: str) -> list[float]:
        """将文本编码为向量"""
        if self._st_model:
            return list(self._st_model.encode(text).tolist())
        return self._tfidf_encode(text)

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        if self._st_model:
            return [list(v) for v in self._st_model.encode(texts).tolist()]
        return [self._tfidf_encode(t) for t in texts]

    # ------------------------------------------------------------------
    # TF-IDF 实现
    # ------------------------------------------------------------------

    def _tfidf_encode(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        vec: dict[str, float] = {}
        for word, freq in tf.items():
            idf = self._tfidf_idf.get(word, 1.0)
            vec[word] = freq * idf / len(tokens)

        # 归一化
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        # 按字典序排列保证向量顺序一致
        vocab = sorted(self._tfidf_idf.keys()) if self._tfidf_idf else sorted(vec.keys())
        return [vec.get(w, 0.0) / norm for w in vocab]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """中英文混合分词"""
        text = text.lower()
        # 中文按单字+双字组合；英文按单词
        tokens: list[str] = []
        # 英文单词
        tokens.extend(re.findall(r"[a-z0-9]{2,}", text))
        # 中文双字组合
        chinese_chars = re.findall(r"[一-鿿]", text)
        for i in range(len(chinese_chars) - 1):
            tokens.append(chinese_chars[i] + chinese_chars[i + 1])
        tokens.extend(chinese_chars)  # 单字也保留
        return tokens
