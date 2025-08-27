# -*- coding: utf-8 -*-
import json
from collections import defaultdict

INPUT_FILE = '所有颜色变体URL_Cursor.json'
OUTPUT_FILE = '所有颜色变体URL_Cursor_dedup.json'


def main():
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：未找到输入文件 {INPUT_FILE}")
        return
    except json.JSONDecodeError as e:
        print(f"错误：无法解析 {INPUT_FILE} 的JSON：{e}")
        return

    if not isinstance(data, list):
        print("错误：输入JSON顶层应为数组(list)")
        return

    grouped = {}

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"警告：第{idx}项不是对象，已跳过")
            continue

        url = item.get('url')
        if not url:
            print(f"警告：第{idx}项缺少url字段，已跳过")
            continue

        color = item.get('color')
        level1 = item.get('level1_category')
        level2 = item.get('level2_category')
        level3 = item.get('level3_category')

        if url not in grouped:
            grouped[url] = {
                'url': url,
                'color': color,
                'level3_category': level3,
                'level1_category': set([level1]) if level1 else set(),
                'level2_category': set([level2]) if level2 else set(),
            }
        else:
            g = grouped[url]
            # 校验color与level3一致性
            if g.get('color') is None and color is not None:
                g['color'] = color
            elif color is not None and g.get('color') is not None and g['color'] != color:
                print(f"警告：url相同但color不一致：{url} -> '{g['color']}' vs '{color}'，保留首次值")

            if g.get('level3_category') is None and level3 is not None:
                g['level3_category'] = level3
            elif level3 is not None and g.get('level3_category') is not None and g['level3_category'] != level3:
                print(f"警告：url相同但level3_category不一致：{url} -> '{g['level3_category']}' vs '{level3}'，保留首次值")

            # 合并level1/level2分类
            if level1:
                g['level1_category'].add(level1)
            if level2:
                g['level2_category'].add(level2)

    # 输出结果列表
    output_list = []
    for url, obj in grouped.items():
        output_list.append({
            'url': obj['url'],
            'color': obj.get('color'),
            'level3_category': obj.get('level3_category'),
            # 将集合转为去重后的列表
            'level1_category': sorted(list(obj['level1_category'])),
            'level2_category': sorted(list(obj['level2_category'])),
        })

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_list, f, ensure_ascii=False, indent=4)
        print(f"完成：共输入 {len(data)} 条，去重后 {len(output_list)} 条，已写入 {OUTPUT_FILE}")
    except Exception as e:
        print(f"错误：写出结果文件失败：{e}")


if __name__ == '__main__':
    main()
