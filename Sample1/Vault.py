import os
import sys
import time
import shutil
import re
import json
import io
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from urllib.parse import unquote

# ======================================================================
# LOAD CONFIG
# ======================================================================

with open("config.json", "r") as cfg:
    config = json.load(cfg)

USERNAME = config["USERNAME"]
PASSWORD = config["PASSWORD"]
BAMBOO_URL = config["BAMBOO_URL"]
VERSION = config["VERSION"]
BASE_DOWNLOAD = config["BASE_DOWNLOAD"]
TEAMS_WEBHOOK = config["TEAMS_WEBHOOK"]

# ======================================================================
# TEE LOGGER
# ======================================================================

class TeeLogger(io.StringIO):
    def __init__(self, stream):
        super().__init__()
        self.stream = stream

    def write(self, message):
        self.stream.write(message)
        super().write(message)

    def flush(self):
        self.stream.flush()


log_buffer = TeeLogger(sys.stdout)
sys.stdout = log_buffer
sys.stderr = log_buffer

# ======================================================================
# JOB DEFINITIONS
# ======================================================================

BUILD_JOBS = [
    {
        "name": "UPDATE",
        "download_dir": rf"{BASE_DOWNLOAD}\Update",
        "destination": r"\\172.25.136.6\share\Velocity\3.9.1 Builds\Update",
        "dashboard_xpath": "//*[@id='dashboard']/tbody[6]/tr[4]/td[1]/a[2]",
        "build_link": "//a[@href='/browse/VELT-UPD9/latestSuccessful']",
        "artifact_button": "//a[text()='Update']",
    },
    {
        "name": "VCCS",
        "download_dir": rf"{BASE_DOWNLOAD}\VCCS",
        "destination": r"\\172.25.136.6\share\Velocity\3.9.1 Builds\VCCS",
        "dashboard_xpath": "//*[@id='dashboard']/tbody[2]/tr/td[3]/a[2]/span",
        "build_link": "//a[@href='/browse/VCCS-TRUNK5/latestSuccessful']",
        "artifact_button": "//a[text()='Update']",
    },
    {
        "name": "VWSC",
        "download_dir": rf"{BASE_DOWNLOAD}\VWSC",
        "destination": r"\\172.25.136.6\share\Velocity\3.9.1 Builds\VWSC",
        "dashboard_xpath": "//*[@id='dashboard']/tbody[10]/tr/td[3]/a[2]/span",
        "build_link": "//a[@href='/browse/VWSC-VWARK2207/latestSuccessful']",
        "artifact_button": "//a[contains(.,'vwc2install')]",
    },
    {
        "name": "INSTALLER",
        "download_dir": rf"{BASE_DOWNLOAD}\Installer",
        "destination": r"\\172.25.136.6\share\Velocity\3.9.1 Builds\Install",
        "dashboard_xpath": "//*[@id='dashboard']/tbody[6]/tr[2]/td[1]/a[2]/span",
        "build_link": "//a[@href='/browse/VELT-INST5/latestSuccessful']",
        "artifact_button": "//a[text()='Installer']",
    }
]

# ======================================================================
# HELPERS
# ======================================================================

def clear_folder(folder):
    os.makedirs(folder, exist_ok=True)
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        except Exception:
            pass


def wait_for_download(folder, before_files, timeout=900, stable_seconds=20):
    """
    Wait for Chrome download completion.
    Handles large installer downloads and stuck .crdownload files.
    """

    start = time.time()
    last_sizes = {}
    stable_since = {}

    while True:
        time.sleep(2)

        if time.time() - start > timeout:
            raise TimeoutError("Download timeout")

        files = os.listdir(folder)

        # --------------------------------------------------------------
        # Check completed files
        # --------------------------------------------------------------
        completed_files = [
            f for f in files
            if not f.endswith(".crdownload")
            and f not in before_files
        ]

        if completed_files:
            completed_path = os.path.join(folder, completed_files[0])

            # ensure file is stable
            size = os.path.getsize(completed_path)

            if completed_path not in last_sizes:
                last_sizes[completed_path] = size
                stable_since[completed_path] = time.time()

            elif size == last_sizes[completed_path]:
                if time.time() - stable_since[completed_path] >= stable_seconds:
                    return completed_path
            else:
                last_sizes[completed_path] = size
                stable_since[completed_path] = time.time()

        # --------------------------------------------------------------
        # Handle stuck .crdownload files
        # --------------------------------------------------------------
        partials = [
            f for f in files
            if f.endswith(".crdownload")
        ]

        for partial in partials:

            partial_path = os.path.join(folder, partial)

            try:
                size = os.path.getsize(partial_path)
            except:
                continue

            if partial_path not in last_sizes:
                last_sizes[partial_path] = size
                stable_since[partial_path] = time.time()

            elif size == last_sizes[partial_path]:

                # If partial file size has not changed for long time,
                # assume Chrome got stuck.
                if time.time() - stable_since[partial_path] >= stable_seconds:

                    # Try renaming partial file
                    final_name = partial.replace(".crdownload", "")
                    final_path = os.path.join(folder, final_name)

                    try:
                        os.rename(partial_path, final_path)

                        if os.path.exists(final_path):
                            return final_path

                    except Exception:
                        pass

            else:
                last_sizes[partial_path] = size
                stable_since[partial_path] = time.time()

def extract_filename(element):
    href = element.get_attribute("href")
    return unquote(os.path.basename(href.split("?")[0])) if href else element.text.strip()


def extract_build_from_filename(filename):
    """
    UPDATE / INSTALLER:
      Velocity_Update_3.9.1(build-3.9.1.190).exe -> 190

    VCCS:
      VelocityCertService_3.9.1.4.exe -> 4
    """

    # build-3.9.1.190
    m = re.search(r'build-\d+\.\d+\.\d+\.(\d+)', filename, re.IGNORECASE)
    if m:
        return m.group(1)

    # version-style 3.9.1.4.exe
    m = re.search(r'\d+\.\d+\.\d+\.(\d+)(?=\.[^.]+$)', filename)
    if m:
        return m.group(1)

    # fallback
    m = re.search(r'(\d+)(?=\.[^.]+$)', filename)
    if m:
        return m.group(1)

    return "Unknown"


def get_existing_build(destination):
    if not os.path.exists(destination):
        return None

    files = [f for f in os.listdir(destination) if os.path.isfile(os.path.join(destination, f))]
    if not files:
        return None

    files.sort(key=lambda f: os.path.getmtime(os.path.join(destination, f)), reverse=True)
    return extract_build_from_filename(files[0])


def safe_move(src, dst, retries=10, delay=2):
    for i in range(retries):
        try:
            shutil.move(src, dst)
            return
        except PermissionError:
            if i == retries - 1:
                raise
            time.sleep(delay)

# ======================================================================
# BROWSER
# ======================================================================

def new_browser(download_dir):
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "safebrowsing.enabled": True,
        },
    )
    driver = webdriver.Chrome(options=opts)
    return driver, WebDriverWait(driver, 40)

# ======================================================================
# LOGIN
# ======================================================================

def login(driver, wait):
    driver.get(BAMBOO_URL)
    wait.until(EC.presence_of_element_located((By.ID, "loginForm_os_username"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.ID, "loginForm_os_password"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.ID, "loginForm_save"))).click()

# ======================================================================
# BUILD NUMBER EXTRACTION (VWSC UNCHANGED)
# ======================================================================

def extract_vwsc_build(wait):
    try:
        el = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[@id='plan-status-history']/ol/li[10]/a/span")
            )
        )
        title = el.get_attribute("title")
        m = re.search(r"#(\d+)", title)
        return m.group(1) if m else "Unknown"
    except Exception:
        return "Unknown"

# ======================================================================
# MAIN
# ======================================================================

any_build_downloaded = False
print("Build Details:")

for job in BUILD_JOBS:
    clear_folder(job["download_dir"])
    driver, wait = new_browser(job["download_dir"])

    try:
        login(driver, wait)

        wait.until(EC.element_to_be_clickable((By.XPATH, job["dashboard_xpath"]))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[text()='{VERSION}']"))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, job["build_link"]))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, "//strong[text()='Artifacts']"))).click()

        # Existing build (for no-download case)
        if job["name"] == "VWSC":
            build_no = extract_vwsc_build(wait)
        else:
            build_no = get_existing_build(job["destination"])

        artifact = wait.until(EC.element_to_be_clickable((By.XPATH, job["artifact_button"])))
        artifact_name = extract_filename(artifact)

        before_files = set(os.listdir(job["download_dir"]))
        artifact.click()

        try:
            downloaded = wait_for_download(job["download_dir"], before_files)
        except TimeoutError:
            print(f"Velocity {job['name']} - No new build available (Build 3.9.1.{build_no})")
            continue

        # New build
        if job["name"] != "VWSC":
            build_no = extract_build_from_filename(os.path.basename(downloaded))
            final_name = artifact_name
        else:
            final_name = f"vwc2install_{VERSION}_{build_no}.exe"
            renamed = os.path.join(job["download_dir"], final_name)
            os.rename(downloaded, renamed)
            downloaded = renamed

        expected_dest = os.path.join(job["destination"], final_name)

        if os.path.exists(expected_dest):
            print(f"Velocity {job['name']} - No new build available (Build 3.9.1.{build_no})")
            continue

        os.makedirs(job["destination"], exist_ok=True)
        safe_move(downloaded, expected_dest)

        print(f"Velocity {job['name']} - Build 3.9.1.{build_no} downloaded and available in Share location")
        any_build_downloaded = True

    except Exception as e:
        print(f"Error ({job['name']}): {e}")
    finally:
        driver.quit()
        time.sleep(3)

print(
    r"""
 Share location: \\172.25.136.6\share\Velocity\3.9.1 Builds
=== Have a great day! ===
"""
)

# ======================================================================
# TEAMS NOTIFICATION
# ======================================================================

payload = {"text": f"```\n{log_buffer.getvalue()[-25000:]}\n```"}
try:
    r = requests.post(TEAMS_WEBHOOK, json=payload)
    print(f"Teams Response: {r.status_code}")
except Exception as e:
    print("Teams send failed:", e)
finally:
    sys.exit(0)
