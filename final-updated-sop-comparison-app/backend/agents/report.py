from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from llm.factory import LLMFactory

class RecommendationReportSchema(BaseModel):
    summary: str = Field(description="High-level summary of the comparison findings.")
    similarity_score: float = Field(description="Overall similarity score from 0 to 100.")
    necessity_score: float = Field(description="Local Necessity Score from 0 to 100.")
    recommendations: list = Field(
        description="List of recommendations per clause. Each item must have: clause_number, action ('keep', 'retire', 'merge', 'appendix', 'SME review'), and justification."
    )

class ReportOrchestrationAgent:
    """Assembles final rationalization report and action items based on accumulated graph facts."""

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a Senior Regulatory Analyst. Review the comparison findings between the Global SOP 
            and the Local SOP, and generate a structured Recommendation Report.
            
            For each clause difference, recommend one of these actions:
            - 'keep': If the local deviation is fully justified by site conditions.
            - 'retire': If the local deviation is unjustified and should match the Global SOP.
            - 'merge': If the local clause has unique language that should be merged back into the Global SOP.
            - 'appendix': Move to local site appendix.
            - 'SME review': Flags high risk or complex differences that require human expert verification.
            """),
            ("user", """
            - Global SOP: {global_name}
            - Local SOP: {local_name}
            
            Comparison Data Summary:
            - Similarity Score: {similarity_score}
            - Necessity Score: {necessity_score}
            - Mapped Differences & Valdity List:
            {deviations_list}
            
            Generate the recommendation report.
            """)
        ])

    def generate_report(self, global_name: str, local_name: str, 
                        similarity_score: float, necessity_score: float, 
                        deviations_list: list) -> RecommendationReportSchema:
        """Invokes LLM to construct recommendations."""
        model = LLMFactory.get_chat_model()
        structured_llm = model.with_structured_output(RecommendationReportSchema)
        chain = self.prompt | structured_llm
        
        result = chain.invoke({
            "global_name": global_name,
            "local_name": local_name,
            "similarity_score": similarity_score,
            "necessity_score": necessity_score,
            "deviations_list": str(deviations_list)
        })
        return result
