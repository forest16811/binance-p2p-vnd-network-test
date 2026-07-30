import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

BINANCE_URL = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
CALLBACK_URL = 'https://binance-vnd-telegram-bot.forest16811.workers.dev/github-result'

def post_json(url, payload, headers):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.read().decode('utf-8')

try:
    payload = {'page': 1, 'rows': 10, 'payTypes': [], 'countries': [], 'publisherType': None, 'asset': 'USDT', 'fiat': 'VND', 'tradeType': 'BUY'}
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*', 'Origin': 'https://p2p.binance.com', 'Referer': 'https://p2p.binance.com/', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36'}
    status, raw = post_json(BINANCE_URL, payload, headers)
    print(f'BINANCE_HTTP_STATUS={status}')
    data = json.loads(raw)
    quotes = []
    for item in data.get('data', [])[:10]:
        price = float(item.get('adv', {}).get('price', 0))
        merchant = str(item.get('advertiser', {}).get('nickName', '')).strip()
        if price > 0 and merchant:
            quotes.append((price, merchant))
    quotes.sort(key=lambda row: row[0])
    if not quotes:
        raise RuntimeError('Binance returned no usable advertisements')
    now = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
    lines = ['🇻🇳 Binance VND 买入 USDT｜TOP 10', f'🕒 {now}', '']
    medals = ['🥇', '🥈', '🥉']
    for index, (price, merchant) in enumerate(quotes, 1):
        rank = medals[index - 1] if index <= 3 else f'{index:02d}'
        lines.append(f'{rank}  {price:,.0f} VND  {merchant}')
    low_price = quotes[0][0]
    high_price = quotes[-1][0]
    lines.extend(['', f'📌 1 USDT ≈ {low_price:,.0f}–{high_price:,.0f} VND', '📊 价格由低到高排列'])
    reply_text = '\n'.join(lines)
except Exception as error:
    reply_text = f'Binance报价暂时无法获取，请稍后再试。\n错误信息：{error}'

params = urllib.parse.urlencode({'secret': os.environ['CALLBACK_SECRET'], 'chat_id': os.environ['CHAT_ID'], 'request_id': os.environ['REQUEST_ID'], 'text': reply_text})
request = urllib.request.Request(CALLBACK_URL + '?' + params, headers={'User-Agent': 'Mozilla/5.0 GitHub-Actions-Binance-VND-Bot/1.0'}, method='GET')
with urllib.request.urlopen(request, timeout=30) as response:
    print(f'CALLBACK_HTTP_STATUS={response.status}')
    print(response.read().decode('utf-8')[:500])
