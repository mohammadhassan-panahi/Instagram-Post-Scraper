from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os

# ##############################################################################
# ############## تنظیمات اسکریپت - این بخش را ویرایش کنید #################
# ##############################################################################
# INSTAGRAM_PROFILE_URL = "https://www.instagram.com/mehrad.ux/" # این خط حذف یا کامنت می شود
OUTPUT_FILE = r"D:\project\downloaders\insta_accunt_Scraper\instagram_post_links.txt"
# اگر می‌خواهید فایل در همان پوشه اسکریپت ذخیره شود، این خط را جایگزین کنید:
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_FILE = os.path.join(SCRIPT_DIR, "instagram_post_links.txt")


# مسیر کامل فایل اجرایی ChromeDriver
CHROME_DRIVER_PATH = r"D:\project\downloaders\insta_accunt_Scraper\chromedriver-win64\chromedriver.exe"
# مثال برای مک/لینوکس: CHROME_DRIVER_PATH = "/usr/local/bin/chromedriver"
# اگر ChromeDriver در PATH سیستم شما قرار دارد، می‌توانید این مقدار را خالی بگذارید یا از `webdriver.Chrome()` بدون `service` استفاده کنید.
# CHROME_DRIVER_PATH = r"مسیر کامل فایل chromedriver را اینجا وارد کنید"
#CHROME_DRIVER_PATH = "" # اگر در PATH است، خالی بگذارید. در غیر این صورت مسیر کامل را بدهید.

# مدت زمان انتظار (به ثانیه) برای بارگذاری عناصر صفحه
# این مقدار را در صورت نیاز و بر اساس سرعت اینترنت خود تنظیم کنید
WAIT_TIMEOUT = 15
SCROLL_PAUSE_TIME = 8  # زمان بین اسکرول ها، می توانید کمی بیشتر کنید اگر لینک ها جا می مانند
MAX_SCROLLS = None

# XPATH ارائه شده توسط کاربر برای کانتینر اصلی پست‌ها
USER_PROVIDED_POSTS_CONTAINER_XPATH = "//main//div[contains(@style,'flex-direction: column;')]"


# ##############################################################################
# ######################## پایان بخش تنظیمات #################################
# ##############################################################################

def get_links_via_javascript(driver, container_element):
    script = """
    let links = [];
    if (!arguments[0]) return links; // اگر کانتینر وجود نداشت
    let all_a_tags = arguments[0].getElementsByTagName('a');
    for (let i = 0; i < all_a_tags.length; i++) {
        if (all_a_tags[i].hasAttribute('href')) {
            links.push(all_a_tags[i].getAttribute('href'));
        }
    }
    return links;
    """
    try:
        hrefs = driver.execute_script(script, container_element)
        return hrefs if hrefs else []
    except Exception as e:
        print(f"خطا در اجرای جاوا اسکریپت برای استخراج لینک‌ها: {e}")
        return []


def get_post_links_from_profile(profile_url, output_file, driver_path, wait_timeout_general, scroll_pause_time,
                                max_scrolls):
    print(f"Starting process for page: {profile_url}")
    print(f"Using posts container XPATH: {USER_PROVIDED_POSTS_CONTAINER_XPATH}")

    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu");
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--lang=fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")

    driver = None  # تعریف اولیه
    try:
        if driver_path and os.path.exists(driver_path):
            service = ChromeService(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            print("ChromeDriver path not specified or invalid. Trying to use ChromeDriver from PATH.")
            driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Error initializing ChromeDriver: {e}");
        return

    post_links_found = set()
    scroll_attempts = 0

    try:
        driver.get(profile_url)
        print("Page opened. Attempting to manage pop-ups and initial load...")
        time.sleep(7)

        possible_popups_selectors = {
            "Decline Cookies": "//button[text()='Decline optional cookies']",
            "Accept All Cookies": "//button[text()='Accept All']",
            "Allow All Cookies": "//button[text()='Allow all cookies']", "Accept Cookies": "//button[text()='Accept']",
            "Not Now (Notifications/Login)": "//button[text()='Not Now']",
            "General Accept Dialog": "//div[@role='dialog']//button[contains(., 'Accept') or contains(., 'Allow')]",
            "General Decline/Close Dialog": "//div[@role='dialog']//button[contains(., 'Decline') or contains(., 'Close') or contains(@aria-label,'Close') or contains(@aria-label,'Dismiss')]"
        }
        for _, selector in possible_popups_selectors.items():
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, selector))).click(); time.sleep(3)
            except:
                pass
        time.sleep(2)

        posts_container_element = None
        try:
            print(
                f"Attempting to find posts container with XPATH: {USER_PROVIDED_POSTS_CONTAINER_XPATH} (before manual intervention)...")
            posts_container_element = WebDriverWait(driver, wait_timeout_general).until(
                EC.presence_of_element_located((By.XPATH, USER_PROVIDED_POSTS_CONTAINER_XPATH))
            )
            print("Posts container found on initial load.")
            hrefs_from_js_initial = get_links_via_javascript(driver, posts_container_element)
            print(f"Raw links found by JS (initial load): {hrefs_from_js_initial}")
            for href in hrefs_from_js_initial:
                if href and ("/p/" in href or "/reel/" in href):
                    full_link = href if href.startswith(
                        "https://www.instagram.com") else f"https://www.instagram.com{href if href.startswith('/') else '/' + href}"
                    if full_link not in post_links_found: post_links_found.add(full_link)
            if post_links_found: print(
                f"{len(post_links_found)} valid initial links added from container (with JS and new filter).")
        except TimeoutException:
            print(f"Warning: Posts container with specified XPATH not found on initial page load.")

        if not post_links_found:
            print("\n!!! ATTENTION: Script paused. !!!")
            print("Please look at the opened browser window and take necessary actions (e.g., login).")
            input("After manual review, press Enter to continue scrolling...")
            print("Resuming script after manual intervention...")
            print("Allowing time for page to fully load after login (30 seconds)...")

            try:
                print(
                    f"Attempting to find posts container with XPATH: {USER_PROVIDED_POSTS_CONTAINER_XPATH} (after manual intervention and delay)...")
                posts_container_element = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, USER_PROVIDED_POSTS_CONTAINER_XPATH))
                )
                print("Posts container found after manual intervention.")

                hrefs_from_js_manual = get_links_via_javascript(driver, posts_container_element)
                print(f"Raw links found by JS (after manual intervention): {hrefs_from_js_manual}")

                newly_found_after_manual = 0
                if hrefs_from_js_manual:
                    for href in hrefs_from_js_manual:
                        if href and ("/p/" in href or "/reel/" in href):
                            full_link = href if href.startswith(
                                "https://www.instagram.com") else f"https://www.instagram.com{href if href.startswith('/') else '/' + href}"
                            if full_link not in post_links_found:
                                post_links_found.add(full_link)
                                newly_found_after_manual += 1

                    if newly_found_after_manual > 0:
                        print(
                            f"After manual intervention, {newly_found_after_manual} new valid links (with JS and new filter) added from container. Current total: {len(post_links_found)}")
                    elif post_links_found:
                        print(
                            f"After manual intervention, no new valid links added. Current total: {len(post_links_found)}")
                    else:
                        print("Warning: Links were found via JS, but none were valid posts (with new filter).")
                else:
                    print("Serious warning: No href links found via JS within the identified container.")
                    if posts_container_element:
                        try:
                            print("-" * 50); print(posts_container_element.get_attribute('innerHTML')[:2000]); print(
                                "-" * 50)
                        except:
                            pass

            except TimeoutException:
                print(
                    f"Error: After 30 seconds wait and manual intervention, posts container with XPATH ({USER_PROVIDED_POSTS_CONTAINER_XPATH}) still not found.")
                try:
                    print("-" * 50); print(driver.page_source[:2000]); print("-" * 50)
                except:
                    pass
            except Exception as e_after_manual:
                print(f"Unexpected error after manual intervention while searching for content: {e_after_manual}")

        print("Starting to scroll to load all posts...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        consecutive_no_change_scrolls = 0

        if not post_links_found: print("Warning: No links found before starting scroll.")

        while True:
            if max_scrolls is not None and scroll_attempts >= max_scrolls:
                print(f"Reached maximum number of scrolls ({max_scrolls}).");
                break

            current_posts_container_in_scroll = None
            hrefs_in_scroll = []
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                scroll_attempts += 1
                time.sleep(scroll_pause_time)

                current_posts_container_in_scroll = driver.find_element(By.XPATH, USER_PROVIDED_POSTS_CONTAINER_XPATH)
                hrefs_in_scroll = get_links_via_javascript(driver, current_posts_container_in_scroll)
            except NoSuchElementException:
                print(f"Warning: On scroll {scroll_attempts}, the main posts container was no longer found.")
            except Exception as e_scroll_js:
                print(f"Error extracting links with JS during scroll {scroll_attempts}: {e_scroll_js}")

            new_links_added_this_scroll = 0
            for href in hrefs_in_scroll:
                if href and ("/p/" in href or "/reel/" in href):
                    full_link = href if href.startswith(
                        "https://www.instagram.com") else f"https://www.instagram.com{href if href.startswith('/') else '/' + href}"
                    if full_link not in post_links_found:
                        post_links_found.add(full_link)
                        new_links_added_this_scroll += 1

            if new_links_added_this_scroll > 0:
                print(
                    f"Scroll {scroll_attempts}: {new_links_added_this_scroll} new valid links (with JS and new filter) added. Total: {len(post_links_found)}")

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                consecutive_no_change_scrolls += 1
                if consecutive_no_change_scrolls >= 3:
                    print(
                        "Page height has not changed for several consecutive scrolls. Assuming end of page has been reached.");
                    break
            else:
                consecutive_no_change_scrolls = 0
            last_height = new_height

        print(f"\nFound a total of {len(post_links_found)} unique post links.")

        if post_links_found:
            with open(output_file, 'w', encoding='utf-8') as f:
                for link in sorted(list(post_links_found)): f.write(link + "\n")
            print(f"Links successfully saved to file: '{output_file}'")
        else:
            print("No post links were ultimately found.")

    except Exception as e:
        print(f"An error occurred during execution: {e}");
        import traceback;
        traceback.print_exc()
    finally:
        if driver is not None: print("Closing browser..."); driver.quit()
        print("Process finished.")


if __name__ == "__main__":
    # دریافت آدرس صفحه اینستاگرام از کاربر
    profile_url_input = input(
        "لطفا آدرس کامل صفحه اینستاگرام را وارد کنید (مثال: https://www.instagram.com/username/): ")

    if not profile_url_input or not profile_url_input.startswith("https://www.instagram.com/"):
        print("خطا: آدرس وارد شده معتبر به نظر نمی‌رسد. لطفا آدرس کامل را وارد کنید.")
    else:
        get_post_links_from_profile(
            profile_url_input,  # استفاده از ورودی کاربر
            OUTPUT_FILE,
            CHROME_DRIVER_PATH,
            WAIT_TIMEOUT,
            SCROLL_PAUSE_TIME,
            MAX_SCROLLS
        )
