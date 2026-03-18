from email.header import Header

from selenium import webdriver
from Sample1.Feature_File.POM.Page_Keyword import Pagekeywords
from selenium.webdriver.chrome.options import Options

def before_all(context):
    options = Options()
    # options.add_argument("--headless")  # ❌ keep this commented if you want UI

    context.driver = webdriver.Chrome(options=options)
    context.driver.maximize_window()

    context.PKEY = Pagekeywords(context)


def after_all(context):
    context.driver.quit()