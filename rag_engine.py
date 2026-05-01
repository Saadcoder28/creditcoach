#!/usr/bin/env python3
"""
CreditCoach AI — RAG Engine
Vector-based retrieval over FICO scoring guides and consumer rights documents.
Uses IBM watsonx.ai embeddings with TF-IDF fallback for semantic search.
"""
import os, math, re

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge")


# ── Document Chunking ──

def chunk_markdown(text, source_name):
    """Split markdown by ## and ### headers into semantic chunks."""
    chunks = []
    current_header = source_name
    current_content = []

    for line in text.split("\n"):
        if line.startswith("## ") or line.startswith("### "):
            if current_content:
                body = "\n".join(current_content).strip()
                if len(body) > 30:
                    chunks.append({"source": source_name, "header": current_header, "content": body})
            current_header = line.lstrip("#").strip()
            current_content = [line]
        else:
            current_content.append(line)

    if current_content:
        body = "\n".join(current_content).strip()
        if len(body) > 30:
            chunks.append({"source": source_name, "header": current_header, "content": body})

    return chunks


# ── TF-IDF Fallback (pure Python, no dependencies) ──

def _tokenize(text):
    return re.findall(r"\b[a-z]{2,}\b", text.lower())


def _build_tfidf(chunks):
    doc_freq = {}
    all_tokens = []
    for chunk in chunks:
        tokens = set(_tokenize(chunk["content"]))
        all_tokens.append(tokens)
        for t in tokens:
            doc_freq[t] = doc_freq.get(t, 0) + 1

    vocab = list(doc_freq.keys())
    vocab_idx = {w: i for i, w in enumerate(vocab)}
    n = len(chunks)

    vectors = []
    for chunk in chunks:
        toks = _tokenize(chunk["content"])
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        vec = [0.0] * len(vocab)
        for t, cnt in tf.items():
            if t in vocab_idx:
                vec[vocab_idx[t]] = cnt * math.log(n / (1 + doc_freq[t]))
        vectors.append(vec)

    return vectors, vocab, vocab_idx, doc_freq, n


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


# ── RAG Engine ──

class RAGEngine:
    """Retrieval-Augmented Generation engine with watsonx embeddings + TF-IDF fallback."""

    def __init__(self, credentials=None, project_id=None):
        self.chunks = []
        self.vectors = []
        self.use_watsonx = False
        self.embeddings_model = None
        # TF-IDF state
        self._vocab = []
        self._vocab_idx = {}
        self._doc_freq = {}
        self._n_docs = 0

        # Try watsonx embeddings
        if credentials and project_id:
            try:
                from ibm_watsonx_ai.foundation_models import Embeddings
                self.embeddings_model = Embeddings(
                    model_id="ibm/slate-125m-english-rtrvr-v2",
                    credentials=credentials,
                    project_id=project_id,
                )
                self.use_watsonx = True
                print("  RAG: Using watsonx embeddings (ibm/slate-125m-english-rtrvr-v2)")
            except Exception as e:
                print(f"  RAG: watsonx embeddings unavailable ({e}), using TF-IDF fallback")

        self._load_documents()

    # ── Loading ──

    def _load_documents(self):
        for fname in sorted(os.listdir(KNOWLEDGE_DIR)):
            if fname.endswith(".md"):
                with open(os.path.join(KNOWLEDGE_DIR, fname)) as f:
                    text = f.read()
                source = fname.replace(".md", "").replace("_", " ").title()
                self.chunks.extend(chunk_markdown(text, source))

        print(f"  RAG: Loaded {len(self.chunks)} chunks from knowledge base")

        if self.use_watsonx:
            self._embed_watsonx()
        else:
            self._embed_tfidf()

    def _embed_watsonx(self):
        try:
            texts = [c["content"] for c in self.chunks]
            result = self.embeddings_model.embed_documents(texts=texts)
            if isinstance(result, list):
                self.vectors = result
            elif isinstance(result, dict) and "results" in result:
                self.vectors = [r["embedding"] for r in result["results"]]
            else:
                self.vectors = result
            print(f"  RAG: Embedded {len(self.vectors)} chunks with watsonx")
        except Exception as e:
            print(f"  RAG: Embedding failed ({e}), falling back to TF-IDF")
            self.use_watsonx = False
            self._embed_tfidf()

    def _embed_tfidf(self):
        self.vectors, self._vocab, self._vocab_idx, self._doc_freq, self._n_docs = \
            _build_tfidf(self.chunks)
        print(f"  RAG: Built TF-IDF index ({len(self._vocab)} terms)")

    # ── Query ──

    def _query_vec(self, query):
        if self.use_watsonx:
            try:
                result = self.embeddings_model.embed_query(text=query)
                if isinstance(result, list):
                    return result
                if isinstance(result, dict):
                    return result.get("results", [result])[0].get("embedding", result)
                return result
            except Exception:
                pass
        # TF-IDF fallback
        toks = _tokenize(query)
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        vec = [0.0] * len(self._vocab)
        for t, cnt in tf.items():
            if t in self._vocab_idx:
                vec[self._vocab_idx[t]] = cnt * math.log(self._n_docs / (1 + self._doc_freq.get(t, 0)))
        return vec

    def search(self, query, top_k=3):
        """Return top-k most relevant chunks for a query."""
        if not self.chunks:
            return []
        qv = self._query_vec(query)
        scored = [(i, _cosine(qv, v)) for i, v in enumerate(self.vectors)]
        scored.sort(key=lambda x: -x[1])
        results = []
        for idx, sim in scored[:top_k]:
            if sim > 0.10:
                c = self.chunks[idx]
                results.append({
                    "source": c["source"],
                    "header": c["header"],
                    "content": c["content"],
                    "relevance": round(sim, 4),
                })
        return results

    def get_context(self, query, top_k=3):
        """Return formatted context string for agent prompt injection."""
        results = self.search(query, top_k)
        if not results:
            return "No relevant knowledge base articles found."
        ctx = "RETRIEVED KNOWLEDGE BASE CONTEXT (via RAG vector search):\n\n"
        for i, r in enumerate(results, 1):
            ctx += f"[{i}] Source: {r['source']} | Section: {r['header']} | Relevance: {r['relevance']}\n"
            ctx += r["content"] + "\n\n"
        return ctx
