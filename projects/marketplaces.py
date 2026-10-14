import concurrent.futures
import re
from decimal import Decimal
from html import unescape
from urllib.parse import unquote, urljoin, urlparse

import requests

from .ozon import HEADERS, OzonFetchError, fetch_ozon_product


class MarketplaceFetchError(Exception):
  pass


MARKETPLACE_LABELS = {
  'ozon': 'OZON',
  'wildberries': 'Wildberries',
  'aliexpress': 'AliExpress',
}


def _host_matches(host: str, domains: tuple[str, ...]) -> bool:
  host = (host or '').lower().split(':', 1)[0].rstrip('.')
  return any(host == domain or host.endswith('.' + domain) for domain in domains)


def _ensure_url(url: str) -> str:
  url = (url or '').strip()
  if not url:
    raise MarketplaceFetchError('Вставьте ссылку на товар.')
  if not url.startswith(('http://', 'https://')):
    url = 'https://' + url
  return url


def _resolve_redirect(url: str, domains: tuple[str, ...]) -> str:
  current = _ensure_url(url)
  for _ in range(5):
    parsed = urlparse(current)
    if parsed.scheme not in {'http', 'https'} or not _host_matches(parsed.netloc, domains):
      raise MarketplaceFetchError('Ссылка ведёт на другой сайт.')
    try:
      response = requests.get(
        current,
        headers=HEADERS,
        timeout=15,
        allow_redirects=False,
        stream=True,
      )
    except requests.RequestException as exc:
      raise MarketplaceFetchError('Не удалось открыть ссылку магазина.') from exc
    try:
      location = response.headers.get('Location', '').strip()
    finally:
      response.close()
    if not location:
      return current
    current = urljoin(current, location)
  raise MarketplaceFetchError('Слишком много перенаправлений в ссылке.')


def _wb_card_url(basket: int, product_id: str) -> str:
  number = int(product_id)
  return (
    f'https://basket-{basket:02d}.wbbasket.ru/'
    f'vol{number // 100000}/part{number // 1000}/{number}/info/ru/card.json'
  )


def _load_wb_card(product_id: str) -> tuple[dict | None, int | None]:
  def load(basket: int):
    try:
      response = requests.get(_wb_card_url(basket, product_id), timeout=6)
      if response.status_code == 200:
        return response.json(), basket
    except (requests.RequestException, ValueError):
      pass
    return None, None

  number = int(product_id)
  if number >= 800_000_000:
    first_basket = 38
  elif number >= 400_000_000:
    first_basket = 22
  elif number >= 100_000_000:
    first_basket = 8
  else:
    first_basket = 1
  baskets = list(range(first_basket, 81)) + list(range(1, first_basket))

  executor = concurrent.futures.ThreadPoolExecutor(max_workers=12)
  # WB continuously adds new basket hosts. Product IDs above one billion are
  # already stored beyond basket-40, so keep a generous searchable range and
  # probe the likely recent hosts first.
  futures = [executor.submit(load, basket) for basket in baskets]
  try:
    for future in concurrent.futures.as_completed(futures):
      card, basket = future.result()
      if card:
        for pending in futures:
          pending.cancel()
        return card, basket
  finally:
    executor.shutdown(wait=False, cancel_futures=True)
  return None, None


def _load_wb_price(product_id: str, basket: int) -> Decimal | None:
  url = _wb_card_url(basket, product_id).replace('ru/card.json', 'price-history.json')
  try:
    response = requests.get(url, timeout=8)
    response.raise_for_status()
    history = response.json()
  except (requests.RequestException, ValueError):
    return None
  if not isinstance(history, list) or not history:
    return None
  latest = max(history, key=lambda item: item.get('dt', 0))
  raw_price = (latest.get('price') or {}).get('RUB')
  if not isinstance(raw_price, (int, float)) or raw_price <= 0:
    return None
  return (Decimal(str(raw_price)) / Decimal('100')).quantize(Decimal('0.01'))


def fetch_wildberries_product(url: str) -> dict:
  domains = ('wildberries.ru', 'wb.ru')
  resolved = _resolve_redirect(url, domains)
  parsed = urlparse(resolved)
  match = re.search(r'/catalog/(\d+)', unquote(parsed.path))
  if not match:
    raise MarketplaceFetchError('Не удалось определить артикул Wildberries из ссылки.')
  product_id = match.group(1)
  canonical_url = f'https://www.wildberries.ru/catalog/{product_id}/detail.aspx'
  card, basket = _load_wb_card(product_id)
  name = ''
  price = None
  if card:
    name = (card.get('imt_name') or card.get('subj_name') or '').strip()
    if basket:
      price = _load_wb_price(product_id, basket)

  warning = ''
  if not name and not price:
    warning = 'Wildberries не отдал данные карточки. Заполните название и цену вручную.'
  elif not price:
    warning = 'Название получено. Актуальную цену укажите вручную.'

  return {
    'name': name,
    'price': str(price) if price is not None else '',
    'product_url': canonical_url,
    'external_product_id': product_id,
    'marketplace': 'wildberries',
    'warning': warning,
  }


def _extract_html_product(html: str) -> tuple[str, Decimal | None]:
  name = ''
  for pattern in (
    r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)',
    r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:title["\']',
    r'<title[^>]*>(.*?)</title>',
  ):
    match = re.search(pattern, html, re.I | re.S)
    if match:
      name = re.sub(r'\s+', ' ', unescape(match.group(1))).strip()
      name = re.sub(r'\s*[-|–—]\s*AliExpress.*$', '', name, flags=re.I).strip()
      if name and 'captcha' not in name.lower():
        break
      name = ''

  price = None
  for pattern in (
    r'"(?:salePrice|formattedActivityPrice|price|minPrice)"\s*:\s*"?([\d\s.,]+)',
    r'<meta\s+property=["\']product:price:amount["\']\s+content=["\']([\d.,]+)',
  ):
    match = re.search(pattern, html, re.I)
    if not match:
      continue
    raw = match.group(1).replace(' ', '').replace(',', '.')
    try:
      candidate = Decimal(raw).quantize(Decimal('0.01'))
    except Exception:
      continue
    if candidate > 0:
      price = candidate
      break
  return name, price


def fetch_aliexpress_product(url: str) -> dict:
  domains = ('aliexpress.ru', 'aliexpress.com', 'a.aliexpress.com')
  resolved = _resolve_redirect(url, domains)
  parsed = urlparse(resolved)
  match = re.search(r'/item/(\d+)(?:\.html)?', unquote(parsed.path))
  product_id = match.group(1) if match else ''
  try:
    response = requests.get(resolved, headers=HEADERS, timeout=20)
    html = response.text if response.status_code == 200 else ''
  except requests.RequestException:
    html = ''
  name, price = _extract_html_product(html)
  warning = ''
  if not name and not price:
    warning = 'AliExpress не отдал данные карточки. Заполните название и цену вручную.'
  elif not price:
    warning = 'Название получено. Актуальную цену укажите вручную.'
  return {
    'name': name,
    'price': str(price) if price is not None else '',
    'product_url': resolved,
    'external_product_id': product_id,
    'marketplace': 'aliexpress',
    'warning': warning,
  }


def fetch_marketplace_product(url: str, marketplace: str) -> dict:
  if marketplace == 'ozon':
    try:
      data = fetch_ozon_product(url, allow_partial=True)
    except OzonFetchError as exc:
      raise MarketplaceFetchError(str(exc)) from exc
    data['product_url'] = data.get('ozon_url', '')
    data['external_product_id'] = data.get('ozon_product_id', '')
    data['marketplace'] = 'ozon'
    return data
  if marketplace == 'wildberries':
    return fetch_wildberries_product(url)
  if marketplace == 'aliexpress':
    return fetch_aliexpress_product(url)
  raise MarketplaceFetchError('Неизвестный магазин.')
