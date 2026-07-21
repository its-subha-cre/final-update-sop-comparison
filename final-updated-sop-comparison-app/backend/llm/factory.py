import os
from langchain_core.language_models.chat_models import BaseChatModel

class LLMFactory:
    """Factory to generate provider-agnostic LLM chat clients based on dynamic config."""
    
    @staticmethod
    def get_chat_model(provider: str = None, model: str = None, api_key: str = None, azure_endpoint: str = None, ollama_host: str = None) -> BaseChatModel:
        """
        Instantiates a LangChain-compatible Chat Model.
        If parameters are not provided, reads them from the global config_instance.
        """
        from config import config_instance
        
        provider = provider or config_instance.LLM_PROVIDER
        model = model or config_instance.LLM_MODEL
        
        provider = provider.lower() if provider else ""
        
        if provider == 'gemini':
            from langchain_google_genai import ChatGoogleGenerativeAI
            key = api_key or config_instance.GEMINI_API_KEY
            if not key:
                raise ValueError("GEMINI_API_KEY is missing. Please set it in the Setup Wizard.")
            return ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                google_api_key=key,
                temperature=0.0
            )
            
        elif provider == 'openai':
            from langchain_openai import ChatOpenAI
            key = api_key or config_instance.OPENAI_API_KEY
            if not key:
                raise ValueError("OPENAI_API_KEY is missing. Please set it in the Setup Wizard.")
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                openai_api_key=key,
                temperature=0.0
            )

        elif provider == 'deepseek':
            from langchain_openai import ChatOpenAI
            key = api_key or config_instance.DEEPSEEK_API_KEY
            if not key:
                raise ValueError("DEEPSEEK_API_KEY is missing. Please set it in the Setup Wizard.")
            return ChatOpenAI(
                model=model or "deepseek-chat",
                openai_api_key=key,
                openai_api_base="https://api.deepseek.com/v1",
                temperature=0.0
            )

        elif provider == 'azure':
            from langchain_openai import AzureChatOpenAI
            key = api_key or config_instance.AZURE_OPENAI_API_KEY
            endpoint = azure_endpoint or config_instance.AZURE_OPENAI_ENDPOINT
            if not key or not endpoint:
                raise ValueError("AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT is missing. Please set it in the Setup Wizard.")
            return AzureChatOpenAI(
                azure_deployment=model or "gpt-4o",
                azure_endpoint=endpoint,
                api_key=key,
                api_version="2024-02-01",
                temperature=0.0
            )

        elif provider == 'ollama':
            from langchain_community.chat_models import ChatOllama
            host = ollama_host or config_instance.OLLAMA_HOST
            if not host:
                raise ValueError("OLLAMA_HOST is missing. Please set it in the Setup Wizard.")
            return ChatOllama(
                model=model or "llama3",
                base_url=host,
                temperature=0.0
            )

        elif provider == 'groq':
            from langchain_groq import ChatGroq
            key = api_key or config_instance.GROQ_API_KEY
            if not key:
                raise ValueError("GROQ_API_KEY is missing. Please set it in the Setup Wizard.")
            return ChatGroq(
                model=model or "llama-3.1-8b-instant",
                groq_api_key=key,
                temperature=0.0
            )
            
        elif provider == 'anthropic':
            from langchain_anthropic import ChatAnthropic
            key = api_key or config_instance.ANTHROPIC_API_KEY
            if not key:
                raise ValueError("ANTHROPIC_API_KEY is missing. Please set it in the Setup Wizard.")
            return ChatAnthropic(
                model=model or "claude-3-5-sonnet-20240620",
                anthropic_api_key=key,
                temperature=0.0
            )
            
        else:
            raise ValueError(
                f"Unsupported or unconfigured LLM provider: '{provider}'. "
                "Please configure a valid provider using the Setup Wizard."
            )

    @staticmethod
    def test_connection(provider: str, model: str, api_key: str, azure_endpoint: str = None, ollama_host: str = None) -> bool:
        try:
            chat = LLMFactory.get_chat_model(
                provider=provider,
                model=model,
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                ollama_host=ollama_host
            )

            response = chat.invoke("Reply with only the word OK.")

            content = response.content

            if isinstance(content, list):
                text = " ".join(
                    item.get("text", str(item))
                    if isinstance(item, dict)
                    else str(item)
                    for item in content
                )
            else:
                text = str(content)

            text = text.strip()

            return len(text) > 0

        except Exception as e:
            raise RuntimeError(
                f"Connection test failed for {provider}/{model}: {e}"
            )