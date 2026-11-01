import unittest
import threading
import time
from werkzeug.serving import make_server
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app import create_app

PORT = 5055
BASE_URL = f"http://127.0.0.1:{PORT}"


class ServerThread(threading.Thread):
    def __init__(self, app):
        super().__init__()
        self.server = make_server("127.0.0.1", PORT, app)
        self.daemon = True

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class CocoNutriCareSeleniumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start background test server
        cls.app = create_app()
        cls.server = ServerThread(cls.app)
        cls.server.start()
        time.sleep(1)

        # Configure headless Edge browser
        edge_options = Options()
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--window-size=1280,800")
        cls.driver = webdriver.Edge(options=edge_options)
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        finally:
            cls.server.shutdown()

    def test_01_landing_page(self):
        """Verify landing page loads successfully with brand and navigation."""
        self.driver.get(BASE_URL)
        self.assertIn("Coco NutriCare", self.driver.title)
        brand = self.driver.find_element(By.CLASS_NAME, "brand")
        self.assertIn("Coco NutriCare", brand.text)

    def test_02_login_failure(self):
        """Verify error flash message for invalid login credentials."""
        self.driver.get(f"{BASE_URL}/auth/login")
        self.driver.find_element(By.NAME, "email").send_keys("invalid@user.com")
        self.driver.find_element(By.NAME, "password").send_keys("wrongpassword")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        error_flash = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "flash"))
        )
        self.assertIn("Wrong email or password", error_flash.text)

    def test_03_parent_login_and_dashboard(self):
        """Verify parent authentication and navigation to parent dashboard."""
        self.driver.get(f"{BASE_URL}/auth/login")
        self.driver.find_element(By.NAME, "email").clear()
        self.driver.find_element(By.NAME, "email").send_keys("parent@coco.com")
        self.driver.find_element(By.NAME, "password").clear()
        self.driver.find_element(By.NAME, "password").send_keys("12345678")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/parent"))
        self.assertIn("/parent", self.driver.current_url)

        greeting = self.driver.find_element(By.CLASS_NAME, "greeting")
        self.assertIn("Amal", greeting.text)

    def test_04_parent_child_detail(self):
        """Verify child detail view for parent."""
        self.driver.get(f"{BASE_URL}/parent/children/1")
        child_name = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "h2"))
        )
        self.assertIn("Emma Rahman", child_name.text)

    def test_05_parent_reminders(self):
        """Verify parent reminders page."""
        self.driver.get(f"{BASE_URL}/parent/reminders")
        self.assertIn("/parent/reminders", self.driver.current_url)
        content = self.driver.find_element(By.TAG_NAME, "body").text
        self.assertTrue("Reminders" in content or "reminders" in content.lower())

    def test_06_doctor_login_and_dashboard(self):
        """Verify doctor authentication and access to doctor dashboard."""
        self.driver.get(f"{BASE_URL}/auth/logout")
        self.driver.get(f"{BASE_URL}/auth/login")
        self.driver.find_element(By.NAME, "email").send_keys("doctor@coco.com")
        self.driver.find_element(By.NAME, "password").send_keys("12345678")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/doctor"))
        self.assertIn("/doctor", self.driver.current_url)

    def test_07_maternal_login_and_dashboard(self):
        """Verify pregnant mother authentication and access to maternal dashboard."""
        self.driver.get(f"{BASE_URL}/auth/logout")
        self.driver.get(f"{BASE_URL}/auth/login")
        self.driver.find_element(By.NAME, "email").send_keys("mother@coco.com")
        self.driver.find_element(By.NAME, "password").send_keys("12345678")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(self.driver, 5).until(EC.url_contains("/maternal"))
        self.assertIn("/maternal", self.driver.current_url)

    def test_08_unauthorized_access_redirect(self):
        """Verify unauthenticated access to protected route redirects to login (Failure / Security test)."""
        self.driver.get(f"{BASE_URL}/auth/logout")
        self.driver.get(f"{BASE_URL}/parent/")
        WebDriverWait(self.driver, 5).until(EC.url_contains("/auth/login"))
        self.assertIn("/auth/login", self.driver.current_url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
