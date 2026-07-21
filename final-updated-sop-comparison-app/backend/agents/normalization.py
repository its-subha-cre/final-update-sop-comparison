from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.factory import LLMFactory

class SectionNormalizationAgent:
    """LLM Agent mapping local SOP section headers to a canonical list of Global Section titles."""

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a Section Normalization Agent. Your job is to map a local section heading 
            to one of the canonical global sections.
            
            Canonical Global Sections:
            {global_sections}
            
            Map the local heading as closely as possible. If it doesn't match any global section, 
            return "UNRESOLVED".
            """),
            ("user", "Local Section Heading: '{local_heading}'\nContent Preview: '{content_preview}'")
        ])

    def normalize_section(self, local_heading: str, content_preview: str, global_sections: list) -> str:
        """Invokes LLM to select the best canonical heading."""
        try:
            model = LLMFactory.get_chat_model()
            chain = self.prompt | model | StrOutputParser()
            result = chain.invoke({
                "global_sections": ", ".join(global_sections),
                "local_heading": local_heading,
                "content_preview": content_preview[:300]
            })
            return result.strip()
        except Exception as e:
            print(f"Section normalization failed: {e}. Falling back to original.")
            return "UNRESOLVED"
