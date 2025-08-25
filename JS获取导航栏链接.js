const results = [];

// 假设所有的导航项都在一个共同的父容器内
const primaryItems = document.querySelectorAll('.xlt-firstLevelCategory'); 

primaryItems.forEach(link => {
  const primaryLink = link;
  const primaryUrl = primaryLink.href;
  const primaryTextElement = primaryLink.querySelector('span.link-inner');
  const primaryText = primaryTextElement ? primaryTextElement.textContent.trim() : primaryLink.textContent.trim();

  // 创建一级分类对象
  const primaryCategory = {
    level1_category: primaryText,
    level1_url: primaryUrl,
    children: [] // 用于存储二级链接
  };
  results.push(primaryCategory);

  const subMenu = link.closest('.a-level-1').nextElementSibling;

  if (subMenu) {
    const secondaryItems = subMenu.querySelectorAll('.a-level-2');
    secondaryItems.forEach(secondaryLink => {
      const secondaryCategory = {
        level2_category: secondaryLink.textContent.trim(),
        level2_url: secondaryLink.href,
        children: [] // 用于存储三级链接
      };
      primaryCategory.children.push(secondaryCategory);

      const tertiaryMenu = secondaryLink.closest('.a-level-2').nextElementSibling;

      if (tertiaryMenu) {
        const tertiaryLinks = tertiaryMenu.querySelectorAll('.a-level-3');
        tertiaryLinks.forEach(tertiaryLink => {
          secondaryCategory.children.push({
            level3_category: tertiaryLink.textContent.trim(),
            level3_url: tertiaryLink.href
          });
        });
      }
    });
  }
});

// 将结果保存为JSON文件
const jsonData = JSON.stringify(results, null, 2);
const a = document.createElement('a');
a.href = 'data:application/json;charset=utf-8,' + encodeURIComponent(jsonData);
a.download = 'navigation_data.json';
a.click();