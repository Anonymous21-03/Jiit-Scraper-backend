from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import base64
import time
import os
from threading import Lock

app = Flask(__name__)
CORS(app)

class WebDriverManager:
    def __init__(self):
        self.driver = None
        self.lock = Lock()
        
    def get_driver(self):
        with self.lock:
            if self.driver is None:
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
                self.driver.get("https://webportal.jiit.ac.in:6011/studentportal#/")
            return self.driver
    
    def quit_driver(self):
        with self.lock:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def check_invalid_captcha(self):
        try:
            error_toast = self.driver.find_elements(By.CSS_SELECTOR, ".toast-error")
            return error_toast and "Invalid captcha" in error_toast[0].text
        except:
            return False

driver_manager = WebDriverManager()

@app.route('/get_captcha', methods=['POST'])
def get_captcha():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'status': 'error',
                'message': 'Username and password are required'
            })

        driver = driver_manager.get_driver()
        wait = WebDriverWait(driver, 10)

        # Enter username first (as per your Python code)
        username_field = wait.until(EC.presence_of_element_located((By.ID, "mat-input-0")))
        username_field.clear()
        username_field.send_keys(username)

        # Get captcha image
        captcha_image = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#login-form form img")))
        captcha_url = captcha_image.get_attribute("src")
        
        if "base64," in captcha_url:
            image_data = captcha_url.split(",")[1]
            return jsonify({
                'status': 'success',
                'captcha_image': image_data
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to get captcha image'
            })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/verify_login', methods=['POST'])
def verify_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        captcha = data.get('captcha')

        if not all([username, password, captcha]):
            return jsonify({
                'status': 'error',
                'message': 'All fields are required'
            })

        driver = driver_manager.get_driver()
        wait = WebDriverWait(driver, 40)  # Increased timeout as per your Python code

        try:
            # Fill username and captcha first
            username_field = wait.until(EC.presence_of_element_located((By.ID, "mat-input-0")))
            username_field.clear()
            username_field.send_keys(username)

            captcha_input = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "input[formcontrolname='captcha']")))
            captcha_input.clear()
            captcha_input.send_keys(captcha)

            # Click first login button
            login_button = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "button[aria-label='LOGIN']")))
            login_button.click()

            time.sleep(2)  # Wait for response

            # Check for invalid captcha
            if driver_manager.check_invalid_captcha():
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid captcha'
                })

            # If captcha is valid, proceed with password
            password_field = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "input[type='password']")))
            password_field.send_keys(password)

            # Click second login button
            login_button = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "button[aria-label='LOGIN']")))
            login_button.click()

            time.sleep(5)  # Wait for login to complete

            # Check if login was successful
            if "studentportal/#/student" in driver.current_url:
                return jsonify({
                    'status': 'success',
                    'message': 'Login successful'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Login failed'
                })

        except TimeoutException:
            return jsonify({
                'status': 'error',
                'message': 'Timeout while waiting for elements'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Login process error: {str(e)}'
            })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/logout', methods=['POST'])
def logout():
    try:
        driver_manager.quit_driver()
        return jsonify({'status': 'success', 'message': 'Session ended successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)