"""
Provides methods to establish a connection to the GPRO website as well as
scrape and parse its contents.
"""
import json
import os
from dataclasses import dataclass, field, asdict
import datetime
import logging
import re
from getpass import getpass

import requests
from bs4 import BeautifulSoup


@dataclass
class DriverDataClass:
    name: str
    oa: int
    concentration: int
    talent: int
    aggressiveness: int
    experience: int
    technical_insight: int
    stamina: int
    charisma: int
    motivation: int
    reputation: int
    weight: int


@dataclass
class SetupDataClass:
    tyre: str
    front_wing: int
    rear_wing: int
    engine: int
    brakes: int
    gearbox: int
    suspension: int


@dataclass
class PracticeLapDataClass:
    setup: SetupDataClass
    lap_time: datetime.timedelta
    net_time: datetime.timedelta
    driver_mistake: datetime.timedelta
    comments: str


@dataclass
class RaceRiskData:
    overtake: int = None
    defend: int = None
    clear: int = None
    malfunction: int = None


@dataclass
class EnergyDataClass:
    q1_pre: int = None
    q1_post: int = None
    q2_pre: int = None
    q2_post: int = None
    race_pre: int = None
    race_post: int = None


@dataclass
class CcpDataClass:
    power: int = None
    handling: int = None
    acceleration: int = None


@dataclass
class TyreSupplierDataClass:
    name: str
    peak_temperature: int
    dry: int
    wet: int
    durability: int
    warmup: int


@dataclass
class QualifyingData:
    setup: SetupDataClass = None
    fuel: int = None
    risk: str = None
    temperature: int = None
    humidity: int = None
    weather: str = None
    lap_time: datetime.timedelta = None


@dataclass
class WeatherForecastData:
    temperature_min: int = None
    temperature_max: int = None
    humidity_min: int = None
    humidity_max: int = None
    rain_min: int = None
    rain_max: int = None


@dataclass
class PitStopData:
    lap: int = None
    reason: str = None
    tyre_condition: int = None
    fuel_left_percent: int = None
    fuel_refilled: int = None
    time: datetime.timedelta = None


@dataclass
class TechProblemData:
    lap: int = None
    details: str = None


@dataclass
class OvertakingData:
    initiated_blocked: int = None
    initiated_successful: int = None
    on_you_blocked: int = None
    on_you_successful: int = None


@dataclass
class FinancesData:
    total_income: int = None
    race_position: int = None
    qualifying_position: int = None
    sponsor: int = None
    driver_salary: int = None
    staff_salary: int = None
    facility_cost: int = None
    tyre_cost: int = None


@dataclass
class CarPartData:
    chassis: int = None
    engine: int = None
    front_wing: int = None
    rear_wing: int = None
    underbody: int = None
    sidepods: int = None
    cooling: int = None
    gearbox: int = None
    brakes: int = None
    suspension: int = None
    electronics: int = None


@dataclass
class LapData:
    lap: int = None
    boost: bool = None
    time: datetime.timedelta = None
    position: int = None
    tyres: str = None
    weather: str = None
    temperature: int = None
    humidity: int = None
    events: str = None


@dataclass
class RaceAnalysisData:
    track_name: str = None
    track_id: str = None
    season: int = None
    race: int = None
    group: str = None
    practice: list[PracticeLapDataClass] = field(default_factory=list)
    qualifying1: QualifyingData = field(default_factory=QualifyingData)
    qualifying2: QualifyingData = field(default_factory=QualifyingData)
    setup_race: SetupDataClass = None
    risk_race: RaceRiskData = None
    driver_stats: DriverDataClass = None
    driver_change: DriverDataClass = None
    energy: EnergyDataClass = None
    position_start: int = None
    position_finish: int = None
    ccp: CcpDataClass = None
    tyre_supplier: TyreSupplierDataClass = None
    weather: tuple[WeatherForecastData, WeatherForecastData, WeatherForecastData, WeatherForecastData] = field(
        default_factory=tuple)
    pitstops: list[PitStopData] = field(default_factory=list)
    problems: list[TechProblemData] = field(default_factory=list)
    tyre_condition_finish: int = None
    fuel_start: int = None
    fuel_left_finish: int = None
    overtaking: OvertakingData = None
    finances: FinancesData = None
    car_part_levels: CarPartData = None
    car_part_wear_start: CarPartData = None
    car_part_wear_finish: CarPartData = None
    lap_chart: list[LapData] = field(default_factory=list)
    notes: str = None


class GproScraper:
    def __init__(self, username: str, password: str):
        self.username: str = username
        self.password: str = password
        self.session: requests.Session = self._session_login()
        self.saved_data: dict[(int, int), RaceAnalysisData] = dict()
        logging.basicConfig()
        self.logger = logging.getLogger()

    def _session_login(self):
        session = requests.Session()
        login_url = "https://gpro.net/gb/Login.asp"
        login_data = {'textLogin': self.username,
                      'textPassword': self.password,
                      'token': '',
                      'Logon': 'Login',
                      'LogonFake': 'Sign+in'}
        login_headers = {'User-Agent': 'GASS/0.0.1 by Jens Jaeschke'}
        session.headers.update(login_headers)
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
        result = session.get(login_url)
        try:
            result = session.post(login_url, data=login_data, headers=login_headers,
                                  allow_redirects=False)
            assert result.status_code == 302
        except RuntimeError:
            print("Login failed. Response code: " + str(result.status_code))
        # print(result.status_code)
        # print(result.text)
        return session

    def get_race_analysis(self, season: int = None, race: int=None) -> RaceAnalysisData:
        try:
            data = self.saved_data[(season,race)]
        except KeyError:
            data = self.parse_race_analysis(season, race)
        return data

    def parse_race_analysis(self, season: int = None, race: int = None) -> RaceAnalysisData:
        """Download and parse the race analysis page for the specified race, defaults to most recent"""

        parsed_page = self.load_race_analysis(season, race)

        # check for race participation and error if not participated
        if parsed_page.select_one(".center").text == f"You did not participate in Season {season}, Race {race}":
            raise NotRacedError(f"You did not participate in Season {season}, Race {race}")
        data = RaceAnalysisData()
        # populate instance with basic info
        data.track_name = parsed_page.select_one(".block > a:nth-child(7)").text
        data.track_id = re.search(r"id=(\d*)", parsed_page.select_one(
            ".block > a:nth-child(7)").attrs.get("href")).group(1)
        # pull season, race number and group with regex
        regex = re.compile(r"Season (\d*) - Race (\d*) \((\w* - \d*)\)")
        regex.search(parsed_page.select_one(".block").text).group(1)
        data.season = int(regex.search(parsed_page.select_one(".block").text).group(1))
        data.race = int(regex.search(parsed_page.select_one(".block").text).group(2))
        data.group = regex.search(parsed_page.select_one(".block").text).group(3)
        # parse setups
        (data.qualifying1.setup, data.qualifying2.setup, data.setup_race) = _parse_race_analysis_setups(parsed_page)
        # parse driver
        (data.driver_stats, data.driver_change) = _parse_race_analysis_driver(parsed_page)
        # parse car parts data_dict
        (data.car_part_levels, data.car_part_wear_start, data.car_part_wear_finish) = _parse_race_analysis_car_parts(
            parsed_page)
        # parse weather forecast
        weather_table = parsed_page.find("th", text="Sessions weather").parent.parent
        qualifying_weather_regex = re.compile(r"Temp: (\d*)°C\s*Humidity: (\d*)%")
        # qualifying 1 weather
        data.qualifying1.weather = weather_table.select_one("tr:nth-of-type(3) > td:nth-of-type(1) > img").attrs["title"]
        data.qualifying1.temperature = int(qualifying_weather_regex.search(weather_table.select_one("tr:nth-of-type(3) > "
                                                                                                    "td:nth-of-type(1)"
                                                                                                    ).text).group(1))
        data.qualifying1.humidity = int(qualifying_weather_regex.search(weather_table.select_one("tr:nth-of-type(3) > "
                                                                                                 "td:nth-of-type(1)"
                                                                                                 ).text).group(2))
        # qualifying 2 weather
        data.qualifying2.weather = weather_table.select_one("tr:nth-of-type(3) > td:nth-of-type(2) > img").attrs["title"]
        data.qualifying2.temperature = int(
            qualifying_weather_regex.search(weather_table.select_one("tr:nth-of-type(3) > td:nth-of-type(2)").text).group(
                1))
        data.qualifying2.humidity = int(
            qualifying_weather_regex.search(weather_table.select_one("tr:nth-of-type(3) > td:nth-of-type(2)").text).group(
                2))
        # forecasts
        forecast_regex = re.compile(
            r"Temp:\s*(\d*)°\s*-\s*(\d*)°\s*Humidity:\s*(\d*)%\s*-\s*(\d*)%\s*Rain\s*probability:\s*(\d*)%\s*-?\s*(\d*)%?"
        )
        match1 = forecast_regex.search(weather_table.select_one("tr:nth-of-type(6)>td:nth-of-type(1)").text)
        forecast1 = WeatherForecastData(temperature_min=match1.group(1), temperature_max=match1.group(2),
                                        humidity_min=match1.group(3), humidity_max=match1.group(4),
                                        rain_min=match1.group(5),
                                        rain_max=match1.group(6) if match1.group(6) else match1.group(5))
        match2 = forecast_regex.search(weather_table.select_one("tr:nth-of-type(6)>td:nth-of-type(2)").text)
        forecast2 = WeatherForecastData(temperature_min=match2.group(1), temperature_max=match2.group(2),
                                        humidity_min=match2.group(3), humidity_max=match2.group(4),
                                        rain_min=match2.group(5),
                                        rain_max=match2.group(6) if match2.group(6) else match2.group(5))
        match3 = forecast_regex.search(weather_table.select_one("tr:nth-of-type(8)>td:nth-of-type(1)").text)
        forecast3 = WeatherForecastData(temperature_min=match3.group(1), temperature_max=match3.group(2),
                                        humidity_min=match3.group(3), humidity_max=match3.group(4),
                                        rain_min=match3.group(5),
                                        rain_max=match3.group(6) if match3.group(6) else match3.group(5))
        match4 = forecast_regex.search(weather_table.select_one("tr:nth-of-type(8)>td:nth-of-type(2)").text)
        forecast4 = WeatherForecastData(temperature_min=match4.group(1), temperature_max=match4.group(2),
                                        humidity_min=match4.group(3), humidity_max=match4.group(4),
                                        rain_min=match4.group(5),
                                        rain_max=match4.group(6) if match4.group(6) else match4.group(5))
        data.weather = (forecast1, forecast2, forecast3, forecast4)
        self.saved_data[(season,race)] = data
        return data

    def load_race_analysis(self, season, race):
        """load the race analysis of the specified race"""
        if season is None and race is None:
            html_page = self.session.get("https://gpro.net/gb/RaceAnalysis.asp")

        elif season is not None and race is not None:
            html_page = self.session.get(f"https://gpro.net/gb/RaceAnalysis.asp?SR={season},{race}")

        else:
            raise ValueError("season and race must either both be provided or neither.")
        parsed_page = BeautifulSoup(html_page.text, 'html.parser')
        return parsed_page

    def parse_season_race_analysis(self, season: int = None):
        most_recent = self.parse_race_analysis()
        results = dict()
        for r in range(1, 18):
            try:
                data = self.parse_race_analysis(season, r)
                results[(season, r)] = data
                self.logger.log(logging.DEBUG, f"scraped Season {season}, Race {r} successfully.")
            except NotRacedError:
                self.logger.log(logging.DEBUG, f"Season {season}, Race {r} was not raced. Skipping.")
                continue
        self.logger.log(logging.DEBUG, f"successfully scraped {len(results)} races in season {season}.")
        return results

    def parse_all_race_analysis(self) -> dict[tuple[int, int], RaceAnalysisData]:
        """Parse the race analysis page for all races"""
        most_recent = self.parse_race_analysis()
        results = dict()
        for s in range(1, most_recent.season + 1):
            results.update(self.parse_season_race_analysis(s))
        self.logger.log(logging.DEBUG, f"successfully scraped {len(results)} races in total.")
        return results


class NotRacedError(Exception):
    pass


def _parse_race_analysis_setups(parsed_page: BeautifulSoup) -> tuple[SetupDataClass, SetupDataClass, SetupDataClass]:
    """
    parse the Setups used table on the Race analysis page
    :param parsed_page: BeautifulSoup object for the Race analysis page
    :return: tuple of SetupDataClass containing the setups and tyres used
    """
    setup_table = parsed_page.find("th", text="Setups used").parent.parent
    setups_dict = {
        "Q1": [ele.text.strip() for ele in setup_table.select_one("tr:nth-of-type(3)").find_all("td")],
        "Q2": [ele.text.strip() for ele in setup_table.select_one("tr:nth-of-type(4)").find_all("td")],
        "Race": [ele.text.strip() for ele in setup_table.select_one("tr:nth-of-type(5)").find_all("td")]
    }
    # clean up the lists and extract tyres
    setups_dict["Q1"].pop(0)
    setups_dict["Q1_tyres"] = setups_dict["Q1"].pop()
    setups_dict["Q2"].pop(0)
    setups_dict["Q2_tyres"] = setups_dict["Q2"].pop()
    setups_dict["Race"].pop(0)
    setups_dict["Race_tyres"] = setups_dict["Race"].pop()
    # type conversion to int
    setups_dict["Q1"] = [int(e) for e in setups_dict["Q1"]]
    setups_dict["Q2"] = [int(e) for e in setups_dict["Q2"]]
    setups_dict["Race"] = [int(e) for e in setups_dict["Race"]]

    setup_q1 = SetupDataClass(setups_dict["Q1_tyres"], *setups_dict["Q1"])
    setup_q2 = SetupDataClass(setups_dict["Q2_tyres"], *setups_dict["Q2"])
    setup_race = SetupDataClass(setups_dict["Race_tyres"], *setups_dict["Race"])

    return setup_q1, setup_q2, setup_race


def _parse_race_analysis_driver(parsed_page: BeautifulSoup) -> tuple[DriverDataClass, DriverDataClass]:
    """
    parse the driver stats and stat changes on the race analysis page
    :param parsed_page: BeautifulSoup object for the Race analysis page
    :return: tuple of 2 DriverDataClass instances denoting stats and stat changes
    """
    driver_table = parsed_page.find("th", text="Driver attributes").parent.parent
    driver_info_list = [ele.text.strip() for ele in driver_table.select_one("tr:nth-of-type(3)").find_all("td")]
    driver_name = driver_info_list[0]
    driver_stat_list = [int(e) for e in driver_info_list[1:]]
    driver_stats = DriverDataClass(driver_name, *driver_stat_list)
    try:
        driver_change_list = [int(ele.text.strip("() \n")) for ele in
                              driver_table.select_one("tr:nth-of-type(4)").find_all("td")]
        driver_changes = DriverDataClass(driver_name, *driver_change_list)
    except AttributeError:
        driver_changes = None
    return driver_stats, driver_changes


def _parse_race_analysis_car_parts(parsed_page: BeautifulSoup) -> tuple[CarPartData, CarPartData, CarPartData]:
    """
    parse the car part level, start wear and finish wear of the race analysis page
    :param parsed_page: BeautifulSoup object for the Race analysis page
    :return: tuple of 3 CarPartData instances, denoting level, start wear and finish wear
    """
    car_table = parsed_page.find("th", text="Car parts level").parent.parent
    car_level_list = [int(ele.text.strip()) for ele in car_table.select_one("tr:nth-of-type(3)").find_all("td")]
    car_level_data = CarPartData(*car_level_list)
    start_wear_list = [int(ele.text.strip("% \n)")) for ele in car_table.select_one("tr:nth-of-type(5)").find_all("td")]
    start_wear = CarPartData(*start_wear_list)
    finish_wear_list = [int(ele.text.strip("% \n)")) for ele in
                        car_table.select_one("tr:nth-of-type(7)").find_all("td")]
    finish_wear = CarPartData(*finish_wear_list)

    return car_level_data, start_wear, finish_wear


def terminal_login():
    """
    Requests username and password on the command line, creates a logged-in scraper instance
    """
    username = input("GPRO-Username:")
    password = getpass("GPRO-Password:")
    scraper = GproScraper(username, password)
    return scraper


def manual_test_parse_all_race_analysis():
    scraper = terminal_login()
    results = scraper.parse_all_race_analysis()
    print(len(results))


def main():
    """Main method for manual testing purposes."""
    manual_test_dump_json_file()


def manual_test_parse_single_race_analysis(season=None, race=None):
    scraper = terminal_login()
    try:
        parsed_race = scraper.parse_race_analysis(season, race)
    except NotRacedError:
        raise
    print(parsed_race)
    print(asdict(parsed_race))


def manual_test_dump_json_file(season=None, race=None):
    scraper = terminal_login()
    try:
        parsed_race = scraper.parse_race_analysis(season, race)
        dump_json_to_file(parsed_race, f"./scraped_data/race_analysis_{parsed_race.season}-{parsed_race.race}.json")
    except NotRacedError:
        raise


def dump_json_to_file(data: RaceAnalysisData, filename: str):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as file:
        file.write(json.dumps(asdict(data), indent=4))


if __name__ == "__main__":
    main()
