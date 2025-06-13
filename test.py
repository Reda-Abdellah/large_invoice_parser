import requests
import json

def test_ollama_remote(host_ip, port=11434, model="deepseek-r1:latest"):
    """
    Test Ollama API on a remote machine
    
    Args:
        host_ip (str): IP address of the remote machine running Ollama
        port (int): Port number (default: 11434)
        model (str): Model name to use
    """
    
    # Construct the API URL
    url = f"http://{host_ip}:{port}/api/generate"
    
    # Prepare the request payload
    payload = {
        "model": model,
        "prompt": "Hello! Can you tell me a short joke?",
        "stream": False  # Get single response instead of streaming
    }
    
    # Set headers
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Testing connection to Ollama at {host_ip}:{port}")
        print(f"Using model: {model}")
        print("-" * 50)
        
        # Send POST request
        response = requests.post(
            url, 
            headers=headers, 
            data=json.dumps(payload),
            timeout=30
        )
        
        # Check response status
        if response.status_code == 200:
            result = response.json()
            print("✅ Connection successful!")
            print(f"Response: {result['response']}")
            print(f"Model: {result['model']}")
            print(f"Total duration: {result.get('total_duration', 'N/A')} ns")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Make sure:")
        print("1. Ollama is running on the remote machine")
        print("2. Firewall allows connections on port 11434")
        print("3. The IP address is correct")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def check_available_models(host_ip, port=11434):
    """Check what models are available on the remote Ollama instance"""
    
    url = f"http://{host_ip}:{port}/api/tags"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            models = response.json()
            print("Available models:")
            for model in models.get('models', []):
                print(f"  - {model['name']}")
        else:
            print(f"Failed to get models: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error checking models: {e}")
import os
os.environ['NO_PROXY'] = "http://127.0.0.1,localhost,http://10.8.13.21"
if __name__ == "__main__":
    # Replace with your remote machine's IP address
    REMOTE_IP = "10.8.13.21"  # Change this to your remote machine's IP
    
    # First, check available models
    print("Checking available models...")
    check_available_models(REMOTE_IP)
    print()
    
    # Test with default model
    test_ollama_remote(REMOTE_IP)
