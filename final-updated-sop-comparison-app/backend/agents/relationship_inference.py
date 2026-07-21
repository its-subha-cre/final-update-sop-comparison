from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from llm.factory import LLMFactory

class RelationshipDecision(BaseModel):
    target_chunk_id: Optional[str] = Field(
        None,
        description="The ID of the target chunk to connect to."
    )
    relationship_type: Optional[str] = Field(
        None,
        description="Dynamic relationship type decided by the LLM (e.g. NEXT_STEP, HAS_SECTION, DIFFERS_FROM, REQUIRES, COMPLIES_WITH, REFERENCES)."
    )
    confidence: float = Field(
        description="Similarity or linking confidence score between 0.0 (low) and 1.0 (high)."
    )
    diff_type: Optional[str] = Field(
        None,
        description="Classification of differences: exact_match, semantic_match, cosmetic, addition, deletion, modification, role_change, control_change."
    )
    rationale: str = Field(
        description="Short natural-language rationale explaining why this relationship is justified."
    )

class SemanticNodeMapping(BaseModel):
    chunk_id: str = Field(description="The ID of the current chunk.")
    node_type: str = Field(
        description="The dynamic Neo4j node label (e.g. Section, Clause, Requirement, SafetyCheck, Role, Equipment constraint)."
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Cleaned properties for the node, e.g. text, title, or clause number."
    )
    relationships: List[RelationshipDecision] = Field(
        default_factory=list,
        description="List of outbound semantic relationships decided by the LLM."
    )
class RelationshipInferenceAgent:
    """LLM Agent responsible for semantic parsing, node labeling, and dynamic edge determination."""
    
    def __init__(self):
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """
            You are a Principal Knowledge Graph Architect, Enterprise Knowledge Graph Architect, Neo4j Expert, GraphRAG Architect, LangGraph Engineer, Graph Data Science (GDS) Specialist, and Senior Python Engineer.
            Your task is to transform a normalized SOP clause chunk into a rich enterprise knowledge graph node and edge mapping.

            === CORE GRAPH DESIGN & INTEGRATION RULES ===
            1. FIXED STRUCTURAL GRAPH (MANDATORY):
               The structural node hierarchy MUST remain: (SOP)-[:HAS_SECTION]->(Section)-[:HAS_CLAUSE]->(Clause).
               - If the current chunk represents a Section or Clause, output "Section" or "Clause" as the node_type.
               - These structural labels and relationships must be preserved to support downstream comparison logic.

            2. DYNAMIC DOMAIN ONTOLOGY (DYNAMIC ENTITIES):
               In addition to structural nodes, dynamically identify and extract meaningful business entities mentioned in the clause content.
               - You must infer the most appropriate semantic label for these entities from the text (e.g. Equipment, PPE, Role, Parameter, SafetyControl, Hazard, Chemical, Procedure, etc.).
               - Do not restrict yourself to a fixed list of labels. Be ontology-aware and dynamic.
               - Future entity types must be supported automatically.

            3. DYNAMIC RELATIONSHIP EXTRACTION:
               Do not hardcode relationship types. Infer meaningful semantic relationships (e.g. USES, REQUIRES, DEPENDS_ON, OPERATED_BY, LOCATED_IN, DEVIATES_FROM, COMPLIES_WITH, REFERENCES).
               - Standardize relationships to UPPERCASE_SNAKE_CASE.
               - SEQUENTIAL CHAINING (NEXT_NODE): You must always link consecutive clauses within the same section. Identify the next chronological clause in sequence from the sibling context and generate a `(CurrentClause)-[:NEXT_NODE]->(NextClause)` relationship to form an unbroken workflow path for GraphRAG.

            4. CANONICAL ENTITY RESOLUTION:
               Normalize all entity names to their absolute singular root form and resolve acronyms (e.g. "Nitrile Gloves" / "Nitrile Glove" -> "Nitrile Glove", "FDA" -> "Food and Drug Administration") to prevent duplicate nodes.

            5. STRICT CONFIDENCE SCORING:
               Assign a confidence score (0.0 to 1.0) to every relationship.
               - If confidence is >= 0.90, categorize as Strong.
               - If confidence is 0.75-0.89, categorize as Medium.
               - If confidence is 0.60-0.74, categorize as Weak.
               - If confidence is < 0.60, DO NOT output/create the relationship.

            6. PROVENANCE & GRAPHRAG OPTIMIZATION (Properties):
               - Track lineage: store document_id, source_document, page_number, extraction_method, created_by_agent ("relationship_inference_agent"), and timestamp in the properties.
               - Optimize for GraphRAG: include searchable_text, keywords, entity_aliases, traversal_priority (1-5), and graph_depth_hint in Clause properties.

            === CRITICAL COMPLIANCE BOUNDARIES ===
            - Do NOT compute compliance scores, similarity percentages, or decide Keep / Update / SME Review.
            - Only handle structural graph construction and relationship inference.
            - Ensure full backward compatibility.
            """),
            ("user", """
            Analyze the following document chunk:
            - Chunk ID: {chunk_id}
            - Content: "{chunk_content}"
            
            Contextual details:
            - Parent Metadata: {parent_context}
            - Sibling Chunks: {sibling_context}
            
            Candidate Paired SOP Chunks (for difference comparisons):
            {candidate_pairs}

            Determine the appropriate dynamic Node Type, dynamic relationships, and populate the properties dictionary with the GraphRAG optimization and provenance metadata based on the mandates above.
            Ensure you compare this chunk against candidate pairs to decide if a DEVIATES_FROM, COMPLIES_WITH, or similar relation applies.
            Provide detailed, audit-traceable rationales.
            """)
        ])

    def infer_relationships(self, chunk_id: str, chunk_content: str, 
                            parent_context: dict, sibling_context: list, 
                            candidate_pairs: list) -> SemanticNodeMapping:
        """Invokes LLM with structured output parsing to obtain semantic nodes and edges mapping."""
        # Retrieve client from dynamic provider config factory
        model = LLMFactory.get_chat_model()
        
        # Equip client with structured output schemas
        structured_llm = model.with_structured_output(SemanticNodeMapping)
        
        # Construct and call prompt chain
        chain = self.prompt_template | structured_llm
        result = chain.invoke({
            "chunk_id": chunk_id,
            "chunk_content": chunk_content,
            "parent_context": str(parent_context),
            "sibling_context": str(sibling_context),
            "candidate_pairs": str(candidate_pairs)
        })
        
        return result