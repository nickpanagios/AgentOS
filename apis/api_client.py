#!/usr/bin/env python3
"""
Multi-Agent API Client Library
Usage:
    from api_client import APIClient
    api = APIClient()
    
    # Currency conversion
    rates = api.get_exchange_rates(base="USD")
    
    # Weather
    weather = api.get_weather(lat=40.71, lon=-74.01)
    
    # Crypto prices
    btc = api.get_crypto_price("bitcoin")
    
    # Search Wikipedia
    results = api.search_wikipedia("artificial intelligence")
    
    # Country data
    country = api.get_country("US")
    
    # All available APIs
    catalog = api.list_apis()
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error

REGISTRY_PATH = "/home/executive-workspace/apis/registry.json"
KEYS_PATH = "/home/executive-workspace/apis/keys.env"

class APIClient:
    def __init__(self):
        with open(REGISTRY_PATH) as f:
            self.registry = json.load(f)
        self.keys = self._load_keys()
    
    def _load_keys(self):
        keys = {}
        try:
            with open(KEYS_PATH) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        if v and not v.startswith('#'):
                            keys[k.strip()] = v.strip()
        except: pass
        return keys
    
    def _get(self, url, headers=None):
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "AgentOS/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "url": url}
        except Exception as e:
            return {"error": str(e), "url": url}
    
    def list_apis(self, category=None):
        """List all available APIs, optionally filtered by category."""
        result = {}
        cats = self.registry.get("categories", {})
        for cat_name, cat_data in cats.items():
            if category and cat_name != category:
                continue
            apis = {}
            for api_id, api_info in cat_data.get("apis", {}).items():
                apis[api_id] = {
                    "name": api_info.get("name"),
                    "description": api_info.get("description"),
                    "auth": api_info.get("auth", "none"),
                    "url": api_info.get("url")
                }
            result[cat_name] = {"owner": cat_data.get("owner_team"), "apis": apis}
        return result
    
    # ── Finance & Currency ──────────────────────────────────
    
    def get_exchange_rates(self, base="USD", symbols=None):
        url = f"https://api.frankfurter.app/latest?from={base}"
        if symbols:
            url += f"&to={','.join(symbols)}"
        return self._get(url)
    
    def convert_currency(self, amount, from_cur, to_cur):
        url = f"https://api.frankfurter.app/latest?from={from_cur}&to={to_cur}&amount={amount}"
        return self._get(url)
    
    def get_crypto_price(self, coin_id="bitcoin", vs="usd"):
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={vs}&include_24hr_change=true"
        return self._get(url)
    
    def get_crypto_trending(self):
        return self._get("https://api.coingecko.com/api/v3/search/trending")
    
    def get_crypto_market(self, limit=10):
        return self._get(f"https://api.coincap.io/v2/assets?limit={limit}")
    
    # ── Weather ─────────────────────────────────────────────
    
    def get_weather(self, lat, lon, hourly=False):
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        if hourly:
            url += "&hourly=temperature_2m,precipitation,windspeed_10m"
        return self._get(url)
    
    def get_weather_by_city(self, city):
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        return self._get(url)
    
    # ── Data & Reference ────────────────────────────────────
    
    def get_country(self, code):
        return self._get(f"https://restcountries.com/v3.1/alpha/{code}")
    
    def search_countries(self, name):
        return self._get(f"https://restcountries.com/v3.1/name/{urllib.parse.quote(name)}")
    
    def search_wikipedia(self, query, limit=5):
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
        return self._get(url)
    
    def get_definition(self, word):
        return self._get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}")
    
    def find_words(self, rel_type, word):
        """rel_type: syn (synonym), rhy (rhyme), trg (trigger), ant (antonym)"""
        return self._get(f"https://api.datamuse.com/words?rel_{rel_type}={urllib.parse.quote(word)}&max=10")
    
    # ── News & Media ────────────────────────────────────────
    
    def get_hacker_news(self, story_type="top", limit=10):
        ids = self._get(f"https://hacker-news.firebaseio.com/v0/{story_type}stories.json")
        if isinstance(ids, list):
            stories = []
            for sid in ids[:limit]:
                s = self._get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                if isinstance(s, dict):
                    stories.append({"title": s.get("title"), "url": s.get("url"), "score": s.get("score")})
            return stories
        return ids
    
    # ── Geocoding ───────────────────────────────────────────
    
    def geocode(self, address):
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address)}&format=json&limit=3"
        return self._get(url)
    
    def reverse_geocode(self, lat, lon):
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        return self._get(url)
    
    def zip_lookup(self, country, zipcode):
        return self._get(f"https://api.zippopotam.us/{country}/{zipcode}")
    
    # ── Legal & Government ──────────────────────────────────
    
    def get_public_holidays(self, year, country_code):
        return self._get(f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}")
    
    def search_federal_register(self, term, per_page=10):
        url = f"https://www.federalregister.gov/api/v1/documents.json?conditions[term]={urllib.parse.quote(term)}&per_page={per_page}"
        return self._get(url)
    
    # ── Science ─────────────────────────────────────────────
    
    def get_nasa_apod(self):
        key = self.keys.get("NASA_API_KEY", "DEMO_KEY")
        return self._get(f"https://api.nasa.gov/planetary/apod?api_key={key}")
    
    def get_world_bank_indicator(self, country, indicator):
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=10"
        return self._get(url)
    
    # ── Utilities ───────────────────────────────────────────
    
    def get_my_ip(self):
        req = urllib.request.Request("https://icanhazip.com")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode().strip()
    
    def get_ip_info(self, ip=None):
        url = f"http://ip-api.com/json/{ip}" if ip else "http://ip-api.com/json/"
        return self._get(url)


if __name__ == "__main__":
    api = APIClient()
    print("=== API Registry Loaded ===")
    for cat, info in api.list_apis().items():
        print(f"  {cat} ({info['owner']}): {len(info['apis'])} APIs")
    print(f"\n=== Quick Test ===")
    print(f"IP: {api.get_my_ip()}")
    rates = api.get_exchange_rates("USD", ["EUR", "GBP", "JPY"])
    print(f"USD rates: {rates.get('rates', {})}")
