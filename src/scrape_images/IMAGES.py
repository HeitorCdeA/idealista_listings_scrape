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
                        logging.FileHandler("alvalade_images_log.log"),  # Log to this file
                        logging.StreamHandler()  # And also log to console
                    ])


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


options = uc.ChromeOptions()
driver = uc.Chrome(options=options)

# Global Set for All Scraped URLs in Current Run
all_scraped_urls = set()


def extract_tag_from_url(url):
    parts = url.split('/')
    try:
        return parts[5].replace('-', ' ')  # Replaces '-' with space in the tag
    except IndexError:
        return "default_tag"

    
def go_next_page(driver):
    try:
        next_page_link = driver.find_element(By.CSS_SELECTOR, 'li.next a.icon-arrow-right-after')
        if next_page_link:
            next_page_url = next_page_link.get_attribute('href')
            logging.info(f"Navigating to next page URL: {next_page_url}")
            return str(next_page_url)  # Convert URL to string explicitly
        else:
            logging.info("No more pages to scrape for this URL.")
            return None
    except Exception as e:
        logging.error(f"Reached the end or faced an error while trying to navigate to the next page: {e}")
        return None
    

# Function to download the image
def download_image(image_url, save_path): #Downloads the image from the given URL and saves it to the specified path.
    try:
        response = requests.get(image_url)
        response.raise_for_status()  # Checks for HTTP request errors
        with open(save_path, "wb") as file:
            file.write(response.content)
        logging.info(f"Image downloaded successfully at {save_path}.")
    except requests.RequestException as e:
        logging.error(f"Failed to download the image from {image_url}. Error: {e}")
        
# Global Counter for Skipping Image Downloads
skip_image_download_counter = {'counter': 0}
        
def scrape_listing_images_within_page(driver, listing_element, images_dir, listing_id, skip_image_download_counter): #Downloads images from a listing's carousel found directly within the page.
   
    if skip_image_download_counter ['counter'] >= 100:
        logging.info(f"10 consecutive listings already have all images. Exiting image scraping. Continuing with general info updates.")
        return False # Return False to indicate that the image scraping process should be stopped
    
    # Ensure the directory path is correct
    listing_images_dir = os.path.join(images_dir, listing_id)
    os.makedirs(listing_images_dir, exist_ok=True)
    
    try:
        # Attempt to extract the total number of images for this listing
        multimedia_info = listing_element.find_element(By.CSS_SELECTOR, "div.item-multimedia-pictures")
        total_images = int(multimedia_info.text.split('/')[-1])
        
        # Count the number of image files already present in the directory
        num_existing_images = len([name for name in os.listdir(listing_images_dir) if os.path.isfile(os.path.join(listing_images_dir, name))])
        
        # If the directory already has all images, skip further processing for this listing
        if num_existing_images >= total_images:
            logging.info(f"Directory {listing_id} already has all images. Skipping.")
            skip_image_download_counter ['counter'] += 1 # Increment the counter for each skip
            return True
        
        else:
            logging.info(f"Downloading images for listing {listing_id}...")
            skip_image_download_counter ['counter'] = 0  # Reset the counter if images are found for this listing
            for image_number in range(1, total_images + 3):
                try:
                    # Wait for the image to become visible and then download it
                    WebDriverWait(listing_element, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "figure.item-gallery img")))
                    image_element = listing_element.find_element(By.CSS_SELECTOR, "figure.item-gallery img")
                    current_image_url = image_element.get_attribute('src')
                    image_path = os.path.join(listing_images_dir, f"{listing_id}_{image_number}.jpg")
                    download_image(current_image_url, image_path)
                    
                    # Logic to click the "Next" button and wait for a random delay
                    if image_number < total_images + 2:  # No need to click next on the last image
                        next_button = listing_element.find_element(By.CSS_SELECTOR, "button.image-gallery-right-nav")
                        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(random.uniform(5, 7))  # Adjusted delay to more reasonable range
                        
                except Exception as e:
                    logging.error(f"Error downloading image {image_number} for listing {listing_id}: {e}")
                    break
        return True   # Indicates images were processed successfully
        
    except NoSuchElementException:
        # This exception is thrown if the div.item-multimedia-pictures element is not found, meaning no images are available for the listing
        logging.info(f"No images available for listing {listing_id}. Skipping image download.")
        return True # Indicates the function executed without needing to download images
    
    

def scrape_all_listings_on_page(driver, base_url):
    driver.get(base_url)
    sleep_duration = random.uniform(10, 18)
    logging.info(f"Sleeping 2 for {sleep_duration:.2f} seconds.")
    time.sleep(sleep_duration)
    
    
    # Find all listings on the page
    listings = driver.find_elements(By.CSS_SELECTOR, "article.item.extended-item.item-multimedia-container")
    image_scrape_allowed = True  # Initially allow image scraping
    
    # start_downloading_images = False  # Flag to indicate when to start downloading images
    
    for listing in listings:
        listing_id = listing.get_attribute('data-adid')
        
        # Check if the current directory is the one after which we want to start downloading images
        #if listing_id == '33026279':
        #  start_downloading_images = True
        #    continue  # Move to the next iteration without processing this specific directory
        
        # Only proceed with image scraping if the flag is True
        #if start_downloading_images:
        images_dir = os.path.join(os.getcwd(), "data/images/alvalade_images")
    
        # Scrape images for this listing if allowed
        if image_scrape_allowed:
            try:
                image_scrape_result = scrape_listing_images_within_page(driver, listing, images_dir, listing_id, skip_image_download_counter)
                if not image_scrape_result:
                    image_scrape_allowed = False  # Stop trying to download images for subsequent listings
                    
            except Exception as e:
                logging.error(f"An error occurred while scraping images for listing {listing_id}: {e}")
        
    sleep_duration = random.uniform(7, 15)
    logging.info(f"Sleeping 3 for {sleep_duration:.2f} seconds.")
    time.sleep(sleep_duration)


def main_scraping_process(driver, base_urls):
    for base_url in base_urls:
        url = base_url
        while url:
            scrape_all_listings_on_page(driver, url)
            next_url = go_next_page(driver)
            if next_url and isinstance(next_url, str):  # Check if next_url is a string
                url = next_url
            else:
                break  # Exit the loop if no next page is available or next_url is not a valid string
        

    driver.quit()
    logging.info("Scraping process completed and WebDriver closed.")


if __name__ == "__main__":
    base_urls = ["https://www.idealista.pt/arrendar-casas/alvalade/alvalade/?ordem=atualizado-desc",
                "https://www.idealista.pt/arrendar-casas/alvalade/campo-grande/?ordem=atualizado-desc",
                "https://www.idealista.pt/arrendar-casas/alvalade/sao-joao-de-brito/?ordem=atualizado-desc"
                ]
    main_scraping_process(driver, base_urls)
    