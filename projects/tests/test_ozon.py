from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from projects.ozon import OzonFetchError, extract_ozon_path, resolve_ozon_url
from projects.marketplaces import (
  MarketplaceFetchError,
  fetch_marketplace_product,
  fetch_wildberries_product,
)


class OzonUrlTests(SimpleTestCase):
  def test_full_product_url_is_canonicalized(self):
    url = 'https://ozon.ru/product/testovyy-tovar-123456/?from=share'

    self.assertEqual(
      resolve_ozon_url(url),
      'https://www.ozon.ru/product/testovyy-tovar-123456/',
    )

  @patch('projects.ozon.requests.get')
  def test_short_url_is_resolved(self, mocked_get):
    response = Mock()
    response.headers = {
      'Location': 'https://www.ozon.ru/product/testovyy-tovar-123456/?from=share_web',
    }
    mocked_get.return_value = response

    self.assertEqual(
      resolve_ozon_url('https://ozon.ru/t/abc123'),
      'https://www.ozon.ru/product/testovyy-tovar-123456/',
    )
    response.close.assert_called_once()

  def test_extract_path_accepts_full_url(self):
    self.assertEqual(
      extract_ozon_path('www.ozon.ru/product/testovyy-tovar-123456'),
      '/product/testovyy-tovar-123456/',
    )

  def test_rejects_lookalike_host(self):
    with self.assertRaises(OzonFetchError):
      resolve_ozon_url('https://ozon.ru.example.com/product/test-123/')


class MarketplaceTests(SimpleTestCase):
  @patch('projects.marketplaces._load_wb_price', return_value=499)
  @patch('projects.marketplaces._load_wb_card')
  @patch('projects.marketplaces._resolve_redirect')
  def test_wildberries_product_is_normalized(self, resolve, load_card, _load_price):
    resolve.return_value = 'https://www.wildberries.ru/catalog/123456/detail.aspx'
    load_card.return_value = ({'imt_name': 'Тестовый товар'}, 2)

    data = fetch_wildberries_product('https://www.wildberries.ru/catalog/123456/detail.aspx')

    self.assertEqual(data['name'], 'Тестовый товар')
    self.assertEqual(data['price'], '499')
    self.assertEqual(data['product_url'], 'https://www.wildberries.ru/catalog/123456/detail.aspx')

  def test_unknown_marketplace_is_rejected(self):
    with self.assertRaises(MarketplaceFetchError):
      fetch_marketplace_product('https://example.com/item/1', 'other')

  @patch('projects.marketplaces.requests.get')
  def test_wildberries_search_includes_new_basket_hosts(self, mocked_get):
    from projects.marketplaces import _load_wb_card

    def response_for(url, **_kwargs):
      response = Mock()
      response.status_code = 200 if 'basket-42.' in url else 404
      response.json.return_value = {'imt_name': 'Новый товар'}
      return response

    mocked_get.side_effect = response_for
    card, basket = _load_wb_card('1067024171')

    self.assertEqual(basket, 42)
    self.assertEqual(card['imt_name'], 'Новый товар')
