import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import logging
import json
import time
import random
import pandas as pd
from selenium.webdriver.common.by import By
from datetime import datetime
import requests
import os
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("logs/penha_de_franca_log.log"),  # Log to this file
                        logging.StreamHandler()  # And also log to console
                    ])


# Record start time
start_time = time.time()


options = uc.ChromeOptions()
driver = uc.Chrome(options=options)


def extract_tag_from_url(url):
    parts = url.split('/')
    try:
        return parts[5].replace('-', ' ')  # Replaces '-' with space in the tag
    except IndexError:
        return "default_tag"


def load_existing_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_data_to_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        
        logging.info(f"Data successfully saved to {file_path}.")
        
    #df = pd.DataFrame(data)
    #excel_file_path = file_path.replace('.json', '.xlsx')
    #df.to_excel(excel_file_path, index=False)

    
def extract_listings(html_content, tag):
    soup = BeautifulSoup(html_content, 'html.parser')
    listings = soup.find_all('article', class_='item')
    extracted_data = []

    for listing in listings:
        data = {'região': tag}

        title_tag = listing.find('a', class_='item-link')
        price_tag = listing.find('span', class_='item-price')
        details_tags = listing.find_all('span', class_='item-detail')
        description_tag = listing.find('div', class_='item-description')
        advertiser_tag = listing.find('picture', class_='logo-branding')

        if title_tag:
            data['title'] = title_tag.get_text(strip=True)
            data['link'] = 'https://www.idealista.pt' + title_tag.get('href')
        if price_tag:
            data['price'] = price_tag.get_text(strip=True)
        if details_tags:
            data['details'] = ' | '.join(tag.get_text(strip=True) for tag in details_tags)
        if description_tag:
            data['description'] = description_tag.get_text(strip=True)
        if advertiser_tag:
            advertiser_a_tag = advertiser_tag.find('a')
            if advertiser_a_tag and 'title' in advertiser_a_tag.attrs:
                data['advertiser'] = advertiser_a_tag['title']

        extracted_data.append(data)

    logging.info(f"Extracted {len(extracted_data)} listings from a page.")
    return extracted_data


def scrape_all_urls(driver, url, existing_data):
    global all_scraped_urls
    logging.info(f"All Scraped URls {all_scraped_urls}.")
    

    existing_urls = {item['link'] for item in existing_data}  # URLs from existing data
    logging.info(f"Existing_urls {existing_urls}.")
    new_urls = set()  # New URLs found in the current run

    tag = extract_tag_from_url(url)
    sleep_duration = random.uniform(5, 9)
    logging.info(f"Sleeping 1 for {sleep_duration:.2f} seconds.")
    time.sleep(sleep_duration)

    try:
        logging.info(f"Navigating to URL: {url}")
        if driver.current_url != url:
            driver.get(url)
        driver.implicitly_wait(4)

        html_content = driver.page_source
        new_listings = extract_listings(html_content, tag)

        for new_listing in new_listings:
            all_scraped_urls.add(new_listing['link'])  # Add the URL of the new listing
            logging.info(f"Number of URLs added to scraped list: {len(all_scraped_urls)}")

            if new_listing['link'] in existing_urls:
                logging.info(f"New listing: {new_listing}")
                
                for entry in existing_data:
                        if entry['link'] == new_listing['link']:
                            
                            if entry.get('status') == 'new':
                                entry['status'] = 'available'
                                logging.info(f"New listing before is still available: {entry['link']}")
                                
                            # If previously marked as 'rented' but found again, update status and optionally handle 'rented on'
                            if entry.get('status') == 'rented':
                                logging.info(f"Listing previously marked as rented is now available: {entry['link']}")
                                entry['status'] = 'available'
                                entry.pop('rented on', None)

                            # Check for and handle a price change
                            if 'price' in entry and entry['price'] != new_listing['price']:
                                entry['original price'] = entry.get('price', new_listing['price'])  # Preserve the original price if available
                                entry['price'] = new_listing['price']  # Update to the new price
                                entry['date of price update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                                logging.info(f"Price updated for {entry['link']} from {entry['original price']} to {new_listing['price']} on {entry['date of price update']}")

                            # Update other details as needed, excluding specific fields to avoid overwriting important info
                            entry.update({k: new_listing[k] for k in new_listing if k not in ['added_on', 'price', 'original price']})
                            break
                    
            else:
                
                # Logic for a completely new listing
                new_listing['status'] = 'new'
                new_listing['added_on'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                existing_data.append(new_listing)
                new_urls.add(new_listing['link'])
                
                
        logging.info(f"New listing added: {new_listing['link']} with price {new_listing['price']}")
        logging.info(f"Price updated for {entry['link']} from {entry['original price']} to {new_listing['price']} on {entry['date of price update']}")
        
        logging.info(f"New URLs found in this run: {len(new_urls)}")
        logging.info(f"Existing data: {(existing_urls)}")
    
        

    except Exception as e:
        logging.error(f"An error occurred while processing {url}: {e}")
    finally:
        
        print("Processing complete.")
       
    save_data_to_file(existing_data, file_path)
    logging.info(f"Processed and saved data from page {url}.")
    # After processing one URL, the rest of your code can remain to handle the data as intended
        
    sleep_duration = random.uniform(5, 9)
    logging.info(f"Sleeping 2 for {sleep_duration:.2f} seconds.")
    time.sleep(sleep_duration)
    

def go_next_page(driver):
    try:
        next_page_link = driver.find_element(By.CSS_SELECTOR, 'li.next a.icon-arrow-right-after')
        if next_page_link:
            next_page_url = next_page_link.get_attribute('href')
            logging.info(f"Next page URL: {next_page_url}")
            return next_page_url
        else:
            logging.info("No more pages to scrape for this URL.")
            return None
    except Exception as e:
        logging.error(f"Reached the end or faced an error while trying to navigate to the next page: {e}")
        return None
    
    
def update_listings_to_rented(existing_data, file_path):
    global all_scraped_urls
    logging.info(f"Number of Scraped URLs: {len(all_scraped_urls)}")
    existing_urls = {item['link'] for item in existing_data}
    
    # Listings not found in the current scrape are considered rented
    rented_urls = existing_urls - all_scraped_urls
    
    logging.info(f"Rented URLs: {rented_urls}")

    for entry in existing_data:
        if entry['link'] in rented_urls and entry.get('status') != 'rented':
            entry['status'] = 'rented'
            entry['rented on'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            logging.info(f"Marked as rented: {entry['link']} on {entry['rented on']}")
            
            save_data_to_file(existing_data, file_path)  # Save the updated data once after all updates
    

def main_scraping_process(driver, base_urls, file_path):
    global all_scraped_urls
    all_scraped_urls = set()  # Initialize as a set

    existing_data = load_existing_data(file_path)  # Load data once at the start

    for base_url in base_urls:
        url = base_url
        while url:
            scrape_all_urls(driver, url, existing_data)  # Pass existing_data directly
            url = go_next_page(driver)

        # Pass both existing_data and file_path to update_listings_to_rented
        update_listings_to_rented(existing_data, file_path)  # Corrected argument list

    save_data_to_file(existing_data, file_path)  # Save the updated data once after all updates

    driver.quit()
    logging.info("Scraping process completed and WebDriver closed.")

        
if __name__ == "__main__":
    base_url = ["https://www.idealista.pt/arrendar-casas/penha-de-franca/alto-de-sao-joao-alto-do-varejao/?ordem=atualizado-desc",
                "https://www.idealista.pt/arrendar-casas/penha-de-franca/bairro-dos-actores-barao-sabrosa/?ordem=atualizado-desc",
                "https://www.idealista.pt/arrendar-casas/penha-de-franca/centro/?ordem=atualizado-desc",
                "https://www.idealista.pt/arrendar-casas/penha-de-franca/santa-apolonia-cruz-da-pedra/?ordem=atualizado-desc"
                ]
                

    file_path = "data/json/penha_de_franca_regions.json"
    main_scraping_process(driver, base_url, file_path)

# Record end time
end_time = time.time()

# Calculate total execution time
execution_time_seconds = end_time - start_time

# Convert execution time to minutes and seconds
minutes = int(execution_time_seconds // 60)
seconds = execution_time_seconds % 60

# Log the execution time
logging.info(f'Total execution time: {minutes} minutes and {seconds:.2f} seconds')