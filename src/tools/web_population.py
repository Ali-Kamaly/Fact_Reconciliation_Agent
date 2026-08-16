import os
from dotenv import load_dotenv
from anthropic import Anthropic
import json

def get_web_population(country, excluded_urls = None):
    load_dotenv()
    client = Anthropic(api_key = os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""
    Search the web for one recent population estimate for {country}.

    Choose one single webpage as the evidence source.
    Prefer an authoritative or well-established source.
    Do not use any urls that are in {excluded_urls}.
    Do not combine population figures from multiple webpages.

    Identify:
    - the population figure
    - the year that figure represents
    - the publisher of the webpage
    - the underlying provenance of the population data, if stated
    - the URL of the webpage

    If the underlying provenance cannot be determined, report it as unknown.
    """

    message = client.messages.create(
        model = "claude-haiku-4-5",
        max_tokens = 500,
        messages = [
            {"role": "user",
            "content": prompt
            }
        ],
        tools = [
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 2
                    }
        ],
        output_config = {
            #forcing required structure of data output by Claude 
            #can easily convert to python dictionary 
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "population": {
                            "type": "integer"
                        },
                        "year": {
                            "type": "integer"
                        },
                        "publisher": {
                            "type": "string"
                        },
                        "provenance": {
                            "type": "string"
                        },
                        "url": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "population",
                        "year",
                        "publisher",
                        "provenance",
                        "url"
                    ],
                    "additionalProperties": False
                    }
                }
            }
    )
    web_evidence = json.loads(message.content[-1].text)
    #-1 since web search contains messages of tools used etc. which are irrelevant

    return web_evidence

if __name__ == "__main__":
    print(get_web_population("Bangladesh"))
    print(get_web_population("Bangladesh", excluded_urls=['https://www.worldometers.info/world-population/bangladesh-population/']))