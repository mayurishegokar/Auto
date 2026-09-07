from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import random
import urllib.parse

# --- CONFIGURATION ---
EMAIL = os.getenv("NAUKRI_EMAIL") or "mayurirshegokar@gmail.com"
PASSWORD = os.getenv("NAUKRI_PASSWORD") or "Mayuri@2010"
# Support multiple comma-separated keywords (e.g. "Software Developer, Java Developer, React Developer")
JOB_KEYWORDS = os.getenv("JOB_KEYWORDS") or "Software Developer, Java Developer, React Developer"
KEYWORDS_LIST = [k.strip() for k in JOB_KEYWORDS.split(",") if k.strip()]
if not KEYWORDS_LIST:
    KEYWORDS_LIST = ["Software Developer"]
JOB_LOCATION = os.getenv("JOB_LOCATION", "")          # Leave empty "" for all India or specify e.g. "Pune", "Bangalore"
MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))          # Maximum search pages to process
MAX_JOBS_PER_PAGE = int(os.getenv("MAX_JOBS_PER_PAGE", "20")) # Max jobs to process per page
FILTER_TITLE_KEYWORDS = os.getenv("FILTER_TITLE_KEYWORDS", "True").lower() in ("true", "1", "yes")
MAX_RUN_MINUTES = float(os.getenv("MAX_RUN_MINUTES", "12"))  # Maximum run duration
MAX_RUN_SECONDS = MAX_RUN_MINUTES * 60 - 20                  # 20s buffer for clean shutdown
START_TIME = time.time()

# --- CHROME SETUP ---
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-notifications")
options.add_argument("--disable-popup-blocking")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

if os.getenv("CI") == "true" or os.getenv("HEADLESS", "false").lower() == "true":
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

# Initialize Chrome driver
driver = None
try:
    # Selenium 4 built-in driver manager
    driver = webdriver.Chrome(options=options)
except Exception:
    try:
        # Fallback to webdriver_manager
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception as e:
        print(f"❌ Failed to initialize Chrome WebDriver: {e}")
        raise

driver.set_page_load_timeout(45)

# Remove navigator.webdriver flag
try:
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """
    })
except Exception:
    pass

wait = WebDriverWait(driver, 15)

def dismiss_popups():
    """Dismiss common Naukri popups, chat drawers, and overlays."""
    popup_xpaths = [
        "//div[contains(@class, 'crossIcon')]",
        "//div[contains(@class, 'chat_close')]",
        "//div[contains(@class, 'chatbot_drawer_close')]",
        "//span[contains(@class, 'crossIcon')]",
        "//button[contains(text(), 'Later') or contains(text(), 'Skip') or contains(text(), 'Not now') or contains(text(), 'Cancel')]"
    ]
    for xpath in popup_xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                if elem.is_displayed():
                    driver.execute_script("arguments[0].click();", elem)
                    time.sleep(0.5)
        except Exception:
            pass

def build_search_url(keywords, location, page=1):
    """Builds valid Naukri search URLs for page 1 and subsequent pages."""
    keywords_clean = keywords.strip()
    keywords_slug = keywords_clean.replace(" ", "-")
    encoded_keywords = urllib.parse.quote_plus(keywords_clean)

    if location.strip():
        loc_clean = location.strip()
        loc_slug = loc_clean.replace(" ", "-")
        encoded_loc = urllib.parse.quote_plus(loc_clean)
        if page == 1:
            return f"https://www.naukri.com/{keywords_slug}-jobs-in-{loc_slug}?k={encoded_keywords}&l={encoded_loc}"
        else:
            return f"https://www.naukri.com/{keywords_slug}-jobs-in-{loc_slug}-{page}?k={encoded_keywords}&l={encoded_loc}"
    else:
        if page == 1:
            return f"https://www.naukri.com/{keywords_slug}-jobs?k={encoded_keywords}"
        else:
            return f"https://www.naukri.com/{keywords_slug}-jobs-{page}?k={encoded_keywords}"

try:
    # --- 1. LOGIN ---
    print("🔐 Navigating to Naukri Login...")
    driver.get("https://www.naukri.com/nlogin/login")
    time.sleep(3)

    try:
        email_input = wait.until(EC.presence_of_element_located((
            By.XPATH, "//input[@id='usernameField' or @placeholder='Enter your active Email ID / Username' or contains(@placeholder, 'Email')]"
        )))
        email_input.clear()
        email_input.send_keys(EMAIL)
        time.sleep(1)

        password_input = driver.find_element(
            By.XPATH, "//input[@id='passwordField' or @placeholder='Enter your password' or @type='password']"
        )
        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1)

        login_button = driver.find_element(
            By.XPATH, "//button[@type='submit' or contains(@class, 'loginButton') or contains(text(),'Login')]"
        )
        login_button.click()
        print("⏳ Logging in, waiting for dashboard...")
        time.sleep(6)

        # Wait for redirect away from login
        try:
            WebDriverWait(driver, 8).until(
                lambda d: "nlogin" not in d.current_url or d.find_elements(By.XPATH, "//div[contains(@class, 'user-profile') or contains(@class, 'nI-gNb-drawer') or @title='My Naukri']")
            )
        except Exception:
            pass

    except Exception as e:
        print(f"⚠️ Login interaction encountered issue: {e}")

    # Check login status
    driver.save_screenshot("login_status.png")
    if "nlogin" in driver.current_url:
        print("⚠️ Still on login page. (If running in GitHub Actions, Naukri may have prompted CAPTCHA/OTP).")
    else:
        print("✅ Logged in successfully!")

    dismiss_popups()

    # --- 2. SEARCH & APPLY LOOP ---
    applied_count = 0
    already_applied_count = 0
    skipped_count = 0
    seen_job_links = set()

    print(f"\n🎯 Search Keywords ({len(KEYWORDS_LIST)}): {', '.join(KEYWORDS_LIST)}")

    for kw_idx, current_keyword in enumerate(KEYWORDS_LIST, 1):
        if time.time() - START_TIME >= MAX_RUN_SECONDS:
            print(f"\n⏰ Overall run time limit reached ({int(time.time() - START_TIME)}s elapsed). Stopping gracefully.")
            break

        print(f"\n{'='*55}")
        print(f"🔍 [{kw_idx}/{len(KEYWORDS_LIST)}] Searching for: '{current_keyword}'")
        print(f"{'='*55}")

        page_num = 1
        while page_num <= MAX_PAGES:
            # Check overall runtime limit
            if time.time() - START_TIME >= MAX_RUN_SECONDS:
                print(f"\n⏰ Time limit reached ({int(time.time() - START_TIME)}s elapsed). Stopping gracefully.")
                break

            search_url = build_search_url(current_keyword, JOB_LOCATION, page_num)
            print(f"\n📄 Navigating to Page {page_num} for '{current_keyword}': {search_url}")
            driver.get(search_url)
            time.sleep(4)
            dismiss_popups()

            # Wait for job listings to load
            job_cards = []
            card_xpaths = [
                "//div[contains(@class, 'srp-jobtuple-wrapper')]",
                "//div[contains(@class, 'cust-job-tuple')]",
                "//div[contains(@class, 'jobTuple')]",
                "//article[contains(@class, 'jobTuple')]",
                "//div[@data-job-id]"
            ]
            
            for xpath in card_xpaths:
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    job_cards = driver.find_elements(By.XPATH, xpath)[:MAX_JOBS_PER_PAGE]
                    if job_cards:
                        break
                except Exception:
                    continue

            if not job_cards:
                safe_kw = "".join(c if c.isalnum() else "_" for c in current_keyword)
                driver.save_screenshot(f"search_error_{safe_kw}_page_{page_num}.png")
                print(f"⚠️ No job cards found for '{current_keyword}' on page {page_num}. Moving to next keyword.")
                break

            print(f"📋 Found {len(job_cards)} job listings on page {page_num} for '{current_keyword}'.")

            for idx, card in enumerate(job_cards, 1):
                if time.time() - START_TIME >= MAX_RUN_SECONDS:
                    print(f"\n⏰ Time limit reached ({int(time.time() - START_TIME)}s elapsed). Exiting job loop.")
                    break

                main_window = driver.window_handles[0]
                try:
                    # Scroll card into view
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                    time.sleep(0.8)

                    # Extract job title and link
                    title_elem = None
                    for title_xpath in [
                        ".//a[contains(@class, 'title')]",
                        ".//a[contains(@class, 'job-title')]",
                        ".//div[contains(@class, 'row1')]//a",
                        ".//a[contains(@href, 'job-listings')]",
                        ".//a[@title]",
                        ".//a"
                    ]:
                        matches = card.find_elements(By.XPATH, title_xpath)
                        if matches:
                            title_elem = matches[0]
                            break

                    if not title_elem:
                        print(f"⏭️ Skipping job #{idx}: Could not find job title element.")
                        continue

                    job_title = title_elem.text.strip()
                    job_link = title_elem.get_attribute("href")

                    if not job_link or "javascript:" in job_link:
                        print(f"⏭️ Skipping job #{idx}: Invalid job URL.")
                        continue

                    # Avoid duplicate jobs across keywords
                    if job_link in seen_job_links:
                        print(f"⏭️ Skipping job #{idx} ('{job_title}'): Already processed in this run.")
                        continue
                    seen_job_links.add(job_link)

                    # Check keyword relevance if enabled
                    if FILTER_TITLE_KEYWORDS:
                        keyword_tokens = [k.strip().lower() for k in current_keyword.split() if len(k.strip()) > 1]
                        if not any(token in job_title.lower() for token in keyword_tokens):
                            print(f"⏭️ Skipping job #{idx} ('{job_title}') — does not match '{current_keyword}'.")
                            skipped_count += 1
                            continue

                    print(f"\n🔍 Processing job #{idx} on page {page_num} [{current_keyword}]: {job_title}")

                    # Open job in new tab
                    driver.execute_script("window.open(arguments[0], '_blank');", job_link)
                    time.sleep(2)

                    if len(driver.window_handles) < 2:
                        print("⚠️ Job did not open in new tab. Skipping.")
                        continue

                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(2.5)

                    current_url = driver.current_url.lower()

                    # Check if already applied
                    already_applied = driver.find_elements(
                        By.XPATH, "//span[contains(text(), 'Already Applied') or contains(text(), 'Applied')] | //button[contains(text(), 'Applied')]"
                    )
                    if already_applied:
                        print("ℹ️ Already applied to this job.")
                        already_applied_count += 1
                    elif "naukri.com" not in current_url:
                        print("🔁 External company website — skipping auto-apply.")
                        skipped_count += 1
                    else:
                        # Look for the Apply button
                        apply_clicked = False
                        apply_button_xpaths = [
                            "//button[@id='apply-button']",
                            "//button[contains(@class, 'apply-button') and not(contains(text(), 'Company'))]",
                            "//div[contains(@class, 'apply-button-container')]//button",
                            "//button[normalize-space(text())='Apply' or normalize-space(text())='Quick Apply' or normalize-space(text())='I am interested']",
                            "//button[contains(text(), 'Apply on Naukri')]",
                            "//span[normalize-space(text())='Apply' or normalize-space(text())='Apply on Naukri']/parent::button",
                            "//button[contains(@class, 'waves-effect') and contains(., 'Apply')]"
                        ]

                        for btn_xpath in apply_button_xpaths:
                            try:
                                btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
                                driver.execute_script("arguments[0].click();", btn)
                                apply_clicked = True
                                print(f"✅ Clicked Apply for: {job_title}")
                                applied_count += 1
                                time.sleep(2)
                                break
                            except Exception:
                                continue

                        if not apply_clicked:
                            company_site_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Company Site') or contains(text(), 'company website')]")
                            if company_site_btn:
                                print("🔁 Job requires applying directly on company website — skipping.")
                            else:
                                print("⚠️ Apply button not found or already applied.")
                            skipped_count += 1

                        # Handle optional questionnaire / chatbot drawer
                        dismiss_popups()

                except Exception as e:
                    safe_kw = "".join(c if c.isalnum() else "_" for c in current_keyword)
                    driver.save_screenshot(f"error_job_{safe_kw}_{page_num}_{idx}.png")
                    print(f"❌ Error on job #{idx}: {e}")

                finally:
                    # Safely close extra tabs and return to main search tab
                    try:
                        while len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[-1])
                            driver.close()
                        driver.switch_to.window(main_window)
                    except Exception:
                        if driver.window_handles:
                            driver.switch_to.window(driver.window_handles[0])

                    time.sleep(random.uniform(1.0, 2.5))

            page_num += 1

    print("\n" + "="*50)
    print("🎉 Run Complete!")
    print(f"   Applied: {applied_count}")
    print(f"   Already Applied: {already_applied_count}")
    print(f"   Skipped / External: {skipped_count}")
    print("="*50)

finally:
    if driver:
        driver.quit()
