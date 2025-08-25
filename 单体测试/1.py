
import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_product_details(page, url):
    """
    采集单个产品的详细信息并返回一个字典
    """
    await page.goto(url)
    await page.wait_for_load_state('domcontentloaded')

    # 提取产品标题
    title_element = await page.query_selector('span.heading-1')
    title = await title_element.inner_text() if title_element else 'N/A'
    
    # 提取产品价格
    price_element = await page.query_selector('span.price-standard')
    price = await price_element.inner_text() if price_element else 'N/A'

    # 提取产品宽度
    width_element = await page.query_selector('span.swatchanchor.width-type.width span')
    width = (await width_element.inner_text()).strip() if width_element else 'N/A'

    # 提取产品颜色
    color_element = await page.query_selector('div.selection span.selection-text')
    color = await color_element.get_attribute('data-value') if color_element else 'N/A'

    # 提取产品简介
    description_parts = []

    # 提取主描述文本
    main_description_element = await page.query_selector('span.product-description-text')
    if main_description_element:
        description_parts.append(await main_description_element.inner_text())

    # 提取产品特点列表
    feature_list_elements = await page.query_selector_all('ul.product-description-list li')
    for li in feature_list_elements:
        description_parts.append(await li.inner_text())

    # 提取附加信息列表 (如果需要，但通常包含样式或空div，需要过滤)
    additional_list_elements = await page.query_selector_all('ul.product-description-additional-list li')
    for li in additional_list_elements:
        text = (await li.inner_text()).strip()
        if text and "content-asset" not in text: # 过滤掉空的或包含特定关键词的li
            description_parts.append(text)

    # 新增：提取 div.content-asset 中的简介内容
    content_asset_element = await page.query_selector('div.toggle-container.expanded div.content-asset')
    if content_asset_element:
        content_text = (await content_asset_element.inner_text()).strip()
        if content_text:
            description_parts.append(content_text)

    description = ' '.join(description_parts).strip() if description_parts else 'N/A'
    # 提取图片 URL
    image_urls = []
    base_url = 'https:'
    # 查找所有包含产品图片的缩略图元素
    image_elements = await page.query_selector_all('div.grid-tile.thumb img.productthumbnail')
    for img in image_elements:
        # 尝试从 data-lgimg 属性中提取高分辨率图片 URL
        lg_img_data = await img.get_attribute('data-lgimg')
        if lg_img_data:
            try:
                lg_img_json = json.loads(lg_img_data)
                full_url = lg_img_json.get('hires') or lg_img_json.get('url')
                if full_url and full_url.startswith('//'):
                    full_url = base_url + full_url
                elif full_url and not full_url.startswith('http'):
                    full_url = base_url + full_url
                if full_url:
                    image_urls.append(full_url)
                    continue # 如果找到高分辨率图片，则跳过 src 属性
            except json.JSONDecodeError:
                pass # 如果解析失败，则继续尝试 src 属性

        # 如果没有 data-lgimg 或解析失败，则从 src 属性中提取图片 URL
        src = await img.get_attribute('src')
        if src and src.startswith('//'):
            full_url = base_url + src
            image_urls.append(full_url)
        elif src and not src.startswith('http'):
            full_url = base_url + src
            image_urls.append(full_url)

    product_data = {
        'url': url,
        'title': title.strip(),
        'width': width,
        'color': color,
        'price': price.strip(),
        'description': description.strip(),
        'image_urls': list(set(image_urls)) # 使用 set 去重，然后转回 list
    }

    # 检查是否有N/A字段或空的图片URL
    if product_data['title'] == 'N/A' or \
       product_data['width'] == 'N/A' or \
       product_data['color'] == 'N/A' or \
       product_data['price'] == 'N/A' or \
       product_data['description'] == 'N/A' or \
       not product_data['image_urls']:
        print(f"警告: URL {url} 缺少关键数据。请检查规则。")
        return None
    
    return product_data

async def main(initial_url):
    """
    主函数：获取所有尺寸链接并采集详细信息
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 创建一个空列表来存储所有产品数据
        all_products_data = []
        last_processed_url = None
        last_processed_file = 'last_processed_url.txt'

        # 尝试从文件中读取上次处理的URL
        try:
            with open(last_processed_file, 'r', encoding='utf-8') as f:
                last_processed_url = f.read().strip()
                print(f"从 {last_processed_file} 读取到上次处理的URL: {last_processed_url}")
        except FileNotFoundError:
            print("未找到上次处理的URL文件，将从头开始采集。")
        except Exception as e:
            print(f"读取上次处理的URL时发生错误: {e}")

        try:
            # 1. 导航到初始URL以获取所有颜色链接
            print(f"导航到初始URL: {initial_url}")
            await page.goto(initial_url)
            await page.wait_for_load_state('domcontentloaded')

            # 2. 获取所有颜色链接
            colors = {}
            color_elements = await page.query_selector_all('ul.swatches.color li a.swatchanchor.width-type.color')

            if not color_elements:
                print("未找到颜色切换器。将只采集初始URL。")
                colors['current_product'] = initial_url
            else:
                for element in color_elements:
                    color_text = await element.get_attribute('data-value')
                    color_link = await element.get_attribute('href')
                    if color_link.startswith('/'):
                        full_link = f'https://www.birkenstock.com{color_link}'
                    else:
                        full_link = color_link
                    colors[color_text] = full_link

            print(f"找到以下颜色链接: {colors}")
            print("---")

            # 3. 遍历所有颜色链接并采集数据
            should_start_scraping = True if not last_processed_url else False
            for color_text, url in colors.items():
                if not should_start_scraping and url == last_processed_url:
                    should_start_scraping = True
                    print(f"从上次中断的URL继续采集: {url}")
                    continue
                elif not should_start_scraping:
                    print(f"跳过已处理的URL: {url}")
                    continue

                print(f"开始采集颜色: {color_text} ({url})")
                product_data = await scrape_product_details(page, url)
                
                if product_data:
                    all_products_data.append(product_data)
                    # 成功采集后更新上次处理的URL
                    with open(last_processed_file, 'w', encoding='utf-8') as f:
                        f.write(url)
                    print(f"已采集 {color_text} 的数据。")
                else:
                    print(f"因数据缺失中断采集。请检查URL: {url}")
                    break # 中断整个采集过程
                print("---")
            
            # 4. 将数据写入 JSON 文件
            with open('birkenstock_products.json', 'w', encoding='utf-8') as f:
                json.dump(all_products_data, f, ensure_ascii=False, indent=4)
            
            print("所有产品数据已成功保存到 birkenstock_products.json 文件。")

        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    initial_product_url = 'https://www.birkenstock.com/sg/arizona-birko-flor-birkibuc/arizona-core-birkoflornubuck-0-eva-u_328.html'
    asyncio.run(main(initial_product_url))
