import copy
import re
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

from bs4 import BeautifulSoup, Tag
from selenium.common import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver

from model.sheet_model import DD


class FilterParams:
    def __init__(self):
        self.stock_min = 0
        self.level_min = 0

    def apply(self, product: "DD373Product") -> bool:
        """Apply the filter to a product"""
        if self.level_min is not None and product.credit_rating < self.level_min:
            return False
        if self.stock_min is not None and product.stock < self.stock_min:
            return False
        return True


@dataclass
class DD373Product:
    title: str = ""
    url: str = ""
    product_id: str = ""
    server_info: str = ""
    price: float = 0.0
    stock: int = 0
    exchange_rate_1: str = ""  # 1元=17.5439钻
    exchange_rate_2: str = ""  # 1钻=0.0570元
    credit_rating: int = 0  # Trust level (1-15): 1-5 hearts, 6-10 diamonds, 11-15 crowns
    purchase_url: str = ""

    @classmethod
    def from_html_element(cls, item: Tag, domain: str = "https://www.dd373.com") -> "DD373Product":
        product = cls()

        # 1. Title and URL
        title_elem = item.select_one('.goods-list-title')
        if title_elem:
            product.title = title_elem.text.strip()
            href = title_elem.get('href', '')
            if href and href.startswith('/'):
                href = f"{domain}{href}"
            product.url = href

            if '/detail-' in href:
                try:
                    product.product_id = href.split('/detail-')[1].split('.html')[0]
                except IndexError:
                    pass

        # 2. Server info
        server_info = item.select_one('.game-qufu-attr')
        if server_info:
            servers = [a.text.strip() for a in server_info.select('a')]
            product.server_info = '/'.join(servers) if servers else ''

        # 3. Price (Lấy tất cả số trong thẻ giá)
        price_elem = item.select_one('.goods-price')
        if price_elem:
            # Chỉ lấy số và dấu chấm (ví dụ: ￥103.10 -> 103.10)
            try:
                product.price = float(re.sub(r'[^\d.]', '', price_elem.text))
            except (ValueError, TypeError):
                product.price = 0.0

        # 4. STOCK (TỒN KHO) - CẢI TIẾN QUAN TRỌNG
        # Thay vì tìm class .colorff5, ta tìm text "库存" hoặc "Stock" trong vùng chứa thông tin
        # Cách này an toàn hơn nhiều.
        reputation_div = item.select_one('.game-reputation')
        if reputation_div:
            # Regex tìm chuỗi kiểu: "库存： 7" hoặc "库存:7"
            # \s* chấp nhận mọi khoảng trắng
            stock_match = re.search(r'库存\s*[：:]\s*(\d+)', reputation_div.text)
            if stock_match:
                product.stock = int(stock_match.group(1))
            else:
                # Fallback: Thử tìm thẻ đậm (bold) nếu regex thất bại
                bold_span = reputation_div.select_one('.bold')
                if bold_span and bold_span.text.strip().isdigit():
                    product.stock = int(bold_span.text.strip())

        # Fallback cũ: Nếu vẫn chưa tìm ra stock, thử tìm trong .kucun (phòng khi web rollback)
        if product.stock == 0:
            stock_elem_old = item.select_one('.kucun span')
            if stock_elem_old and stock_elem_old.text.strip().isdigit():
                product.stock = int(stock_elem_old.text.strip())

        # 5. Exchange rates (Tỷ lệ)
        # Tìm trong .kucun, bất kể cấu trúc div lồng nhau thế nào
        kucun_div = item.select_one('.kucun')
        if kucun_div:
            # Lấy tất cả thẻ p, vì text tỷ lệ luôn nằm trong p
            ps = kucun_div.select('p')
            if len(ps) >= 2:
                product.exchange_rate_1 = ps[0].text.strip()
                product.exchange_rate_2 = ps[1].text.strip()
            # Fallback cho giao diện cũ (.width233)
            elif not ps:
                old_rate_div = item.select_one('.width233')
                if old_rate_div:
                    ps_old = old_rate_div.select('p')
                    if len(ps_old) >= 2:
                        product.exchange_rate_1 = ps_old[0].text.strip()
                        product.exchange_rate_2 = ps_old[1].text.strip()

        # 6. Credit rating
        reputation = item.select_one('.game-reputation')
        if reputation:
            hearts = len(reputation.select('i.icon-heart'))
            diamonds = len(reputation.select('i.icon-bluediamond'))
            crowns = len(reputation.select('i.icon-crown'))

            if hearts > 0:
                product.credit_rating = hearts
            elif diamonds > 0:
                product.credit_rating = 5 + diamonds
            elif crowns > 0:
                product.credit_rating = 10 + crowns

        # 7. Purchase URL
        buy_btn = item.select_one('.shop-btn-group a.im-buy-btn')
        if buy_btn:
            href = buy_btn.get('href', '')
            if href and not href.startswith('http'):
                href = f"https:{href}"
            product.purchase_url = href

        # 8. Tính toán số lượng thực (Quantity & Unit Price)
        # Logic: Title "1000 Divine = 100 tệ", Stock hiển thị 2 -> Tổng stock = 2000
        quantity = 1
        if product.title and '=' in product.title:
            try:
                # Lấy phần text trước dấu =, ví dụ "1000个神圣石"
                quantity_part = product.title.split('=')[0]
                # Tìm số đầu tiên trong chuỗi này
                match = re.search(r'\d+', quantity_part)
                if match:
                    quantity = int(match.group())
                    # Nhân stock hiển thị với số lượng gói
                    product.stock = quantity * product.stock
            except (ValueError, TypeError, IndexError):
                quantity = 1

        # Tính giá đơn vị
        if quantity > 0:
            product.price = product.price / quantity

        return product

    def to_dict(self) -> Dict[str, Any]:
        """Convert the product to a dictionary"""
        return asdict(self)


def get_dd373_listings(url: str, driver: WebDriver) -> List[DD373Product]:
    """
    Scrapes product listings from DD373 website

    Args:
        url: The DD373 URL to scrape

    Returns:
        A list of DD373Product objects
        :param driver:
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    domain = url.split('/s-')[0] if '/s-' in url else 'https://www.dd373.com'
    driver.get(url)
    page_source = driver.page_source
    timeout = 15
    start_time = time.time()

    while True:
        current_page_source = driver.page_source
        if "acw_sc__v2" not in current_page_source:
            page_source = current_page_source
            break

        if time.time() - start_time > timeout:
            raise TimeoutException("Timeout when loading page source")
        time.sleep(0.5)

    soup = BeautifulSoup(page_source, 'html.parser')

    # Find all product listings
    goods_list_items = soup.select('div.goods-list-item')

    # Create product objects from HTML elements
    return [DD373Product.from_html_element(item, domain) for item in goods_list_items]


def _filter_valid_offer_item(listOffers: List[DD373Product], filterParams: FilterParams) -> List[DD373Product]:
    # Make a copy of the list
    offers_copy = copy.deepcopy(listOffers)

    # Sort by exchange_rate_2
    # sorted_offers = sorted(offers_copy, key=lambda x: float(x.exchange_rate_2.split('=')[1].replace('元', '').strip()))

    sorted_offers = sorted(
        offers_copy,
        key=lambda x: float(x.exchange_rate_2.split('=')[1].replace('元', '').strip())
        if '=' in x.exchange_rate_2 and len(x.exchange_rate_2.split('=')) > 1
        else float('inf')
    )

    # apply filter
    valid_offers = []
    for offer in sorted_offers:
        if filterParams.apply(offer):
            valid_offers.append(offer)

    return valid_offers


def get_dd_min_price(dd: DD, driver: WebDriver) -> Optional[Tuple[float, str]]:
    """
    Get the minimum price from the payload

    Args:
        dd: DD object gets from payload

    Returns:
        Minimum price
    """
    _filterParams = FilterParams()
    _filterParams.stock_min = dd.DD_STOCKMIN
    _filterParams.level_min = dd.DD_LEVELMIN
    list_offers = []
    list_offers = get_dd373_listings(dd.DD_PRODUCT_LINK, driver)
    filter_list = _filter_valid_offer_item(list_offers, _filterParams)

    if not filter_list:
        return None
    min_price_object = min(filter_list, key=lambda product: product.price)

    min_price = min_price_object.price
    min_seller = min_price_object.title
    stock = min_price_object.stock
    dd_min_price = (min_price, min_seller, stock)
    return dd_min_price


if __name__ == "__main__":
    url = "https://www.dd373.com/s-9fv09v-5tgdjq-55ns9v-0-0-0-3xb9qq-0-0-0-0-0-1-0-3-0.html"
    listings = get_dd373_listings(url)
    for listing in listings:
        print(listing)

    filterParams = FilterParams()
    filterParams.stock_min = 1
    filterParams.level_min = 5
    new_listings = _filter_valid_offer_item(listings, filterParams)
    print(new_listings)
