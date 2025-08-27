# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_product_urls_from_category(browser, category_data):
    """
    从单个分类页面上采集所有产品的URL。
    """
    url = category_data['level3_url']
    all_product_urls = []
    context = None
    page = None
    try:
        context = await browser.new_context()
        page = await context.new_page()
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
            print("在此页面上第二步_未找到任何产品接。")
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
    finally:
        if page:
            await page.close()
        if context:
            await context.close()
    
    return all_product_urls, category_data

async def main():
    """
    主函数，用于组织整个采集流程。
    """
    # 步骤 1: 从JSON文件中读取分类信息
    try:
        with open('第一步_导航目录.json', 'r', encoding='utf-8') as f:
            categories_data = json.load(f)
    except FileNotFoundError:
        print("错误: 未找到 第一步_导航目录.json 文件。")
        return
    except json.JSONDecodeError:
        print("错误: 解析 第一步_导航目录.json 文件失败。")
        return

    # 步骤 2: 查找所有三级分类信息（包括名称和URL）
    third_level_categories_to_scrape = []
    for level1_cat in categories_data:
        level1_category = level1_cat.get('level1_category')
        level1_url = level1_cat.get('level1_url')
        for level2_cat in level1_cat.get('children', []):
            level2_category = level2_cat.get('level2_category')
            level2_url = level2_cat.get('level2_url')
            for level3_cat in level2_cat.get('children', []):
                if 'level3_url' in level3_cat and 'level3_category' in level3_cat:
                    third_level_categories_to_scrape.append({
                        "level1_category": level1_category,
                        "level1_url": level1_url,
                        "level2_category": level2_category,
                        "level2_url": level2_url,
                        "level3_category": level3_cat['level3_category'],
                        "level3_url": level3_cat['level3_url'],
                        "product_urls": [] # 初始化一个空列表来存储产品URL
                    })
    if not third_level_categories_to_scrape:
        print("未找到任何三级分类。")
        return

    final_third_level_categories = third_level_categories_to_scrape
    
    print(f"找到 {len(final_third_level_categories)} 个三级分类进行采集。")

    # 步骤 3: 采集所有找到的三级分类下的产品URL
    total_product_urls_count = 0
    urls_without_products = [] # 初始化一个空列表来存储未找到产品链接的URL
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 设置并发限制
        concurrency_limit = 5  # 可以根据需要调整并发数量
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def bounded_scrape(browser, category_data, semaphore):
            async with semaphore:
                return await scrape_product_urls_from_category(browser, category_data)

        # 创建一个列表来存储所有的异步任务
        tasks = []
        for category_data in final_third_level_categories:
            tasks.append(bounded_scrape(browser, category_data, semaphore))
        
        # 并发运行所有任务
        results = await asyncio.gather(*tasks)

        # 处理结果
        for scraped_urls, original_category_data in results:
            original_category_data['product_urls'] = scraped_urls
            total_product_urls_count += len(original_category_data['product_urls'])
            
            if not scraped_urls:
                urls_without_products.append(original_category_data['level3_url'])
                print(f"在三级分类 '{original_category_data['level3_category']}' ({original_category_data['level3_url']}) 页面上第二步_未找到任何产品接。")
            else:
                print(f"从三级分类 '{original_category_data['level3_category']}' ({original_category_data['level3_url']}) 采集了 {len(original_category_data['product_urls'])} 个产品URL")
            print("---")

        await browser.close()

    # 步骤 4: 将包含三级分类和产品URL的结果保存到文件
    print(f"总共找到 {total_product_urls_count} 个产品URL。")

    with open('第二步_产品链接.json', 'w', encoding='utf-8') as f:
        json.dump(final_third_level_categories, f, ensure_ascii=False, indent=4)
    
    print("所有三级分类及其下的产品URL已成功保存到 第二步_产品链接.json 文件。")

    # 步骤 5: 将未找到产品链接的URL保存到单独的文件
    if urls_without_products:
        with open('第二步_未找到任何产品.json', 'w', encoding='utf-8') as f:
            json.dump(urls_without_products, f, ensure_ascii=False, indent=4)
        print(f"已将 {len(urls_without_products)} 个未找到产品链接的URL保存到 第二步_未找到任何产品接.json 文件。")
    else:
        print("所有分类页面都找到了产品链接，未生成 第二步_未找到任何产品接.json 文件。")

if __name__ == "__main__":
    asyncio.run(main())
