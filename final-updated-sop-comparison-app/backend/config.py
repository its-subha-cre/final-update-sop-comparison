import os
from dotenv import load_dotenv, dotenv_values

class Config:
    """Handles application configuration, allowing dynamic hot-reloads of env variables."""
    
    def __init__(self, root_dir=None):
        self.root_dir = root_dir or os.path.dirname(os.path.abspath(__file__))
        self.env_path = os.path.join(self.root_dir, '.env')
        self.load()

    def load(self):
        """Loads configuration variables from .env on disk."""
        # Ensure .env exists, if not, copy from .env.example
        if not os.path.exists(self.env_path):
            example_path = os.path.join(self.root_dir, '.env.example')
            if os.path.exists(example_path):
                with open(example_path, 'r') as f_in:
                    with open(self.env_path, 'w') as f_out:
                        f_out.write(f_in.read())

        # Load environment variables into os.environ
        load_dotenv(self.env_path, override=True)

        # Populate internal settings dict
        self.FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
        self.PORT = int(os.environ.get('PORT', 5000))
        self.NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        self.NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
        self.NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')
        self.LLM_PROVIDER = os.environ.get('LLM_PROVIDER', '')
        self.LLM_MODEL = os.environ.get('LLM_MODEL', '')
        self.GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
        self.OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
        self.ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
        self.DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
        self.AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY', '')
        self.AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT', '')
        self.OLLAMA_HOST = os.environ.get('OLLAMA_HOST', '')
        self.GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
        self.GROQ_TRANSLATION_API_KEY = os.environ.get('GROQ_TRANSLATION_API_KEY', '')
        self.TRANSLATION_MODEL = os.environ.get('TRANSLATION_MODEL', 'llama-3.1-8b-instant')

    def update_env_file(self, updates: dict):
        """Writes updates to the .env file and reloads configurations in-memory."""
        current_env = {}
        if os.path.exists(self.env_path):
            current_env = dotenv_values(self.env_path)

        # Merge updates
        for key, val in updates.items():
            current_env[key] = str(val)

        # Write back to .env
        with open(self.env_path, 'w') as f:
            for key, val in current_env.items():
                f.write(f"{key}={val}\n")
        
        # Reload configuration
        self.load()

    def is_configured(self):
        """Checks if LLM provider and corresponding API key are set."""
        if not self.LLM_PROVIDER:
            return False
        prov = self.LLM_PROVIDER.lower()
        if prov == 'gemini' and not self.GEMINI_API_KEY:
            return False
        if prov == 'openai' and not self.OPENAI_API_KEY:
            return False
        if prov == 'anthropic' and not self.ANTHROPIC_API_KEY:
            return False
        if prov == 'deepseek' and not self.DEEPSEEK_API_KEY:
            return False
        if prov == 'azure' and (not self.AZURE_OPENAI_API_KEY or not self.AZURE_OPENAI_ENDPOINT):
            return False
        if prov == 'ollama' and not self.OLLAMA_HOST:
            return False
        if prov == 'groq' and not self.GROQ_API_KEY:
            return False
        return True

    def update_config(self, provider, model, api_key, azure_endpoint=None, ollama_host=None):
        """Updates LLM configuration variables based on provider."""
        updates = {
            "LLM_PROVIDER": provider,
            "LLM_MODEL": model
        }
        prov = provider.lower()
        if prov == 'gemini':
            updates["GEMINI_API_KEY"] = api_key
        elif prov == 'openai':
            updates["OPENAI_API_KEY"] = api_key
        elif prov == 'anthropic':
            updates["ANTHROPIC_API_KEY"] = api_key
        elif prov == 'deepseek':
            updates["DEEPSEEK_API_KEY"] = api_key
        elif prov == 'azure':
            updates["AZURE_OPENAI_API_KEY"] = api_key
            if azure_endpoint:
                updates["AZURE_OPENAI_ENDPOINT"] = azure_endpoint
        elif prov == 'ollama':
            if ollama_host:
                updates["OLLAMA_HOST"] = ollama_host
        elif prov == 'groq':
            updates["GROQ_API_KEY"] = api_key
            
        self.update_env_file(updates)

# Global config instance
config_instance = Config()