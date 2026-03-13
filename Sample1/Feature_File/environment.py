from selenium import webdriver
from Sample1.Feature_File.POM.Page_Keyword import Pagekeywords


def before_all(context):
    context.driver = webdriver.Chrome()
    context.driver.maximize_window()
    context.PKEY = Pagekeywords(context)


def after_all(context):
    context.driver.quit()