import requests
import json
import time

# Base URL for the API
BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

def print_response(response, title="Response"):
    print(f"\n[{title}] Status: {response.status_code}")
    try:
        print(f"Data: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Raw content: {response.text}")

def demo_chat_interface():
    """Demonstrate the complete chat interface functionality"""
    
    print_section("CHAT INTERFACE API DEMO")
    
    # 1. Check API health
    print_section("1. Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response, "Health Check")
    
    # 2. Create a user
    print_section("2. Create User")
    user_data = {
        "username": f"demo_user_{int(time.time())}",
        "email": f"demo_{int(time.time())}@example.com"
    }
    response = requests.post(f"{BASE_URL}/users", json=user_data)
    print_response(response, "User Creation")
    
    if response.status_code != 200:
        print("❌ Failed to create user. Stopping demo.")
        return
    
    user = response.json()
    user_id = user["id"]
    print(f"✅ Created user with ID: {user_id}")
    
    # 3. Start a chat conversation
    print_section("3. Start Chat Conversation")
    chat_data = {
        "message": "Hello! Can you help me understand what you can do?",
        "user_id": user_id
    }
    response = requests.post(f"{BASE_URL}/chat", json=chat_data)
    print_response(response, "Chat Response")
    
    if response.status_code != 200:
        print("❌ Failed to start chat. Continuing with other demos...")
    else:
        chat_response = response.json()
        conversation_id = chat_response["conversation"]["id"]
        print(f"✅ Started conversation with ID: {conversation_id}")
        
        # 4. Continue the conversation
        print_section("4. Continue Conversation")
        chat_data = {
            "message": "What's the weather like today?",
            "user_id": user_id,
            "conversation_id": conversation_id
        }
        response = requests.post(f"{BASE_URL}/chat", json=chat_data)
        print_response(response, "Continued Chat")
        
        # 5. Get conversation history
        print_section("5. Get Conversation History")
        response = requests.get(f"{BASE_URL}/conversations/{conversation_id}/messages")
        print_response(response, "Conversation History")
    
    # 6. Create a manual conversation
    print_section("6. Create Manual Conversation")
    conv_data = {"title": "Manual Test Conversation"}
    response = requests.post(f"{BASE_URL}/conversations?user_id={user_id}", json=conv_data)
    print_response(response, "Manual Conversation")
    
    if response.status_code == 200:
        manual_conv = response.json()
        manual_conv_id = manual_conv["id"]
        
        # 7. Add manual message
        print_section("7. Add Manual Message")
        message_data = {"content": "This is a manually added message"}
        response = requests.post(f"{BASE_URL}/conversations/{manual_conv_id}/messages", json=message_data)
        print_response(response, "Manual Message")
    
    # 8. Get all user conversations
    print_section("8. Get All User Conversations")
    response = requests.get(f"{BASE_URL}/users/{user_id}/conversations")
    print_response(response, "User Conversations")
    
    # 9. Get user details
    print_section("9. Get User Details")
    response = requests.get(f"{BASE_URL}/users/{user_id}")
    print_response(response, "User Details")
    
    # 10. Test file upload (create a sample file)
    print_section("10. File Upload Demo")
    try:
        # Create a sample text file
        sample_content = "Hello, this is a sample file for testing upload functionality!"
        files = {
            'file': ('sample.txt', sample_content, 'text/plain')
        }
        response = requests.post(f"{BASE_URL}/upload", files=files)
        print_response(response, "File Upload")
        
        if response.status_code == 200:
            file_info = response.json()
            file_id = file_info["id"]
            
            # Get file info
            print_section("11. Get File Info")
            response = requests.get(f"{BASE_URL}/files/{file_id}")
            print_response(response, "File Info")
    except Exception as e:
        print(f"❌ File upload demo failed: {e}")
    
    print_section("DEMO COMPLETED")
    print("✅ Chat Interface API demo completed successfully!")
    print("\nAvailable endpoints:")
    print("- POST /users - Create user")
    print("- GET /users/{user_id} - Get user")
    print("- POST /chat - Chat with AI")
    print("- POST /conversations - Create conversation")
    print("- GET /conversations/{id}/messages - Get chat history")
    print("- POST /upload - Upload file")
    print("- GET /health - Health check")
    print("\n📖 See api.py for complete endpoint documentation")

if __name__ == "__main__":
    try:
        demo_chat_interface()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server.")
        print("💡 Please ensure the server is running with: python api.py")
    except Exception as e:
        print(f"❌ Demo failed with error: {e}") 