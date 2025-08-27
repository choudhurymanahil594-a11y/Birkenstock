const colorSwatches = document.querySelectorAll('.swatchanchor.color');

colorSwatches.forEach(swatch => {
  const dataLayer = swatch.getAttribute('data-data-layer');
  if (dataLayer) {
    try {
      const data = JSON.parse(dataLayer);
      const productInfo = data.ecommerce.detail.products[0];
      const colorName = productInfo.color_str;
      const id = productInfo.id;
      const price = productInfo.price;
      
      console.log(`颜色: ${colorName}, ID: ${id}, 价格: $${price}`);
    } catch (e) {
      console.error('解析 JSON 失败:', e);
    }
  }
});


// 获取所有颜色选项
const colorSwatches = document.querySelectorAll('.swatchanchor.color');

colorSwatches.forEach(swatch => {
  const colorName = swatch.getAttribute('data-value');
  const hrefUrl = swatch.getAttribute('href');
  const selectionUrl = swatch.getAttribute('data-selectionurl');

  console.log(`颜色: ${colorName}`);
  console.log(`  href: ${hrefUrl}`);
  console.log(`  data-selectionurl: ${selectionUrl}`);
});