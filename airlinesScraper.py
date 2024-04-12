import time
from datetime import datetime
import re

from bs4 import BeautifulSoup
from dateutil.rrule import rrule, DAILY
from selenium import webdriver
from selenium.webdriver.common.by import By


def get_date_input(prompt):
    while True:
        date_str = input(prompt)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD format.")


def extract_points(points_str):
    # Find the index of the first occurrence of " pts"
    index = points_str.find(" pts")

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

        print(number)
        return number
    else:
        print("The string ' pts' was not found.")
        return -1


def main():
    start_date = get_date_input("Enter the start date (YYYY-MM-DD): ")
    end_date = get_date_input("Enter the end date (YYYY-MM-DD): ")
    page_load_wait_time = int(input("Enter main page load wait time in seconds: "))
    max_pts_limit = int(input("Enter max points limit: "))
    dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
    username = 'yojathoma+2@gmail.com'
    password = '12345687Qwe'
    class_of_flight = 'economy'
    default_buffer_wait = 2
    # departure_date = "2024-06-07"
    urls = [(f"https://www.point.me/results?departureCity=Seattle&departureIata=SEA&arrivalCity=Charlotte&arrivalIata"
             f"=CLT&legType=oneWay&classOfService=economy&passengers=1&pid=&depar"
             f"tureDate={date.strftime('%Y-%m-%d')}&arrivalDate=2024-07-29") for date in dates]

    # Initialize the driver
    driver = webdriver.Chrome()
    driver.get('https://www.point.me')

    time.sleep(default_buffer_wait)

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

    # Open each URL in a new tab with a delay
    first_tab = True
    handles = []  # To store the window handles of the tabs
    for url in urls:
        if first_tab:
            driver.get(url)
            first_tab = False
        else:
            driver.execute_script(f"window.open('{url}');")
        time.sleep(1)  # Delay between opening each tab
        handles.append(driver.window_handles[-1])  # Store the handle of the new tab

    time.sleep(page_load_wait_time)

    with open('airlines.txt', 'w') as f:
        f.write(f"Results\n")

    # Now visit each tab and use BeautifulSoup to parse the page
    i = -1
    for handle in handles:
        i = i+1
        driver.switch_to.window(handle)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all divs that have a class attribute starting with 'result_'
        results = soup.find_all(
            lambda tag: tag.name == "div" and tag.get("class", "") and tag["class"][0].startswith("result_"))

        with open('results.txt', 'w') as f:
            f.write(f"{results}\n")

        airlines = []

        with open('airlines.txt', 'a') as f:
            f.write(f"{dates[i]}\n")
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
                pts_value = extract_points(points)
                if airline_div and pts_value != -1:
                    airline = airline_div.get_text(strip=True)
                    if pts_value <= max_pts_limit:
                        airlines.append(f"{airline}: {points}")

        # Saving the airline names into a file
        with open('airlines.txt', 'a') as f:
            for airline in airlines:
                f.write(f"{airline}\n")
            f.write(f"\n\n")


main()
