from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
from pathlib import Path
from webdriver_manager.chrome import ChromeDriverManager

# ##############################################################################
# ############## تنظیمات اسکریپت ##############################################
# ##############################################################################

# ------ تغییر جدید برای ذخیره در دسکتاپ ------
try:
    # پیدا کردن مسیر دسکتاپ کاربر به صورت خودکار و مستقل از سیستم‌عامل
    desktop_path = Path.home() / "Desktop"
    OUTPUT_FILE_NAME = "instagram_post_links.txt"
    OUTPUT_FILE = desktop_path / OUTPUT_FILE_NAME
    # اطمینان از اینکه پوشه دسکتاپ وجود دارد (معمولاً وجود دارد، اما این کار برای اطمینان است)
    desktop_path.mkdir(exist_ok=True)
except Exception as e_path:
    print(f"خطا در یافتن مسیر دسکتاپ: {e_path}")
    print("فایل خروجی در کنار اسکریپت/فایل اجرایی ذخیره خواهد شد.")
    # اگر به هر دلیلی مسیر دسکتاپ پیدا نشد، در کنار اسکریپت ذخیره کن
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_FILE_NAME = "instagram_post_links.txt"
    OUTPUT_FILE = os.path.join(SCRIPT_DIR, OUTPUT_FILE_NAME)

# ------------------------------------------------

WAIT_TIMEOUT = 15
SCROLL_PAUSE_TIME = 6
MAX_SCROLLS = None

USER_PROVIDED_POSTS_CONTAINER_XPATH = "//main//div[contains(@style,'flex-direction: column;')]"


# ##############################################################################
# ######################## پایان بخش تنظیمات #################################
# ##############################################################################

def get_links_via_javascript(driver, container_element):
    script = """
    let links = [];
    if (!arguments[0]) return links; 
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


def get_post_links_from_profile(profile_url, output_file_path, wait_timeout_general, scroll_pause_time, max_scrolls):
    print(f"شروع فرآیند برای صفحه: {profile_url}")
    print(f"استفاده از XPATH کانتینر پست‌ها: {USER_PROVIDED_POSTS_CONTAINER_XPATH}")
    print(f"لینک‌ها در فایل زیر ذخیره خواهند شد: {output_file_path}")

    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu");
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--lang=fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = None
    try:
        print("در حال راه‌اندازی و نصب خودکار ChromeDriver در صورت نیاز...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("ChromeDriver با موفقیت راه‌اندازی شد.")
    except Exception as e:
        print(f"خطا در راه‌اندازی ChromeDriver با webdriver_manager: {e}")
        print("لطفا از اتصال به اینترنت و عدم مسدود بودن دانلودها توسط آنتی‌ویروس اطمینان حاصل کنید.")
        return

    post_links_found = set()
    scroll_attempts = 0

    try:
        driver.get(profile_url)
        print("صفحه باز شد. تلاش برای مدیریت پاپ‌آپ‌ها و بارگذاری اولیه...")
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
                f"تلاش برای یافتن کانتینر پست‌ها با XPATH: {USER_PROVIDED_POSTS_CONTAINER_XPATH} (قبل از دخالت دستی)...")
            posts_container_element = WebDriverWait(driver, wait_timeout_general).until(
                EC.presence_of_element_located((By.XPATH, USER_PROVIDED_POSTS_CONTAINER_XPATH))
            )
            print("کانتینر پست‌ها در بارگذاری اولیه پیدا شد.")
            hrefs_from_js_initial = get_links_via_javascript(driver, posts_container_element)
            for href in hrefs_from_js_initial:
                if href and ("/p/" in href or "/reel/" in href):
                    full_link = href if href.startswith(
                        "https://www.instagram.com") else f"https://www.instagram.com{href if href.startswith('/') else '/' + href}"
                    if full_link not in post_links_found: post_links_found.add(full_link)
            if post_links_found: print(
                f"{len(post_links_found)} لینک معتبر اولیه از داخل کانتینر (با JS و فیلتر جدید) اضافه شد.")
        except TimeoutException:
            print(f"هشدار: کانتینر پست‌ها با XPATH مشخص شده در بارگذاری اولیه صفحه پیدا نشد.")

        if not post_links_found:
            print("\n!!! توجه: اسکریپت متوقف شده است. !!!")
            print("لطفا به پنجره مرورگر باز شده نگاه کنید و اقدامات لازم (مانند لاگین) را انجام دهید.")
            input("پس از بررسی دستی و انجام لاگین، Enter را در این کنسول فشار دهید...")
            print("ادامه کار اسکریپت پس از دخالت دستی...")
            print("دادن زمان به صفحه برای بارگذاری کامل پس از لاگین (۳۰ ثانیه)...")

            try:
                print(
                    f"تلاش برای یافتن کانتینر پست‌ها با XPATH: {USER_PROVIDED_POSTS_CONTAINER_XPATH} (پس از دخالت دستی و تاخیر)...")
                posts_container_element = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, USER_PROVIDED_POSTS_CONTAINER_XPATH))
                )
                print("کانتینر پست‌ها پس از دخالت دستی پیدا شد.")

                hrefs_from_js_manual = get_links_via_javascript(driver, posts_container_element)
                # print(f"لینک‌های خام یافت شده توسط JS (پس از دخالت دستی): {hrefs_from_js_manual}")

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
                            f"پس از دخالت دستی، {newly_found_after_manual} لینک جدید معتبر از داخل کانتینر اضافه شد. مجموع فعلی: {len(post_links_found)}")
                    elif post_links_found:
                        print(f"پس از دخالت دستی، لینک جدید معتبری اضافه نشد. مجموع فعلی: {len(post_links_found)}")
                    else:
                        print("هشدار: لینک‌هایی از طریق JS پیدا شدند اما هیچکدام پست معتبر نبودند.")
                else:
                    print("هشدار جدی: هیچ لینک href ای از طریق JS داخل کانتینر پیدا شده یافت نشد.")

            except TimeoutException:
                print(
                    f"خطا: پس از ۳۰ ثانیه انتظار و دخالت دستی، هنوز کانتینر پست‌ها با XPATH ({USER_PROVIDED_POSTS_CONTAINER_XPATH}) پیدا نشد.")
            except Exception as e_after_manual:
                print(f"خطای غیرمنتظره پس از دخالت دستی هنگام جستجوی محتوا: {e_after_manual}")

        print("شروع اسکرول برای بارگذاری تمام پست‌ها...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        consecutive_no_change_scrolls = 0

        if not post_links_found: print("هشدار: هیچ لینکی قبل از شروع اسکرول پیدا نشد.")

        while True:
            if max_scrolls is not None and scroll_attempts >= max_scrolls:
                print(f"به حداکثر تعداد اسکرول ({max_scrolls}) رسیدیم.");
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
                print(f"هشدار: در اسکرول {scroll_attempts}، کانتینر اصلی پست‌ها دیگر پیدا نشد.")
            except Exception as e_scroll_js:
                print(f"خطا در استخراج لینک با JS در حین اسکرول {scroll_attempts}: {e_scroll_js}")

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
                    f"اسکرول {scroll_attempts}: {new_links_added_this_scroll} لینک جدید معتبر اضافه شد. مجموع: {len(post_links_found)}")

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                consecutive_no_change_scrolls += 1
                if consecutive_no_change_scrolls >= 3:
                    print("ارتفاع صفحه برای چندین بار متوالی تغییر نکرد. به نظر می‌رسد به انتهای صفحه رسیده‌ایم.");
                    break
            else:
                consecutive_no_change_scrolls = 0
            last_height = new_height

        print(f"\nمجموعا {len(post_links_found)} لینک پست منحصر به فرد پیدا شد.")

        if post_links_found:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                for link in sorted(list(post_links_found)): f.write(link + "\n")
            print(f"لینک‌ها با موفقیت در فایل '{output_file_path}' ذخیره شدند.")
        else:
            print("هیچ لینک پستی در نهایت پیدا نشد.")

    except Exception as e:
        print(f"خطایی در حین اجرا رخ داد: {e}");
        import traceback;
        traceback.print_exc()
    finally:
        if driver is not None: print("بستن مرورگر..."); driver.quit()
        print("فرآیند تمام شد.")


if __name__ == "__main__":
    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        print("کتابخانه webdriver-manager یافت نشد. در حال تلاش برای نصب...")
        try:
            import subprocess;
            import sys

            subprocess.check_call([sys.executable, "-m", "pip", "install", "webdriver-manager"])
            from webdriver_manager.chrome import ChromeDriverManager

            print("webdriver-manager با موفقیت نصب شد.")
        except Exception as e_install:
            print(f"خطا در نصب خودکار webdriver-manager: {e_install}");
            exit()

    profile_url_input = input(
        "لطفا آدرس کامل صفحه اینستاگرام را وارد کنید (مثال: https://www.instagram.com/username/): ")

    if not profile_url_input or not profile_url_input.startswith("https://www.instagram.com/"):
        print("خطا: آدرس وارد شده معتبر به نظر نمی‌رسد. لطفا آدرس کامل را وارد کنید.")
    else:
        get_post_links_from_profile(
            profile_url_input,
            OUTPUT_FILE,
            WAIT_TIMEOUT,
            SCROLL_PAUSE_TIME,
            MAX_SCROLLS
        )

    print("\nاجرای اسکریپت به پایان رسید.")
    input("برای بستن این پنجره، کلیدی را فشار دهید...")
