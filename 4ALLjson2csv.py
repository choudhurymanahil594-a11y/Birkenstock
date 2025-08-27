import json
import csv
import re

def generate_handle(title, color):
    """
    根据产品标题和颜色生成一个对 Shopify 友好的 handle。
    格式为：handle-color-Type
    参数:
        title (str): 产品标题
        color (str): 产品颜色
    返回:
        str: 生成的 handle 字符串
    """
    # 通常取标题中逗号前的部分作为基础
    title_part = title.split(',')[0]

    def _sanitize(text):
        # 移除特殊字符，转为小写，用连字符替换空格
        s = re.sub(r'[^a-z0-9\s-]', '', str(text).lower())
        s = re.sub(r'[\s-]+', '-', s).strip('-')
        return s

    handle_base = _sanitize(title_part)
    color_part = _sanitize(color)

    if color_part:
        # 返回格式为 "handle-color-Type" 的 handle
        return f"{handle_base}-{color_part}-Customize"
    return handle_base

def generate_sku(handle, size, color, index):
    """
    生成唯一的SKU
    """
    size_clean = re.sub(r'[^a-zA-Z0-9]', '', str(size))
    color_clean = re.sub(r'[^a-zA-Z0-9]', '', str(color))
    return f"{handle[:3].upper()}_{color_clean}_{size_clean}_{index:03d}"

def build_product_category(category_data):
    """
    构建产品分类路径
    """
    categories = []
    if category_data.get('level1_category'):
        categories.extend(category_data['level1_category'])
    if category_data.get('level2_category'):
        categories.extend(category_data['level2_category'])
    if category_data.get('level3_category'):
        categories.append(category_data['level3_category'])
    
    return ' > '.join(filter(None, categories))

def convert_json_to_shopify_csv():
    """
    读取 all_scraped_products.json 文件，并将其转换为 Shopify 兼容的 CSV 导入文件。
    遵循官方模板格式：主产品行包含完整信息，变体行只包含变体信息，图片行只包含图片信息。
    """
    Type = 'Customize' # 定义产品类型
    Vendor = 'Birkenstock' # 品牌名称

    json_input_file = 'all_scraped_products.json'
    csv_output_file = 'shopify_import.csv'
    
    # 使用官方模板的完整表头
    headers = [
        'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Product Category', 'Type', 'Tags', 'Published',
        'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value', 'Option3 Name', 'Option3 Value',
        'Variant SKU', 'Variant Grams', 'Variant Inventory Tracker', 'Variant Inventory Qty',
        'Variant Inventory Policy', 'Variant Fulfillment Service', 'Variant Price', 'Variant Compare At Price',
        'Variant Requires Shipping', 'Variant Taxable', 'Variant Barcode', 'Image Src', 'Image Position', 
        'Image Alt Text', 'Gift Card', 'SEO Title', 'SEO Description', 'Google Shopping / Google Product Category',
        'Google Shopping / Gender', 'Google Shopping / Age Group', 'Google Shopping / MPN', 
        'Google Shopping / Condition', 'Google Shopping / Custom Product', 'Variant Image', 'Variant Weight Unit',
        'Variant Tax Code', 'Cost per item', 'Included / United States', 'Price / United States',
        'Compare At Price / United States', 'Included / International', 'Price / International',
        'Compare At Price / International', 'Status'
    ]

    try:
        # 读取 JSON 输入文件
        with open(json_input_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
    except FileNotFoundError:
        print(f"错误: 输入文件 '{json_input_file}' 未找到。请先运行 '4.多个链接2json'。")
        return

    try:
        # 打开 CSV 输出文件
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for product in products:
                # 提取颜色
                color = ''
                url = product.get('url', '')
                color_match = re.search(r'dwvar_.*?_color=([a-zA-Z0-9]+)', url)
                if color_match:
                    color = color_match.group(1)
                
                handle = generate_handle(product.get('title', ''), color)
                
                # 处理价格
                price_str = product.get('price', '0').replace('$', '')
                try:
                    original_price = float(price_str)
                    compare_at_price = f"{original_price:.2f}"
                    discounted_price = f"{(original_price * 0.5):.2f}"
                except (ValueError, TypeError):
                    compare_at_price = "0.00"
                    discounted_price = "0.00"

                # 构建分类和标签
                product_category = build_product_category(product.get('category', {}))
                categories = []
                category_data = product.get('category', {})
                if category_data.get('level1_category'):
                    categories.extend(category_data['level1_category'])
                if category_data.get('level2_category'):
                    categories.extend(category_data['level2_category'])
                if category_data.get('level3_category'):
                    categories.append(category_data['level3_category'])
                
                all_tags = [Type] + categories
                tags_str = ','.join(filter(None, all_tags))

                # 提取尺寸
                sizes_data = product.get('sizes', {})
                men_sizes = sizes_data.get('men', [])
                women_sizes = sizes_data.get('women', [])
                
                # 确定选项结构
                if women_sizes and men_sizes:
                    option1_name = 'Women'
                    option2_name = 'Men'
                    option3_name = 'Color'
                    option1_values = women_sizes
                    option2_values = men_sizes
                    option3_values = [color]
                elif women_sizes:
                    option1_name = 'Women'
                    option2_name = 'Color'
                    option3_name = ''
                    option1_values = women_sizes
                    option2_values = [color]
                    option3_values = []
                elif men_sizes:
                    option1_name = 'Men'
                    option2_name = 'Color'
                    option3_name = ''
                    option1_values = men_sizes
                    option2_values = [color]
                    option3_values = []
                else:
                    option1_name = 'Size'
                    option2_name = 'Color'
                    option3_name = ''
                    option1_values = ['Default Size']
                    option2_values = [color]
                    option3_values = []

                # 主产品行 - 包含完整信息
                main_row = {
                    'Handle': handle,
                    'Title': product.get('title', ''),
                    'Body (HTML)': f"<p>{product.get('description', '')}</p>",
                    'Vendor': Vendor,
                    'Product Category':"",
                    'Type': Type,
                    'Tags': tags_str,
                    'Published': 'TRUE',
                    'Option1 Name': option1_name,
                    'Option1 Value': option1_values[0] if option1_values else '',
                    'Option2 Name': option2_name,
                    'Option2 Value': option2_values[0] if option2_values else '',
                    'Option3 Name': option3_name,
                    'Option3 Value': option3_values[0] if option3_values else '',
                    'Variant SKU': generate_sku(handle, option1_values[0] if option1_values else 'DEF', color, 1),
                    'Variant Grams': '500',  # 默认重量
                    'Variant Inventory Tracker': 'shopify',
                    'Variant Inventory Qty': '100',  # 默认库存
                    'Variant Inventory Policy': 'deny',
                    'Variant Fulfillment Service': 'manual',
                    'Variant Price': discounted_price,
                    'Variant Compare At Price': compare_at_price,
                    'Variant Requires Shipping': 'TRUE',
                    'Variant Taxable': 'TRUE',
                    'Variant Barcode': '',
                    'Image Src': product.get('image_urls', [])[0] if product.get('image_urls') else '',
                    'Image Position': '1',
                    'Image Alt Text': product.get('title', ''),
                    'Gift Card': 'FALSE',
                    'SEO Title': product.get('title', ''),
                    'SEO Description': product.get('description', '')[:255] if product.get('description') else '',
                    'Google Shopping / Google Product Category': '212',  # 鞋类
                    'Google Shopping / Gender': 'unisex',
                    'Google Shopping / Age Group': 'adult',
                    'Google Shopping / MPN': '',
                    'Google Shopping / Condition': 'new',
                    'Google Shopping / Custom Product': 'TRUE',
                    'Variant Image': '',
                    'Variant Weight Unit': 'g',
                    'Variant Tax Code': '',
                    'Cost per item': '',
                    'Included / United States': 'TRUE',
                    'Price / United States': discounted_price,
                    'Compare At Price / United States': compare_at_price,
                    'Included / International': 'TRUE',
                    'Price / International': discounted_price,
                    'Compare At Price / International': compare_at_price,
                    'Status': 'active'
                }
                writer.writerow(main_row)

                # 生成所有变体组合
                variant_index = 2
                for val1 in option1_values:
                    for val2 in option2_values:
                        for val3 in option3_values if option3_values else ['']:
                            # 跳过主产品行已经包含的组合
                            if (val1 == option1_values[0] and val2 == option2_values[0] and 
                                (not option3_values or val3 == option3_values[0])):
                                continue
                            
                            # 创建完整的变体行，包含所有必要的字段
                            variant_row = {}
                            # 先设置所有字段为空值
                            for header in headers:
                                variant_row[header] = ''
                            
                            # 然后设置变体相关的字段
                            variant_row.update({
                                'Handle': handle,
                                'Option1 Name': option1_name,
                                'Option1 Value': val1,
                                'Option2 Name': option2_name,
                                'Option2 Value': val2,
                                'Option3 Name': option3_name,
                                'Option3 Value': val3 if option3_values else '',
                                'Variant SKU': generate_sku(handle, val1, color, variant_index),
                                'Variant Grams': '500',
                                'Variant Inventory Tracker': 'shopify',
                                'Variant Inventory Qty': '100',
                                'Variant Inventory Policy': 'deny',
                                'Variant Fulfillment Service': 'manual',
                                'Variant Price': discounted_price,
                                'Variant Compare At Price': compare_at_price,
                                'Variant Requires Shipping': 'TRUE',
                                'Variant Taxable': 'TRUE'
                            })
                            
                            writer.writerow(variant_row)
                            variant_index += 1

                # 为其余图片创建额外的行
                image_urls = product.get('image_urls', [])
                for i, image_url in enumerate(image_urls[1:], start=2):
                    image_row = {
                        'Handle': handle,
                        'Image Src': image_url,
                        'Image Position': str(i),
                        'Image Alt Text': f"{product.get('title', '')} - Image {i}"
                    }
                    writer.writerow(image_row)

        print(f"成功！数据已转换为 Shopify 格式并保存到 '{csv_output_file}'。")
        print("遵循官方模板格式：主产品行包含完整信息，变体行只包含变体信息，图片行只包含图片信息。")
    except PermissionError:
        print(f"\n错误：写入 '{csv_output_file}' 时权限被拒绝。")
        print("请确保该文件没有在其他程序（如 Microsoft Excel）中打开，然后重试。")
    except Exception as e:
        print(f"发生意外错误: {e}")

if __name__ == '__main__':
    convert_json_to_shopify_csv()
