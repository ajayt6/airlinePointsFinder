import time
from datetime import datetime
import pickle
import json
import smtplib
from email.message import EmailMessage
import chardet
import requests
import platform

from bs4 import BeautifulSoup
from dateutil.rrule import rrule, DAILY
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from pyvirtualdisplay import Display

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


def send_email(subject, content):
    # Load the email configuration from the JSON file
    with open('emailConfig.json', 'r') as file:
        email_config = json.load(file)
    # Create the email content
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = email_config['email']
    msg['To'] = email_config['to']
    msg.set_content(content)

    # Gmail SMTP server configuration
    smtp_server = email_config['smtp_server']
    smtp_port = email_config['smtp_port']
    username = email_config['email']
    password = email_config['email_password']

    # Send the email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(username, password)
            server.send_message(msg)
            print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_notification(title, message, token, server):
    url = f'{server}/message?token={token}'
    headers = {'Content-Type': 'application/json'}
    data = {
        'title': title,
        'message': message,
        'priority': 5
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()


def main():
    global display
    if platform.system() != 'Windows':
        display = Display(visible=0, size=(800, 600))
        display.start()
    # Load the configuration from the JSON file
    with open('config.json', 'r') as file:
        config = json.load(file)

    start_date = get_date_input(config['start_date'])
    end_date = get_date_input(config['end_date'])
    page_load_wait_time = config['page_load_wait_time']
    max_pts_limit = config['max_points_limit']
    delta_max_pts_limit = config['delta_max_points_limit']
    departure_city = config['departureCity']
    departure_iata = config['departureIata']
    arrival_city = config['arrivalCity']
    arrival_iata = config['arrivalIata']
    max_duration_hours = config['max_duration_hours']
    is_return = config['return']
    departure_arrival_iata = departure_iata + arrival_iata

    if is_return:
        departure_city, arrival_city = arrival_city, departure_city
        departure_iata, arrival_iata = arrival_iata, departure_iata
        results_filename = "results/return_" + departure_arrival_iata + "_" + str(start_date.strftime('%Y-%m-%d')) + "__" + str(
            end_date.strftime('%Y-%m-%d')) + ".txt"
    else:
        results_filename = "results/" + departure_arrival_iata + "_" + str(start_date.strftime('%Y-%m-%d')) + "__" + str(
            end_date.strftime('%Y-%m-%d')) + ".txt"

    # Load the other details from JSON file
    with open('auth.json', 'r') as file:
        auth = json.load(file)

    username = auth['username']
    password = auth['password']
    url = auth['url']

    dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
    urls = [(
            url + f"/results?departureCity={departure_city}&departureIata={departure_iata}&arrivalCity={arrival_city}&arrivalIata"
                  f"={arrival_iata}&legType=oneWay&classOfService=economy&passengers=1&pid=&depar"
                  f"tureDate={date.strftime('%Y-%m-%d')}&arrivalDate=2024-07-29") for date in dates]

    # Initialize the driver
    options = Options()
    options.headless = True
    options.add_argument("--window-size=1920,1080")  # Optional, set the window size
    options.add_argument("--no-sandbox")  # Bypass OS security model, necessary on some systems
    options.add_argument("--disable-gpu")  # Applicable to windows os only
    options.add_argument("--disable-extensions")  # Disabling extensions
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    driver = webdriver.Chrome(options=options)
    # driver.set_window_size(1280, 800)  # Set the window size to 1280x800
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
                time_value = time_span.text.replace('\xa0', ' ')
                airline = airline_div.get_text(strip=True)
                pts_value, points_dollar_value = extract_points(points, airline)
                duration_full = economy_div.find_next_sibling("div").get_text(strip=True).replace('\xa0', ' ')
                hour_index = duration_full.find("h")
                duration_hours = duration_full[:hour_index]
                if airline_div and pts_value != -1 and int(duration_hours) <= max_duration_hours:
                    if airline == "Delta" and pts_value <= delta_max_pts_limit:
                        value = f"{airline} : {duration_hours} : {time_value} : {pts_value * 0.85}"
                        print(f"{value}\n")
                        airlines.append(value)
                    elif pts_value <= max_pts_limit:
                        value = f"{airline} : {duration_hours} : {time_value} : {points_dollar_value}"
                        print(f"{value}\n")
                        airlines.append(value)

        # Saving the airline names into a file
        with open(results_filename, 'a') as f:
            for airline in airlines:
                f.write(f"{airline}\n")
            f.write(f"\n\n")

    with open(results_filename, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        email_content = raw_data.decode(encoding)
        send_email(results_filename, email_content)
        send_notification(results_filename, email_content, auth['gotify_token'],
                          auth['gotify_server'])

    driver.quit()
    if platform.system() != 'Windows':
        display.stop()


main()
