import random
import time
from typing import Dict, List, Any, Union
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from utils.utils import solve_captch
from rich.console import Console


class Reporter(webdriver.Remote):

    def __init__(self, profile_name: str, profile_uuid: str, urls: List[str], command_executor: str,
                 destroy_browser: bool = True) -> None:
        self.command_executor = command_executor
        # self.capabilities = desired_capabilities
        self.profile_name = profile_name
        self.profile_uuid = profile_uuid
        self.urls = urls
        self.destroy_browser = destroy_browser
        self.console = Console()
        self.tracker = []

        super(Reporter, self).__init__(self.command_executor, desired_capabilities={})
        self.set_page_load_timeout(15)
        self.implicitly_wait(15)

    def start_reporting(self):
        """
        Starts reporting for the urls and profile given in the initial
        """
        self.console.log(f"reporting started for {self.profile_name}", style="green")

        for url in self.urls:

            self.tracker.append({
                'profile': self.profile_name,
                'exists': True,
                'url': url
            })

            if self.get_page(url):
                captcha = self.solve_captcha()
                logged_in = self.is_profile_logged_in()

                self.tracker[-1]['captcha_solved'] = captcha
                self.tracker[-1]['Logged_in'] = logged_in

                if captcha and logged_in:
                    try:
                        self.move_mouse_around()
                        for i in range(3):
                            if self.click_abuse_button():
                                break
                            else:
                                continue
                    except:
                        self.tracker[-1]['report_button_clicked'] = False

                elif not logged_in:
                    break
                else:
                    continue
            else:
                self.tracker[-1]['exists'] = False

            time.sleep(1)



        self.quit()
        return self.tracker

    def get_page(self, url: str) -> None:
        """
        gets the url in the browser.\n
        parameters:\n
        url:<str>
        returns:\n
        None
        """
        attempts = 0
        url_open = False
        while not url_open:
            for kk in range(3):
                try:
                    self.get(url)
                    break
                except Exception as e:
                    if kk >= 2:
                        print(e)
                        return False
                    time.sleep(10)
                    pass
            if self.find_elements(By.CSS_SELECTOR, "img[alt *= 'We couldn\\'t find that page']"):
                self.console.log("404 page found", style="green")
                return False

            if self.find_elements(By.ID, "nav-logo") or "Try different image" in self.page_source:
                url_open = True
                print("page loaded")
                self.bring_to_front()
                time.sleep(2)
                return True
            if attempts >= 3:
                print("page not loaded")
                break
            attempts += 1
        return url_open

    def solve_captcha(self) -> bool:
        """
        Checks if captcha appreared on the page.if appeared will try to solve it.
        return:
        True  : if captcha was solved
        False : if captcha was not solved
        """

        if "Try different image" in self.page_source:
            print(f"Captcha appear for profile [{self.profile_uuid}]")
            if not solve_captch(self):
                print(self.profile_name, "CAPTCHA not solved")
                return False
        return True

    def bring_to_front(self):
        try:
            self.minimize_window()
        except:
            pass
        try:
            self.maximize_window()
        except:
            pass

    def is_profile_logged_in(self) -> bool:
        """
        Checks if the multilogin is logged into amazon \n
        returns:\n
        True  : if the profile is logged in
        False : if the profile is not logged in
        """

        if self.find_elements(By.CSS_SELECTOR, 'a[data-csa-c-content-id="nav_youraccount_btn"]'):
            self.tracker[-1]['Logged_in'] = True
            return True
        self.console.log(f"{self.profile_name}:Profile not logged in into Amazon account", style='red')
        return False

    def click_abuse_button(self) -> bool:
        """
        Clicks abuse button for the review.
        """
        abuse_btns = None
        for i in range(3):
            abuse_btns = self.find_elements(By.CSS_SELECTOR, "a.report-abuse-link")
            if len(abuse_btns) < 1:
                time.sleep(2)
                continue
            else:
                break
        if abuse_btns:
            self.execute_script("arguments[0].scrollIntoView(true);", abuse_btns[0])
            abuse_btns[0].click()
            time.sleep(2)
            report_window = None
            main_window = self.current_window_handle
            # when clicked on abuse button it opens a new tab
            # so we try to find the popup window
            for window in self.window_handles:
                if window != main_window:
                    report_window = window

            if report_window:
                self.switch_to.window(report_window)
                # sometime captcha appears
                captcha = self.solve_captcha()
                self.tracker[-1]['report_captcha_solved'] = captcha
                if captcha:
                    report_button = self.find_element(By.CSS_SELECTOR, 'a[data-hook="cr-report-abuse-pop-over-button"]')
                    if report_button:
                        report_button.click()
                        self.tracker[-1]['abused_button_clicked'] = True
                        time.sleep(1)
                        self.console.log(f"[{self.profile_name}] [Report abuse ] button clicked 2", style="blue")
                        self.close()
                        time.sleep(2)
                        self.switch_to.window(main_window)
                        self.tracker[-1]['report_button_clicked'] = True
                        return True

                    self.tracker[-1]['report_button_clicked'] = False
                    self.console.log("report button not found", style="red")
                else:
                    self.console.log("CAPTCHA not solved for report button popup", style="red")

            return False

        else:
            print(f"[{self.profile_name}] Abuse button not found")
            return False

    def move_mouse_around(self):
        """
        moves mouse arounds the screen in random pattern.
        """
        elements = self.find_elements(By.CSS_SELECTOR, 'a')
        # elements = list(filter(lambda x : x.is_displayed() , elements))
        actions = ActionChains(self)
        length_of_elements = len(elements)
        if elements:
            for _ in range(length_of_elements if length_of_elements <= 5 else 5):
                try:
                    move_to = random.choice(elements)
                    self.execute_script("arguments[0].scrollIntoView(true);", move_to)
                    actions.move_to_element(random.choice(elements)).pause(2).perform()
                    time.sleep(2)
                    actions.reset_actions()
                except:
                    pass
        time.sleep(2)

    def bring_inside_viewport(self, selector: str = '[id^=CardInstance]'):
        """
        brings a element to the center of viewport
        """
        recommendations = self.find_element(By.CSS_SELECTOR, selector)
        if recommendations:
            desired_y = (recommendations.size['height'] / 2) + recommendations.location['y']
            window_h = self.execute_script('return window.innerHeight')
            window_y = self.execute_script('return window.pageYOffset')
            current_y = (window_h / 2) + window_y
            scroll_y_by = desired_y - current_y
            self.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)

    def __exit__(self, *args) -> None:
        if self.destroy_browser:
            try:
                self.quit()
            except:
                pass


