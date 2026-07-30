import json
import os
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

BINANCE_URL = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
CALLBACK_URL = 'https://binance-vnd-telegram-bot.forest16811.workers.dev/github-result'

def post_json(url, payload, headers):
    data = json.dumps(payload).encode('utf-8')
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
    lines = ['Binance商家实时越南盾购买USDT Top10', f'查询时间：{now}', '']
    for index, (price, merchant) in enumerate(quotes, 1):
        lines.append(f'{index}) {price:,.0f}  {merchant}')
    reply_text = '\n'.join(lines)
except Exception as error:
    reply_text = f'Binance报价暂时无法获取，请稍后再试。\n错误信息：{error}'

callback_payload = {'chat_id': os.environ['CHAT_ID'], 'request_id': os.environ['REQUEST_ID'], 'text': reply_text}
callback_headers = {'Content-Type': 'application/json', 'x-callback-secret': os.environ['CALLBACK_SECRET']} 
status, raw = post_json(CALLBACK_URL, callback_payload, callback_headers)
print(f'CALLBACK_HTTP_STATUS={status}')
print(raw[:500])
