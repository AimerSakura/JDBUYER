# 京东抢购脚本
原理就是抓包页面信息 获取商品SKU信息
拼接成支付链接
然后脚本自动确定订单
```
# --------------------- 日志配置 ---------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    filename='jd_buyer5070TiOCPackage.log',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)
```
filename是日志名称，默认输出在根目录

```
# --------------------- 配置 ---------------------
MAX_RETRIES = 600  # 最大抓包尝试次数
TARGET_URL = "https://mall.jd.com/view_page-160787132.html"
```
TARGET_URL  是抓包网址
MAX_RETRIES 是最大抓包尝试次数

```
# --------------------- 全局配置 ---------------------
SKU_CONFIG = [
    {
        "sku_id": "10127456002809",
        "buy_time": "2025-2-20 15:18:00",
        "area_id": "19-1607-6736-62151",
        "retry_max": 50
    }
]

COMMON_CONFIG = {
    "buy_btn_text": ["立即购买","在线支付"],
    'debug_port': 9230,
    'max_workers': 1  # 最大并发任务数
}
```
area_id 对应区域id 可通过浏览器f12查看

sku_id 、buy_time 、retry_max 在此处不用设置

```
# --------------------- 从页面中提取产品信息 ---------------------
def extract_product_info(page_content):
    """从页面内容中提取SKU信息"""
    soup = BeautifulSoup(page_content, 'html.parser')
    products = soup.find_all('a', class_='d-wname J-wname')

    product_info = []
    for product in products:
        title = product.get('title')
        link = product.get('href')

        # 筛选符合条件的产品：包含 "5080"、"Ultra" 和 "OC"
        if '5070 Ti' in title and 'Ultra' in title and 'OC' in title:
            # 使用正则表达式提取链接中的SKU编号（类似100102662755）
            sku_match = re.search(r'\/(\d+)\.html', link)
            if sku_match:
                sku = sku_match.group(1)  # 提取出SKU编号
            else:
                sku = '无SKU'

            product_info.append({'title': title, 'link': 'https:' + link, 'sku': sku})

    return product_info
```
 **if '5070 Ti' in title and 'Ultra' in title and 'OC' in title 部分**

原理是过滤页面元素中的字段，提取商品的SKU信息

根据需求对 **单引号** 的内容进行修改

``` 
# --------------------- 第二个脚本的部分 ---------------------
class JDMissionExecutor:
略
            for attempt in range(mission['retry_max']):
                try:
                    tab.refresh()
                    if tab.ele('无货', timeout=0.05):
                        tab.refresh()

                    for text in COMMON_CONFIG['buy_btn_text']:
                        if buy_btn := tab.ele(("xpath", "/html/body/div[2]/div/taro-view-core[1]/taro-view-core[2]/taro-view-core/taro-view-core/taro-view-core[1]/taro-view-core[2]/taro-button-core"),index=1):
                            buy_btn.click()
                            logger.info(f"{mission['sku_id']} 点击购买成功")
                            success = True
                            tab.wait(0.09, 0.13)
                            return True
                except Exception as e:
                    logger.warning(f"{mission['sku_id']} 第{attempt+1}次尝试失败: {str(e)}")
                    time.sleep(0.3)
略
```
buy_btn 对应 购买按钮的xpath值，可通过f12检查元素获得

tab.wait 时间可根据需要进行调整

``` 
    def schedule_missions(self, sku_list):
        """调度所有任务"""
        with ThreadPoolExecutor(max_workers=COMMON_CONFIG['max_workers']) as executor:
            futures = []
            for sku_id in sku_list:
                mission = {
                    'sku_id': sku_id,
                    'buy_time': '2025-2-20 16:02:00',  # 可以在这里动态更改
                    'retry_max': 50
                }
                # 计算任务延迟
                target_time = datetime.strptime(mission['buy_time'], '%Y-%m-%d %H:%M:%S')
                delay = (target_time - datetime.now()).total_seconds()

                if delay > 0:
                    logger.info(f"任务 {mission['sku_id']} 计划于 {target_time} 执行")
                    futures.append(executor.submit(self._delayed_execution, mission, delay))
                else:
                    logger.warning(f"跳过过期任务 {mission['sku_id']}")

            # 处理结果
            for future in futures:
                sku_id = future.result()[0]
                status = future.result()[1]
                logger.info(f"任务 {sku_id} {'成功' if status else '失败'}")
```

'buy_time': 'xxxx-x-xx xx:xx:xx'

'retry_max': 50

以上内容根据需求进行修改

 