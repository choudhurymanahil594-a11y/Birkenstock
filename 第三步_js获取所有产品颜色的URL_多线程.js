// scraper.js
const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path'); // 引入 path 模块
const HttpsProxyAgent = require('https-proxy-agent').HttpsProxyAgent; // 引入代理模块

// 代理管理器类
class ProxyManager {
    constructor(proxies) {
        this.proxies = proxies.map(p => p.proxy); // 只保留代理字符串
        this.currentIndex = 0;
        this.availableProxies = [...this.proxies]; // 可用代理列表
        this.failedProxies = new Set(); // 失败代理集合
        console.log(`已加载 ${this.proxies.length} 个代理。`);
    }

    // 获取下一个代理
    getNextProxy() {
        if (this.availableProxies.length === 0) {
            console.warn('所有代理都已尝试或失败，正在重置代理列表。');
            this.resetProxies();
            if (this.availableProxies.length === 0) {
                throw new Error('没有可用的代理。');
            }
        }
        const proxy = this.availableProxies[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.availableProxies.length;
        return proxy;
    }

    // 标记代理为失败
    markProxyAsFailed(proxy) {
        if (!this.failedProxies.has(proxy)) {
            this.failedProxies.add(proxy);
            this.availableProxies = this.availableProxies.filter(p => p !== proxy);
            console.warn(`代理 ${proxy} 已标记为失败，剩余可用代理数: ${this.availableProxies.length}`);
            // 重置 currentIndex 以避免超出范围
            if (this.currentIndex >= this.availableProxies.length && this.availableProxies.length > 0) {
                this.currentIndex = 0;
            }
        }
    }

    // 重置代理列表
    resetProxies() {
        this.availableProxies = [...this.proxies];
        this.failedProxies.clear();
        this.currentIndex = 0;
        console.log('代理列表已重置。');
    }
}

async function main() {
    console.log("脚本开始运行...");

    const initialUrlsFile = path.join(__dirname, '第二步_产品链接.json'); // 确保文件名正确
    const outputJsonFile = path.join(__dirname, '第三步_所有颜色变体.json');
    const processedUrlsFile = path.join(__dirname, '第三步已采集包含失败.json'); // 新增：记录已处理的URL
    const noColorsFoundFile = path.join(__dirname, '第三步失败无法采集.json'); // 新增：记录没找到颜色变体的URL
    const certErrorsFile = path.join(__dirname, '第三步_证书错误记录.json'); // 新增：记录证书错误的URL
    const proxiesFile = path.join(__dirname, 'working_proxies.json'); // 代理文件
    const maxConcurrency = 10; // 新增：最大并发数
    const requestDelay = 2000; // 新增：请求间隔延迟（毫秒）
    const randomDelayRange = 1000; // 新增：随机延迟范围（毫秒）
    const isHeadless = false; // 新增：控制浏览器是否以无头模式运行 (true 为无头，false 为有头)
    let allProductsData = [];
    let processedUrls = new Set(); // 新增：已处理URL的集合
    let noColorsFoundUrls = []; // 新增：没找到颜色变体的URL列表
    let certErrors = []; // 新增：证书错误URL列表
    let proxyManager; // 代理管理器实例

    // 读取代理
    try {
        const proxiesContent = await fs.readFile(proxiesFile, 'utf-8');
        const proxies = JSON.parse(proxiesContent);
        proxyManager = new ProxyManager(proxies);
    } catch (e) {
        console.error(`读取代理文件时发生错误: ${e.message}`);
        process.exit(1);
    }

    // 新增：延迟函数
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 新增：随机延迟函数
    async function randomDelay() {
        const delay = requestDelay + Math.random() * randomDelayRange;
        console.log(`等待 ${Math.round(delay)}ms...`);
        await sleep(delay);
    }

    // 读取已处理URL记录
    try {
        const processedUrlsContent = await fs.readFile(processedUrlsFile, 'utf-8');
        processedUrls = new Set(JSON.parse(processedUrlsContent));
        console.log(`从 ${processedUrlsFile} 读取到 ${processedUrls.size} 个已处理的URL记录。`);
    } catch (e) {
        if (e.code === 'ENOENT') {
            console.log(`文件 '${processedUrlsFile}' 不存在，将创建新文件。`);
        } else {
            console.warn(`读取已处理URL记录时发生警告: ${e.message}。将创建新的记录文件。`);
        }
    }

    // 读取没找到颜色变体的URL记录
    try {
        const noColorsFoundContent = await fs.readFile(noColorsFoundFile, 'utf-8');
        noColorsFoundUrls = JSON.parse(noColorsFoundContent);
        console.log(`从 ${noColorsFoundFile} 读取到 ${noColorsFoundUrls.length} 个没找到颜色变体的URL记录。`);
    } catch (e) {
        if (e.code === 'ENOENT') {
            console.log(`文件 '${noColorsFoundFile}' 不存在，将创建新文件。`);
        } else {
            console.warn(`读取没找到颜色变体URL记录时发生警告: ${e.message}。将创建新的记录文件。`);
        }
    }

    // 读取证书错误记录
    try {
        const certErrorsContent = await fs.readFile(certErrorsFile, 'utf-8');
        certErrors = JSON.parse(certErrorsContent);
        console.log(`从 ${certErrorsFile} 读取到 ${certErrors.length} 个证书错误记录。`);
    } catch (e) {
        if (e.code === 'ENOENT') {
            console.log(`文件 '${certErrorsFile}' 不存在，将创建新文件。`);
        } else {
            console.warn(`读取证书错误记录时发生警告: ${e.message}。将创建新的记录文件。`);
        }
    }

    let initialUrls;
    try {
        const fileContent = await fs.readFile(initialUrlsFile, 'utf-8');
        initialUrls = JSON.parse(fileContent);
        console.log(`从 ${initialUrlsFile} 读取到 ${initialUrls.length} 个分类数据。`);
    } catch (e) {
        console.error(`读取初始URL文件时发生错误: ${e.message}`);
        process.exit(1);
    }

    try {
        const fileContent = await fs.readFile(outputJsonFile, 'utf-8');
        allProductsData = JSON.parse(fileContent);
        console.log(`从 ${outputJsonFile} 读取到 ${allProductsData.length} 条已采集数据。`);
    } catch (e) {
        if (e.code === 'ENOENT') {
            console.log(`文件 '${outputJsonFile}' 不存在，将创建新文件。`);
        } else {
            console.warn(`读取已采集数据文件时发生警告: ${e.message}。将覆盖现有文件。`);
        }
    }

    const urlsToProcessWithCategory = initialUrls.flatMap(categoryData => {
        const { level1_category = 'N/A', level2_category = 'N/A', level3_category = 'N/A', product_urls } = categoryData;
        return product_urls.map(url => ({ url, level1_category, level2_category, level3_category }));
    });

    // 过滤掉已处理的URL
    const urlsToProcess = urlsToProcessWithCategory.filter(item => 
        !processedUrls.has(item.url) && 
        !noColorsFoundUrls.some(noColorItem => noColorItem.product_urls && noColorItem.product_urls.includes(item.url)) &&
        !certErrors.some(certErrorItem => certErrorItem.product_urls && certErrorItem.product_urls.includes(item.url))
    );
    const totalUrlsToProcess = urlsToProcess.length;
    const skippedUrls = urlsToProcessWithCategory.length - totalUrlsToProcess;
    
    console.log(`从初始URL文件读取到 ${urlsToProcessWithCategory.length} 个URL，其中 ${skippedUrls} 个已处理、没找到颜色变体或证书错误，${totalUrlsToProcess} 个待处理。`);

    if (totalUrlsToProcess === 0) {
        console.log("所有URL都已处理完成，无需继续执行。");
        process.exit(0);
    }

    // 新增：处理单个URL的异步函数
    async function processUrl(item, pageIndex) {
        const { url: initialUrl, level1_category, level2_category, level3_category } = item;
        let browser;
        let page;
        let currentProxy;

        try {
            // 尝试获取可用代理并启动浏览器
            let proxyAttempts = 0;
            const maxProxyAttempts = proxyManager.proxies.length * 2; // 每个代理尝试两次

            while (proxyAttempts < maxProxyAttempts) {
                currentProxy = proxyManager.getNextProxy();
                console.log(`[页面${pageIndex + 1}] 尝试使用代理: ${currentProxy}`);

                try {
                    browser = await chromium.launch({
                        headless: isHeadless, // 使用 isHeadless 变量控制无头模式
                        ignoreHTTPSErrors: true, // 忽略HTTPS错误
                        proxy: {
                            server: `http://${currentProxy}` // 假设是HTTP代理
                        }
                    });
                    page = await browser.newPage();
                    console.log(`[页面${pageIndex + 1}] 代理 ${currentProxy} 启动浏览器成功。`);
                    break; // 成功启动浏览器，跳出代理选择循环
                } catch (proxyLaunchError) {
                    console.error(`[页面${pageIndex + 1}] 代理 ${currentProxy} 启动浏览器失败: ${proxyLaunchError.message}`);
                    proxyManager.markProxyAsFailed(currentProxy);
                    proxyAttempts++;
                    if (browser) await browser.close(); // 关闭失败的浏览器实例
                    if (proxyAttempts >= maxProxyAttempts) {
                        throw new Error('所有代理都已尝试且失败，无法启动浏览器。');
                    }
                    await sleep(1000); // 稍作等待再尝试下一个代理
                }
            }

            console.log(`[页面${pageIndex + 1}] 正在处理URL: ${initialUrl} (使用代理: ${currentProxy})`);
            
            await randomDelay();
            
            await page.goto(initialUrl, { waitUntil: 'load', timeout: 60000 }); // 增加超时时间到60秒

            // 检查是否出现Access Denied错误
            const pageContent = await page.content();
            if (pageContent.includes('Access Denied') || pageContent.includes('You don\'t have permission to access')) {
                throw new Error('Access Denied: 检测到IP被限制访问，请更换IP地址');
            }

            const colors = {};

            const colorSwatchesData = await page.evaluate(() => {
                const swatches = document.querySelectorAll('.swatchanchor.color');
                const data = [];
                swatches.forEach(swatch => {
                    const colorName = swatch.getAttribute('data-value');
                    const hrefUrl = swatch.getAttribute('href');
                    const selectionUrl = swatch.getAttribute('data-selectionurl');
                    data.push({
                        colorName,
                        url: selectionUrl || hrefUrl
                    });
                });
                return data;
            });

            console.log(`[页面${pageIndex + 1}] URL ${initialUrl} 找到 ${colorSwatchesData.length} 个颜色变体。`);

            for (const swatch of colorSwatchesData) {
                if (swatch.colorName && swatch.url) {
                    const fullLink = new URL(swatch.url, 'https://www.birkenstock.com').href;
                    colors[swatch.colorName.trim()] = fullLink;
                }
            }
            
            console.log(`[页面${pageIndex + 1}] URL ${initialUrl} 找到以下颜色链接: ${JSON.stringify(colors, null, 2)}`);

            if (Object.keys(colors).length === 0) {
                const noColorData = {
                    level1_category,
                    level1_url: `https://www.birkenstock.com/us/${level1_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    level2_category,
                    level2_url: `https://www.birkenstock.com/us/campaign/${level2_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    level3_category,
                    level3_url: `https://www.birkenstock.com/us/campaign/${level3_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    product_urls: [initialUrl],
                    timestamp: new Date().toISOString()
                };
                noColorsFoundUrls.push(noColorData);
                
                await fs.writeFile(noColorsFoundFile, JSON.stringify(noColorsFoundUrls, null, 4), 'utf-8');
                console.log(`[页面${pageIndex + 1}] URL ${initialUrl} 没找到颜色变体，已记录到 ${noColorsFoundFile}。`);
            } else {
                for (const [colorText, url] of Object.entries(colors)) {
                    if (!allProductsData.some(p => p.url === url)) {
                        const productData = {
                            url,
                            color: colorText,
                            level1_category,
                            level2_category,
                            level3_category
                        };
                        allProductsData.push(productData);
                    }
                }
            }

            processedUrls.add(initialUrl);
            
            await fs.writeFile(processedUrlsFile, JSON.stringify(Array.from(processedUrls), null, 4), 'utf-8');
            
            await fs.writeFile(outputJsonFile, JSON.stringify(allProductsData, null, 4), 'utf-8');
            console.log(`[页面${pageIndex + 1}] 已处理完URL ${initialUrl} 并保存到 ${outputJsonFile}。`);
            console.log(`[页面${pageIndex + 1}] 已更新已处理URL记录到 ${processedUrlsFile}。`);
            console.log("---");

            return { success: true, url: initialUrl };

        } catch (e) {
            console.error(`[页面${pageIndex + 1}] 处理URL ${initialUrl} 时发生错误: ${e.message}`);
            if (currentProxy) {
                proxyManager.markProxyAsFailed(currentProxy); // 标记当前代理为失败
            }

            if (e.message.includes('Access Denied')) {
                console.error(`❌ 严重错误: ${e.message}`);
                console.log('🔄 程序已中断，请更换IP地址后重新运行');
                process.exit(1);
            } else if (e.message.includes('net::ERR_CERT_AUTHORITY_INVALID')) {
                const certErrorData = {
                    level1_category,
                    level1_url: `https://www.birkenstock.com/us/${level1_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    level2_category,
                    level2_url: `https://www.birkenstock.com/us/campaign/${level2_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    level3_category,
                    level3_url: `https://www.birkenstock.com/us/campaign/${level3_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    product_urls: [initialUrl],
                    error: e.message, // 记录错误信息
                    timestamp: new Date().toISOString()
                };
                certErrors.push(certErrorData);
                await fs.writeFile(certErrorsFile, JSON.stringify(certErrors, null, 4), 'utf-8');
                console.log(`[页面${pageIndex + 1}] URL ${initialUrl} 发生证书错误，已记录到 ${certErrorsFile}。`);
            } else {
                // 如果是其他类型的错误，记录到 noColorsFoundUrls
                const noColorData = {
                    level1_category,
                    level1_url: `https://www.birkenstock.com/us/${level1_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    level2_category,
                    level2_url: `https://www.birkenstock.com/us/campaign/${level2_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    level3_category,
                    level3_url: `https://www.birkenstock.com/us/campaign/${level3_category.toLowerCase().replace(/\s+/g, '-')}/`,
                    product_urls: [initialUrl],
                    error: e.message, // 记录错误信息
                    timestamp: new Date().toISOString()
                };
                noColorsFoundUrls.push(noColorData);
                await fs.writeFile(noColorsFoundFile, JSON.stringify(noColorsFoundUrls, null, 4), 'utf-8');
                console.log(`[页面${pageIndex + 1}] URL ${initialUrl} 处理失败，已记录到 ${noColorsFoundFile}。`);
            }

            console.log(`[页面${pageIndex + 1}] 继续处理下一个URL...`);
            return { success: false, url: initialUrl, error: e.message };
        } finally {
            if (browser) {
                await browser.close();
                console.log(`[页面${pageIndex + 1}] 浏览器已关闭。`);
            }
        }
    }

    console.log(`开始并发处理 ${totalUrlsToProcess} 个URL，并发数: ${maxConcurrency}`);
    
    const urlChunks = [];
    for (let i = 0; i < urlsToProcess.length; i += maxConcurrency) {
        urlChunks.push(urlsToProcess.slice(i, i + maxConcurrency));
    }

    for (let i = 0; i < urlChunks.length; i++) {
        const batch = urlChunks[i];
        console.log(`处理批次 ${i + 1}/${urlChunks.length}，包含 ${batch.length} 个URL`);
        
        const batchPromises = batch.map((item, batchIndex) => {
            return processUrl(item, i * maxConcurrency + batchIndex); // 确保每个任务有唯一的pageIndex
        });
        
        const batchResults = await Promise.all(batchPromises);
        
        batchResults.forEach((result, batchIndex) => {
            if (result.success) {
                console.log(`批次 ${i + 1} - URL ${result.url} 处理成功。`);
            } else {
                console.warn(`批次 ${i + 1} - URL ${result.url} 处理失败，错误: ${result.error}`);
            }
        });
        
        console.log(`批次 ${i + 1} 处理完成。`);
        
        if (i + 1 < urlChunks.length) {
            console.log(`批次间等待 3 秒...`);
            await sleep(3000);
        }
    }

    console.log(`所有待处理产品数据已成功保存到 ${outputJsonFile} 文件。`);
    console.log(`已处理URL记录已保存到 ${processedUrlsFile} 文件。`);
    console.log(`没找到颜色变体的URL记录已保存到 ${noColorsFoundFile} 文件。`);
    console.log(`证书错误记录已保存到 ${certErrorsFile} 文件。`);
    
    console.log("脚本运行结束。");
}

process.on('SIGINT', async () => {
    console.log('\n收到中断信号，正在保存进度...');
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n收到终止信号，正在保存进度...');
    process.exit(0);
});

main().catch(error => {
    console.error('脚本执行过程中发生未捕获的错误:', error);
    process.exit(1);
});
