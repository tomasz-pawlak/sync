import os
import logging
from ftplib import FTP, error_perm
from datetime import datetime
import time

# =========================
# CONFIGURATION
# =========================

FTP_HOST = "192.168.100.179"          # TODO: zmień
FTP_USER = "ftpuser"            # TODO: zmień
FTP_PASS = "1234"            # TODO: zmień

LOCAL_DIRECTORIES = [
    "/home/gurtoc/Desktop/ftpTest/1",
    "/home/gurtoc/Desktop/ftpTest/2",
    "/home/gurtoc/Desktop/ftpTest/3"
]

REMOTE_BASE_DIR = "/home/ftpuser/uploads"  # TODO: zmień

LOG_FILE = "/home/gurtoc/Desktop/ftp.log"    # TODO: zmień ścieżkę

MAX_RETRIES = 3
RETRY_DELAY = 5  # sekundy

# =========================
# LOGGING
# =========================

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
            pass  # already exists


def file_exists_and_same_size(ftp, remote_path, local_size):
    """Sprawdza czy plik istnieje i ma taki sam rozmiar"""
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

    try:
        ftp = connect_ftp()

        for local_dir in LOCAL_DIRECTORIES:
            folder_name = os.path.basename(local_dir.rstrip("\\"))
            remote_dir = f"{REMOTE_BASE_DIR}/{folder_name}"

            log(f"[SYNC] {local_dir} -> {remote_dir}")
            upload_directory(ftp, local_dir, remote_dir)

        ftp.quit()
        log("[+] FTP connection closed")

    except Exception as e:
        log(f"[CRITICAL] {e}")

    log("===== FTP SYNC END =====\n")


if __name__ == "__main__":
    main()
