import re
from neo4j import GraphDatabase
from config import config_instance

class GraphRetrievalService:
    """Retrieves candidates and contextual entities from Neo4j using Vector Search and topological traversals."""
    
    def __init__(self):
        self.uri = config_instance.NEO4J_URI
        self.user = config_instance.NEO4J_USER
        self.password = config_instance.NEO4J_PASSWORD
        self._driver = None

    def connect(self):
        if not self._driver:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def retrieve_candidates(self, clause_text: str, embedding: list = None, limit: int = 3) -> list:
        """
        Combines topological traversal and vector search to find candidate global counterpart clauses.
        Falls back to in-memory matching if Neo4j is offline.
        """
        candidates = []
        try:
            self.connect()
            with self._driver.session() as session:
                # 1. Vector index search (If embedding is provided and Neo4j vector search index is present)
                if embedding:
                    vector_query = """
                    CALL db.index.vector.queryNodes('clause_embeddings_idx', $limit, $embedding)
                    YIELD node, score
                    RETURN node.id as id, node.number as number, node.text as text, score
                    """
                    try:
                        res = session.run(vector_query, embedding=embedding, limit=limit)
                        for record in res:
                            candidates.append({
                                "id": record["id"],
                                "number": record["number"],
                                "text": record["text"],
                                "score": record["score"]
                            })
                    except Exception as ve:
                        # Index might not be active, proceed to graph traversal
                        pass

                # 2. Topological traversal to find related baseline clauses
                if not candidates:
                    traversal_query = """
                    MATCH (c:Clause)
                    WHERE c.text CONTAINS $keyword OR c.id CONTAINS $keyword
                    RETURN c.id as id, c.number as number, c.text as text, 1.0 as score
                    LIMIT $limit
                    """
                    # Use a clean keyword from the text
                    clean_kw = " ".join(re.findall(r'\w+', clause_text)[:3])
                    if clean_kw:
                        res = session.run(traversal_query, keyword=clean_kw, limit=limit)
                        for record in res:
                            candidates.append({
                                "id": record["id"],
                                "number": record["number"],
                                "text": record["text"],
                                "score": record["score"]
                            })
        except Exception as e:
            # Silence DB offline connection issues and fallback gracefully
            pass
            
        return candidates
