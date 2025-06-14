import requests
import threading
import random
import time
import sys
import argparse
import os
from datetime import datetime
from collections import deque
import urllib3
import json
import itertools # Untuk cycling proxies

# Optional: Untuk tampilan terminal yang lebih canggih
try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.status import Status
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not found. Falling back to basic console output.")


# Nonaktifkan peringatan SSL untuk tujuan demo/pengujian
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KONFIGURASI INTI (DIOPTIMALKAN UNTUK HP NOTEBOOK AZKIAH) ---
DEFAULT_THREADS = 20 # Sedikit dinaikkan, tapi masih aman dengan RPS rendah
DEFAULT_RPS_PER_THREAD = 4  # Disesuaikan: Turunkan lagi RPS per thread agar lebih stabil
DEFAULT_DURATION = 180 # Durasi dalam detik (diperpanjang)
DEFAULT_TIMEOUT = 8 # Timeout untuk setiap permintaan (detik)
DEFAULT_MAX_RETRIES = 2 # Jumlah percobaan ulang jika gagal
DEFAULT_RETRY_DELAY = 1.0 # Jeda sebelum mencoba lagi
DEFAULT_MIN_PAYLOAD_KB = 0.25 # Ukuran payload POST minimum (0.25 KB)
DEFAULT_MAX_PAYLOAD_KB = 1 # Ukuran payload POST maksimum (1 KB)
DEFAULT_THINK_TIME_MIN = 0.1 # Waktu berpikir minimum antar request (detik)
DEFAULT_THINK_TIME_MAX = 0.5 # Waktu berpikir maksimum antar request (detik)
PROXY_FILE = "proxies.txt" # Nama file untuk daftar proxy

# --- DAFTAR USER AGENT (diperluas dengan fokus Linux/Ubuntu) ---
USER_AGENTS = [
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Brave Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

# --- DAFTAR METODE HTTP ---
ATTACK_METHODS = ["GET", "POST", "HEAD"]

# --- GLOBAL STATS ---
total_requests_sent = 0
total_successful_requests = 0
total_failed_requests = 0
response_times = deque(maxlen=300) # Kurangi lagi untuk hemat memori
proxy_errors = {} # Melacak error per proxy
status_code_counts = {} # Melacak hitungan per status kode

# --- LOCK UNTUK MENGAKSES STATS ---
stats_lock = threading.Lock()

# --- Proxy Management ---
available_proxies = []
proxy_iterator = None # Akan diinisialisasi sebagai cycle iterator

def load_proxies(filepath):
    """Membaca daftar proxy dari file."""
    proxies = []
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Format: host:port atau user:pass@host:port
                    if "://" not in line:
                        line = "http://" + line # Asumsi http jika tidak ada skema
                    proxies.append(line)
        if proxies:
            print(f"\033[92m[{datetime.now().strftime('%H:%M:%S')}] [+] {len(proxies)} proxy dimuat dari '{filepath}'.\033[0m")
        else:
            print(f"\033[93m[{datetime.now().strftime('%H:%M:%S')}] [!] Tidak ada proxy valid ditemukan di '{filepath}'.\033[0m")
    else:
        print(f"\033[93m[{datetime.now().strftime('%H:%M:%S')}] [!] File proxy '{filepath}' tidak ditemukan. Menggunakan koneksi langsung.\033[0m")
    return proxies

def get_next_proxy():
    """Mengembalikan proxy berikutnya dari iterator."""
    global proxy_iterator
    if proxy_iterator:
        return {"http": next(proxy_iterator), "https": next(proxy_iterator)}
    return None

# --- Fungsi untuk membersihkan terminal ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def generate_random_params():
    """Menghasilkan parameter URL acak."""
    return {
        "id": random.randint(1000, 999999),
        "session_id": ''.join(random.choices('0123456789abcdef', k=random.randint(16, 32))),
        "cache_buster": int(time.time() * 1000), # Lebih spesifik
        "action": random.choice(["view", "search", "browse", "detail"]),
    }

def generate_random_json_data(min_size_kb, max_size_kb):
    """Menghasilkan data JSON acak dengan ukuran bervariasi."""
    size_bytes = random.randint(int(min_size_kb * 1024), int(max_size_kb * 1024))
    
    # Memastikan data tidak terlalu besar, terutama jika min/max kecil
    random_str_len = min(size_bytes // 2, 1024) # Maks 1KB untuk random string di payload kecil
    random_content = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789 ', k=random_str_len))
    
    data = {
        "user": f"azkiah_{random.randint(100, 9999)}",
        "email": f"user_{random.randint(100, 9999)}@random.com",
        "data_payload": random_content,
        "request_id": ''.join(random.choices('ABCDEF0123456789', k=16)),
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "source_ip": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
    }
    return data

def generate_spoofed_headers(target_url, custom_headers=None):
    """Menghasilkan header dengan spoofing IP, User-Agent, dan beberapa header WAF evasion."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "X-Forwarded-For": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "Via": f"1.1 {random.choice(['anon-proxy.com', 'cache.example.net'])}", # Menyamar sebagai proxy lain
        "Referer": target_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Content-Type": "application/json" # Default untuk POST JSON
    }
    if custom_headers:
        headers.update(custom_headers) # Gabungkan dengan header kustom jika ada
    return headers

def send_request_with_retries(session, target_url, method, headers, params, data, proxies, timeout, max_retries, retry_delay):
    """Mengirimkan satu permintaan HTTP dengan logika retry dan proxy."""
    global total_requests_sent, total_successful_requests, total_failed_requests, proxy_errors, status_code_counts

    for attempt in range(max_retries):
        start_request_time = time.time()
        try:
            if method == "GET":
                response = session.get(target_url, headers=headers, params=params, proxies=proxies, timeout=timeout, verify=False)
            elif method == "POST":
                response = session.post(target_url, headers=headers, json=data, proxies=proxies, timeout=timeout, verify=False)
            elif method == "HEAD":
                response = session.head(target_url, headers=headers, proxies=proxies, timeout=timeout, verify=False)
            else:
                with stats_lock:
                    total_failed_requests += 1
                return False, f"Invalid HTTP method: {method}"

            end_request_time = time.time()
            response_time_ms = (end_request_time - start_request_time) * 1000 # dalam milidetik

            with stats_lock:
                total_requests_sent += 1
                response_times.append(response_time_ms)
                status_code_counts[response.status_code] = status_code_counts.get(response.status_code, 0) + 1

                if 200 <= response.status_code < 300:
                    total_successful_requests += 1
                    return True, response.status_code
                else:
                    total_failed_requests += 1
                    return False, response.status_code

        except requests.exceptions.Timeout:
            with stats_lock:
                total_failed_requests += 1
                if proxies:
                    proxy_errors[proxies['http']] = proxy_errors.get(proxies['http'], 0) + 1
            # print(f"\033[91m[-] Request Timeout ({method} | Attempt {attempt + 1})\033[0m")
        except requests.exceptions.ConnectionError as e:
            with stats_lock:
                total_failed_requests += 1
                if proxies:
                    proxy_errors[proxies['http']] = proxy_errors.get(proxies['http'], 0) + 1
            # print(f"\033[91m[-] Connection Error ({method} | Attempt {attempt + 1}): {e}\033[0m")
        except requests.exceptions.RequestException as e:
            with stats_lock:
                total_failed_requests += 1
                if proxies:
                    proxy_errors[proxies['http']] = proxy_errors.get(proxies['http'], 0) + 1
            # print(f"\033[91m[-] Request Exception ({method} | Attempt {attempt + 1}): {e}\033[0m")
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    with stats_lock:
        total_failed_requests += 1
    return False, "Max retries exceeded"

def worker_thread(target_url, rps_per_thread, duration, timeout, max_retries, retry_delay, 
                  min_payload_kb, max_payload_kb, think_time_min, think_time_max, thread_id):
    """Fungsi yang dijalankan oleh setiap thread."""
    session = requests.Session()
    session.trust_env = False # Penting untuk mengabaikan proxy env
    
    start_thread_time = time.time()
    interval_base = 1.0 / rps_per_thread # Jeda dasar antar permintaan untuk mencapai RPS target

    while time.time() - start_thread_time < duration:
        request_start_time = time.time()
        
        method = random.choice(ATTACK_METHODS)
        headers = generate_spoofed_headers(target_url)
        params = generate_random_params() if method in ["GET", "HEAD"] else None
        data = generate_random_json_data(min_payload_kb, max_payload_kb) if method == "POST" else None
        
        current_proxies = get_next_proxy() # Ambil proxy dari iterator

        send_request_with_retries(session, target_url, method, headers, params, data, current_proxies, timeout, max_retries, retry_delay)
        
        elapsed_for_request = time.time() - request_start_time
        
        # Tambahkan "thinking time" acak
        thinking_delay = random.uniform(think_time_min, think_time_max)
        
        sleep_time = interval_base - elapsed_for_request + thinking_delay
        if sleep_time > 0:
            time.sleep(sleep_time)

def display_summary_table():
    """Menampilkan ringkasan akhir dalam format tabel menggunakan Rich."""
    if not RICH_AVAILABLE:
        return # Skip jika Rich tidak tersedia

    table = Table(
        title=Text("RINGKASAN HASIL PENGUJIAN", style="bold yellow"),
        show_header=True, header_style="bold magenta",
        box=None # Tidak ada box
    )
    table.add_column("METRIK", style="cyan", justify="left")
    table.add_column("NILAI", style="green", justify="right")

    final_elapsed_time = time.time() - main.start_test_time
    final_rps = total_requests_sent / final_elapsed_time if final_elapsed_time > 0 else 0
    final_avg_response_time = sum(response_times) / len(response_times) if response_times else 0

    table.add_row("Target URL", str(main.target_url_global))
    table.add_row("Total Durasi", f"{final_elapsed_time:.2f} detik")
    table.add_row("Total Permintaan Terkirim", f"{total_requests_sent}")
    table.add_row("Permintaan Sukses", f"{total_successful_requests}")
    table.add_row("Permintaan Gagal", f"{total_failed_requests}")
    table.add_row("Rata-rata RPS Keseluruhan", f"{final_rps:.2f}")
    table.add_row("Rata-rata Waktu Respons", f"{final_avg_response_time:.2f} ms")

    # Status Code Distribution
    status_codes_text = Text()
    for code, count in sorted(status_code_counts.items()):
        status_codes_text.append(f"  {code}: {count}\n", style="blue")
    if status_codes_text:
        table.add_row("Distribusi Status Kode", status_codes_text)
    else:
        table.add_row("Distribusi Status Kode", "N/A")

    # Proxy Error Report
    if proxy_errors:
        proxy_error_text = Text()
        for proxy, errors in sorted(proxy_errors.items(), key=lambda item: item[1], reverse=True):
            proxy_error_text.append(f"  {proxy}: {errors} errors\n", style="red")
        table.add_row("Error Proxy", proxy_error_text)
    else:
        table.add_row("Error Proxy", "Tidak ada error proxy.")

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="""
╔╦╗┬ ┬┬ ┬┌─┐  ┬ ┬┌─┐┌─┐┬─┐┌┬┐
 ║ ├─┤├─┤│      └┬┘├─┘├┤ ├┬┘ │
 ╩ ┴ ┴┴ ┴└─┘    ┴ ┴  └─┘┴└─ ┴ 
        (HTTP Load Test / Stress Tool - For Ethical Use Only)
        
        Disesuaikan untuk HP Notebook Azkiah.
        Memastikan performa optimal tanpa terlalu membebani sistem.
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("url", help="Target URL (e.g., https://example.com/api/data)")
    parser.add_argument("-t", "--threads", type=int, default=DEFAULT_THREADS,
                        help=f"Jumlah thread konkurensi (default: {DEFAULT_THREADS})")
    parser.add_argument("-r", "--rps", type=int, default=DEFAULT_RPS_PER_THREAD,
                        help=f"Permintaan per detik per thread (default: {DEFAULT_RPS_PER_THREAD})")
    parser.add_argument("-d", "--duration", type=int, default=DEFAULT_DURATION,
                        help=f"Durasi pengujian dalam detik (default: {DEFAULT_DURATION}s)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Timeout untuk setiap permintaan (detik) (default: {DEFAULT_TIMEOUT}s)")
    parser.add_argument("--retries", type=int, default=DEFAULT_MAX_RETRIES,
                        help=f"Jumlah percobaan ulang jika permintaan gagal (default: {DEFAULT_MAX_RETRIES})")
    parser.add_argument("--retry-delay", type=float, default=DEFAULT_RETRY_DELAY,
                        help=f"Jeda antara percobaan ulang (detik) (default: {DEFAULT_RETRY_DELAY}s)")
    parser.add_argument("--min-payload", type=float, default=DEFAULT_MIN_PAYLOAD_KB,
                        help=f"Ukuran payload POST minimum (KB) (default: {DEFAULT_MIN_PAYLOAD_KB}KB)")
    parser.add_argument("--max-payload", type=float, default=DEFAULT_MAX_PAYLOAD_KB,
                        help=f"Ukuran payload POST maksimum (KB) (default: {DEFAULT_MAX_PAYLOAD_KB}KB)")
    parser.add_argument("--think-time-min", type=float, default=DEFAULT_THINK_TIME_MIN,
                        help=f"Waktu berpikir minimum antar request (detik) (default: {DEFAULT_THINK_TIME_MIN}s)")
    parser.add_argument("--think-time-max", type=float, default=DEFAULT_THINK_TIME_MAX,
                        help=f"Waktu berpikir maksimum antar request (detik) (default: {DEFAULT_THINK_TIME_MAX}s)")
    parser.add_argument("--proxies-file", type=str, default=PROXY_FILE,
                        help=f"File berisi daftar proxy (format: host:port, satu per baris) (default: {PROXY_FILE})")
    
    args = parser.parse_args()

    # Set global target_url untuk summary
    main.target_url_global = args.url
    main.start_test_time = time.time()

    clear_screen() # Bersihkan layar di awal

    # Output "Dibuat oleh Azkiah"
    print("\033[95m" + "=" * 60 + "\033[0m")
    print("\033[93m" + "    _    _ _______ _     _ ___________ ______ _   _ " + "\033[0m")
    print("\033[93m" + "   / \\  / |______  \\_  _/ |     |     |  ____| \\ | |" + "\033[0m")
    print("\033[93m" + "  /_  \\/  |______   | |  |  ___|_____| |_____|  \\| |" + "\033[0m")
    print("\033[93m" + "\n" + "          \033[92mDibuat oleh: \033[96m azkiah \033[0m")
    print("\033[95m" + "=" * 60 + "\033[0m")

    print("\033[91m" + """
███████╗██╗  ██╗██████╗ ███████╗██████╗  █████╗ ████████╗███████╗
██╔════╝██║  ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
███████╗███████║██████╔╝█████╗  ██████╔╝███████║   ██║   █████╗  
╚════██║██╔══██║██╔══██╗██╔══╝  ██╔══██╗██╔══██║   ██║   ██╔══╝  
███████║██║  ██║██║  ██║███████╗██║  ██║██║  ██║   ██║   ███████╗
╚══════╝╚═╝  ╚═╝╚╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
    """ + "\033[0m") # ASCII Art dan Warna Merah

    print(f"\033[93m[{datetime.now().strftime('%H:%M:%S')}] Memulai Uji Beban HTTP pada \033[96m{args.url}\033[0m")
    print(f"\033[93m[{datetime.now().strftime('%H:%M:%S')}] Konfigurasi:\033[0m")
    print(f"  \033[92m[*] Thread:\033[0m {args.threads}")
    print(f"  \033[92m[*] RPS per Thread:\033[0m {args.rps}")
    print(f"  \033[92m[*] Total RPS (estimasi):\033[0m {args.threads * args.rps}")
    print(f"  \033[92m[*] Durasi:\033[0m {args.duration} detik")
    print(f"  \033[92m[*] Timeout:\033[0m {args.timeout} detik")
    print(f"  \033[92m[*] Payload POST:\033[0m {args.min_payload:.2f}KB - {args.max_payload:.2f}KB")
    print(f"  \033[92m[*] Waktu Berpikir:\033[0m {args.think_time_min:.2f}s - {args.think_time_max:.2f}s")
    print("\033[95m" + "=" * 60 + "\033[0m")

    global available_proxies, proxy_iterator
    available_proxies = load_proxies(args.proxies_file)
    if available_proxies:
        proxy_iterator = itertools.cycle(available_proxies)

    threads_list = []
    
    # Pre-test / Health Check (opsional)
    print(f"\033[93m[{datetime.now().strftime('%H:%M:%S')}] Melakukan pre-test koneksi...\033[0m")
    try:
        test_session = requests.Session()
        test_session.trust_env = False
        test_response = test_session.get(args.url, timeout=DEFAULT_TIMEOUT, verify=False)
        print(f"\033[92m[{datetime.now().strftime('%H:%M:%S')}] [+] Koneksi awal berhasil. Status: {test_response.status_code}\033[0m")
    except requests.exceptions.RequestException as e:
        print(f"\033[91m[{datetime.now().strftime('%H:%M:%S')}] [!] Koneksi awal gagal: {e}. Periksa URL atau koneksi internet Anda.\033[0m")
        sys.exit(1) # Keluar jika pre-test gagal

    # Inisialisasi threads
    print(f"\033[93m[{datetime.now().strftime('%H:%M:%S')}] Menginisialisasi {args.threads} thread...\033[0m")
    for i in range(args.threads):
        thread = threading.Thread(
            target=worker_thread,
            args=(args.url, args.rps, args.duration, args.timeout, args.retries, args.retry_delay, 
                  args.min_payload, args.max_payload, args.think_time_min, args.think_time_max, i)
        )
        thread.daemon = True
        threads_list.append(thread)
        thread.start()
        # print(f"\033[94m[{datetime.now().strftime('%H:%M:%S')}] [+] Thread-{i + 1} aktif.\033[0m") # Terlalu banyak output

    try:
        # Tampilan progres yang lebih canggih (opsional dengan rich)
        if RICH_AVAILABLE:
            with Live(refresh_per_second=4, screen=False) as live: # Update lebih sering
                while time.time() - main.start_test_time < args.duration:
                    elapsed_time = int(time.time() - main.start_test_time)
                    
                    with stats_lock:
                        current_total = total_requests_sent
                        current_success = total_successful_requests
                        current_failed = total_failed_requests
                        current_rps = current_total / elapsed_time if elapsed_time > 0 else 0
                        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

                    progress_text = Text()
                    progress_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] ", style="yellow")
                    progress_text.append(f"Waktu: {elapsed_time:03d}s/{args.duration}s | ", style="cyan")
                    progress_text.append(f"Kirim: {current_total:<6} | ", style="white")
                    progress_text.append(f"Sukses: {current_success:<5} ", style="green")
                    progress_text.append(f"| Gagal: {current_failed:<5} ", style="red")
                    progress_text.append(f"| RPS: {current_rps:.2f} | ", style="yellow")
                    progress_text.append(f"Resp (ms): {avg_response_time:.2f}", style="yellow")
                    
                    live.update(progress_text)
                    time.sleep(0.25) # Update setiap 0.25 detik
        else: # Fallback ke ANSI biasa jika Rich tidak tersedia
            while time.time() - main.start_test_time < args.duration:
                time.sleep(1)
                elapsed_time = int(time.time() - main.start_test_time)
                
                with stats_lock:
                    current_total = total_requests_sent
                    current_success = total_successful_requests
                    current_failed = total_failed_requests
                    current_rps = current_total / elapsed_time if elapsed_time > 0 else 0
                    avg_response_time = sum(response_times) / len(response_times) if response_times else 0

                sys.stdout.write(
                    f"\r\033[93m[\033[92m{datetime.now().strftime('%H:%M:%S')}\033[93m] "
                    f"\033[96mWaktu:\033[0m {elapsed_time:03d}s/{args.duration}s | "
                    f"\033[96mKirim:\033[0m \033[97m{current_total:<6}\033[0m | "
                    f"\033[96mSukses:\033[0m \033[92m{current_success:<5}\033[0m | "
                    f"\033[96mGagal:\033[0m \033[91m{current_failed:<5}\033[0m | "
                    f"\033[96mRPS:\033[0m \033[93m{current_rps:.2f}\033[0m | "
                    f"\033[96mResp (ms):\033[0m \033[93m{avg_response_time:.2f}\033[0m"
                )
                sys.stdout.flush()

        print(f"\n\033[93m[{datetime.now().strftime('%H:%M:%S')}] Durasi pengujian selesai.\033[0m")

    except KeyboardInterrupt:
        print(f"\n\033[91m[{datetime.now().strftime('%H:%M:%S')}] Uji beban dihentikan pengguna (\033[97mCtrl+C\033[91m).\033[0m")
    finally:
        # Tunggu semua thread selesai (jika belum)
        for t in threads_list:
            if t.is_alive():
                t.join(timeout=2) # Beri waktu lebih singkat untuk thread selesai secara elegan
        
        if RICH_AVAILABLE:
            console.print("\n" + "=" * 60, style="magenta")
            display_summary_table()
            console.print("=" * 60, style="magenta")
        else:
            final_elapsed_time = time.time() - main.start_test_time
            final_rps = total_requests_sent / final_elapsed_time if final_elapsed_time > 0 else 0
            final_avg_response_time = sum(response_times) / len(response_times) if response_times else 0

            print("\n\033[95m" + "=" * 60 + "\033[0m")
            print(f"\033[93m[{datetime.now().strftime('%H:%M:%S')}] RINGKASAN HASIL PENGUJIAN:\033[0m")
            print(f"  \033[92m[*] Target URL:\033[0m \033[96m{args.url}\033[0m")
            print(f"  \033[92m[*] Total Durasi:\033[0m \033[97m{final_elapsed_time:.2f}\033[0m detik")
            print(f"  \033[92m[*] Total Permintaan Terkirim:\033[0m \033[97m{total_requests_sent}\033[0m")
            print(f"  \033[92m[*] Permintaan Sukses:\033[0m \033[92m{total_successful_requests}\033[0m")
            print(f"  \033[92m[*] Permintaan Gagal:\033[0m \033[91m{total_failed_requests}\033[0m")
            print(f"  \033[92m[*] Rata-rata RPS Keseluruhan:\033[0m \033[93m{final_rps:.2f}\033[0m")
            print(f"  \033[92m[*] Rata-rata Waktu Respons:\033[0m \033[93m{final_avg_response_time:.2f}\033[0m ms")
            
            print(f"\033[93m  [*] Distribusi Status Kode:\033[0m")
            for code, count in sorted(status_code_counts.items()):
                print(f"    \033[94m-> {code}:\033[0m {count}")

            if proxy_errors:
                print(f"\033[93m  [*] Error Proxy Terbanyak:\033[0m")
                for proxy, errors in sorted(proxy_errors.items(), key=lambda item: item[1], reverse=True)[:5]: # Tampilkan top 5
                    print(f"    \033[91m-> {proxy}:\033[0m {errors} errors")
            print("\033[95m" + "=" * 60 + "\033[0m")
        sys.exit(0)

if __name__ == "__main__":
    main()
