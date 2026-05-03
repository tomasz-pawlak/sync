import os
import logging
from ftplib import FTP, error_perm
import time

# =========================
# CONFIGURATION
# =========================

FTP_HOST = "ftp.example.com"         
FTP_USER = "your_username"           
FTP_PASS = "your_password"           

# MAPOWANIE: lokalny → zdalny
DIRECTORY_MAPPING = {
    "Z:\\folder1": "/public_html/siteA",    
    "Z:\\folder2": "/backups/images",       
    "Z:\\folder3": "/logs/app"              
}

# Linux / Synology przykład:
# DIRECTORY_MAPPING = {
#     "/volume1/folder1": "/public_html/siteA",
#     "/volume1/folder2": "/backups/images",
#     "/volume1/folder3": "/logs/app"
# }

LOG_FILE = "./ftp.log"   # możesz zmienić na np. /volume1/scripts/logs/ftp.log

MAX_RETRIES = 3
RETRY_DELAY = 5


# =========================
# PREP LOGGING
# =========================

log_dir = os.path.dirname(LOG_FILE)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log(msg):
    print(msg)
    logging.info(msg)


# =========================
# FTP FUNCTIONS
# =========================

def connect_ftp():
    for attempt in range(MAX_RETRIES):
        try:
            ftp = FTP(FTP_HOST, timeout=30)
            ftp.login(FTP_USER, FTP_PASS)
            log("[+] Connected to FTP")
            return ftp
        except Exception as e:
            log(f"[ERROR] FTP connection failed: {e}")
            time.sleep(RETRY_DELAY)
    raise Exception("FTP connection failed after retries")


def ensure_remote_directory(ftp, path):
    dirs = path.split("/")
    current_path = ""

    for d in dirs:
        if d == "":
            continue

        current_path += f"/{d}"
        try:
            ftp.mkd(current_path)
            log(f"[+] Created dir: {current_path}")
        except error_perm:
            pass


def file_exists_and_same_size(ftp, remote_path, local_size):
    try:
        size = ftp.size(remote_path)
        return size == local_size
    except:
        return False


def upload_file(ftp, local_file, remote_file):
    local_size = os.path.getsize(local_file)

    if file_exists_and_same_size(ftp, remote_file, local_size):
        log(f"[SKIP] {remote_file} (same size)")
        return

    for attempt in range(MAX_RETRIES):
        try:
            with open(local_file, "rb") as f:
                ftp.storbinary(f"STOR {remote_file}", f)
            log(f"[UPLOAD] {local_file} -> {remote_file}")
            return
        except Exception as e:
            log(f"[ERROR] Upload failed: {remote_file} ({e})")
            time.sleep(RETRY_DELAY)

    log(f"[FAILED] {remote_file}")


def upload_directory(ftp, local_dir, remote_dir):
    if not os.path.exists(local_dir):
        log(f"[WARNING] Local dir not found: {local_dir}")
        return

    for root, dirs, files in os.walk(local_dir):
        relative = os.path.relpath(root, local_dir)
        remote_path = os.path.join(remote_dir, relative).replace("\\", "/")

        ensure_remote_directory(ftp, remote_path)

        for file in files:
            local_file = os.path.join(root, file)
            remote_file = f"{remote_path}/{file}".replace("\\", "/")

            upload_file(ftp, local_file, remote_file)


# =========================
# MAIN
# =========================

def main():
    log("===== FTP SYNC START =====")

    if not DIRECTORY_MAPPING:
        raise Exception("No directory mappings defined!")

    log(f"[CONFIG] Loaded {len(DIRECTORY_MAPPING)} directory mappings")

    try:
        ftp = connect_ftp()

        for local_dir, remote_dir in DIRECTORY_MAPPING.items():
            log(f"[SYNC] {local_dir} -> {remote_dir}")
            upload_directory(ftp, local_dir, remote_dir)

        ftp.quit()
        log("[+] FTP connection closed")

    except Exception as e:
        log(f"[CRITICAL] {e}")

    log("===== FTP SYNC END =====\n")


if __name__ == "__main__":
    main()
