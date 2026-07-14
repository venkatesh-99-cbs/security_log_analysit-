from app.ai.ollama_client import ChatService

service = ChatService()
print('base_url=', service.client.base_url)
print('availability=', service.client.is_available())
print('response=', service.respond('Hello', []))
