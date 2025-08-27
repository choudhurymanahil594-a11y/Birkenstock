// 测试脚本：验证修改后的JSON格式
const fs = require('fs').promises;

async function testFormat() {
    console.log('测试修改后的JSON格式...');
    
    // 模拟第二步的格式
    const step2Format = [
        {
            "level1_category": "What's New",
            "level1_url": "https://www.birkenstock.com/us/new-arrivals/",
            "level2_category": "The Latest",
            "level2_url": "https://www.birkenstock.com/us/campaign/new-arrivals/",
            "level3_category": "Back to School",
            "level3_url": "https://www.birkenstock.com/us/campaign/back-to-school/",
            "product_urls": [
                "https://www.birkenstock.com/us/boston-soft-footbed-suede-leather/boston-suede-suedeleather-softfootbed-eva-u_46.html"
            ]
        }
    ];
    
    // 模拟修改后第三步失败记录的格式
    const step3FailedFormat = [
        {
            "level1_category": "What's New",
            "level1_url": "https://www.birkenstock.com/us/whats-new/",
            "level2_category": "The Latest",
            "level2_url": "https://www.birkenstock.com/us/campaign/the-latest/",
            "level3_category": "Back to School",
            "level3_url": "https://www.birkenstock.com/us/campaign/back-to-school/",
            "product_urls": [
                "https://www.birkenstock.com/us/boston-soft-footbed-suede-leather/boston-suede-suedeleather-softfootbed-eva-u_46.html"
            ],
            "timestamp": "2025-08-26T05:26:12.713Z"
        }
    ];
    
    // 模拟修改后第三步错误记录的格式
    const step3ErrorFormat = [
        {
            "level1_category": "What's New",
            "level1_url": "https://www.birkenstock.com/us/whats-new/",
            "level2_category": "The Latest",
            "level2_url": "https://www.birkenstock.com/us/campaign/the-latest/",
            "level3_category": "Back to School",
            "level3_url": "https://www.birkenstock.com/us/campaign/back-to-school/",
            "product_urls": [
                "https://www.birkenstock.com/us/boston-soft-footbed-suede-leather/boston-suede-suedeleather-softfootbed-eva-u_46.html"
            ],
            "error": "页面加载超时",
            "timestamp": "2025-08-26T05:26:12.713Z"
        }
    ];
    
    console.log('\n=== 第二步格式 ===');
    console.log(JSON.stringify(step2Format, null, 2));
    
    console.log('\n=== 修改后第三步失败记录格式 ===');
    console.log(JSON.stringify(step3FailedFormat, null, 2));
    
    console.log('\n=== 修改后第三步错误记录格式 ===');
    console.log(JSON.stringify(step3ErrorFormat, null, 2));
    
    // 测试过滤逻辑
    const testUrl = "https://www.birkenstock.com/us/boston-soft-footbed-suede-leather/boston-suede-suedeleather-softfootbed-eva-u_46.html";
    
    const isInFailedUrls = step3FailedFormat.some(noColorItem => 
        noColorItem.product_urls && noColorItem.product_urls.includes(testUrl)
    );
    
    console.log(`\n=== 测试过滤逻辑 ===`);
    console.log(`测试URL: ${testUrl}`);
    console.log(`是否在失败记录中: ${isInFailedUrls}`);
    
    console.log('\n✅ 格式测试完成！');
}

testFormat().catch(console.error);
