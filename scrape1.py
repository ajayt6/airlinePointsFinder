from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time


def main():
    username = 'yojathoma+2@gmail.com'
    password = '12345687Qwe'
    class_of_flight = 'economy'
    departure_date = "2024-06-07"
    search_url = (("https://www.point.me/results?departureCity=Seattle&departureIata=SEA&arrivalCity=Charlotte"
                  "&arrivalIata=CLT&legType=oneWay&classOfService=economy&passengers=1&pid=&departureDate=") +
                  departure_date + "&arrivalDate=2024-07-29")

    # Initialize the driver
    driver = webdriver.Chrome()
    driver.get('https://www.point.me')

    time.sleep(2)

    signup_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign up')]")
    signup_button.click()

    time.sleep(3)

    login_link = driver.find_element(By.XPATH, "//a[text()='Log in']")
    login_link.click()

    time.sleep(3)

    # Find and fill the username field
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(username)

    # Find and fill the password field
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(password)

    # Find and click the button with the text 'Continue'
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
    login_button.click()

    time.sleep(5)

    driver.get(search_url)

    #search_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Search')]")
    #search_button.click()

    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    print(soup.prettify())

    # Switch to tab
    # driver.switch_to.window(driver.window_handles[0])

    # Assuming `driver.page_source` contains the HTML source
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # print(soup.prettify())
    with open('temp.txt', 'w') as f:
        f.write(f"{soup}\n")

    results = []

    # Find all divs that have a class attribute starting with 'result_'
    results = soup.find_all(
        lambda tag: tag.name == "div" and tag.get("class", "") and tag["class"][0].startswith("result_"))

    with open('results.txt', 'w') as f:
        f.write(f"{results}\n")

    airlines = []

    for result in results:
        # Within each result, find the 'Economy' div
        economy_div = result.find("div", string=class_of_flight)
        if economy_div:
            # Navigating up to b
            b_div = economy_div.find_parent().find_parent().find_parent()

            print("\n")
            print(b_div)
            print("\n")

            # Find the sibling div of b and then search for the nested child containing "pts"
            c_div = b_div.find_next_sibling("div")
            points_div = c_div.find_next_sibling("div").find(lambda tag: tag.name == "div" and "pts" in tag.text)

            print("\n")
            print(c_div.find_next_sibling("div"))
            print("\n")

            if points_div:
                points = points_div.get_text(strip=True)
            else:
                points = "Points not found"

            # Find the preceding sibling that should contain the airline name
            airline_div = economy_div.find_previous_sibling("div")
            if airline_div:
                airline = airline_div.get_text(strip=True)
                # airlines.append(airline_div.text.strip())
                airlines.append(f"{airline}: {points}")

    # Saving the airline names into a file
    with open('airlines.txt', 'w') as f:
        for airline in airlines:
            f.write(f"{airline}\n")

main()