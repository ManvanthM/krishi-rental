import urllib.request
import re

url = "http://127.0.0.1:5000"
response = urllib.request.urlopen(url)
html = response.read().decode('utf-8')

# Let's count some elements and see how they are structured
print("HTML length:", len(html))
print("Container div count:", len(re.findall(r'class="[^"]*container[^"]*"', html)))
print("Landing-shell existence:", 'landing-shell' in html)
print("page-shell existence:", 'page-shell' in html)

# No headless browser here, so we just get raw HTML
