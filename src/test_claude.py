import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key = os.getenv("ANTHROPIC_API_KEY"))

def test_claude_link():
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

#print(test_claude_link())

def test_claude_web():
    message = client.messages.create(
        model = "claude-haiku-4-5",
        max_tokens = 500,
        messages = [
            {"role": "user",
            "content": (
                "Search the web for the latest available population "
                "of Bangladesh. Tell me the population, the year the "
                "figure represents, and the source."
            )
        }
        ],
        tools = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 3
            }
        ]

    )
    return message

print(test_claude_web())