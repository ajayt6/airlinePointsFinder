import time
from datetime import datetime
import pickle
import json

from bs4 import BeautifulSoup
from dateutil.rrule import rrule, DAILY
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# username = 'yojathoma+2@gmail.com'
# password = '12345687Qwe'
class_of_flight = 'economy'
default_buffer_wait = 2
default_buffer_wait_tab_load = 2


def get_date_input(date):
    while True:
        date_str = date
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD format.")


def extract_points(points_str, airline):
    # Find the index of the first occurrence of " pts"
    index = points_str.find(" pts")
    star_index = points_str.find("*")

    if index != -1:
        # Extract the part of the string before " pts"
        # Assuming a reasonable distance before " pts" for the number
        number_str = points_str[:index].strip()

        # If there are multiple numbers or elements, take the last part which should be the number
        # This is split on space and takes the last segment assuming it's the number
        number_str = number_str.split()[-1]

        # Remove commas
        number_str = number_str.replace(',', '')

        # Convert to integer
        number = int(number_str)
        print(f"{number} : {airline}")
        points_dollar_value = points_str[:star_index].strip()
        return number, points_dollar_value
    else:
        print("The string ' pts' was not found.")
        return -1


def select_sort_order(driver):
    # Waiting for the dropdown button to be clickable and then click it
    dropdown_button = WebDriverWait(driver, 2).until(
        EC.element_to_be_clickable((By.ID, "headlessui-menu-button-:rg:"))
    )
    dropdown_button.click()

    # Locate the option and click it
    option_to_select = WebDriverWait(driver, 2).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@id='headlessui-menu-button-:rg:']//span[text()='Points Low to High']"))
    )
    option_to_select.click()


def explicit_login(driver, username, password):
    signup_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign up')]")
    signup_button.click()

    time.sleep(default_buffer_wait)

    login_link = driver.find_element(By.XPATH, "//a[text()='Log in']")
    login_link.click()

    time.sleep(default_buffer_wait)

    # Find and fill the username field
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(username)

    # Find and fill the password field
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(password)

    # Find and click the button with the text 'Continue'
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
    login_button.click()

    time.sleep(default_buffer_wait)


def scroll_down(driver):
    # Initial call to execute_script to scroll down
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(1)  # Adjust this depending upon your page's response time

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def main():
    # Load the configuration from the JSON file
    with open('config.json', 'r') as file:
        config = json.load(file)

    start_date = get_date_input(config['start_date'])
    end_date = get_date_input(config['end_date'])
    page_load_wait_time = config['page_load_wait_time']
    max_pts_limit = config['max_points_limit']
    delta_max_pts_limit = config['delta_max_points_limit']
    departureCity = config['departureCity']
    departureIata = config['departureIata']
    arrivalCity = config['arrivalCity']
    arrivalIata = config['arrivalIata']

    # Load the other details from JSON file
    with open('auth.json', 'r') as file:
        auth = json.load(file)

    username = auth['username']
    password = auth['password']
    url = auth['url']

    dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
    results_filename = "results\\" + str(start_date.strftime('%Y-%m-%d')) + "__" + str(
        end_date.strftime('%Y-%m-%d')) + ".txt"
    urls = [(
                        url + f"/results?departureCity={departureCity}&departureIata={departureIata}&arrivalCity={arrivalCity}&arrivalIata"
                              f"={arrivalIata}&legType=oneWay&classOfService=economy&passengers=1&pid=&depar"
                              f"tureDate={date.strftime('%Y-%m-%d')}&arrivalDate=2024-07-29") for date in dates]

    # Initialize the driver
    driver = webdriver.Chrome()
    driver.set_window_size(1280, 800)  # Set the window size to 1280x800
    driver.get(url)

    time.sleep(default_buffer_wait)

    # Load cookies from the file and add them to the browser
    is_logged_in: bool = False
    try:
        with open('cookies.pkl', 'rb') as file:
            cookies = pickle.load(file)
            is_logged_in = True
            for cookie in cookies:
                driver.add_cookie(cookie)
                driver.refresh()  # Refresh the page to make use of the newly added cookies
    except Exception as e:
        print("Unable to find cookies file. So default to login path", e)

    time.sleep(default_buffer_wait)

    if not is_logged_in:
        explicit_login(driver, username, password)

    # Save cookies to a file after login
    with open('cookies.pkl', 'wb') as file:
        pickle.dump(driver.get_cookies(), file)

    # Open each URL in a new tab with a delay
    first_tab = True
    handles = []  # To store the window handles of the tabs
    for url in urls:
        if first_tab:
            driver.get(url)
            first_tab = False
            # select_sort_order(driver)
        else:
            driver.execute_script(f"window.open('{url}');")
            # select_sort_order(driver)
        time.sleep(default_buffer_wait_tab_load)  # Delay between opening each tab
        handles.append(driver.window_handles[-1])  # Store the handle of the new tab

    time.sleep(page_load_wait_time)

    with open(results_filename, 'w') as f:
        f.write(f"Results\n")

    # Now visit each tab and use BeautifulSoup to parse the page
    for handle in handles:
        driver.switch_to.window(handle)
        scroll_down(driver)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all divs that have a class attribute starting with 'result_'
        results = soup.find_all(
            lambda tag: tag.name == "div" and tag.get("class", "") and tag["class"][0].startswith("result_"))

        airlines = []
        departure_date = soup.find('input', id='departureDate')['value']

        with open(results_filename, 'a') as f:
            f.write(f"{departure_date}\n")
            f.write(f"\n\n")

        for result in results:
            # Within each result, find the 'Economy' div
            economy_div = result.find("div", string=class_of_flight)
            if economy_div:
                # Navigating up to b
                b_div = economy_div.find_parent().find_parent().find_parent()

                # Find the sibling div of b and then search for the nested child containing "pts"
                c_div = b_div.find_next_sibling("div")
                points_div = c_div.find_next_sibling("div").find(lambda tag: tag.name == "div" and "pts" in tag.text)

                if points_div:
                    points = points_div.get_text(strip=True)
                else:
                    points = "Points not found"

                # Find the preceding sibling that should contain the airline name
                airline_div = economy_div.find_previous_sibling("div")
                time_div = airline_div.find_parent().find_previous_sibling("div")
                time_span = time_div.find("span")
                time_value = time_span.text
                airline = airline_div.get_text(strip=True)
                pts_value, points_dollar_value = extract_points(points, airline)
                if airline_div and pts_value != -1:
                    if airline == "Delta" and pts_value <= delta_max_pts_limit:
                        value = f"{airline} : {time_value} : {pts_value * 0.85}"
                        print(f"{value}\n")
                        airlines.append(value)
                    elif pts_value <= max_pts_limit:
                        value = f"{airline} : {time_value} : {points_dollar_value}"
                        print(f"{value}\n")
                        airlines.append(value)

        # Saving the airline names into a file
        with open(results_filename, 'a') as f:
            for airline in airlines:
                f.write(f"{airline}\n")
            f.write(f"\n\n")


main()
