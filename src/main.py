from agent import run_agent
from tools.local_population import get_country_code

def main():
    country_name = input("Enter a country: ").strip()
    country_code = get_country_code(country_name)

    if country_code is None:
        print(f"Country {country_name} is not found")
        return None
    
    result = run_agent(country_name, country_code)
    answer = result["answer"]

    if answer['population'] is None:
        print("\n=== Final Answer ===")
        print(f"Country: {answer['country']}")
        print("Population: unavailable")
        print(f"Confidence: {answer['confidence']}")
        print(f"\n{answer['explanation']}")
        return

    print("\n=== Final Answer ===")
    print(f"Country: {answer['country']}")
    print(f"Population: {answer['population']:,}")
    print(f"Year: {answer['year']}")
    print(f"Source: {answer['publisher']}")
    print(f"Source quality: {answer['source_quality']}")
    print(f"Confidence: {answer['confidence']}")
    print(f"\n{answer['explanation']}")

if __name__ == "__main__":
    main()
