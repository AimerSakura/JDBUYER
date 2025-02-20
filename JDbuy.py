import requests
from bs4 import BeautifulSoup
import re  # 引入正则表达式库，用于提取SKU编号
from DrissionPage import Chromium
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time
import logging
# --------------------- 日志配置 ---------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    filename='jd_buyer5070TiOCPackage.log',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# --------------------- 配置 ---------------------
MAX_RETRIES = 600  # 最大抓包尝试次数
TARGET_URL = "https://mall.jd.com/view_page-160787132.html"

# --------------------- 全局配置 ---------------------
#<div class="ui-area-text" data-id="19-1607-6736-62151" title="广东深圳市坪山区石井街道">广东深圳市坪山区石井街道</div>
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
# ---------------------------------------------------
# --------------------- 获取页面内容 ---------------------
def get_page_content():
    """获取页面内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(TARGET_URL, headers=headers)
        response.raise_for_status()  # 如果返回码不是200，会抛出异常
        return response.text
    except Exception as e:
        logger.error(f"获取页面内容失败: {str(e)}")
        return None

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

# --------------------- 抓取和提取SKU直到成功 ---------------------
def scrape_until_success():
    """反复抓包直到成功提取SKU信息"""
    retries = 0
    while retries < MAX_RETRIES:
        logger.info(f"尝试第 {retries + 1} 次抓取...")
        page_content = get_page_content()
        if page_content:
            product_info = extract_product_info(page_content)
            if product_info:  # 如果找到了符合条件的产品
                logger.info("成功抓取到符合条件的SKU信息")
                return [product['sku'] for product in product_info]
            else:
                logger.info("未找到符合条件的产品，继续尝试...")
        else:
            logger.warning("获取页面内容失败，重试中...")

        retries += 1
        time.sleep(0.3)  # 等待5秒再重试

    logger.error(f"超过最大重试次数({MAX_RETRIES})，未能成功抓取到SKU")
    return []

# --------------------- 第二个脚本的部分 ---------------------
class JDMissionExecutor:
    def __init__(self):
        self.browser = Chromium(COMMON_CONFIG['debug_port'])
        self.main_tab = self.browser.latest_tab
        self.main_tab.set.window.size(1200, 800)

    def login(self):
        """登录京东"""
        try:
            self.main_tab.get('https://plogin.m.jd.com/login/login?appid=300&returnurl=https%3A%2F%2Fmy.m.jd.com%2F')
            logger.info("请登录...")

            # 等待登录完成
            self.main_tab.wait.url_change('https://my.m.jd.com/', timeout=120)
            logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return False

    def _get_trade_url(self, productId):
        return f"https://trade.m.jd.com/pay?sceneval=2&scene=jd&isCanEdit=1&EncryptInfo=&Token=&bid=&type=0&lg=0&supm=0&wdref=https%3A%2F%2Fitem.m.jd.com%2Fproduct%{productId}.html%3Fsceneval%3D2%26jxsid%3D17291551552449629789%26appCode%3Dms0ca95114%26_fd%3Djdm&commlist={productId},,1,{productId},1,0,0&locationid=1-72-2819-0&jxsid=17291551552449629789&appCode=ms0ca95114#/index"

    def _execute_single_mission(self, mission: dict):
        """执行单个商品抢购"""
        tab = self.browser.new_tab()
        try:
            logger.info(f"开始处理商品 {mission['sku_id']}")

            # 跳转到商品页
            sku_url = self._get_trade_url(mission['sku_id'])
            logger.info(f"{mission['sku_id']} 正在打开商品页 {sku_url}")

            tab.get(sku_url)

            # 时间同步等待
            # target_time = datetime.strptime(mission['buy_time'], '%Y-%m-%d %H:%M:%S')
            # while (delta := (target_time - datetime.now()).total_seconds()) > 0:
            #     logger.debug(f"{mission['sku_id']} 剩余等待时间: {delta:.1f}s")
            #     time.sleep(min(0.05, delta))

            # 抢购尝试
            success = False
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

            return False
        finally:
            tab.close()

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

    def _delayed_execution(self, mission: dict, delay: float):
        """延迟执行包装器"""
        time.sleep(max(0, delay))
        status = self._execute_single_mission(mission)
        return (mission['sku_id'], status)


# --------------------- 主函数 ---------------------
def main():
    """主函数：执行抓包任务，直到成功获取SKU"""
    # 第一步：获取页面内容并提取SKU信息
    sku_list = scrape_until_success()
    if sku_list:
        logger.info(f"最终抓取到的SKU列表: {sku_list}")
        # 执行后续任务，例如将SKU传递给第二个脚本
        executor = JDMissionExecutor()
        try:
            if executor.login():
                executor.schedule_missions(sku_list)
            else:
                logger.error("登录失败，程序终止")
        except KeyboardInterrupt:
            logger.info("用户中断执行")
        finally:
            executor.browser.quit()
    else:
        logger.error("没有成功获取SKU信息，程序终止。")

if __name__ == '__main__':
    main()
