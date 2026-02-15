#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Multi-Agent API Helpers — Source this in your .agent_env
# Usage: source /home/executive-workspace/apis/api_helpers.sh
# ══════════════════════════════════════════════════════════════

# Load API keys
if [ -f /home/executive-workspace/apis/keys.env ]; then
  set -a
  source /home/executive-workspace/apis/keys.env 2>/dev/null
  set +a
fi

# Currency
api_exchange_rate() { curl -sf "https://api.frankfurter.app/latest?from=${1:-USD}&to=${2:-EUR}"; }
api_convert() { curl -sf "https://api.frankfurter.app/latest?from=$1&to=$2&amount=$3"; }

# Crypto
api_crypto_price() { curl -sf "https://api.coingecko.com/api/v3/simple/price?ids=${1:-bitcoin}&vs_currencies=usd"; }
api_crypto_trending() { curl -sf "https://api.coingecko.com/api/v3/search/trending"; }

# Weather
api_weather() { curl -sf "https://wttr.in/${1:-New+York}?format=j1"; }
api_weather_oneliner() { curl -sf "https://wttr.in/${1:-New+York}?format=%C+%t+%h+%w"; }

# Data
api_country() { curl -sf "https://restcountries.com/v3.1/alpha/$1"; }
api_wikipedia() { curl -sf "https://en.wikipedia.org/api/rest_v1/page/summary/$(echo "$1" | sed 's/ /_/g')"; }
api_define() { curl -sf "https://api.dictionaryapi.dev/api/v2/entries/en/$1"; }

# News
api_hackernews() { curl -sf "https://hacker-news.firebaseio.com/v0/topstories.json" | python3 -c "import sys,json;[print(i) for i in json.load(sys.stdin)[:${1:-5}]]"; }

# Geo
api_geocode() { curl -sf "https://nominatim.openstreetmap.org/search?q=$(echo "$1" | sed 's/ /+/g')&format=json&limit=3" -H "User-Agent: AgentOS/1.0"; }
api_zipcode() { curl -sf "https://api.zippopotam.us/${1:-us}/$2"; }

# Legal
api_holidays() { curl -sf "https://date.nager.at/api/v3/PublicHolidays/${1:-2026}/${2:-US}"; }
api_fed_register() { curl -sf "https://www.federalregister.gov/api/v1/documents.json?conditions[term]=$(echo "$1" | sed 's/ /+/g')&per_page=5"; }

# Utilities
api_myip() { curl -sf https://icanhazip.com; }
api_ipinfo() { curl -sf "http://ip-api.com/json/$1"; }
api_qrcode() { echo "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=$(echo "$1" | sed 's/ /+/g')"; }

echo "📡 API helpers loaded. Run 'api_weather Boston' or 'api_crypto_price ethereum' to test."
