import time
from amazoncaptcha import AmazonCaptcha
from selenium.webdriver.common.by import By


def solve_captch(driver, attempts=3):
    for i in range(0, attempts):
        print(f"Trying to solve captcha, attempt {i+1}")
        try:
            href = driver.find_element(By.XPATH, "//img[contains(@src, 'captcha')]").get_attribute('src')
            captcha = AmazonCaptcha.fromlink(href)
            solution = captcha.solve()
            print(f"Captcha solution - {solution}")
            driver.find_element(By.CSS_SELECTOR, 'input#captchacharacters').send_keys(solution)
            time.sleep(1)
            driver.find_element(By.CSS_SELECTOR, 'button.a-button-text').click()
            time.sleep(1)
            if "Try different image" in driver.page_source:
                try:
                    driver.minimize_window()
                except:
                    pass
                try:
                    driver.maximize_window()
                except:
                    pass

                continue
            else:
                print("Captcha solved")
                return True
        except Exception as e:
            try:
                driver.minimize_window()
            except:
                pass
            try:
                driver.maximize_window()
            except:
                pass
            continue

    print("Captcha not solved.")
    return False
