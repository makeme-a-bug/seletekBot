from typing import Dict, List, Any, Union
import requests
import pandas as pd
from .reporter import Reporter
from rich.console import Console
import time
from concurrent.futures import ThreadPoolExecutor
import datetime
import random
import os

start_time = datetime.datetime.now()
fold = f"./{start_time.strftime('%y-%m-%d %H-%M-%S')}_results"


class ReporterManager:

    def __init__(self, file: str = "inputs/report_abuse_input.csv", port: int = 35111):

        self.file = file
        self.port = port
        self.console = Console()
        self.profiles = self.getProfiles()
        self.inputs = self.getInput()
        self.create_reporters()

    def getProfiles(self) -> Union[Dict, None]:
        """
        Get all profiles from multilogin
        """
        try:
            url = f'http://localhost:{self.port}/api/v2/profile'
            profiles = requests.get(url)
            print(profiles.status_code)
            profiles = profiles.json()
            profiles_map = {}
            for r in profiles:
                profiles_map[r['name']] = r['uuid']

            return profiles_map

        except requests.exceptions.Timeout:
            self.console.log(f"Request to get profiles timeout", style="red")
            return

        except requests.exceptions.ConnectionError as e:
            self.console.log(f"Please make sure multilogin API is running. Failed to make request to the API.",
                             style="red")
            print(e)
            raise SystemExit()

        except requests.exceptions as e:
            self.console.log("Request failed due to", style="red")
            print(e)
            return

    def getInput(self) -> pd.DataFrame:
        """
        reads the report_abuse_input.csv
        """
        df = pd.read_csv(self.file)
        df.sort_values(["Profile"], inplace=True)
        df = df[50:]
        return df

    def start_profile_browser(self, profile_id: str) -> Union[str, None]:
        """
            Starts browser profile for given profile_id
        """
        json: Dict = {}
        for i in range(2):
            try:
                mla_url = (
                        f"http://127.0.0.1:{self.port}/api/v1/profile/start?automation=true&profileId=" + profile_id
                )
                resp = requests.get(mla_url)
                json = resp.json()
                if resp.status_code == 500:
                    self.console.log(f"profile with id:{profile_id} not found. trying again", style="red")
                    time.sleep(5)
                    continue
                break


            except requests.exceptions.Timeout as e:
                self.console.log(f"Request to get profile:{profile_id} timeout", style="red")

            except requests.exceptions.ConnectionError as e:
                self.console.log(f"Please make sure multilogin API is running. Failed to make request to the API.",
                                 style="red")

            except requests.exceptions as e:
                self.console.log("Request failed due to", style="red")
                print(e)

            except Exception as e:
                print(e)

            self.console.log("trying again", style="red")
            time.sleep(5)
            continue

        return json.get('value', None)

    def reporter(self, profile_name) -> List:
        data = []
        profile_uuid: str = self.profiles.get(profile_name, None)
        if not profile_uuid:
            self.console.log(f"profile not found:{profile_name}", style='red')
            data.append({
                'profile': profile_name,
                'exists': False,
            })
            return data

        urls: List[str] = self.inputs[self.inputs['Profile'] == profile_name]['Review URL'].tolist()
        random.shuffle(urls)

        mla_url = self.start_profile_browser(profile_uuid)
        if not mla_url:
            return
        R = Reporter(profile_name, profile_uuid, urls, mla_url)
        data = R.start_reporting()

        self.console.log(f"{profile_name} reporting complete", style='green')
        tracker = pd.DataFrame(data)
        tracker.to_csv(f'{fold}/{profile_name}__report.csv')
        time.sleep(60)
        return data

    def create_reporters(self):
        # with self.console.status("[bold green]Working on tasks...") as status:
        if not os.path.exists(fold):
            os.mkdir(fold)

        profiles = []
        for p in range(0, len(self.inputs.Profile.unique()), 2):
            with ThreadPoolExecutor(max_workers=2) as executor:
                data = executor.map(self.reporter, self.inputs.Profile.unique()[p: p + 2]) 
                for d in data:
                    profiles.extend(d)
            time.sleep(10)

        tracker = pd.DataFrame(profiles)
        tracker.to_csv(f'{fold}/final__report.csv')

