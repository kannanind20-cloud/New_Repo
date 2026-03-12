import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from behave import given, when, then


@given(u'User need to navigated to practicetestautomation')
def step_impl(context):
    context.driver.get('https://practicetestautomation.com/practice-test-login/')
    title = context.driver.title
    print(title)
    assert title == 'Test Login | Practice Test Automation'


@when(u'Enter {username} and {password}')
def step_impl(context, username, password):
    context.PKEY.userlogin(username, password)


@then(u'User should be redirected to logged in page')
def step_impl(context):
    WebDriverWait(context.driver, 10).until(
        lambda driver: "logged-in-successfully" in driver.current_url
    )
    assert "logged-in-successfully" in context.driver.current_url


@when(u'User enters invalid {username1} and {password}')
def step_impl(context, username1, password):
    context.driver.find_element(By.XPATH, "//input[@name='username']").send_keys(username1)
    context.driver.find_element(By.XPATH, "//input[@name='password']").send_keys(password)


@when(u'Users clicks on Login button')
def step_impl(context):
    context.driver.find_element(By.ID, "submit").click()


@then(u'User not logged in due to invalid username and password')
def step_impl(context):
    print("Invalid login attempted")