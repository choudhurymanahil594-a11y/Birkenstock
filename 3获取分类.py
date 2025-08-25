# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_categories(initial_url):
    """
    采集给定页面上所有分类的URL和标题，包括一级、二级和三级分类。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        all_categories_data = []

        try:
            print(f"导航到初始URL: {initial_url}")
            await page.goto(initial_url)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000) # 等待页面加载完成，特别是动态内容

            # 提取所有一级分类
            first_level_category_elements = await page.query_selector_all('a.xlt-firstLevelCategory.a-level-1')
            
            if not first_level_category_elements:
                print("未找到任何一级分类链接。请检查选择器或页面结构。")
            else:
                print(f"找到 {len(first_level_category_elements)} 个一级分类。")
                for i, first_level_element in enumerate(first_level_category_elements):
                    first_level_title = await first_level_element.text_content()
                    first_level_href = await first_level_element.get_attribute('href')
                    
                    if not first_level_title or not first_level_href:
                        continue

                    first_level_data = {
                        "level1_category": first_level_title.strip(),
                        "level1_url": first_level_href,
                        "sub_categories": []
                    }
                    
                    print(f"处理一级分类: {first_level_data['level1_category']}")

                    # 模拟鼠标悬停以展开子菜单
                    await first_level_element.hover()
                    await page.wait_for_timeout(1000) # 等待子菜单显示

                    # 提取二级分类
                    # 假设二级分类在展开的菜单中，并且可以通过 'a.a-level-2' 选择器找到
                    second_level_category_elements = await page.query_selector_all('a.a-level-2')
                    
                    if not second_level_category_elements:
                        print(f"未找到一级分类 '{first_level_data['level1_category']}' 下的任何二级分类。")
                    else:
                        for second_level_element in second_level_category_elements:
                            second_level_title = await second_level_element.text_content()
                            second_level_href = await second_level_element.get_attribute('href')

                            if not second_level_title or not second_level_href:
                                continue

                            second_level_data = {
                                "level2_category": second_level_title.strip(),
                                "level2_url": second_level_href,
                                "sub_categories": []
                            }
                            
                            print(f"  处理二级分类: {second_level_data['level2_category']}")

                            # 提取三级分类
                            # 假设三级分类在二级分类的某个父元素下，或者在整个菜单中
                            # 这里我们使用原始的三级分类选择器，并假设它在当前展开的菜单中可见
                            third_level_category_elements = await page.query_selector_all('li.li-level-3 a.a-level-3')
                            
                            if not third_level_category_elements:
                                print(f"    未找到二级分类 '{second_level_data['level2_category']}' 下的任何三级分类。")
                            else:
                                for third_level_element in third_level_category_elements:
                                    third_level_title = await third_level_element.text_content()
                                    third_level_href = await third_level_element.get_attribute('href')

                                    if not third_level_title or not third_level_href:
                                        continue

                                    third_level_data = {
                                        "level3_category": third_level_title.strip(),
                                        "level3_url": third_level_href
                                    }
                                    second_level_data["sub_categories"].append(third_level_data)
                                    print(f"      找到三级分类: {third_level_data['level3_category']}")
                            
                            first_level_data["sub_categories"].append(second_level_data)
                    
                    all_categories_data.append(first_level_data)
                    # 鼠标移开，关闭当前一级菜单，为下一个一级菜单做准备
                    await page.mouse.move(0, 0) # 移动鼠标到页面左上角
                    await page.wait_for_timeout(500) # 等待菜单收起

            print(f"总共找到 {len(all_categories_data)} 个一级分类。")
            print("---")

            # 将分类数据写入JSON文件
            with open('birkenstock_categories_full.json', 'w', encoding='utf-8') as f:
                json.dump(all_categories_data, f, ensure_ascii=False, indent=4)
            
            print("所有分类的URL和标题已成功保存到 birkenstock_categories_full.json 文件。")

        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    categories_page_url = 'https://www.birkenstock.com/sg/' 
    asyncio.run(scrape_categories(categories_page_url))
