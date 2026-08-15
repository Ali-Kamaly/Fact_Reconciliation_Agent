import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

def test_claude_link():
    client = Anthropic(api_key = os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        #most cost efficient model
        model = "claude-haiku-4-5",
        max_tokens = 100,
        messages = [
            {
                "role": "user",
                "content": "Reply with exactly: Claude connection working"
            }
        ]
    )
    return message.content[0].text

print(test_claude_link)

def test_claude_web():
    client = Anthropic.anthropic