from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from llm.factory import LLMFactory

class ValidityAssessmentSchema(BaseModel):
    justified: bool = Field(
        description="True if the deviation is justified by site, equipment, or regulatory constraints, False otherwise."
    )
    justification_type: str = Field(
        description="One of: 'regulatory', 'equipment', 'site_specific', 'unjustified'."
    )
    rationale: str = Field(
        description="A clear audit-ready justification explanation citing the context factors."
    )

class ValidityAssessmentAgent:
    """LLM Agent that evaluates if a deviation is valid based on site/equipment/regulatory constraints."""

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a Compliance Auditor Agent. Your task is to review a deviation between 
            a Local SOP Clause and the Global SOP Standard, and determine if this deviation 
            is valid (justified) or invalid (unjustified).
            
            Valid reasons for deviations include:
            1. Regulatory constraints: Regional laws or local compliance standards.
            2. Equipment variation: The local site uses different machinery (e.g. a different X-ray model).
            3. Site-specific limitations: Environmental, staffing, or structural realities.
            
            Identify any relationships to Site/Equipment/Regulatory context nodes.
            """),
            ("user", """
            - Global SOP Clause: "{global_clause}"
            - Local SOP Clause: "{local_clause}"
            - Site Context: {site_context}
            - Equipment Context: {equipment_context}
            - Regulatory Context: {regulatory_context}
            
            Decide if the deviation is justified and specify why.
            """)
        ])

    def assess_validity(self, global_clause: str, local_clause: str, 
                        site_context: str, equipment_context: str, 
                        regulatory_context: str) -> ValidityAssessmentSchema:
        """Invokes LLM with structured output mapping to assess validity."""
        model = LLMFactory.get_chat_model()
        structured_llm = model.with_structured_output(ValidityAssessmentSchema)
        chain = self.prompt | structured_llm
        
        result = chain.invoke({
            "global_clause": global_clause,
            "local_clause": local_clause,
            "site_context": site_context,
            "equipment_context": equipment_context,
            "regulatory_context": regulatory_context
        })
        return result
