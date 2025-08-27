// scraper.js
const { chromium } = require('playwright');
const fs = require('fs').promises;

async function main() {
    console.log("脚本开始运行...");

    const initialUrlsFile = 'birkenstock_campaign_product_urls copy.json';
    const outputJsonFile = '所有颜色变体URL_Cursor.json';
    const processedUrlsFile = 'processed_urls_Cursor.json'; // 新增：记录已处理的URL
    const noColorsFoundFile = 'no_colors_found_urls_Cursor.json'; // 新增：记录没找到颜色变体的URL
    const maxConcurrency = 2; // 新增：最大并发数
    const requestDelay = 2000; // 新增：请求间隔延迟（毫秒）
    const randomDelayRange = 1000; // 新增：随机延迟范围（毫秒）
    let allProductsData = [];
    let processedUrls = new Set(); // 新增：已处理URL的集合
    let noColorsFoundUrls = []; // 新增：没找到颜色变体的URL列表

    const browser = await chromium.launch({ headless: false });
    
    // 新增：创建多个页面实例
    const pages = [];
    for (let i = 0; i < maxConcurrency; i++) {
        const page = await browser.newPage();
        pages.push(page);
    }
    console.log(`已创建 ${maxConcurrency} 个页面实例用于并发处理。`);

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

    let initialUrls;
    try {
        const fileContent = await fs.readFile(initialUrlsFile, 'utf-8');
        initialUrls = JSON.parse(fileContent);
        console.log(`从 ${initialUrlsFile} 读取到 ${initialUrls.length} 个分类数据。`);
    } catch (e) {
        console.error(`读取初始URL文件时发生错误: ${e.message}`);
        await browser.close();
        return;
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
        !noColorsFoundUrls.some(noColorItem => noColorItem.url === item.url)
    );
    const totalUrlsToProcess = urlsToProcess.length;
    const skippedUrls = urlsToProcessWithCategory.length - totalUrlsToProcess;
    
    console.log(`从初始URL文件读取到 ${urlsToProcessWithCategory.length} 个URL，其中 ${skippedUrls} 个已处理或没找到颜色变体，${totalUrlsToProcess} 个待处理。`);

    if (totalUrlsToProcess === 0) {
        console.log("所有URL都已处理完成，无需继续执行。");
        await browser.close();
        return;
    }

    // 新增：处理单个URL的异步函数
    async function processUrl(item, pageIndex) {
        const { url: initialUrl, level1_category, level2_category, level3_category } = item;
        const page = pages[pageIndex];
        
        try {
            console.log(`[页面${pageIndex + 1}] 正在处理URL: ${initialUrl}`);
            
            // 新增：在访问页面前添加延迟
            await randomDelay();
            
            await page.goto(initialUrl, { waitUntil: 'load' });

            // 检查是否出现Access Denied错误
            const pageContent = await page.content();
            if (pageContent.includes('Access Denied') || pageContent.includes('You don\'t have permission to access')) {
                throw new Error('Access Denied: 检测到IP被限制访问，请更换IP地址');
            }

            const colors = {};

            // Use page.evaluate with your logic to get all color swatches
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

            // Process the extracted data
            for (const swatch of colorSwatchesData) {
                if (swatch.colorName && swatch.url) {
                    const fullLink = new URL(swatch.url, 'https://www.birkenstock.com').href;
                    colors[swatch.colorName.trim()] = fullLink;
                }
            }
            
            console.log(`[页面${pageIndex + 1}] URL ${initialUrl} 找到以下颜色链接: ${JSON.stringify(colors, null, 2)}`);

            // 检查是否找到颜色变体
            if (Object.keys(colors).length === 0) {
                // 没找到颜色变体，记录到noColorsFoundUrls
                const noColorData = {
                    url: initialUrl,
                    level1_category,
                    level2_category,
                    level3_category,
                    timestamp: new Date().toISOString()
                };
                noColorsFoundUrls.push(noColorData);
                
                // 保存没找到颜色变体的URL记录
                await fs.writeFile(noColorsFoundFile, JSON.stringify(noColorsFoundUrls, null, 4), 'utf-8');
                console.log(`[页面${pageIndex + 1}] URL ${initialUrl} 没找到颜色变体，已记录到 ${noColorsFoundFile}。`);
            } else {
                // 找到颜色变体，处理数据
                for (const [colorText, url] of Object.entries(colors)) {
                    // Avoid duplicates by checking if the URL is already processed
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

            // 标记当前URL为已处理
            processedUrls.add(initialUrl);
            
            // 保存已处理URL记录
            await fs.writeFile(processedUrlsFile, JSON.stringify(Array.from(processedUrls), null, 4), 'utf-8');
            
            // Write to file after each main URL is processed
            await fs.writeFile(outputJsonFile, JSON.stringify(allProductsData, null, 4), 'utf-8');
            console.log(`[页面${pageIndex + 1}] 已处理完URL ${initialUrl} 并保存到 ${outputJsonFile}。`);
            console.log(`[页面${pageIndex + 1}] 已更新已处理URL记录到 ${processedUrlsFile}。`);
            console.log("---");

            return { success: true, url: initialUrl };

        } catch (e) {
            // 检查是否是Access Denied错误
            if (e.message.includes('Access Denied')) {
                console.error(`❌ 严重错误: ${e.message}`);
                console.log('🔄 程序已中断，请更换IP地址后重新运行');
                console.log(`📊 已成功采集 ${allProductsData.length} 个产品的数据`);
                console.log(`💾 数据已保存到: ${outputJsonFile}`);
                console.log(`📝 已处理URL记录已保存到: ${processedUrlsFile}`);
                console.log(`📝 没找到颜色变体的URL记录已保存到: ${noColorsFoundFile}`);
                
                // 关闭所有页面和浏览器
                for (const page of pages) {
                    await page.close();
                }
                await browser.close();
                console.log("所有页面和浏览器已关闭。");
                
                // 退出程序
                process.exit(1);
            }
            
            console.error(`[页面${pageIndex + 1}] 处理URL ${initialUrl} 时发生错误: ${e.message}`);
            console.log(`[页面${pageIndex + 1}] 继续处理下一个URL...`);
            return { success: false, url: initialUrl, error: e.message };
        }
    }

    // 并发处理URL
    console.log(`开始并发处理 ${totalUrlsToProcess} 个URL，并发数: ${maxConcurrency}`);
    
    // 分批处理，控制并发数
    for (let i = 0; i < urlsToProcess.length; i += maxConcurrency) {
        const batch = urlsToProcess.slice(i, i + maxConcurrency);
        console.log(`处理批次 ${Math.floor(i / maxConcurrency) + 1}/${Math.ceil(urlsToProcess.length / maxConcurrency)}，包含 ${batch.length} 个URL`);
        
        const batchPromises = batch.map((item, batchIndex) => {
            const pageIndex = i + batchIndex;
            return processUrl(item, pageIndex % maxConcurrency);
        });
        
        const batchResults = await Promise.all(batchPromises);
        
        // 检查批次处理结果
        batchResults.forEach((result, batchIndex) => {
            if (result.success) {
                console.log(`批次 ${Math.floor(i / maxConcurrency) + 1} - URL ${result.url} 处理成功。`);
            } else {
                console.warn(`批次 ${Math.floor(i / maxConcurrency) + 1} - URL ${result.url} 处理失败，错误: ${result.error}`);
            }
        });
        
        console.log(`批次 ${Math.floor(i / maxConcurrency) + 1} 处理完成。`);
        
        // 新增：批次之间添加额外延迟
        if (i + maxConcurrency < urlsToProcess.length) {
            console.log(`批次间等待 3 秒...`);
            await sleep(3000);
        }
    }

    console.log(`所有待处理产品数据已成功保存到 ${outputJsonFile} 文件。`);
    console.log(`已处理URL记录已保存到 ${processedUrlsFile} 文件。`);
    console.log(`没找到颜色变体的URL记录已保存到 ${noColorsFoundFile} 文件。`);
    
    // 关闭所有页面和浏览器
    for (const page of pages) {
        await page.close();
    }
    await browser.close();
    console.log("所有页面和浏览器已关闭。");
}

// 添加错误处理和优雅退出
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
