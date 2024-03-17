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
                        logging.FileHandler("avenidas_novas_gulbenkian_praca_espanha.log"),  # Log to this file
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
        
    df = pd.DataFrame(data)
    excel_file_path = file_path.replace('.json', '.xlsx')
    df.to_excel(excel_file_path, index=False)
    
def go_next_page(driver):
    try:
        next_page_link = driver.find_element(By.CSS_SELECTOR, 'li.next a.icon-arrow-right-after')
        if next_page_link:
            next_page_url = next_page_link.get_attribute('href')
            logging.info(f"Navigating to next page URL: {next_page_url}")
            driver.get(next_page_url)
            time.sleep(random.uniform(12, 25))  # Mimic human browsing behavior
            logging.info("Successfully navigated to the next page.")
            return True
        else:
            logging.info("No more pages to scrape for this URL.")
            return False
    except Exception as e:
        logging.error(f"Reached the end or faced an error while trying to navigate to the next page: {e}")
        return False
    
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


def scrape_all_urls(url, file_path):
    global all_scraped_urls
    existing_data = load_existing_data(file_path)
    existing_urls = {item['link'] for item in existing_data}  # URLs from existing data
    new_urls = set()  # New URLs found in the current run

    tag = extract_tag_from_url(url)
    time.sleep(random.uniform(10, 15))

    try:
        logging.info(f"Navigating to URL: {url}")
        driver.get(url)
        driver.implicitly_wait(15)
        sleep_duration = random.uniform(10, 17)
        logging.info(f"Sleeping 1 for {sleep_duration:.2f} seconds.")
        time.sleep(sleep_duration)

        html_content = driver.page_source
        new_listings = extract_listings(html_content, tag)
        logging.info(f"Listing previously marked as rented is now available: {new_listings}")

        for new_listing in new_listings:
            all_scraped_urls.add(new_listing['link'])  # Global tracking of scraped URLs
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
                            entry.update({k: new_listing[k] for k in new_listing if k not in ['região', 'added_on', 'price', 'original price']})
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
        # This could be a point to wait for further instruction if integrated into a larger application
        # For example, a simple input() here could pause the script waiting for the user to press Enter
        print("Processing complete.")
        # input("Press Enter to continue...") # Uncomment this line if you wish to manually pause execution here

    save_data_to_file(existing_data, file_path)
    logging.info(f"Processed page of {url}.")
    # After processing one URL, the rest of your code can remain to handle the data as intended
        
    time.sleep(5)



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
   
    if skip_image_download_counter ['counter'] >= 50:
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
        images_dir = os.path.join(os.getcwd(), "avenidas_novas_gulbenkian_praca_espanha")
    
        # Scrape images for this listing if allowed
        if image_scrape_allowed:
            image_scrape_result = scrape_listing_images_within_page(driver, listing, images_dir, listing_id, skip_image_download_counter)
            if not image_scrape_result:
                image_scrape_allowed = False  # Stop trying to download images for subsequent listings
        
    sleep_duration = random.uniform(7, 15)
    logging.info(f"Sleeping 3 for {sleep_duration:.2f} seconds.")
    time.sleep(sleep_duration)
        
def update_listings_to_rented(existing_data, file_path):
    global all_scraped_urls
    logging.info(f"Number of Scraped URLS: {len(all_scraped_urls)}")
    
    # Ensure this is the same set populated during scraping
    listings_marked_rented = 0  # Counter for listings marked as rented

    for listing in existing_data:
        if listing['link'] not in all_scraped_urls and listing.get('status') != 'rented':
            logging.info(f"{listing['link']} COMPARE {all_scraped_urls}")
            
            listing['status'] = 'rented'
            listing['rented on'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            listings_marked_rented += 1
            logging.info(f"Marked as rented: {listing['link']} on {listing['rented on']}")

    if listings_marked_rented > 0:
        save_data_to_file(existing_data, file_path)
        logging.info(f"Total listings marked as rented in this session: {listings_marked_rented}")

def main_scraping_process(driver, base_url, file_path):
    global all_scraped_urls 
    existing_data = load_existing_data(file_path)  # Load data at the beginning of the run
    try:
        # Assuming `scrape_all_urls` and `scrape_all_listings_on_page` are your main scraping functions.
        scrape_all_urls(base_url, file_path)
        scrape_all_listings_on_page(driver, base_url)
        
        # Loop to navigate through all pages
        while go_next_page(driver):
            scrape_all_urls(driver.current_url, file_path)
            scrape_all_listings_on_page(driver, driver.current_url)
        

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        update_listings_to_rented(existing_data, file_path)  # Update status after all scraping is done
        driver.quit()
        logging.info("Scraping process completed and WebDriver closed.")

if __name__ == "__main__":
    base_url = "https://www.idealista.pt/arrendar-casas/avenidas-novas/gulbenkian-praca-espanha/?ordem=atualizado-desc"
    file_path = "gulbenkian_praca_espanha.json"
    main_scraping_process(driver, base_url, file_path)
    
