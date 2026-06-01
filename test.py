import requests
TOKEN = "8683465806:AAF-s71vva9cWffI-MS2UORmn9lRcY7PqFk"
url = f"https://api.telegram.org/bot{TOKEN}/getMe"
print(requests.get(url).json())
