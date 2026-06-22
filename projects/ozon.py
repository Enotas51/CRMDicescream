import json
import re
from decimal import Decimal, InvalidOperation
from html import unescape
from urllib.parse import unquote, urlparse

import requests


class OzonFetchError(Exception):
  pass


HEADERS = {
  'User-Agent': (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
  ),
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
  'Cache-Control': 'no-cache',
  'Pragma': 'no-cache',
}


def extract_ozon_path(url: str) -> str:
  url = (url or '').strip()
  if not url:
    raise OzonFetchError('Укажите ссылку на товар OZON')
  if not url.startswith('http'):
    url = 'https://' + url
  parsed = urlparse(url)
  if 'ozon.ru' not in parsed.netloc.lower():
    raise OzonFetchError('Ссылка должна быть с сайта ozon.ru')
  path = unquote(parsed.path)
  if '/product/' not in path:
    raise OzonFetchError('Ссылка должна вести на страницу товара (/product/...)')
  if not path.endswith('/'):
    path += '/'
  return path


def extract_product_id(path: str) -> str:
  match = re.search(r'-(\d+)/?$', path.rstrip('/'))
  if match:
    return match.group(1)
  match = re.search(r'/product/(\d+)', path)
  return match.group(1) if match else ''


def name_from_ozon_path(path: str) -> str:
  slug_match = re.search(r'/product/([^/?#]+)', path)
  if not slug_match:
    return ''
  slug = slug_match.group(1)
  slug = re.sub(r'-\d+$', '', slug)
  slug = slug.replace('-', ' ').strip()
  if not slug:
    return ''
  return slug[:1].upper() + slug[1:]


def _parse_price(value) -> Decimal | None:
  if value is None:
    return None
  if isinstance(value, bool):
    return None
  if isinstance(value, (int, float, Decimal)):
    amount = Decimal(str(value))
    if amount > 100_000:
      amount = (amount / 100).quantize(Decimal('0.01'))
    return amount.quantize(Decimal('0.01'))
  text = str(value)
  text = text.replace('\u2009', '').replace('\xa0', '').replace(' ', '')
  text = re.sub(r'[^\d.,]', '', text.replace(',', '.'))
  if not text:
    return None
  try:
    return Decimal(text).quantize(Decimal('0.01'))
  except InvalidOperation:
    return None


def _clean_title(title: str) -> str:
  title = unescape((title or '').strip())
  title = re.sub(r'\s*купить на OZON.*$', '', title, flags=re.I).strip()
  title = re.sub(r'\s*\|\s*OZON.*$', '', title, flags=re.I).strip()
  title = re.sub(r'\s*—\s*OZON.*$', '', title, flags=re.I).strip()
  title = re.sub(r'\s+', ' ', title)
  return title


def _pick_title(obj) -> str | None:
  title_keys = {'title', 'name', 'productName', 'productTitle', 'heading', 'seoName'}
  if isinstance(obj, dict):
    for key in title_keys:
      value = obj.get(key)
      if isinstance(value, str) and len(value.strip()) > 3:
        return _clean_title(value)
    for value in obj.values():
      found = _pick_title(value)
      if found:
        return found
  elif isinstance(obj, list):
    for item in obj:
      found = _pick_title(item)
      if found:
        return found
  return None


def _pick_price(obj) -> Decimal | None:
  price_keys = {
    'finalPrice', 'price', 'originalPrice', 'cardPrice',
    'marketingPrice', 'minPrice', 'currentPrice', 'premiumPrice',
  }
  if isinstance(obj, dict):
    for key in price_keys:
      if key in obj:
        price = _parse_price(obj[key])
        if price and price > 0:
          return price
    for value in obj.values():
      found = _pick_price(value)
      if found:
        return found
  elif isinstance(obj, list):
    for item in obj:
      found = _pick_price(item)
      if found:
        return found
  return None


def _parse_widget_states(data: dict) -> tuple[str | None, Decimal | None]:
  title = _pick_title(data)
  price = _pick_price(data)
  widget_states = data.get('widgetStates') or {}
  for raw in widget_states.values():
    if not isinstance(raw, str):
      continue
    try:
      parsed = json.loads(raw)
    except json.JSONDecodeError:
      continue
    title = title or _pick_title(parsed)
    price = price or _pick_price(parsed)
  return title, price


def _extract_from_html(html: str) -> tuple[str | None, Decimal | None]:
  title = None
  price = None

  for pattern in (
    r'<meta\s+property="og:title"\s+content="([^"]+)"',
    r'<meta\s+content="([^"]+)"\s+property="og:title"',
    r'"seo"\s*:\s*\{\s*"title"\s*:\s*"([^"]+)"',
    r'"title"\s*:\s*"((?:\\.|[^"\\]){4,200})"',
  ):
    match = re.search(pattern, html, re.I | re.S)
    if match:
      candidate = _clean_title(match.group(1))
      if len(candidate) > 3 and 'OZON' not in candidate.upper()[:10]:
        title = candidate
        break

  for pattern in (
    r'"finalPrice"\s*:\s*"?(\d+)"?',
    r'"cardPrice"\s*:\s*"?(\d+)"?',
    r'"price"\s*:\s*"?(\d+)"?',
    r'"originalPrice"\s*:\s*"?(\d+)"?',
    r'data-price="(\d+)"',
  ):
    match = re.search(pattern, html)
    if match:
      price = _parse_price(match.group(1))
      if price:
        break

  if not price:
    rub_matches = re.findall(
      r'(\d[\d\s\u00a0\u2009]{1,12})\s*(?:₽|&#8381;|&#x20BD;|руб\.?)',
      html,
      re.I,
    )
    for raw in rub_matches:
      candidate = _parse_price(raw)
      if candidate and candidate >= 10:
        price = candidate
        break

  return title, price


def parse_ozon_text(text: str) -> dict:
  text = (text or '').strip()
  if not text:
    raise OzonFetchError('Вставьте текст или ссылку с OZON')

  if 'ozon.ru' in text and text.startswith('http'):
    return fetch_ozon_product(text)

  if 'ozon.ru/product/' in text:
    url_match = re.search(r'https?://[^\s]+ozon\.ru/product/[^\s]+', text)
    if url_match:
      return fetch_ozon_product(url_match.group(0).rstrip('.,)'))

  name = None
  price = None

  if '<html' in text.lower() or '<meta' in text.lower() or 'og:title' in text:
    name, price = _extract_from_html(text)

  lines = [line.strip() for line in re.split(r'[\r\n]+', text) if line.strip()]
  if lines and not name:
    candidates = [line for line in lines if len(line) > 5 and not re.search(r'^\d', line)]
    if candidates:
      name = _clean_title(max(candidates, key=len))

  price_patterns = [
    r'(\d[\d\s\u00a0\u2009]{1,12})\s*(?:₽|руб\.?)',
    r'(?:цена|price)\s*[:\-]?\s*(\d[\d\s\u00a0\u2009]{1,12})',
  ]
  if not price:
    for pattern in price_patterns:
      match = re.search(pattern, text, re.I)
      if match:
        price = _parse_price(match.group(1))
        if price:
          break

  if not name:
    raise OzonFetchError('Не удалось определить название. Скопируйте название товара с OZON.')
  if not price:
    raise OzonFetchError('Не удалось определить цену. Скопируйте строку с ценой (например: 4 590 ₽).')

  return {
    'name': name,
    'price': str(price),
    'ozon_url': '',
    'ozon_product_id': '',
    'source': 'paste',
  }


def _fetch_with_requests(session: requests.Session, path: str, full_url: str) -> tuple[str | None, Decimal | None]:
  title = price = None
  api_urls = (
    'https://www.ozon.ru/api/composer-api.bx/page/json/v2',
    'https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2',
  )
  api_headers = {
    **HEADERS,
    'Accept': 'application/json',
    'Referer': full_url,
    'X-Requested-With': 'XMLHttpRequest',
  }

  session.get('https://www.ozon.ru/', headers=HEADERS, timeout=15)

  for api_url in api_urls:
    try:
      response = session.get(api_url, params={'url': path}, headers=api_headers, timeout=20)
      if response.status_code != 200:
        continue
      data = response.json()
      api_title, api_price = _parse_widget_states(data)
      title = title or api_title
      price = price or api_price
      if title and price:
        break
    except Exception:
      continue

  if not title or not price:
    response = session.get(full_url, headers={**HEADERS, 'Referer': 'https://www.ozon.ru/'}, timeout=20)
    if response.status_code == 200:
      html_title, html_price = _extract_from_html(response.text)
      title = title or html_title
      price = price or html_price

  return title, price


def _fetch_with_playwright(full_url: str) -> tuple[str | None, Decimal | None]:
  try:
    from playwright.sync_api import sync_playwright
  except ImportError:
    return None, None

  title = price = None
  with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
      locale='ru-RU',
      user_agent=HEADERS['User-Agent'],
    )
    page = context.new_page()
    page.goto('https://www.ozon.ru/', wait_until='domcontentloaded', timeout=45000)
    page.goto(full_url, wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(2500)
    html = page.content()
    title, price = _extract_from_html(html)
    if not price:
      for selector in ('[data-widget="webPrice"]', '[data-widget="webSale"]'):
        locator = page.locator(selector).first
        if locator.count():
          text = locator.inner_text(timeout=3000)
          match = re.search(r'(\d[\d\s\u00a0\u2009]+)\s*₽', text)
          if match:
            price = _parse_price(match.group(1))
            break
    browser.close()
  return title, price


def fetch_ozon_product(url: str, allow_partial: bool = False) -> dict:
  path = extract_ozon_path(url)
  product_id = extract_product_id(path)
  full_url = f'https://www.ozon.ru{path}'
  slug_name = name_from_ozon_path(path)

  session = requests.Session()
  title, price = _fetch_with_requests(session, path, full_url)

  if not title or not price:
    pw_title, pw_price = _fetch_with_playwright(full_url)
    title = title or pw_title
    price = price or pw_price

  if not title:
    title = slug_name

  if not title:
    raise OzonFetchError('Не удалось получить название. Заполните поля вручную.')

  if not price:
    if allow_partial:
      return {
        'name': title,
        'price': '',
        'ozon_url': full_url,
        'ozon_product_id': product_id,
        'source': 'slug' if title == slug_name else 'partial',
        'warning': (
          'OZON блокирует автоматическое получение цены. '
          'Скопируйте цену со страницы товара или используйте «Вставить текст с OZON».'
        ),
      }
    raise OzonFetchError(
      'OZON блокирует автозагрузку. Откройте товар в браузере, скопируйте название и цену '
      'и нажмите «Вставить текст с OZON», либо укажите цену вручную.'
    )

  return {
    'name': title,
    'price': str(price),
    'ozon_url': full_url,
    'ozon_product_id': product_id,
    'source': 'fetch',
  }
