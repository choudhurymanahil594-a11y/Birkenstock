import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 从文件中读取代理列表
def load_proxies(file_path):
    try:
        with open(file_path, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        return proxies
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return []

# 检测单个代理
def check_proxy(proxy):
    url = 'http://httpbin.org/get'  # 使用一个可靠的测试网址
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }
    timeout = 5  # 设置超时时间（秒）

    try:
        start_time = time.time()
        response = requests.get(url, proxies=proxies, timeout=timeout)
        end_time = time.time()

        if response.status_code == 200:
            latency = round((end_time - start_time) * 1000, 2)  # 转换为毫秒
            print(f"Proxy {proxy} is working! Latency: {latency} ms")
            return {'proxy': proxy, 'latency': latency}
        else:
            print(f"Proxy {proxy} failed with status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Proxy {proxy} failed: {e}")
        return None

# 主函数
def main():
    proxy_list_file = 'proxy.txt'
    working_proxies_file = 'working_proxies.json'

    proxies_to_check = load_proxies(proxy_list_file)
    if not proxies_to_check:
        return

    working_proxies = []
    
    # 使用多线程加速检测
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(check_proxy, proxy) for proxy in proxies_to_check]
        for future in as_completed(futures):
            result = future.result()
            if result:
                working_proxies.append(result)

    # 按照速度排序
    working_proxies.sort(key=lambda x: x['latency'])

    # 保存到 JSON 文件
    with open(working_proxies_file, 'w') as f:
        json.dump(working_proxies, f, indent=4)

    print(f"\nSuccessfully checked {len(proxies_to_check)} proxies.")
    print(f"Found {len(working_proxies)} working proxies.")
    print(f"Results saved to '{working_proxies_file}'.")

if __name__ == "__main__":
    main()