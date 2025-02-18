import django.contrib.staticfiles.management.commands.collectstatic
from django.conf import settings
from django.urls import reverse
#from django.test.selenium import SeleniumTestCase, screenshot_cases
#from selenium.webdriver.common.by import By

from thunderbird_accounts.authentication.models import User
from django.core import management


# class BaseUITestCase(SeleniumTestCase):
#     """Default UI test case that specifies the browsers and headless mode."""
#     browsers = ['firefox', 'chrome']
#     headless = True
#     screenshots = True
#
#
# class SignUpTestCase(BaseUITestCase):
#     def setUp(self):
#         self.user = User.objects.create(
#             username='Test',
#             email='test@example.org',
#         )
#
#     def force_login(self, user):
#         """Logins a user for selenium tests. Note: We need to load a single page first to add a cookie."""
#         self.client.force_login(user)
#         session_key = self.client.cookies[settings.SESSION_COOKIE_NAME].value
#         self.selenium.get(self.live_server_url)
#         self.selenium.add_cookie({'name': settings.SESSION_COOKIE_NAME, 'value': session_key, 'path': '/'})
#
#     @screenshot_cases(['desktop_size', 'mobile_size'])
#     def test_without_auth(self):
#         self.selenium.get(self.live_server_url + reverse('sign_up'))
#         self.selenium.implicitly_wait(1)
#         self.take_screenshot('sign-in')
#         form = self.selenium.find_element(By.CSS_SELECTOR, '#sign-in-form')
#         sign_in_button = form.find_element(By.CSS_SELECTOR, '#sign-in-btn')
#
#     @screenshot_cases(['desktop_size', 'mobile_size'])
#     def test_with_auth(self):
#         self.force_login(self.user)
#         self.selenium.get(self.live_server_url + reverse('sign_up'))
#         self.selenium.implicitly_wait(1)
#         self.take_screenshot('sign-up')
#         form = self.selenium.find_element(By.CSS_SELECTOR, '#sign-up-flow-form')
#         sign_up_button = form.find_element(By.CSS_SELECTOR, '#sign-up-btn')
#         sign_up_button.click()
#         self.selenium.implicitly_wait(1)
#         print(self.selenium.current_url)