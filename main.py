
from bs4 import BeautifulSoup
import requests
from multiprocessing import freeze_support
from threading import Thread
freeze_support()

import zipfile
from bs4 import BeautifulSoup
from random import randint, uniform
import time, os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium import webdriver
import json
from requests.exceptions import RequestException
config = json.load(open('settings.json'))

PROXY_HOST = config['PROXY_SETTINGS']['HOST']
try:
    PROXY_PORT = int(config['PROXY_SETTINGS']['PORT'])
except:
    print('PORT has to be a number.')
PROXY_USER = config['PROXY_SETTINGS']['USER']
PROXY_PASS = config['PROXY_SETTINGS']['PASSWORD']



manifest_json = """
{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "Chrome Proxy",
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
    ],
    "background": {
        "scripts": ["background.js"]
    },
    "minimum_chrome_version":"22.0.0"
}
"""

background_js = """
var config = {
        mode: "fixed_servers",
        rules: {
        singleProxy: {
            scheme: "http",
            host: "%s",
            port: parseInt(%s)
        },
        bypassList: ["localhost"]
        }
    };

chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "%s",
            password: "%s"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ['blocking']
);
""" % (PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)


global proxy_error

proxy_error = False
def get_driver_proxies():
    global proxy_error
    if proxy_error:
        PROXY=f'{PROXY_HOST}:{PROXY_PORT}'
        webdriver.DesiredCapabilities.CHROME['proxy'] = {
            "httpProxy": PROXY,
            "ftpProxy": PROXY,
            "sslProxy": PROXY,
            "proxyType": "MANUAL",

        }

        webdriver.DesiredCapabilities.CHROME['acceptSslCerts']=True
    chrome_options = webdriver.ChromeOptions()
    
    chrome_options.add_argument(f'--proxy-server={PROXY_HOST}:{PROXY_PORT}')        
    # chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # PROXY=f"{PROXY_HOST}:{PROXY_PORT}"
    # user_agent = 'Mozilla/5.0 CK={} (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko'
    # webdriver.DesiredCapabilities.CHROME['proxy'] = {
    #     "httpProxy": PROXY,
    #     "ftpProxy": PROXY,
    #     "sslProxy": PROXY,
    #     "proxyType": "MANUAL",
    # }
    # webdriver.DesiredCapabilities.CHROME['acceptSslCerts']=True
    # chrome_options.add_argument("user-agent="+user_agent)
    driver = uc.Chrome(use_subprocess=True,options=chrome_options)
    return driver


def get_chromedriver(use_proxy=False, user_agent=None):
    path = os.path.dirname(os.path.abspath(__file__))
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    if use_proxy:
        pluginfile = 'proxy_auth_plugin.zip'

        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
        chrome_options.add_extension(pluginfile)
    if user_agent:
        chrome_options.add_argument('--user-agent=%s' % user_agent)
    driver = uc.Chrome(
        options=chrome_options,version_main=105)
    return driver


def main():
    driver = get_chromedriver(use_proxy=True)
    #driver.get('https://www.google.com/search?q=my+ip+address')
    driver.get('https://httpbin.org/ip')

def spoof_geolocation(proxy, driver):
    try:
        proxy_dict = {
            "http": f"http://{proxy}",
                    "https": f"http://{proxy}",
        }
        resp = requests.get(
            "http://ip-api.com/json", proxies=proxy_dict, timeout=30)

        if resp.status_code == 200:
            location = resp.json()
            params = {
                "latitude": location['lat'],
                "longitude": location['lon'],
                "accuracy": randint(20, 100)
            }
            driver.execute_cdp_cmd(
                "Emulation.setGeolocationOverride", params)
            return driver
    except:
        pass



def init_driver():
    cnt = 0
    while True or cnt<5:
        driver = get_driver_proxies()
        wait = WebDriverWait(driver, randint(config['MIN_WAIT'],config['MAX_WAIT']))
        driver.maximize_window()
        print('Checking the IP...')
        driver.get('https://httpbin.org/ip')
        obj = json.loads(BeautifulSoup(driver.page_source,'lxml').find('body').text)
        ip = obj['origin']
        if ip!=config['HOST_IP']:
            print(f"Connected to IP: {ip}")
            return driver, wait
        else:
            print("Proxies didn't work.")
            try:
                driver.close()
            except:
                pass
            cnt+=1
        
    
def search_task(driver, wait, st):
    global state_1, state_2
    print(f"Looking for {st}")
    driver.get('https://www.bol.com/nl/nl/')
    time.sleep(randint(config['MIN_WAIT'],config['MAX_WAIT']))
    accept_cookies(wait)
    if state_1>150:
        y = 1000
        for timer in range(0,2):
            driver.execute_script("window.scrollTo(0, "+str(y)+")")
            y += 1000  
            time.sleep(0.01)
    print("trying to find the search bar")
    myElem = wait.until(EC.presence_of_element_located((By.ID, 'searchfor')))
    driver.execute_script("arguments[0].scrollIntoView();", myElem)
    for k in st:
        myElem.send_keys(k)
        time.sleep(uniform(.1, .4))
    myElem.send_keys(Keys.RETURN)


def accept_cookies(wait):
    global driver
    try:
        myElem = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@data-test="consent-modal-ofc-confirm-btn"]')))
        driver.execute_script("arguments[0].scrollIntoView();", myElem)
        myElem.click()
        print("Button clicked for cookies.")
    except:
        pass



def task(st):
    url = st['url']
    search = st['search']
    st = st['keyword']
    global proxy_error
    while True:
        try:
            state_1 = randint(0,250)
            state_2 = randint(0,500)
            pg_cnt = 0
            
            driver, wait = init_driver()
            
            if search:
                search_task(driver, wait, st)
            else:
                driver.get(url)

            while True:
                if url.split('/')[-2] in str(driver.page_source) and search:
                    print('Product Located!')
                    id = url.split('/')[-2]
                    if state_2<150:
                        total_height = int(driver.execute_script("return document.body.scrollHeight"))/3
                        for i in range(1, int(total_height), 10):
                            driver.execute_script("window.scrollTo(0, {});".format(i))
                    try:
                        myElem = wait.until(EC.presence_of_element_located((By.XPATH, f'//a[contains(@href, "{id}")]')))
                        myElem.click()
                    except Exception as e:
                        print(e)
                    accept_cookies(wait)


                    time.sleep(randint(1,3))
                    try:
                        if state_1>50:
                            if state_2>150:
                                total_height = int(driver.execute_script("return document.body.scrollHeight"))
                                for i in range(1, total_height, 5):
                                    driver.execute_script("window.scrollTo(0, {});".format(i))
                            if state_1>120:
                                myElem = wait.until(EC.presence_of_element_located((By.XPATH, f"//div[@data-test='rating-suffix']")))
                                driver.execute_script("arguments[0].scrollIntoView();", myElem)
                                time.sleep(1)
                                myElem.click()
                                time.sleep(1.5)
                                total_height = int(driver.execute_script("return document.body.scrollHeight"))
                                for i in range(1, total_height, 5):
                                    driver.execute_script("window.scrollTo(0, {});".format(i))
                            if state_2<120:
                                myElem = wait.until(EC.presence_of_element_located((By.XPATH, f"//button[@data-test='carousel-next']")))
                                driver.execute_script("arguments[0].scrollIntoView();", myElem)
                                for next in range(3):
                                    myElem.click()
                                    time.sleep(randint(1,4))

                            myElem = wait.until(EC.presence_of_element_located((By.XPATH, f"//a[@data-test='add-to-basket']")))
                            url1 = myElem.get_attribute('href')
                            driver.execute_script("arguments[0].scrollIntoView();", myElem)
                            time.sleep(2)
                            driver.get(url1)
                            
                            print('Added to basket!')
                            time.sleep(randint(config['MIN_WAIT'],config['MIN_WAIT']*3))
                            driver.close()
                            continue
                        elif search:
                            if state_1<100:
                                total_height = int(driver.execute_script("return document.body.scrollHeight"))
                                for i in range(1, total_height, 5):
                                    driver.execute_script("window.scrollTo(0, {});".format(i))
                            myElem = wait.until(EC.presence_of_element_located((By.XPATH, '//wsp-wishlist-button[@data-test="btn-wishlist"]')))
                            driver.execute_script("arguments[0].scrollIntoView();", myElem)
                            myElem = wait.until(EC.presence_of_element_located((By.XPATH, '//wsp-wishlist-button[@data-test="btn-wishlist"]')))
                            myElem.click()
                            print('Added to Wishlist!')
                            time.sleep(randint(config['MIN_WAIT'],config['MAX_WAIT']))
                            driver.close()
                            continue
                        continue
                    except Exception as e:
                        print('1',e)
                        pass
                else:
                    try:
                        time.sleep(randint(config['MIN_WAIT'],config['MAX_WAIT']))
                        total_height = int(driver.execute_script("return document.body.scrollHeight"))-300
                        for i in range(1, total_height, 10):
                            driver.execute_script("window.scrollTo(0, {});".format(i))
                            time.sleep(0.01)
                            
                        element = driver.find_elements(By.XPATH,'//a[@class="js_pagination_item"]')
                        if element:
                            if state_1>100:
                                ins = 0
                            else:
                                ins = -1
                            driver.execute_script("arguments[0].scrollIntoView();", element[ins])
                            time.sleep(randint(config['MIN_WAIT'],config['MAX_WAIT']))
                            element[pg_cnt].click()
                            pg_cnt+=1
                        else:
                            print('pagination not found.')
                            driver.close()
                            
                            continue
                        
                    except Exception as e:
                        print(e)
                        try:
                            driver.close()
                            continue
                        except:
                            pass
                        continue
                    # myElem = wait.until(EC.presence_of_element_located((By.XPATH, '//li[@class="[ pagination__controls pagination__controls--next ] js_pagination_item"]')))
                    # myElem.click()

        except Exception as e:
            if "ERR_TUNNEL_CONNECTION_FAILED" in str(e):
                proxy_error=True
            print(f"ME: {e}")
            try:
                driver.close()
                continue
            except:
                pass
            time.sleep(30)




if __name__=="__main__":
    import os
    print(os.getpid())
    freeze_support()
    import undetected_chromedriver as uc
    threads = []
    search_terms = config['keywords']
    for st in list(search_terms):
        t = Thread(target=task,args=(st,),daemon=True)
        threads.append(t)
        
    [t.start() for t in threads]
    [t.join() for t in threads]
    
