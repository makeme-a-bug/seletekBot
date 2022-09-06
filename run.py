import json
import random
import time
from typing import Dict,List,Any,Union
import requests
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
import pandas as pd
# from utils import solve_captch
from .utils import solve_captch


class ReporterManager:
    
    def __init__(self,file:str="inputs/report_abuse_input.csv" , port:int = 35000):
        
        self.file = file
        self.port = port
        self.profiles = self.getProfiles()
        self.inputs = self.getInput()
        self.runDriver()
        
    
    def getProfiles(self) -> Dict:
        """
        Get all profiles from multilogin
        """
        url = f'http://localhost:{self.port}/api/v2/profile'
        profiles = requests.get(url)
        profiles = profiles.json()
        profiles_map = {}
        for r in profiles:
            profiles_map[r['name']] = r['uuid']

        return profiles_map
        
    
    def getInput(self) -> pd.DataFrame:
        """
        reads the report_abuse_input.csv
        """
        df = pd.read_csv(self.file)
        df = df[df['Profile']=='AlessiaSwan76']
        df.sort_values(["Profile"],inplace=True)
        return df
        
        
    
    def start_profile_browser(self, profile_id:str) -> Union[str, None]:
        """
            Starts browser profile for given profile_id        
        """
        try:
            mla_url = (
                f"http://127.0.0.1:{self.port}/api/v1/profile/start?automation=true&profileId=" + profile_id
            )
            print(mla_url)
            resp = requests.get(mla_url)
            json:Dict = resp.json()
            if resp.status_code == 500:
                print(f"profile with id:{profile_id} not found")
                return
            

        except requests.exceptions.Timeout:
            print(f"Request to get profile:{profile_id} timeout")
            return

        except requests.exceptions.ConnectionError as e:
            print(f"Please make sure multilogin API is running. Failed to make request to the API.")
            raise SystemExit(e)

        except requests.exceptions as e:
            print("Request failed due to")
            print(e)
            return
        
        return json.get('value',None)

            
    
    def create_reporters(self):
        for profile_name in self.inputs.Profile.unique():

            profile_uuid:str = self.profiles[profile_name]
            urls:List[str] = self.inputs[self.inputs['Profile'] == profile_name]['Review URL'].tolist()
            print(urls)

            mla_url = self.start_profile_browser(profile_uuid)
            if not mla_url:
                continue
            
            with Reporter(profile_name , profile_uuid , urls , mla_url) as R:
                R.start_reporting()


            
                    

class Reporter(webdriver.Remote):

    def __init__(self,profile_name:str,profile_uuid:str, urls:List[str], command_executor:str, desired_capabilities:Dict={} , destroy_browser:bool = True ) -> None:
        self.command_executor = command_executor
        self.capabilities = desired_capabilities
        self.profile_name = profile_name
        self.profile_uuid = profile_uuid
        self.urls = urls
        self.destroy_browser = destroy_browser

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
            self.move_mouse_around()
            logged_in = self.is_profile_logged_in()
            if captcha and logged_in:
                self.click_abuse_button()
            else:
                continue

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
        print(self.profile_name, "Profile not logged in into Amazon account")
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
                        print(f"[{self.profile_name}] [Report abuse ] button clicked")
                        time.sleep(2)
                        self.close()
                        self.switch_to_window(main_window)
                        return True
                print("report button not found")
            return False
            
        else:
            print(f"[{self.profile_name}] Abuse button not found")
            return False


    def move_mouse_around(self):
        """
        moves mouse arounds the screen in random pattern.
        """
        movements = [ [ 1 + random.random() * 100  , 1 + random.random() * 100]  for i in range(5) ]
        print(movements)
        actions = ActionChains(self)
        for move in movements:
            actions.move_by_offset(move[0], move[1]).pause(2).perform()
            actions.reset_actions()
            print(f'moved mouse to {move[0],move[1]}')

       

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


if __name__ == "__main__":
    bot = ReporterManager()

    
    
    
    