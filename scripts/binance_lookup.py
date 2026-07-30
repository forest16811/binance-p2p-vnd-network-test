import json
import os
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

BINANCE_URL = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'

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
    lines = ['Binance商家实时越南盾购买USDT Top10', f'查询时间：{now}', '']
    for index, (price, merchant) in enumerate(quotes, 1):
        lines.append(f'{index}) {price:,.0f}  {merchant}')
    reply_text = '\n'.join(lines)
except Exception as error:
    reply_text = f'Binance报价暂时无法获取，请稍后再试。\n错误信息：{error}'

telegram_url = f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/sendMessage"
telegram_payload = {'chat_id': os.environ['CHAT_ID'], 'text': reply_text, 'disable_web_page_preview': True}
status, raw = post_json(telegram_url, telegram_payload, {'Content-Type': 'application/json', 'User-Agent': 'Binance-VND-GitHub-Bot/1.0'})
print(f'TELEGRAM_HTTP_STATUS={status}')
print(raw[:500])
