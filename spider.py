from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC

from pyquery import PyQuery as pq
from config import *
import pymongo
import re

driver = webdriver.PhantomJS(service_args=SERVICE_ARGS)
wait = WebDriverWait(driver, 10)

driver.set_window_size(1400, 900)

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

def search(kw):
    ''' 返回所要查找的宝贝的总页数
        kw: 要查找的宝贝
    '''
    print('正在搜索')
    driver.get('https://www.taobao.com/')
    try:
        input_ = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#q'))
        )
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button'))
        )
        input_.send_keys(kw)
        submit.click()
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total'))
        )
        get_products()
        total = re.search('(\d+)', total.text).group(1)
        return int(total)
    except TimeoutException as e:
        return search(kw)


def next_page(page_number):
    print('正在翻页', page_number)
    try:
        input_ = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input')
        ))
        submit = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')
        ))
        input_.clear()
        input_.send_keys(page_number)
        submit.click()
        wait.until(EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_number)
        ))
        get_products()
    except TimeoutException as e:
        print(e)


def get_products():
    ''' 获取查找商品的信息并返回
    '''
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, '#mainsrp-itemlist .items .item')
    ))
    html = driver.page_source
    doc = pq(html)
    items = doc('#mainsrp-itemlist .items .item').items()
    # print(items)
    # print(type(items))
    for item in items:
        product = {
            'image': item.find('.pic .img').attr('src'),
            'prices': item.find('.price').text().strip(),
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text(),
        }
        save_to_mongo(product)


def save_to_mongo(result):
    ''' 将得到的信息存储到 mongodb 数据库中
        result: 要存储的数据
    '''
    try:
        if db[MONGO_TABLE].insert(result):
            print('存储成功', result)
    except:
        print('存储失败', result)


def main():
    try:
        total = search(KEY_WORD)
        for i in range(2, total+1):
            next_page(i)
    except Exception:
        print('出错了！')
    finally:
        driver.close()


if __name__ == '__main__':
    main()