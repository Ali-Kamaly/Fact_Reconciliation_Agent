import os
from dotenv import load_dotenv
import anthropic
#from anthropic import Anthropic
import json

WEB_RETRIEVAL_TYPE = "web_search"

def get_web_population(country, excluded_urls = None):
    try:
        load_dotenv()
        client = anthropic.Anthropic(api_key = os.getenv("ANTHROPIC_API_KEY"), timeout=15.0)

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

        web_evidence["retrieval_type"] = WEB_RETRIEVAL_TYPE
        web_evidence["last_updated"] = None
        web_evidence["status"] = "success"
        web_evidence["error"] = None

        return web_evidence

    except anthropic.APITimeoutError:
        return failed_web_request("Claude web request timed out")

    except anthropic.APIConnectionError as error:
        return failed_web_request(f"Could not connect to Anthropic API: {error}")

    except json.JSONDecodeError as error:
        return failed_web_request(f"Claude returned invalid JSON: {error}")

def failed_web_request(error_message):
    return {
        "retrieval_type": WEB_RETRIEVAL_TYPE,
        "population": None,
        "year": None,
        "publisher": None,
        "provenance": None,
        "url": None,
        "last_updated": None,
        "status": "failed",
        "error": error_message
    }


if __name__ == "__main__":
    print(get_web_population("Bangladesh"))
    print(get_web_population("Bangladesh", excluded_urls=['https://www.worldometers.info/world-population/bangladesh-population/']))