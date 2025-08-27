# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright
import json
import urllib.parse
import os

async def scrape_product_details(page, url):
    """
    采集单个产品的详细信息并返回一个字典
    """
    await page.goto(url)
    await page.wait_for_load_state('domcontentloaded')

    # 如果是 SFCC 的 Product-Variation 片段地址，自动跳到完整的 Product-Show 页面
    if 'Product-Variation' in url:
        try:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            pid_values = query.get('pid')
            if pid_values and len(pid_values) > 0:
                pid = pid_values[0]
                base = url.split('Product-Variation')[0]
                product_show_url = urllib.parse.urljoin(base, f'Product-Show?pid={pid}')
                await page.goto(product_show_url)
                await page.wait_for_load_state('domcontentloaded')
        except Exception:
            pass

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

    # 提取产品尺码
    sizes = {}
    
    # 提取女性尺码
    women_size_group = await page.query_selector('.wsizegroup')
    if women_size_group:
        women_size_items = await women_size_group.query_selector_all('.swatchanchor')
        women_sizes = []
        for item in women_size_items:
            size_top = await item.query_selector('.size-top')
            if size_top:
                size_text = await size_top.inner_text()
                # 移除 " US" 后缀
                size_text = size_text.strip().replace(' US', '')
                women_sizes.append(size_text)
        if women_sizes:
            sizes['women'] = women_sizes
    
    # 提取男性尺码
    men_size_group = await page.query_selector('.msizegroup')
    if men_size_group:
        men_size_items = await men_size_group.query_selector_all('.swatchanchor')
        men_sizes = []
        for item in men_size_items:
            size_top = await item.query_selector('.size-top')
            if size_top:
                size_text = await size_top.inner_text()
                # 移除 " US" 后缀
                size_text = size_text.strip().replace(' US', '')
                men_sizes.append(size_text)
        if men_sizes:
            sizes['men'] = men_sizes
    
    # 提取童鞋尺码
    kids_size_group = await page.query_selector('.ksizegroup')
    if kids_size_group:
        kids_sizes = {}
        
        # 查找所有尺码项
        kids_size_items = await kids_size_group.query_selector_all('.swatchanchor')
        
        for item in kids_size_items:
            size_top = await item.query_selector('.size-top')
            if size_top:
                size_text = await size_top.inner_text()
                # 移除 " US" 后缀
                size_text = size_text.strip().replace(' US', '')
                
                # 根据尺码范围判断是Little Kids还是Big Kids
                # Little Kids: 8-8.5 到 10-10.5 (对应EU 26-28)
                # Big Kids: 11-11.5 到 3-3.5 (对应EU 29-34)
                try:
                    # 提取尺码数字进行判断
                    if '-' in size_text:
                        size_parts = size_text.split('-')
                        first_size = float(size_parts[0])
                        
                        if first_size <= 10.5:  # Little Kids
                            if 'little_kids' not in kids_sizes:
                                kids_sizes['little_kids'] = []
                            kids_sizes['little_kids'].append(size_text)
                        else:  # Big Kids
                            if 'big_kids' not in kids_sizes:
                                kids_sizes['big_kids'] = []
                            kids_sizes['big_kids'].append(size_text)
                    else:
                        # 单个尺码的情况
                        size_num = float(size_text)
                        if size_num <= 10.5:  # Little Kids
                            if 'little_kids' not in kids_sizes:
                                kids_sizes['little_kids'] = []
                            kids_sizes['little_kids'].append(size_text)
                        else:  # Big Kids
                            if 'big_kids' not in kids_sizes:
                                kids_sizes['big_kids'] = []
                            kids_sizes['big_kids'].append(size_text)
                except ValueError:
                    # 如果无法解析尺码数字，则按顺序分配
                    if 'little_kids' not in kids_sizes:
                        kids_sizes['little_kids'] = []
                    kids_sizes['little_kids'].append(size_text)
        
        if kids_sizes:
            sizes['kids'] = kids_sizes
    
    # 如果没有找到任何尺码，设置为N/A
    if not sizes:
        sizes = 'N/A'

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
        'sizes': sizes,
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
    主函数：从 initial_urls.json 获取初始 URL 列表，然后采集详细信息
    """
    async with async_playwright() as p:
        # 调试：使用无头模式，避免本地打开浏览器窗口
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        initial_urls_file = '所有颜色变体URL_Cursor_dedup.json'
        output_json_file = 'birkenstock_all_products_details.json'
        na_log_file = 'NA.txt'  # N/A记录文件
        all_products_data = []
        na_urls = []  # 存储所有出现N/A的URL

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
        
        # 尝试加载已有的N/A记录，如果文件不存在则初始化为空列表
        try:
            with open(na_log_file, 'r', encoding='utf-8') as f:
                na_urls = [line.strip() for line in f.readlines() if line.strip()]
            print(f"从 {na_log_file} 读取到 {len(na_urls)} 条N/A记录。")
        except FileNotFoundError:
            na_urls = []
            print(f"文件 '{na_log_file}' 不存在，将创建新文件。")
        except Exception as e:
            print(f"读取N/A记录文件时发生错误: {e}。将创建新文件。")
            na_urls = []
        
        # 创建一个集合来存储已处理的URL，避免重复采集
        processed_urls_set = {p['url'] for p in all_products_data}
        # 可配置：是否排除已记录为N/A的URL（默认排除）
        exclude_na = os.getenv('EXCLUDE_NA', '1') == '1'
        if exclude_na:
            processed_urls_set.update(set(na_urls))
        
        # 存储所有待处理的URL和对应的分类
        urls_to_process_with_category = []
        for category_data in initial_urls:
            level1 = category_data.get('level1_category')
            level2 = category_data.get('level2_category')
            level3 = category_data.get('level3_category')

            # 结构一：每项直接是单个URL（本文件 dedup.json 的结构）
            if 'url' in category_data:
                url = category_data.get('url')
                if url and url not in processed_urls_set:
                    urls_to_process_with_category.append({
                        'url': url,
                        'category': {
                            'level1_category': level1,
                            'level2_category': level2,
                            'level3_category': level3
                        }
                    })
                continue

            # 结构二：分组包含多条 product_urls 的结构（兼容旧数据）
            product_urls = category_data.get('product_urls')
            if isinstance(product_urls, list):
                for url in product_urls:
                    if url not in processed_urls_set:
                        urls_to_process_with_category.append({
                            'url': url,
                            'category': {
                                'level1_category': level1,
                                'level2_category': level2,
                                'level3_category': level3
                            }
                        })

        # 以下代码用于调试时限制处理的URL数量。
        # 用户要求处理所有URL，因此已将此限制代码注释掉。
        # 如果需要重新启用限制，请取消注释以下代码行并设置 max_urls_to_process 的值。
        # max_urls_to_process = int(os.getenv('MAX_URLS', '0')) # 通过环境变量控制最大处理数量，设置为0表示处理所有URL
        # if max_urls_to_process > 0:
        #     urls_to_process_with_category = urls_to_process_with_category[:max_urls_to_process]
        total_urls_to_process = len(urls_to_process_with_category)
        print(f"从 {initial_urls_file} 读取到 {total_urls_to_process} 个待处理URL。")
        if not exclude_na:
            print("提示：当前未排除 N/A 记录，可能会重试之前失败的 URL。")

        for i, item in enumerate(urls_to_process_with_category):
            url = item['url']
            category = item['category']
            print(f"正在处理第 {i+1}/{total_urls_to_process} 条URL: {url} (分类: {category.get('level1_category', 'N/A')} > {category.get('level2_category', 'N/A')} > {category.get('level3_category', 'N/A')})")
            
            try:
                print(f"开始采集产品信息: {url}")
                product_data = await scrape_product_details(page, url)
                
                if product_data:
                    product_data['category'] = category
                    all_products_data.append(product_data)
                    processed_urls_set.add(url)
                    
                    # 每采集一次就写入一次 JSON 文件
                    with open(output_json_file, 'w', encoding='utf-8') as f:
                        json.dump(all_products_data, f, ensure_ascii=False, indent=4)
                    print(f"已采集产品数据并保存到 {output_json_file}。")
                else:
                    print(f"因数据缺失中断采集。请检查URL: {url}")
                    # 记录N/A的URL到文件
                    if url not in na_urls:
                        na_urls.append(url)
                        with open(na_log_file, 'a', encoding='utf-8') as f:
                            f.write(url + '\n')
                        print(f"已将N/A URL记录到 {na_log_file}。")
                    continue 
                print("---")
                
            except Exception as e:
                print(f"处理URL {url} 时发生错误: {e}")
                # 记录出错的URL到N/A文件
                if url not in na_urls:
                    na_urls.append(url)
                    with open(na_log_file, 'a', encoding='utf-8') as f:
                        f.write(url + '\n')
                    print(f"已将出错URL记录到 {na_log_file}。")
            
        print(f"所有待处理产品数据已成功保存到 {output_json_file} 文件。")
        print(f"N/A记录已保存到 {na_log_file} 文件，共 {len(na_urls)} 条记录。")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
