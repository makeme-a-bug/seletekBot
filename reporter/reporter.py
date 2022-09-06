import random
import time
from typing import Dict,List,Any,Union
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from utils.utils import solve_captch
from rich.console import Console

class Reporter(webdriver.Remote):

    def __init__(self,profile_name:str,profile_uuid:str, urls:List[str], command_executor:str, desired_capabilities:Dict={} , destroy_browser:bool = True ) -> None:
        self.command_executor = command_executor
        self.capabilities = desired_capabilities
        self.profile_name = profile_name
        self.profile_uuid = profile_uuid
        self.urls = urls
        self.destroy_browser = destroy_browser
        self.console = Console()

        super(Reporter,self).__init__(self.command_executor,desired_capabilities=self.capabilities)
        self.set_page_load_timeout(120)
        self.implicitly_wait(120)


    def start_reporting(self):
        """
        Starts reporting for the urls and profile given in the initial
        """
        for url in self.urls:
            self.get_page(url)
            captcha = self.solve_captcha()
            logged_in = self.is_profile_logged_in()
            if captcha and logged_in:
                self.move_mouse_around()
                self.click_abuse_button()
            elif not logged_in:
                break
            else:
                continue

        self.quit()

    def get_page(self,url:str) -> None:
        """
        gets the url in the browser.\n
        parameters:\n
        url:<str>
        returns:\n
        None
        """
        self.get(url)

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
    
    def is_profile_logged_in(self) -> bool:
        """
        Checks if the multilogin is logged into amazon \n
        returns:\n
        True  : if the profile is logged in
        False : if the profile is not logged in
        """

        if self.find_elements(By.CSS_SELECTOR, 'a[data-csa-c-content-id="nav_youraccount_btn"]'):
            return True
        self.console.log(f"{self.profile_name}:Profile not logged in into Amazon account",style='red')
        return False

    def click_abuse_button(self) -> bool:
        """
        Clicks abuse button for the review.
        """

        abuse_btns = self.find_elements(By.CSS_SELECTOR, "a.report-abuse-link")
        if abuse_btns:
            abuse_btns[0].click()
            report_window = None
            main_window = self.current_window_handle
            #when clicked on abuse button it opens a new tab
            #so we try to find the popup window
            for window in self.window_handles:
                if window != main_window:
                    report_window = window

            if report_window:
                self.switch_to_window(report_window)
                #sometime captcha appears
                captcha = self.solve_captcha()
                if captcha:
                    report_button = self.find_element(By.CSS_SELECTOR,'a[data-hook="cr-report-abuse-pop-over-button"]')
                    if report_button:
                        report_button.click()
                        self.console.log(f"[{self.profile_name}] [Report abuse ] button clicked" , style="blue")
                        time.sleep(1)
                        self.close()
                        self.switch_to_window(main_window)
                        return True
                self.console.log("report button not found",style="red")
            return False
            
        else:
            print(f"[{self.profile_name}] Abuse button not found")
            return False


    def move_mouse_around(self):
        """
        moves mouse arounds the screen in random pattern.
        """
        movements = [ [ 1 + random.random() * 100  , 1 + random.random() * 100]  for i in range(5) ]
        actions = ActionChains(self)
        for move in movements:
            actions.move_by_offset(move[0], move[1]).pause(1).perform()
            actions.reset_actions()
        
        self.bring_inside_viewport('[id^=CardInstance]')
        time.sleep(2)

       

    def bring_inside_viewport(self,selector:str='[id^=CardInstance]'):
        """
        brings a element to the center of viewport
        """
        recommendations = self.find_element(By.CSS_SELECTOR,selector)
        desired_y = (recommendations.size['height'] / 2) + recommendations.location['y']
        window_h = self.execute_script('return window.innerHeight')
        window_y = self.execute_script('return window.pageYOffset')
        current_y = (window_h / 2) + window_y
        scroll_y_by = desired_y - current_y
        self.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)




    def __exit__(self, *args) -> None:
        if self.destroy_browser:
            self.quit()


