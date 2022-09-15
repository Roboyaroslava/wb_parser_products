import fake_headers
import itertools
import json
from typing import Any, Dict, List, Tuple
from requests import Session


from project_types import SettingsParseBrands


class WildberriesParser:

    def _selectors(
            self,
            session: Session,
            query: str
    ) -> Dict[str, Any]:
        url = 'https://wbxsearch.wildberries.ru/exactmatch/v2/common?query='
        return json.loads(session.get(url + query.replace(' ', '+')).text)



    def _filters(
            self,
            session: Session,
            selectors: Dict[str, Any]
    ) -> Dict[str, Any]:
        return json.loads(session.get(
            f'https://wbxcatalog-ru.wildberries.ru/{selectors["shardKey"]}/filters'
            f'?filters=fbrand'
            f'&spp=0'
            f'&regions=64,86,83,4,38,30,33,22,31,66,68,1,82,48,40,80'
            f'&stores=6149,130744,117501,507,3158,120762,117986,159402,2737'
            f'&pricemarginCoeff=1.0'
            f'&reg=0'
            f'&appType=1'
            f'&offlineBonus=0'
            f'&onlineBonus=0'
            f'&emp=0'
            f'&locale=ru'
            f'&lang=ru'
            f'&curr=rub'
            f'&couponsGeo=6,3,19,21,8'
            f'&dest=-1059500,-72639,-1754563'
            f'&{selectors["query"]}'
        ).text)

    def _articles(
            self,
            session: Session,
            articles: List[int]
    ):

        return json.loads(session.get(
            f'https://wbxcatalog-ru.wildberries.ru/nm-2-card/catalog'
            f'?filters=fbrand'
            f'&spp=0'
            f'&regions=64,86,83,4,38,30,33,22,31,66,68,1,82,48,40,80'
            f'&stores=6149,130744,117501,507,3158,120762,117986,159402,2737'
            f'&pricemarginCoeff=1.0'
            f'&reg=0'
            f'&appType=1'
            f'&offlineBonus=0'
            f'&onlineBonus=0'
            f'&emp=0'
            f'&locale=ru'
            f'&lang=ru'
            f'&curr=rub'
            f'&couponsGeo=6,3,19,21,8'
            f'&dest=-1059500,-72639,-1754563'
            f'&nm={";".join(map(str, articles))}'
        ).text)



    def _brand_mappings(self, filters_response: Dict[str, Any]) -> Dict[str, int]:
        brands = next(filter(lambda x: x['key'] == 'fbrand', filters_response['data']['filters']))['items']
        return {i['name']: i['id'] for i in brands}

    def _items(
            self,
            session: Session,
            selectors: Dict[str, Any],
            brand_ids: List[int] | None = None,
            price: Tuple[int, int] | None = None,
            page: int = 1                   
            ) -> Dict[str, Any] or None:
        response = session.get(
            f'https://wbxcatalog-ru.wildberries.ru/{selectors["shardKey"]}/catalog'
            f'?spp=0'
            f'&regions=64,86,83,4,38,30,33,22,31,66,68,1,82,48,40,80'
            f'&stores=6149,130744,117501,507,3158,120762,117986,159402,2737'
            f'&pricemarginCoeff=1.0'
            f'&reg=0'
            f'&appType=1'
            f'&offlineBonus=0'
            f'&onlineBonus=0'
            f'&emp=0'
            f'&locale=ru'
            f'&lang=ru'
            f'&curr=rub'
            f'&couponsGeo=6,3,19,21,8'
            f'&dest=-1059500,-72639,-1754563'
            f'&page={page}'
            f'&{selectors["query"]}'
            + (f'&fbrand={";".join(map(str, brand_ids))}' if brand_ids else '')
            + (f'&priceU={price[0]}00;{price[1]}00' if price else '')
        ).text
        return json.loads(response)



    def _extract_articles(self, items_response: Dict[str, Any]) -> List[int]:
        return [i['id'] for i in items_response['data']['products']]

    def parse(
            self,
            writer,
            keyword: str | None = None,
            articles: List[int] | None = None,
            brand_ids: List[int] | None = None,
            brand_names: List[str] | None = None,
            price: Tuple[int, int] | None = None,
            telegramID: str | None = None,
            settings: SettingsParseBrands | None = None,
            compare: bool = False, #для второй формы (сравнение артикула с артикулами)
            proxies: Dict[str, str] | None = None,
    ):
        s = Session()

        s.headers.update(fake_headers.Headers().generate())
        if proxies:
            s.proxies = proxies
        if articles:
            resp = self._articles(s, articles)
            for item in resp['data']['products']:
                
                if compare:
                    writer.save_compare_articles_results(
                        item['id'], #артикул
                        item['name'] + ', ' + item['brand'],
                        (item.get('salePriceU', None) or item['salePrice']) / 100
                    )
                else:
                    writer.save_parse(
                        item['id'], #артикул
                        item['name'] + ', ' + item['brand'],
                        (item.get('salePriceU', None) or item['salePrice']) / 100
                    )
        if not keyword:
            return
        selectors = self._selectors(s, keyword)
        filters = self._filters(s, selectors)
        mappings = self._brand_mappings(filters)
        mappings_values = mappings.values()
        total_brand_ids = []
        if brand_ids:
            for brand_id in brand_ids:
                if brand_id in mappings_values:
                    total_brand_ids.append(brand_id)
                else:
                    print(f'Warning: Brand with ID {brand_id} is not available')

        if brand_names:
            for name in brand_names:
                if name in mappings:
                    total_brand_ids.append(mappings[name])
                else:
                    print(f'Warning: Brand "{name}" is not available')

        try:
            for i in itertools.count(1):
                for item in self._items(s, selectors, brand_ids, price, i)['data']['products']: 
                    writer.save_articles_from_brand(item['id'], settings, telegramID)
        except:  # Out of pages
            pass

