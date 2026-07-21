from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from llm.factory import LLMFactory

class LLMChunk(BaseModel):
    id: str = Field(description="A unique alphanumeric identifier for this chunk (e.g., chunk_1).")
    label: str = Field(description="The dynamic node label/type decided by the LLM (e.g., Section, Clause, Requirement, Control, SafetyRule, Role, Constraint).")
    content: str = Field(description="The actual text content segment of this chunk.")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Key-value properties to store (e.g., title, number, site, equipment).")

class LLMChunkingResult(BaseModel):
    chunks: List[LLMChunk] = Field(description="The complete list of logical chunks identified in the text.")

# Explicit, flat schemas without open-ended dictionaries to guarantee 100% tool-use reliability on Groq API
class _LLMChunk(BaseModel):
    id: str = Field(description="A unique alphanumeric identifier for this chunk (e.g., chunk_1).")
    label: str = Field(description="The dynamic node label/type decided by the LLM (e.g., Section, Clause, Requirement, Control, SafetyRule, Role, Constraint).")
    content: str = Field(description="The actual text content segment of this chunk.")
    clause_number: Optional[str] = Field(None, description="The section or clause number if visible in the text (e.g., '1', '2.1', 'GSOP-XRAY-001').")

class _LLMChunkingResult(BaseModel):
    chunks: List[_LLMChunk] = Field(description="The complete list of logical chunks identified in the text.")

class LLMChunkerAgent:
    """LLM Ingestion Agent that reads raw text and dynamically decides how to partition it into nodes."""

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an expert Document Decomposition Agent. 
            Read the raw document text and partition it into logical chunks/nodes.
            
            You must dynamically decide:
            1. The boundaries of each chunk.
            2. The appropriate Node Label/Type (e.g., Section, Clause, Requirement, SafetyControl, Role, Constraint, etc.).
            3. Extract the clause or section number if it is present at the start of the chunk.
            
            Make sure to capture the entire document without omitting details.
            """),
            ("user", "Document Title: {doc_title}\n\nRaw Text:\n{raw_text}")
        ])

    def chunk_document_with_llm(self, doc_title: str, raw_text: str) -> LLMChunkingResult:
        """Invokes LLM with structured output mapping to dynamically define nodes/chunks."""
        model = LLMFactory.get_chat_model()
        structured_llm = model.with_structured_output(_LLMChunkingResult)
        chain = self.prompt | structured_llm
        
        raw_result = chain.invoke({
            "doc_title": doc_title,
            "raw_text": raw_text[:8000]  # Limit context window to prevent truncation errors in basic runs
        })
        
        # Convert flat _LLMChunkingResult back to public LLMChunkingResult with Dict properties
        final_chunks = []
        for c in raw_result.chunks:
            prop_dict = {}
            if c.clause_number:
                prop_dict["number"] = c.clause_number
            else:
                prop_dict["number"] = "Generic"
                
            final_chunks.append(LLMChunk(
                id=c.id,
                label=c.label,
                content=c.content,
                properties=prop_dict
            ))
            
        return LLMChunkingResult(chunks=final_chunks)