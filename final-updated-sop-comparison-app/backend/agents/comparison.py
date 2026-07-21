import math
import re
import numpy as np
from services.scoring import ScoringService
from config import config_instance
from neo4j import GraphDatabase
from llm.factory import LLMFactory
from pydantic import BaseModel, Field

class CandidateSelection(BaseModel):
    selected_global_id: str = Field(description="The ID of the best matching Global clause from the candidates list.")

class ComparisonAgent:
    """Computes semantic embedding + lexical similarity between mapped clauses, with GraphRAG-assisted candidate selection."""

    def compute_lexical_jaccard(self, text_a: str, text_b: str) -> float:
        """Computes Jaccard similarity coefficient based on word tokens."""
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a and not words_b:
            return 1.0
        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        return len(intersection) / len(union)

    def mock_embeddings(self, text: str) -> list:
        """Returns a deterministic mock vector if no live embedding client is configured."""
        # Clean deterministic vector based on text characters
        vec = [ord(char) % 100 for char in text[:128]]
        if len(vec) < 128:
            vec += [0] * (128 - len(vec))
        norm = math.sqrt(sum(x*x for x in vec))
        return [x/norm for x in vec] if norm > 0 else vec

    def compute_cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        """Computes cosine similarity between two vector lists."""
        a = np.array(vec_a)
        b = np.array(vec_b)
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def compare_clauses(self, text_a: str, text_b: str) -> dict:
        """Performs comparison returning detailed similarities and overall compliance score."""
        if not text_a.strip() or not text_b.strip():
            return {
                "lexical_similarity": 0.0,
                "semantic_similarity": 0.0,
                "combined_score": 0.0
            }
            
        if text_a.strip().lower() == text_b.strip().lower():
            return {
                "lexical_similarity": 1.0,
                "semantic_similarity": 1.0,
                "combined_score": 1.0
            }
            
        lexical = self.compute_lexical_jaccard(text_a, text_b)
        
        vec_a = self.mock_embeddings(text_a)
        vec_b = self.mock_embeddings(text_b)
        
        semantic = self.compute_cosine_similarity(vec_a, vec_b)
        
        overall_score = ScoringService.calculate_similarity_score(lexical, semantic)
        
        return {
            "lexical_similarity": round(lexical, 3),
            "semantic_similarity": round(semantic, 3),
            "combined_score": overall_score
        }

    def get_clause_graph_context(self, session, clause_id: str) -> str:
        """Helper to dynamically traverse the graph and retrieve neighboring context for a clause."""
        query = """
        MATCH (c:Clause {id: $clause_id})-[r]-(n)
        RETURN type(r) as r_type, labels(n)[0] as n_label, n.id as n_id, n.text as n_text, properties(n) as n_props
        LIMIT 10
        """
        context_parts = []
        try:
            res = session.run(query, clause_id=clause_id)
            for record in res:
                r_type = record["r_type"]
                n_label = record["n_label"]
                n_id = record["n_id"]
                n_text = record["n_text"] or ""
                props = record["n_props"] or {}
                prop_details = ", ".join(f"{k}: {v}" for k, v in props.items() if k not in ["id", "text", "number"])
                prop_str = f" ({prop_details})" if prop_details else ""
                
                context_parts.append(
                    f"- Linked to {n_label} '{n_id}' via {r_type} relationship{prop_str}. Text: \"{n_text[:120]}\""
                )
        except Exception:
            pass
        return "\n".join(context_parts) if context_parts else "No neighboring relationships found in graph."

    def find_best_match_graph_rag(self, local_clause: dict, global_clauses: list) -> tuple:
        """
        Uses GraphRAG to select the best matching Global Clause for a given Local Clause.
        Falls back to standard search if Neo4j is offline or selection fails.
        """
        local_id = local_clause.get("id")
        local_text = local_clause.get("text", "")
        
        # 1. Retrieve candidates via Neo4j
        candidates = []
        graph_context_local = ""
        candidates_with_context = []
        
        driver = None
        try:
            driver = GraphDatabase.driver(
                config_instance.NEO4J_URI, 
                auth=(config_instance.NEO4J_USER, config_instance.NEO4J_PASSWORD)
            )
            with driver.session() as session:
                # Get local clause neighborhood context
                graph_context_local = self.get_clause_graph_context(session, local_id)
                
                # Fetch candidates using Neo4j Vector query if index is available
                local_emb = self.mock_embeddings(local_text)
                vector_query = """
                CALL db.index.vector.queryNodes('clause_embeddings_idx', 5, $embedding)
                YIELD node, score
                MATCH (node)-[:HAS_CLAUSE|HAS_SECTION]-(sop:SOP)
                WHERE sop.type = 'Global'
                RETURN node.id as id, node.number as number, node.text as text, score
                """
                try:
                    res = session.run(vector_query, embedding=local_emb)
                    for record in res:
                        candidates.append({
                            "id": record["id"],
                            "number": record["number"],
                            "text": record["text"]
                        })
                except Exception:
                    pass
                
                # Fallback to topological traversal keyword matching if vector query is empty
                if not candidates:
                    traversal_query = """
                    MATCH (c:Clause)-[:HAS_CLAUSE|HAS_SECTION]-(sop:SOP)
                    WHERE sop.type = 'Global' AND (toLower(c.text) CONTAINS $keyword OR toLower(c.id) CONTAINS $keyword)
                    RETURN c.id as id, c.number as number, c.text as text
                    LIMIT 5
                    """
                    clean_kw = " ".join(re.findall(r'\w+', local_text)[:3])
                    if clean_kw:
                        res = session.run(traversal_query, keyword=clean_kw.lower())
                        for record in res:
                            candidates.append({
                                "id": record["id"],
                                "number": record["number"],
                                "text": record["text"]
                            })
                            
                # Retrieve neighborhood context for each candidate global clause
                for cand in candidates:
                    cand_context = self.get_clause_graph_context(session, cand["id"])
                    candidates_with_context.append({
                        "id": cand["id"],
                        "number": cand["number"],
                        "text": cand["text"],
                        "graph_context": cand_context
                    })
        except Exception:
            pass
        finally:
            if driver:
                driver.close()

        # 2. Invoke LLM selection if we have candidates and LLM is configured
        if candidates_with_context:
            try:
                model = LLMFactory.get_chat_model()
                structured_llm = model.with_structured_output(CandidateSelection)
                
                # Format candidates details for LLM prompt
                cands_formatted = ""
                for c in candidates_with_context:
                    cands_formatted += f"Candidate ID: {c['id']} (Clause {c['number']})\n"
                    cands_formatted += f"Text: \"{c['text']}\"\n"
                    cands_formatted += f"Graph Context:\n{c['graph_context']}\n"
                    cands_formatted += "-" * 40 + "\n"
                    
                system_prompt = """
                You are a GraphRAG Ranking Agent.
                Your task is to analyze a Local SOP clause and select the most semantically appropriate Global SOP clause from a list of candidates.
                You will be provided with neighboring graph contexts (connected entities, sections, dynamic relationships) to help you understand the operational context.

                CRITICAL RULES:
                - Focus purely on selecting the best candidate ID.
                - Do NOT compute similarity scores or percentages.
                - Do NOT output compliance classifications (Keep/Update/SME Review).
                """
                
                user_prompt = f"""
                Local Clause Text:
                "{local_text}"

                Local Clause Graph Context:
                {graph_context_local}

                Candidates list:
                {cands_formatted}

                Identify the best candidate Global Clause ID.
                """
                
                # Run the model
                selection = structured_llm.invoke([
                    ("system", system_prompt),
                    ("user", user_prompt)
                ])
                
                selected_id = selection.selected_global_id
                # Verify that selected_id actually belongs to the baseline global clauses list
                matched_gcls = next((g for g in global_clauses if g["id"] == selected_id), None)
                if matched_gcls:
                    comp_res = self.compare_clauses(local_text, matched_gcls["text"])
                    return selected_id, comp_res
            except Exception:
                pass
                
        # 3. Fallback: standard exhaustive in-memory comparison
        best_match_clause_id = None
        best_score = -1.0
        best_res = None
        
        for g_cls in global_clauses:
            comp_res = self.compare_clauses(local_text, g_cls["text"])
            score = comp_res["combined_score"]
            if score > best_score:
                best_score = score
                best_match_clause_id = g_cls["id"]
                best_res = comp_res
                
        return best_match_clause_id, best_res
