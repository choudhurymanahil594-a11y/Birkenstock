import json

def update_widths(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        products = json.load(f)

    # 使用字典来存储唯一的产品，键为 (title, color)，值为产品数据
    # 并且将宽度存储在一个列表中
    unique_products = {}

    for product in products:
        key = (product['title'], product['color'])
        if key not in unique_products:
            # 如果是新产品，复制一份产品数据，并将宽度初始化为列表
            new_product = product.copy()
            new_product['width'] = [product['width']]
            unique_products[key] = new_product
        else:
            # 如果产品已存在，将当前宽度添加到现有产品的宽度列表中（如果尚未添加）
            if product['width'] not in unique_products[key]['width']:
                unique_products[key]['width'].append(product['width'])

    # 将字典的值转换为列表，形成新的产品列表
    updated_products = list(unique_products.values())

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(updated_products, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    json_file = 'birkenstock_all_products_details.json'
    update_widths(json_file)
    print(f"已更新文件: {json_file} 中的产品宽度信息。")
