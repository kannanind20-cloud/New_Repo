from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Sample1.Feature_File.POM.Page_object_Model import page_obj

POBJ = page_obj()


class Pagekeywords:

    def __init__(self, context):
        self.driver = context.driver
        self.wait = WebDriverWait(self.driver, 10)

    def userlogin(self, username, password):

        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, POBJ.username))
        ).send_keys(username)

        self.wait.until(
            EC.visibility_of_element_located((By.XPATH, POBJ.password))
        ).send_keys(password)

        self.driver.find_element(By.ID, POBJ.login_button).click()