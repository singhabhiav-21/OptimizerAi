import requests
from datetime import datetime, timedelta

class Currency:
    def __init__(self, base_url='https://api.exchangerate-api.com/v4/latest', base_currency = 'USD'):
        self.base_url = base_url
        self.base_currency = base_currency
        self.cache = {}
        self.time_out = timedelta(hours=1)
        self._update_cache()

    def _update_cache(self):
        try:
            url = f"{self.base_url}/{self.base_currency}"
            response = requests.get(url, timeout = 10)
            data = response.json()

            
