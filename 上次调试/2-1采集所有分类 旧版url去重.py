# -*- coding: utf-8 -*-
# 包含url去重

import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_product_urls_from_page(page, url):
    """
    从单个页面上采集所有产品的URL。
    """
    all_product_urls = []
    try:
        print(f"正在导航到URL: {url}")
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state('domcontentloaded')

        # 循环点击“加载更多”按钮，直到所有产品都加载完毕
        while True:
            # 尝试查找“加载更多”按钮
            load_more_button_locator = page.locator('button.button-custom-black.outline')
            
            # 检查按钮是否存在且可见
            if await load_more_button_locator.is_visible():
                print("正在点击 '加载更多' 按钮...")
                try:
                    await load_more_button_locator.click(timeout=5000) # 增加点击超时时间
                    # 等待一段时间，让新产品加载出来
                    await page.wait_for_timeout(2000)
                except Exception as click_e:
                    print(f"点击 '加载更多' 按钮时发生错误: {click_e}")
                    break # 如果点击失败，则退出循环
            else:
                print("未找到 '加载更多' 按钮，或所有产品已加载完毕。")
                break

        # 提取所有产品链接
        product_tile_elements = await page.query_selector_all('a.product-tile')
        if not product_tile_elements:
            print("在此页面上未找到任何产品链接。")
        else:
            for element in product_tile_elements:
                href = await element.get_attribute('href')
                if href:
                    # 确保URL是完整的
                    if href.startswith('/'):
                        full_url = f'https://www.birkenstock.com{href}'
                    else:
                        full_url = href
                    all_product_urls.append(full_url)
    except Exception as e:
        print(f"采集 {url} 时发生错误: {e}")
    
    return all_product_urls

async def main():
    """
    主函数，用于组织整个采集流程。
    """
    # 步骤 1: 从JSON文件中读取分类信息
    try:
        with open('navigation_data.json', 'r', encoding='utf-8') as f:
            categories_data = json.load(f)
    except FileNotFoundError:
        print("错误: 未找到 navigation_data.json 文件。")
        return
    except json.JSONDecodeError:
        print("错误: 解析 navigation_datal.json 文件失败。")
        return

    # 步骤 2: 查找所有三级分类信息（包括名称和URL）
    third_level_categories_to_scrape = []
    for level1_cat in categories_data:
        for level2_cat in level1_cat.get('sub_categories', []):
            for level3_cat in level2_cat.get('sub_categories', []):
                if 'level3_url' in level3_cat and 'level3_category' in level3_cat:
                    third_level_categories_to_scrape.append({
                        "level3_category": level3_cat['level3_category'],
                        "level3_url": level3_cat['level3_url'],
                        "product_urls": [] # 初始化一个空列表来存储产品URL
                    })

    if not third_level_categories_to_scrape:
        print("未找到任何三级分类。")
        return

    # 对三级分类进行去重（基于URL）
    unique_third_level_categories = {}
    for cat in third_level_categories_to_scrape:
        unique_third_level_categories[cat['level3_url']] = cat
    
    final_third_level_categories = list(unique_third_level_categories.values())
    
    print(f"找到 {len(final_third_level_categories)} 个唯一的三级分类进行采集。")

    # 步骤 3: 采集所有找到的三级分类下的产品URL
    total_product_urls_count = 0
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        for category_data in final_third_level_categories:
            url = category_data['level3_url']
            scraped_urls = await scrape_product_urls_from_page(page, url)
            
            # 去重并添加到当前三级分类的 product_urls 列表中
            category_data['product_urls'] = sorted(list(set(scraped_urls)))
            total_product_urls_count += len(category_data['product_urls'])
            
            print(f"从三级分类 '{category_data['level3_category']}' ({url}) 采集了 {len(category_data['product_urls'])} 个产品URL")
            print("---")

        await browser.close()

    # 步骤 4: 将包含三级分类和产品URL的结果保存到文件
    print(f"总共找到 {total_product_urls_count} 个产品URL。")

    with open('birkenstock_campaign_product_urls.json', 'w', encoding='utf-8') as f:
        json.dump(final_third_level_categories, f, ensure_ascii=False, indent=4)
    
    print("所有三级分类及其下的产品URL已成功保存到 birkenstock_campaign_product_urls.json 文件。")

if __name__ == "__main__":
    asyncio.run(main())
