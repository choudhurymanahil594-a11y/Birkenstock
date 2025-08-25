import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_all_product_urls(initial_url):
    """
    采集给定页面上所有产品的URL
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        all_product_urls = []

        try:
            print(f"导航到初始URL: {initial_url}")
            await page.goto(initial_url)
            await page.wait_for_load_state('domcontentloaded')

            # 循环点击“加载更多”按钮直到所有产品加载完毕
            while True:
                load_more_button = await page.query_selector('button.button-custom-black.outline')
                if load_more_button and await load_more_button.is_visible():
                    print("点击 '加载更多' 按钮...")
                    await load_more_button.click()
                    await page.wait_for_timeout(2000) # 等待新产品加载
                else:
                    print("未找到 '加载更多' 按钮或所有产品已加载。")
                    break

            # 提取所有产品链接
            # 根据提供的HTML，产品链接在 <a class="product-tile"> 元素的 href 属性中
            product_tile_elements = await page.query_selector_all('a.product-tile')
            
            if not product_tile_elements:
                print("未找到任何产品链接。请检查选择器或页面结构。")
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

            # 对URL进行去重
            unique_product_urls = list(set(all_product_urls))
            print(f"找到 {len(all_product_urls)} 个产品URL，其中 {len(unique_product_urls)} 个是唯一的。")
            print("---")

            # 将去重后的URL写入JSON文件
            with open('birkenstock_campaign_product_urls.json', 'w', encoding='utf-8') as f:
                json.dump(unique_product_urls, f, ensure_ascii=False, indent=4)
            
            print("所有唯一的URL已成功保存到 birkenstock_campaign_product_urls.json 文件。")

        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    campaign_url = 'https://www.birkenstock.com/sg/campaign/water-friendly/'
    asyncio.run(scrape_all_product_urls(campaign_url))
