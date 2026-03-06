"""Novelty scoring using TF-IDF and similarity detection."""

import re
import math
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass
import logging
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document for novelty analysis."""
    id: str
    content: str
    timestamp: datetime
    narrative: str
    tokens: List[str] = None
    vector: Dict[str, float] = None


class NoveltyScorer:
    """Score content novelty using TF-IDF and similarity detection."""

    def __init__(self, max_documents: int = 10000,
                 similarity_threshold: float = 0.7):
        """
        Initialize novelty scorer.

        Args:
            max_documents: Maximum documents to keep in memory
            similarity_threshold: Threshold for duplicate detection (0-1)
        """
        self.max_documents = max_documents
        self.similarity_threshold = similarity_threshold

        # Document storage
        self.documents = []  # Ordered by timestamp
        self.document_index = {}  # id -> document

        # TF-IDF components
        self.document_frequency = defaultdict(int)  # term -> doc count
        self.idf_cache = {}  # term -> IDF value
        self.total_documents = 0

        # Deduplication
        self.content_hashes = set()  # For exact duplicate detection
        self.recent_signatures = []  # For near-duplicate detection

        # Stopwords for crypto context
        self.stopwords = self._init_stopwords()

    def _init_stopwords(self) -> Set[str]:
        """Initialize crypto-specific stopwords."""
        return {
            # Common English
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
            'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you',
            'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they',
            'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one',
            'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out',
            'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when',

            # Crypto common
            'crypto', 'cryptocurrency', 'token', 'coin', 'blockchain',
            'price', 'market', 'trading', 'trade', 'buy', 'sell',

            # URLs and mentions
            'http', 'https', 'com', 'www', 'io',

            # Time references
            'today', 'yesterday', 'tomorrow', 'now', 'just', 'new'
        }

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into meaningful terms."""
        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)

        # Remove mentions and hashtags (keep the word)
        text = re.sub(r'[@#](\w+)', r'\1', text)

        # Remove special characters but keep alphanumeric
        text = re.sub(r'[^a-z0-9\s]', ' ', text)

        # Tokenize
        tokens = text.split()

        # Filter stopwords and short tokens
        tokens = [t for t in tokens if len(t) > 2 and t not in self.stopwords]

        return tokens

    def _calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Calculate term frequency for tokens."""
        if not tokens:
            return {}

        counter = Counter(tokens)
        total = len(tokens)

        # Use logarithmic TF to reduce impact of repeated terms
        tf = {}
        for term, count in counter.items():
            tf[term] = 1 + math.log10(count) if count > 0 else 0

        return tf

    def _update_idf(self, tokens: Set[str]):
        """Update IDF values for new document terms."""
        for term in tokens:
            self.document_frequency[term] += 1

        # Recalculate IDF for affected terms
        for term in tokens:
            df = self.document_frequency[term]
            # Add 1 to avoid division by zero, use log base 10
            self.idf_cache[term] = math.log10((self.total_documents + 1) / (df + 1))

    def _calculate_tfidf_vector(self, document: Document) -> Dict[str, float]:
        """Calculate TF-IDF vector for a document."""
        if not document.tokens:
            return {}

        tf = self._calculate_tf(document.tokens)
        tfidf = {}

        for term, tf_value in tf.items():
            idf_value = self.idf_cache.get(term, 0)
            tfidf[term] = tf_value * idf_value

        # Normalize vector
        magnitude = math.sqrt(sum(v**2 for v in tfidf.values()))
        if magnitude > 0:
            tfidf = {k: v/magnitude for k, v in tfidf.items()}

        return tfidf

    def _cosine_similarity(self, vec1: Dict[str, float],
                          vec2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two TF-IDF vectors."""
        if not vec1 or not vec2:
            return 0.0

        # Get common terms
        common_terms = set(vec1.keys()) & set(vec2.keys())

        if not common_terms:
            return 0.0

        # Calculate dot product
        dot_product = sum(vec1[term] * vec2[term] for term in common_terms)

        # Vectors are already normalized, so cosine similarity = dot product
        return dot_product

    def _generate_signature(self, tokens: List[str]) -> str:
        """Generate a signature for near-duplicate detection."""
        # Use first 100 unique tokens for signature
        unique_tokens = []
        seen = set()
        for token in tokens:
            if token not in seen:
                unique_tokens.append(token)
                seen.add(token)
                if len(unique_tokens) >= 100:
                    break

        # Create signature
        signature = ' '.join(sorted(unique_tokens[:50]))
        return hashlib.md5(signature.encode()).hexdigest()

    def add_document(self, content: str, narrative: str,
                    doc_id: Optional[str] = None,
                    timestamp: Optional[datetime] = None) -> Document:
        """
        Add a document and calculate its novelty.

        Args:
            content: Document content
            narrative: Associated narrative category
            doc_id: Optional document ID
            timestamp: Optional timestamp

        Returns:
            Document object with calculated vectors
        """
        # Generate ID if not provided
        if not doc_id:
            doc_id = hashlib.md5(
                f"{content[:100]}{timestamp}".encode()
            ).hexdigest()[:12]

        # Use current time if not provided
        if not timestamp:
            timestamp = datetime.now()

        # Tokenize content
        tokens = self._tokenize(content)

        # Create document
        doc = Document(
            id=doc_id,
            content=content[:1000],  # Store truncated content
            timestamp=timestamp,
            narrative=narrative,
            tokens=tokens
        )

        # Update document frequency
        unique_tokens = set(tokens)
        self.total_documents += 1
        self._update_idf(unique_tokens)

        # Calculate TF-IDF vector
        doc.vector = self._calculate_tfidf_vector(doc)

        # Store document
        self.documents.append(doc)
        self.document_index[doc_id] = doc

        # Maintain max documents limit
        if len(self.documents) > self.max_documents:
            old_doc = self.documents.pop(0)
            del self.document_index[old_doc.id]

            # Update document frequency
            for term in set(old_doc.tokens):
                self.document_frequency[term] -= 1
                if self.document_frequency[term] <= 0:
                    del self.document_frequency[term]
                    if term in self.idf_cache:
                        del self.idf_cache[term]

        return doc

    def calculate_novelty_score(self, content: str,
                               narrative: str = "",
                               timestamp: Optional[datetime] = None) -> Dict:
        """
        Calculate novelty score for new content.

        Returns:
            Dict with novelty score and analysis
        """
        # Check for exact duplicate
        content_hash = hashlib.md5(content.encode()).hexdigest()
        is_duplicate = content_hash in self.content_hashes

        # Tokenize
        tokens = self._tokenize(content)

        if not tokens:
            return {
                'novelty_score': 0.0,
                'is_duplicate': is_duplicate,
                'is_novel': False,
                'similar_documents': [],
                'new_terms': [],
                'reasoning': 'No meaningful tokens found'
            }

        # Create temporary document
        temp_doc = Document(
            id='temp',
            content=content,
            timestamp=timestamp or datetime.now(),
            narrative=narrative,
            tokens=tokens
        )

        # Calculate TF-IDF vector
        temp_doc.vector = self._calculate_tfidf_vector(temp_doc)

        # Find similar documents
        similar_docs = self._find_similar_documents(temp_doc)

        # Calculate novelty metrics
        max_similarity = max([s['similarity'] for s in similar_docs]) if similar_docs else 0.0

        # Identify new terms (terms not seen frequently)
        new_terms = [
            term for term in set(tokens)
            if self.document_frequency.get(term, 0) < 3
        ]

        # Calculate novelty score (0-1)
        novelty_score = 1.0 - max_similarity

        # Adjust for new terms
        if new_terms:
            term_bonus = min(len(new_terms) / 10, 0.3)  # Up to 30% bonus
            novelty_score = min(1.0, novelty_score + term_bonus)

        # Time decay for similarity (older similar content is less relevant)
        if similar_docs and timestamp:
            most_similar = similar_docs[0]
            time_diff = timestamp - most_similar['timestamp']
            if time_diff > timedelta(days=7):
                # Boost novelty if similar content is old
                novelty_score = min(1.0, novelty_score + 0.2)

        # Determine if content is novel
        is_novel = novelty_score > 0.5 and not is_duplicate

        # Add to hash set if novel
        if is_novel:
            self.content_hashes.add(content_hash)

        return {
            'novelty_score': round(novelty_score, 3),
            'is_duplicate': is_duplicate,
            'is_novel': is_novel,
            'similar_documents': similar_docs[:3],  # Top 3 similar
            'new_terms': new_terms[:10],  # Top 10 new terms
            'max_similarity': round(max_similarity, 3),
            'reasoning': self._generate_reasoning(
                novelty_score, is_duplicate, similar_docs, new_terms
            )
        }

    def _find_similar_documents(self, document: Document,
                               top_k: int = 5) -> List[Dict]:
        """Find most similar documents using cosine similarity."""
        if not document.vector:
            return []

        similarities = []

        # Compare with recent documents (last 1000 or within 7 days)
        cutoff_time = document.timestamp - timedelta(days=7)

        for doc in reversed(self.documents[-1000:]):
            if doc.timestamp < cutoff_time:
                continue

            if not doc.vector:
                continue

            similarity = self._cosine_similarity(document.vector, doc.vector)

            if similarity > 0.1:  # Minimum threshold
                similarities.append({
                    'id': doc.id,
                    'similarity': similarity,
                    'content': doc.content[:200],
                    'timestamp': doc.timestamp,
                    'narrative': doc.narrative
                })

        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        return similarities[:top_k]

    def _generate_reasoning(self, novelty_score: float,
                           is_duplicate: bool,
                           similar_docs: List[Dict],
                           new_terms: List[str]) -> str:
        """Generate human-readable reasoning for novelty score."""
        if is_duplicate:
            return "Exact duplicate of existing content"

        if novelty_score > 0.8:
            if new_terms:
                return f"Highly novel content with new terms: {', '.join(new_terms[:3])}"
            else:
                return "Unique perspective on existing topic"
        elif novelty_score > 0.5:
            if similar_docs:
                return f"Moderately novel, {round((1-similar_docs[0]['similarity'])*100)}% different from similar content"
            else:
                return "Fresh take on familiar narrative"
        elif novelty_score > 0.3:
            return "Recycled discussion with minor variations"
        else:
            return "Very similar to existing content, likely repetitive"

    def get_narrative_novelty_trends(self, narrative: str,
                                    window_hours: int = 24) -> Dict:
        """
        Analyze novelty trends for a specific narrative.

        Returns:
            Dict with novelty metrics over time
        """
        cutoff_time = datetime.now() - timedelta(hours=window_hours)

        narrative_docs = [
            doc for doc in self.documents
            if doc.narrative == narrative and doc.timestamp > cutoff_time
        ]

        if not narrative_docs:
            return {
                'avg_novelty': 0.0,
                'trending_terms': [],
                'recycled_topics': [],
                'innovation_rate': 0.0
            }

        # Calculate average novelty
        novelty_scores = []
        all_terms = []

        for i, doc in enumerate(narrative_docs):
            if i == 0:
                novelty_scores.append(1.0)  # First doc is always novel
            else:
                # Compare with previous docs
                similar = self._find_similar_documents(doc, top_k=1)
                novelty = 1.0 - (similar[0]['similarity'] if similar else 0.0)
                novelty_scores.append(novelty)

            all_terms.extend(doc.tokens)

        # Find trending terms (increasing frequency)
        term_counts = Counter(all_terms)
        trending_terms = term_counts.most_common(10)

        # Identify recycled topics (high similarity clusters)
        recycled_topics = []
        for doc in narrative_docs[-10:]:  # Check recent docs
            similar = self._find_similar_documents(doc)
            if similar and similar[0]['similarity'] > 0.7:
                recycled_topics.append(doc.content[:100])

        return {
            'avg_novelty': sum(novelty_scores) / len(novelty_scores),
            'trending_terms': [term for term, _ in trending_terms],
            'recycled_topics': list(set(recycled_topics))[:5],
            'innovation_rate': len([s for s in novelty_scores if s > 0.5]) / len(novelty_scores),
            'document_count': len(narrative_docs)
        }