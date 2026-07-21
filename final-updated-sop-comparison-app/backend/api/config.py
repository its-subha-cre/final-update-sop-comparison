from flask import Blueprint, request, jsonify
from config import config_instance
from llm.factory import LLMFactory

config_bp = Blueprint('config', __name__)

@config_bp.route('/status', methods=['GET'])
def get_config_status():
    """Checks whether a valid LLM provider and API key are configured."""
    provider = config_instance.LLM_PROVIDER
    has_key = False
    
    if provider == 'gemini' and config_instance.GEMINI_API_KEY:
        has_key = True
    elif provider == 'openai' and config_instance.OPENAI_API_KEY:
        has_key = True
    elif provider == 'anthropic' and config_instance.ANTHROPIC_API_KEY:
        has_key = True
    elif provider == 'deepseek' and config_instance.DEEPSEEK_API_KEY:
        has_key = True
    elif provider == 'azure' and config_instance.AZURE_OPENAI_API_KEY and config_instance.AZURE_OPENAI_ENDPOINT:
        has_key = True
    elif provider == 'ollama' and config_instance.OLLAMA_HOST:
        has_key = True
    elif provider == 'groq' and config_instance.GROQ_API_KEY:
        has_key = True
        
    return jsonify({
        "configured": bool(provider and has_key),
        "provider": provider,
        "model": config_instance.LLM_MODEL,
        "azureEndpoint": config_instance.AZURE_OPENAI_ENDPOINT,
        "ollamaHost": config_instance.OLLAMA_HOST
    })

@config_bp.route('/test', methods=['POST'])
def test_connection_endpoint():
    """Fires a lightweight connection test for the chosen provider, model, and key."""
    data = request.json or {}
    provider = data.get('provider')
    model = data.get('model')
    api_key = data.get('apiKey')
    azure_endpoint = data.get('azureEndpoint')
    ollama_host = data.get('ollamaHost')
    
    # Ollama doesn't require an API key, so we bypass strict API key checks for it
    if provider.lower() != 'ollama' and (not provider or not model or not api_key):
        return jsonify({
            "success": False, 
            "message": "Missing provider, model, or API key parameters."
        }), 400
    
    if provider.lower() == 'ollama' and not ollama_host:
        return jsonify({
            "success": False,
            "message": "Ollama provider requires a Host URL."
        }), 400
        
    try:
        success = LLMFactory.test_connection(provider, model, api_key, azure_endpoint, ollama_host)
        return jsonify({
            "success": success,
            "message": "Connection test succeeded!" if success else "Connection test returned an empty response."
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

@config_bp.route('/save', methods=['POST'])
def save_config_endpoint():
    """Saves verified LLM credentials to .env file and updates configuration in-memory."""
    data = request.json or {}
    provider = data.get('provider')
    model = data.get('model')
    api_key = data.get('apiKey')
    azure_endpoint = data.get('azureEndpoint')
    ollama_host = data.get('ollamaHost')
    
    if provider.lower() != 'ollama' and (not provider or not model or not api_key):
        return jsonify({
            "success": False, 
            "message": "Missing provider, model, or API key parameters."
        }), 400
        
    # Map provider to specific key variable
    key_mapping = {
        'gemini': 'GEMINI_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'deepseek': 'DEEPSEEK_API_KEY',
        'azure': 'AZURE_OPENAI_API_KEY',
        'groq': 'GROQ_API_KEY'
    }
    
    env_key = key_mapping.get(provider.lower())
    if provider.lower() != 'ollama' and not env_key:
        return jsonify({
            "success": False,
            "message": f"Unsupported provider name: {provider}"
        }), 400
        
    updates = {
        'LLM_PROVIDER': provider.lower(),
        'LLM_MODEL': model
    }
    
    if env_key:
        updates[env_key] = api_key
    
    if provider.lower() == 'azure' and azure_endpoint:
        updates['AZURE_OPENAI_ENDPOINT'] = azure_endpoint
        
    if provider.lower() == 'ollama' and ollama_host:
        updates['OLLAMA_HOST'] = ollama_host
        
    try:
        config_instance.update_env_file(updates)
        return jsonify({
            "success": True,
            "message": "Configuration successfully saved to backend/.env and reloaded."
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to save configuration: {str(e)}"
        }), 500
