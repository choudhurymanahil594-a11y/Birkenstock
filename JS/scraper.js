const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false }); // headless: false 可以看到浏览器窗口
  const page = await browser.newPage();
  
  await page.goto('https://www.birkenstock.com/us/arizona-rivet-suede-leather/arizonarivet-suederivets-suedeleather-0-eva-w_1.html');
  
  // 在浏览器环境中执行你的 JavaScript 代码
  const data = await page.evaluate(() => {
    const colorSwatches = document.querySelectorAll('.swatchanchor.color');
    const results = [];
    
    colorSwatches.forEach(swatch => {
      const colorName = swatch.getAttribute('data-value');
      const hrefUrl = swatch.getAttribute('href');
      const selectionUrl = swatch.getAttribute('data-selectionurl');
      
      results.push({
        colorName,
        hrefUrl,
        selectionUrl
      });
    });
    
    return results;
  });
  
  console.log(data);
  
  await browser.close();
})();