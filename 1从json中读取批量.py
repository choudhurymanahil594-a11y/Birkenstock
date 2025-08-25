# -*- coding: utf-8 -*-
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
    width_elements = await page.query_selector_all('ul.swatches.width li span.swatchanchor.width-type.width')
    widths = []
    for element in width_elements:
        # 尝试从 aria-label 属性中提取宽度，例如 "Width Regular"
        aria_label = await element.get_attribute('aria-label')
        if aria_label and aria_label.startswith('Width '):
            widths.append(aria_label.replace('Width ', '').strip())
        else:
            # 如果没有 aria-label 或格式不符，则尝试提取 span 标签内的文本
            span_text_element = await element.query_selector('span')
            if span_text_element:
                widths.append((await span_text_element.inner_text()).strip())
    
    width = ', '.join(widths) if widths else 'N/A'

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
    content_asset_element = await page.query_selector('div.toggle-container.expanded div.toggle-content div.content-asset')
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
    missing_fields = []
    if product_data['title'] == 'N/A':
        missing_fields.append('title')
    if product_data['width'] == 'N/A':
        missing_fields.append('width')
    if product_data['color'] == 'N/A':
        missing_fields.append('color')
    if product_data['price'] == 'N/A':
        missing_fields.append('price')
    if product_data['description'] == 'N/A':
        missing_fields.append('description')
    if not product_data['image_urls']:
        missing_fields.append('image_urls')

    if missing_fields:
        print(f"警告: URL {url} 缺少关键数据: {', '.join(missing_fields)}。请检查规则。")
        return None
    
    return product_data

async def main():
    """
    主函数：从 initial_urls.json 获取初始 URL 列表，然后获取所有颜色链接并采集详细信息
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        initial_urls_file = 'birkenstock_campaign_product_urls.json'
        output_json_file = 'birkenstock_all_products_details.json' # 将 output_json_file 移到这里
        all_products_data = [] # 初始化 all_products_data

        try:
            with open(initial_urls_file, 'r', encoding='utf-8') as f:
                initial_urls = json.load(f)
            total_urls = len(initial_urls)
            print(f"从 {initial_urls_file} 读取到 {total_urls} 个初始URL。")
        except FileNotFoundError:
            print(f"错误：文件 '{initial_urls_file}' 未找到。请确保它包含初始产品URL列表。")
            await browser.close()
            return
        except json.JSONDecodeError:
            print(f"错误：无法解码 '{initial_urls_file}' 中的 JSON。请确保它是有效的 JSON 格式。")
            await browser.close()
            return
        except Exception as e:
            print(f"读取初始URL文件时发生错误: {e}")
            await browser.close()
            return

        # 尝试加载已有的产品数据，如果文件不存在则初始化为空列表
        try:
            with open(output_json_file, 'r', encoding='utf-8') as f:
                all_products_data = json.load(f)
            print(f"从 {output_json_file} 读取到 {len(all_products_data)} 条已采集数据。")
        except FileNotFoundError:
            all_products_data = []
            print(f"文件 '{output_json_file}' 不存在，将创建新文件。")
        except json.JSONDecodeError:
            print(f"警告：无法解码 '{output_json_file}' 中的 JSON。将覆盖现有文件。")
            all_products_data = []
        except Exception as e:
            print(f"读取已采集数据文件时发生错误: {e}。将覆盖现有文件。")
            all_products_data = []
        processed_urls_count = 0
        
        # 创建一个集合来存储已处理的URL，避免重复采集
        processed_urls_set = {p['url'] for p in all_products_data}
        
        # 存储所有待处理的URL和对应的分类
        urls_to_process_with_category = []
        for category_data in initial_urls:
            category = category_data['level3_category']
            for url in category_data['product_urls']:
                if url not in processed_urls_set:
                    urls_to_process_with_category.append({'url': url, 'category': category})

        total_urls_to_process = len(urls_to_process_with_category)
        print(f"从 {initial_urls_file} 读取到 {total_urls_to_process} 个待处理URL。")

        for i, item in enumerate(urls_to_process_with_category):
            initial_url = item['url']
            category = item['category']
            processed_urls_count += 1
            print(f"正在处理第 {processed_urls_count}/{total_urls_to_process} 条初始URL: {initial_url} (分类: {category})")
            try:
                print(f"导航到初始URL: {initial_url}")
                await page.goto(initial_url)
                await page.wait_for_load_state('domcontentloaded')

                colors = {}
                color_elements = await page.query_selector_all('ul.swatches.color li a.swatchanchor.width-type.color')

                if not color_elements:
                    print(f"URL {initial_url} 未找到颜色切换器。将只采集此URL。")
                    colors['current_product'] = initial_url
                else:
                    for element in color_elements:
                        color_text = await element.get_attribute('data-value')
                        color_link = await element.get_attribute('href')
                        if color_link and color_link.startswith('/'):
                            full_link = f'https://www.birkenstock.com{color_link}'
                        else:
                            full_link = color_link
                        colors[color_text] = full_link

                print(f"URL {initial_url} 找到以下颜色链接: {colors}")
                print("---")

                for color_text, url in colors.items():
                    if url in processed_urls_set:
                        print(f"URL {url} 已被采集过，跳过。")
                        continue

                    print(f"开始采集颜色: {color_text} ({url})")
                    product_data = await scrape_product_details(page, url)
                    
                    if product_data:
                        product_data['category'] = category # 添加 category 字段
                        all_products_data.append(product_data)
                        processed_urls_set.add(url) # 将新采集的URL添加到已处理集合
                        # 每采集一次就写入一次 JSON 文件
                        with open(output_json_file, 'w', encoding='utf-8') as f:
                            json.dump(all_products_data, f, ensure_ascii=False, indent=4)
                        print(f"已采集 {color_text} 的数据并保存到 {output_json_file}。")
                    else:
                        print(f"因数据缺失中断采集。请检查URL: {url}")
                        continue 
                    print("---")
                
            except Exception as e:
                print(f"处理URL {initial_url} 时发生错误: {e}")
            
        print(f"所有待处理产品数据已成功保存到 {output_json_file} 文件。")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
