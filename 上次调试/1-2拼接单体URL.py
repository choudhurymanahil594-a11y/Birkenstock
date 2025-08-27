# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    """
    主函数：从 initial_urls.json 获取初始 URL 列表，然后获取所有颜色链接并拼接
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        initial_urls_file = 'birkenstock_campaign_product_urls.json'
        output_json_file = '所有颜色变体URL.json' # 更新输出文件名
        all_products_data = [] # 初始化 all_products_data

        try:
            with open(initial_urls_file, 'r', encoding='utf-8') as f:
                initial_urls = json.load(f)
            total_categories = len(initial_urls)
            print(f"从 {initial_urls_file} 读取到 {total_categories} 个分类数据。")
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
        # 存储所有待处理的URL和对应的分类
        urls_to_process_with_category = []
        for category_data in initial_urls:
            level1_category = category_data.get('level1_category', 'N/A')
            level2_category = category_data.get('level2_category', 'N/A')
            level3_category = category_data.get('level3_category', 'N/A')
            for url in category_data['product_urls']:
                urls_to_process_with_category.append({
                    'url': url,
                    'level1_category': level1_category,
                    'level2_category': level2_category,
                    'level3_category': level3_category
                })

        total_urls_to_process = len(urls_to_process_with_category)
        print(f"从 {initial_urls_file} 读取到 {total_urls_to_process} 个待处理URL。")

        processed_urls_count = 0
        for i, item in enumerate(urls_to_process_with_category):
            initial_url = item['url']
            level1_category = item['level1_category']
            level2_category = item['level2_category']
            level3_category = item['level3_category']
            processed_urls_count += 1
            print(f"正在处理第 {processed_urls_count}/{total_urls_to_process} 条初始URL: {initial_url} (分类: {level3_category})")
            try:
                print(f"导航到初始URL: {initial_url}")
                await page.goto(initial_url, wait_until='domcontentloaded') # 增加等待策略

                colors = {}
                # 尝试等待颜色切换器出现，最多等待5秒，并确保可见
                try:
                    await page.wait_for_selector('ul.swatches.color li a.swatchanchor.width-type.color', timeout=5000, state='visible')
                except Exception:
                    pass # 如果超时，则表示未找到颜色切换器，继续执行
                color_elements = await page.query_selector_all('ul.swatches.color li a.swatchanchor.width-type.color')

                # 获取当前产品的颜色和URL
                current_url = page.url
                current_color_text = 'N/A' # 默认值

                # 尝试从 span.product-color-value 获取当前颜色文本
                current_color_text_element = await page.query_selector('span.product-color-value')
                if current_color_text_element:
                    current_color_text = await current_color_text_element.text_content()
                else:
                    # 如果 span.product-color-value 不存在，尝试从 span.selection-text 获取
                    selection_text_element = await page.query_selector('span.selection-text')
                    if selection_text_element:
                        current_color_text = await selection_text_element.get_attribute('data-value')
                        if not current_color_text:
                            current_color_text = await selection_text_element.text_content()
                    
                colors[current_color_text] = current_url

                if not color_elements:
                    print(f"URL {initial_url} 未找到颜色切换器。将只采集此URL。")
                else:
                    for element in color_elements:
                        color_text = await element.get_attribute('data-value')
                        if not color_text:
                            color_text_raw = await element.get_attribute('aria-label')
                            color_text = color_text_raw.replace('Color: ', '') if color_text_raw else 'N/A'
                        color_link = await element.get_attribute('href')
                        if color_link and color_link.startswith('/'):
                            full_link = f'https://www.birkenstock.com{color_link}'
                        else:
                            full_link = color_link
                        colors[color_text] = full_link

                print(f"URL {initial_url} 找到以下颜色链接: {colors}")
                print("---")

                for color_text, url in colors.items():
                    print(f"开始处理颜色: {color_text} ({url})")
                    
                    product_data = {
                        'url': url,
                        'color': color_text,
                        'level1_category': level1_category,
                        'level2_category': level2_category,
                        'level3_category': level3_category
                    }
                    
                    all_products_data.append(product_data)
                    # 每处理一次就写入一次 JSON 文件
                    with open(output_json_file, 'w', encoding='utf-8') as f:
                        json.dump(all_products_data, f, ensure_ascii=False, indent=4)
                    print(f"已处理颜色 {color_text} 的数据并保存到 {output_json_file}。")
                    print(f"已保存数据: {json.dumps(product_data, ensure_ascii=False, indent=4)}")
                    print("---")
                
            except Exception as e:
                print(f"处理URL {initial_url} 时发生错误: {e}")
            
        print(f"所有待处理产品数据已成功保存到 {output_json_file} 文件。")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
