import json

try:
    with open('所有颜色变体URL_Cursor.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"JSON对象数量: {len(data)}")
    print(f"数据类型: {type(data)}")
    
    if isinstance(data, list) and len(data) > 0:
        print(f"第一个对象: {data[0]}")
        print(f"最后一个对象: {data[-1]}")
        
        # 检查是否有重复的URL
        urls = [item.get('url') for item in data if isinstance(item, dict)]
        unique_urls = set(urls)
        print(f"唯一URL数量: {len(unique_urls)}")
        print(f"总URL数量: {len(urls)}")
        
        # 检查是否有None或空URL
        none_urls = [url for url in urls if not url]
        print(f"空URL数量: {len(none_urls)}")
        
except Exception as e:
    print(f"错误: {e}")
