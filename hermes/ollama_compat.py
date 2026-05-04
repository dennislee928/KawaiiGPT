import sys
import requests
import json

def ollama_pull_if_missing(model: str, host: str):
    """
    Pull the model if it isn't already downloaded in Ollama.
    Shared utility extracted from chat.py logic.
    """
    host = host.rstrip('/')
    tags_url = f"{host}/api/tags"
    
    try:
        resp = requests.get(tags_url, timeout=10)
        if resp.status_code != 200:
            print(f"\033[33mWarning: Received {resp.status_code} from Ollama tags API.\033[0m")
            return
            
        tags = resp.json()
        models = tags.get("models", [])
        
        # Check for exact match or base name match (e.g., 'hermes3:8b' vs 'hermes3')
        model_names = [m["name"] for m in models]
        model_bases = [m["name"].split(":")[0] for m in models]
        
        base_target = model.split(":")[0]
        
        if model not in model_names and base_target not in model_bases:
            print(f"\033[36m[Ollama]: Pulling model '{model}' (this may take a while)...\033[0m")
            
            # Using stream=True to potentially show progress or just wait
            pull_url = f"{host}/api/pull"
            with requests.post(pull_url, json={"name": model}, stream=True, timeout=None) as pull_resp:
                if pull_resp.status_code != 200:
                    print(f"\033[31mError pulling model: {pull_resp.text}\033[0m")
                    return

                for line in pull_resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            status = data.get("status", "")
                            # Only print major status changes to avoid spamming the console
                            if status and not any(x in status.lower() for x in ["downloading", "verifying", "pulling"]):
                                print(f"  [Ollama]: {status}")
                        except json.JSONDecodeError:
                            continue
                             
            print(f"\033[32m[Ollama]: Model '{model}' is now ready.\033[0m")
            
    except requests.exceptions.ConnectionError:
        print(f"\033[31mError: Cannot reach Ollama at {host}.\033[0m")
        print("Make sure Ollama is running (run `ollama serve` or check your Docker containers).")
        # In a real agent we might not want to exit(1) but for the CLI entrypoint it's appropriate
        sys.exit(1)
    except Exception as e:
        print(f"\033[33mWarning: Unexpected error checking Ollama models: {e}\033[0m")
