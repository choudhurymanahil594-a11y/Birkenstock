import requests
from bs4 import BeautifulSoup

# 要抓取的网页 URL
url = "https://www.birkenstock.com/us/arizona-rivet-suede-leather/arizonarivet-suederivets-suedeleather-0-eva-w_1.html"

try:
    # 使用 requests 获取网页内容
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功

    # 使用 Beautiful Soup 解析 HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # 使用 CSS 选择器找到所有颜色选项的元素
    color_swatches = soup.select('.swatchanchor.color')

    # 遍历每个颜色元素，提取信息
    for swatch in color_swatches:
        color_name = swatch.get('data-value')
        href_url = swatch.get('href')
        selection_url = swatch.get('data-selectionurl')

        print(f"颜色: {color_name}")
        print(f"  href: {href_url}")
        print(f"  data-selectionurl: {selection_url}")
        print("-" * 20)  # 添加分隔线，使输出更清晰

except requests.exceptions.RequestException as e:
    print(f"获取网页时出错: {e}")