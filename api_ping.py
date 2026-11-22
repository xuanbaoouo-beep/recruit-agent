import requests

r = requests.get("https://httpbin.org/json", timeout=10)
data = r.json()
print(data["slideshow"]["title"])

