# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright
import json
import time
from typing import List, Dict, Tuple
import sys
import os

# 添加代理模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'proxy'))
from proxy import ProxyManager

class ProxyRotator:
    """
    代理轮换器，为每个任务分配代理
    
    注意：由于Playwright不支持带认证的SOCKS5代理，
    当前版本会记录代理信息但使用直连模式进行采集。
    代理信息可用于其他HTTP请求或后续功能扩展。
    """
    
    def __init__(self, proxy_file_path: str = "proxy/working_proxies.json"):
        # 确保使用正确的文件路径
        self.proxy_file_path = proxy_file_path
        self.proxy_manager = ProxyManager(proxy_file_path, use_json=True)
        self.working_proxies = []
        self.current_index = 0
        self.load_and_test_proxies()
    
    def load_and_test_proxies(self):
        """加载并测试所有代理"""
        print("🔄 正在加载并测试代理...")
        print("⚠️  注意：Playwright不支持带认证的SOCKS5代理，将使用直连模式")
        
        # 首先尝试直接读取代理文件
        try:
            if os.path.exists(self.proxy_file_path):
                with open(self.proxy_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    raw_proxies = data.get('working_proxies', [])
                    print(f"📁 从文件加载了 {len(raw_proxies)} 个原始代理")
                    
                    # 直接使用这些代理，不进行测试（因为文件中的代理应该已经测试过了）
                    self.working_proxies = raw_proxies
                    
                    if self.working_proxies:
                        print(f"✅ 成功加载 {len(self.working_proxies)} 个代理")
                        print("📝 代理信息将用于任务分配，但采集时使用直连模式")
                        # 显示代理信息
                        for i, proxy in enumerate(self.working_proxies):
                            print(f"  {i+1}. {proxy['ip']}:{proxy['port']} ({proxy['username']})")
                        return
            else:
                print(f"⚠️  代理文件不存在: {self.proxy_file_path}")
        except Exception as e:
            print(f"❌ 加载代理文件失败: {e}")
        
        # 如果直接加载失败，尝试使用ProxyManager测试
        print("🔄 尝试使用ProxyManager测试代理...")
        try:
            # 重新初始化ProxyManager，使用绝对路径
            abs_path = os.path.abspath(self.proxy_file_path)
            print(f"🔍 尝试使用绝对路径: {abs_path}")
            
            proxy_manager = ProxyManager(abs_path, use_json=True)
            all_proxies = proxy_manager.get_all_proxies()
            print(f"📊 ProxyManager加载了 {len(all_proxies)} 个代理")
            
            if all_proxies:
                # 测试前几个代理
                test_count = min(3, len(all_proxies))
                working_proxies = []
                
                for i in range(test_count):
                    proxy = all_proxies[i]
                    print(f"🧪 测试代理 {i+1}/{test_count}: {proxy['ip']}:{proxy['port']}")
                    if proxy_manager.test_proxy_with_requests(proxy, timeout=5):
                        working_proxies.append(proxy)
                        print(f"  ✅ 代理可用")
                    else:
                        print(f"  ❌ 代理不可用")
                
                self.working_proxies = working_proxies
                
                if self.working_proxies:
                    print(f"✅ 成功测试并加载 {len(self.working_proxies)} 个可用代理")
                    print("📝 代理信息将用于任务分配，但采集时使用直连模式")
                    return
                else:
                    print("❌ 所有测试的代理都不可用")
            else:
                print("❌ ProxyManager没有加载到任何代理")
                
        except Exception as e:
            print(f"❌ 代理测试失败: {e}")
        
        print("⚠️  将使用直连模式")
    
    def get_next_proxy(self) -> Dict:
        """获取下一个代理"""
        if not self.working_proxies:
            return None
        
        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        return proxy
    
    def get_proxy_count(self) -> int:
        """获取可用代理数量"""
        return len(self.working_proxies)

async def scrape_product_urls_from_category(browser, category_data, semaphore, proxy_info=None):
    """
    从单个分类页面上采集所有产品的URL。
    """
    async with semaphore:  # 使用信号量控制并发
        url = category_data['level3_url']
        all_product_urls = []
        context = None
        page = None
        
        try:
            # 创建浏览器上下文，如果提供了代理则使用代理
            if proxy_info:
                # Playwright不支持带认证的SOCKS5代理，所以使用直连模式
                # 但我们可以记录代理信息用于其他用途
                print(f"  [{category_data['level3_category']}] 代理信息: {proxy_info['ip']}:{proxy_info['port']} (Playwright不支持带认证的SOCKS5代理，使用直连模式)")
                context = await browser.new_context()
            else:
                context = await browser.new_context()
                print(f"  [{category_data['level3_category']}] 使用直连模式")
            
            page = await context.new_page()
            print(f"正在处理: {category_data['level3_category']} - {url}")
            
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')

            # 循环点击"加载更多"按钮，直到所有产品都加载完毕
            load_more_count = 0
            while True:
                # 尝试查找"加载更多"按钮
                load_more_button_locator = page.locator('button.button-custom-black.outline')
                
                # 检查按钮是否存在且可见
                if await load_more_button_locator.is_visible():
                    load_more_count += 1
                    print(f"  [{category_data['level3_category']}] 第{load_more_count}次点击 '加载更多' 按钮...")
                    try:
                        await load_more_button_locator.click(timeout=5000)
                        # 等待新产品加载
                        await page.wait_for_timeout(2000)
                    except Exception as click_e:
                        print(f"  [{category_data['level3_category']}] 点击 '加载更多' 按钮失败: {click_e}")
                        break
                else:
                    if load_more_count > 0:
                        print(f"  [{category_data['level3_category']}] 已加载完毕，共点击了 {load_more_count} 次")
                    break

            # 提取所有产品链接
            product_tile_elements = await page.query_selector_all('a.product-tile')
            if not product_tile_elements:
                print(f"  [{category_data['level3_category']}] 未找到任何产品链接")
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
                
                print(f"  [{category_data['level3_category']}] 成功采集到 {len(all_product_urls)} 个产品URL")
                
        except Exception as e:
            print(f"  [{category_data['level3_category']}] 采集时发生错误: {e}")
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
        
        return all_product_urls, category_data

async def main():
    """
    主函数，使用异步5线程处理，集成代理功能
    """
    start_time = time.time()
    
    # 初始化代理轮换器
    print("🚀 初始化代理系统...")
    proxy_rotator = ProxyRotator()
    
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

    # 步骤 2: 查找所有三级分类信息
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
                        "product_urls": []
                    })
    
    if not third_level_categories_to_scrape:
        print("未找到任何三级分类。")
        return

    print(f"找到 {len(third_level_categories_to_scrape)} 个三级分类进行采集。")
    print("开始异步5线程处理...")

    # 步骤 3: 使用异步5线程采集产品URL
    total_product_urls_count = 0
    urls_without_products = []
    processed_categories = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # 设置5个并发线程
        concurrency_limit = 10
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        # 将分类分成批次处理，每批5个
        batch_size = concurrency_limit
        category_batches = [
            third_level_categories_to_scrape[i:i + batch_size] 
            for i in range(0, len(third_level_categories_to_scrape), batch_size)
        ]
        
        print(f"将 {len(third_level_categories_to_scrape)} 个分类分成 {len(category_batches)} 批处理")
        
        # 逐批处理，每批5个并发
        for batch_index, batch in enumerate(category_batches, 1):
            print(f"\n正在处理第 {batch_index}/{len(category_batches)} 批 ({len(batch)} 个分类)...")
            
            # 创建当前批次的异步任务
            batch_tasks = []
            for category_data in batch:
                task = scrape_product_urls_from_category(browser, category_data, semaphore, proxy_rotator.get_next_proxy())
                batch_tasks.append(task)
            
            # 等待当前批次完成
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理当前批次的结果
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"批次处理中发生错误: {result}")
                    continue
                    
                scraped_urls, original_category_data = result
                original_category_data['product_urls'] = scraped_urls
                processed_categories.append(original_category_data)
                total_product_urls_count += len(scraped_urls)
                
                if not scraped_urls:
                    urls_without_products.append(original_category_data['level3_url'])
                else:
                    print(f"✓ {original_category_data['level3_category']}: {len(scraped_urls)} 个产品URL")
            
            # 批次间短暂休息，避免过度请求
            if batch_index < len(category_batches):
                await asyncio.sleep(1)
        
        await browser.close()

    # 步骤 4: 保存结果
    elapsed_time = time.time() - start_time
    print(f"\n采集完成！")
    print(f"总耗时: {elapsed_time:.2f} 秒")
    print(f"总共采集到 {total_product_urls_count} 个产品URL")
    print(f"成功处理 {len(processed_categories)} 个分类")
    print(f"未找到产品的分类: {len(urls_without_products)} 个")
    print(f"使用的代理数量: {proxy_rotator.get_proxy_count()}")

    # 保存包含产品URL的分类数据
    with open('第二步_产品链接.json', 'w', encoding='utf-8') as f:
        json.dump(processed_categories, f, ensure_ascii=False, indent=4)
    print("产品链接数据已保存到 第二步_产品链接.json")

    # 保存未找到产品的URL
    if urls_without_products:
        with open('第二步_未找到任何产品.json', 'w', encoding='utf-8') as f:
            json.dump(urls_without_products, f, ensure_ascii=False, indent=4)
        print("未找到产品的URL已保存到 第二步_未找到任何产品.json")

if __name__ == "__main__":
    asyncio.run(main())
