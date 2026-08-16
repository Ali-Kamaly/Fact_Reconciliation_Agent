from tools.local_population import get_local_population
from tools.world_bank import get_wb_population
from tools.web_population import get_web_population

def main():
    local = get_local_population("BGD")
    api = get_wb_population("BGD")
    web = get_web_population("BGD")

    print(local)
    print(api)
    print(web)

    print(local.keys())
    print(api.keys())
    print(web.keys())

if __name__ == "__main__":
    main()