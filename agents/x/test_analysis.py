# test_analysis.py

import asyncio
from analysis import XCleaner
from crawler import XCrawler


async def test_clean_raw_data():
    # 初始化 XCrawler
    crawler = XCrawler()

    # 使用 XCrawler 获取原始数据
    user_request = "I need text and tweet_id"
    keyword = "tariff"

    tweet_data = crawler.fetch_search_posts(keyword=keyword, max_pages=1)
    crawler.save_to_json(tweet_data, "tariff.json")

    
    # 初始化 XCleaner
    x_cleaner = XCleaner()

    # 调用 clean_raw_data 方法
    cleaned_data = await x_cleaner.clean_raw_data(user_request, tweet_data)
    print(cleaned_data)

    
if __name__ == '__main__':
     asyncio.run(test_clean_raw_data())