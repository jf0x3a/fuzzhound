import argparse
import sys
import requests
import time
import json
import threading
from queue import Queue
from colorama import Fore, Style, init
import itertools

init(autoreset=True)
# Default threads = 10
THREADS = 10

def display_banner():
    banner = f"""
{Fore.YELLOW}
 ███████████                                  █████   █████                                    █████
░░███░░░░░░█                                 ░░███   ░░███                                    ░░███ 
 ░███   █ ░  █████ ████  █████████  █████████ ░███    ░███   ██████  █████ ████ ████████    ███████ 
 ░███████   ░░███ ░███  ░█░░░░███  ░█░░░░███  ░███████████  ███░░███░░███ ░███ ░░███░░███  ███░░███ 
 ░███░░░█    ░███ ░███  ░   ███░   ░   ███░   ░███░░░░░███ ░███ ░███ ░███ ░███  ░███ ░███ ░███ ░███ 
 ░███  ░     ░███ ░███    ███░   █   ███░   █ ░███    ░███ ░███ ░███ ░███ ░███  ░███ ░███ ░███ ░███ 
 ░███████   ░░███ ░███    ███░   █   ███░   █ ░███    ░███ ░███ ░███ ░███ ░███  ░███ ░███ ░███ ░███ 
 █████       ░░████████  █████████  █████████ █████   █████░░██████  ░░████████ ████ █████░░████████
░░░░░         ░░░░░░░░  ░░░░░░░░░  ░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░░    ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░░░ 
  {Style.BRIGHT}                                                                                                                                                                                                                                          
   / \\__
   (    @\\___   
   /         O   {Style.BRIGHT}{Fore.YELLOW}Sniffing out API endpoints {Fore.YELLOW}  
  /   (_____/    {Style.BRIGHT}{Fore.YELLOW}by: @physx {Fore.YELLOW}            
 /_____/   U	

{Style.RESET_ALL}
    """
    print(banner)

def load_wordlists(wordlist_args):
    """Load multiple wordlists and return a list of combinations"""
    wordlists = []
    wordlist_files = wordlist_args.split(',')
    
    for i, wordlist_file in enumerate(wordlist_files):
        try:
            with open(wordlist_file.strip(), "r", encoding="utf-8", errors="ignore") as f:
                words = [line.strip() for line in f if line.strip()]
            wordlists.append(words)
            print(Fore.GREEN + f"[+] Loaded wordlist {i+1}: {wordlist_file.strip()} ({len(words)} words)")
        except FileNotFoundError:
            print(Fore.RED + f"[-] Error: Wordlist file '{wordlist_file}' not found")
            sys.exit(1)
        except Exception as e:
            print(Fore.RED + f"[-] Error reading wordlist '{wordlist_file}': {e}")
            sys.exit(1)
    
    # Generate all combinations
    combinations = list(itertools.product(*wordlists))
    return combinations

def fuzz_worker(queue, args, results):
    # Use while loop to read word from Queue
    while not queue.empty():
        item = queue.get()
        
        # Handle different types of payloads
        if isinstance(item, tuple):
            # Multiple wordlist combination
            word_combinations = item
            if "FUZZ" in args.target:
                url = args.target.replace("FUZZ", word_combinations[0])
            elif args.data:
                url = args.target
                # Replace placeholders in data
                data = args.data
                for i, word in enumerate(word_combinations):
                    placeholder = f"wordlist_{i+1}"
                    data = data.replace(placeholder, word)
            else:
                url = f"{args.target.rstrip('/')}/{word_combinations[0]}"
            payload_display = " | ".join(word_combinations)
        else:
            # Single wordlist
            word = item
            if not word:
                queue.task_done()
                continue
                
            if "FUZZ" in args.target:
                url = args.target.replace("FUZZ", word)
            elif args.data and "FUZZ" in args.data:
                url = args.target
                data = args.data.replace("FUZZ", word)
            else:
                url = f"{args.target.rstrip('/')}/{word}"
            payload_display = word

        headers = {}
        if args.headers:
            for h in args.headers.split(","):
                if ":" in h:
                    k, v = h.split(":", 1)
                    headers[k.strip()] = v.strip()

        try:
            # Prepare request data
            if args.data:
                if isinstance(item, tuple):
                    # For multiple wordlists, data was already processed above
                    pass
                else:
                    # For single wordlist
                    data = args.data.replace("FUZZ", word)
                
                # Send http or https requests
                res = requests.request(args.method, url, headers=headers, data=data, timeout=5)
            else:
                res = requests.request(args.method, url, headers=headers, timeout=5)

            status = res.status_code
            # Updated color coding - 200 responses now in YELLOW
            color = (
                Fore.YELLOW if status == 200 else  # Changed from GREEN to YELLOW for 200
                Fore.GREEN if status in (201, 202, 204) else  # Other success codes in green
                Fore.YELLOW if status in (301, 302) else
                Fore.RED if status == 403 else
                Fore.MAGENTA if status >= 500 else
                Fore.WHITE
            )

            if status != 404 or args.verbose:
                # Only display status and URL, no response content
                line = f"[{status}] {url}"
                
                # If verbose mode is enabled, show the payload used
                if args.verbose:
                    line = f"[{status}] {url} [Payload: {payload_display}]"
                
                print(color + line)
                
                # Only add to results if not 404 or if verbose mode shows all
                if status != 404:
                    results.append({
                        "payload": payload_display, 
                        "url": url, 
                        "status": status,
                        "data_sent": data if args.data else None
                    })

        except Exception as e:
            print(Fore.CYAN + f"[!] Error on '{payload_display}': {e}")
        finally:
            queue.task_done()

        if args.delay:
            time.sleep(args.delay)

def main():
    # Display ASCII banner
    display_banner()
    
    # This is a tool description shows how tool works and take arguments on command line interface
    parser = argparse.ArgumentParser(description="API FUZZER - Discover Hidden Endpoints")
    parser.add_argument("-u", "--url", help="Target URL/FUZZ (FUZZ will be replaced by wordlist)", required=True, dest="target")
    parser.add_argument("-w", "--wordlist", help="Wordlist File(s). For multiple wordlists, use comma-separated: user.txt,pass.txt", required=False)
    parser.add_argument("-H", "--headers", help="Custom headers (e.g: 'Authorization: Bearer TOKEN, User-Agent: Test')", required=False)
    parser.add_argument("-X", "--method", help="HTTP method", default="GET", choices=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
    parser.add_argument("-d", "--data", help="POST/PUT data with placeholders: {username: wordlist_1, password: wordlist_2}", required=False)
    parser.add_argument("-t", "--threads", help="Number of threads (default=10)", type=int, default=10)
    parser.add_argument("--delay", help="Delay between requests (seconds)", type=float, default=0)
    parser.add_argument("-o", "--output", help="Save results to JSON file", required=False)
    parser.add_argument("-v", "--verbose", help="Show all requests including 404s with payload information", action="store_true")
    args = parser.parse_args()

    # Validate that either wordlist file or stdin is provided
    if not args.wordlist and sys.stdin.isatty():
        print(Fore.RED + "[-] Error: Either provide a wordlist file with -w or pipe input through stdin")
        sys.exit(1)

    # In this stage wordlist is read and put every word it into a Queue
    results = []
    queue = Queue()
    
    if args.wordlist:
        # Check if multiple wordlists are provided
        if ',' in args.wordlist:
            print(Fore.YELLOW + "[+] Multiple wordlists detected, generating combinations...")
            combinations = load_wordlists(args.wordlist)
            
            # Validate data placeholders
            if args.data:
                expected_placeholders = len(args.wordlist.split(','))
                actual_placeholders = sum(1 for i in range(1, expected_placeholders + 1) if f"wordlist_{i}" in args.data)
                if actual_placeholders != expected_placeholders:
                    print(Fore.RED + f"[-] Error: Data expects {expected_placeholders} placeholders (wordlist_1, wordlist_2, etc.) but found {actual_placeholders}")
                    sys.exit(1)
            
            for combo in combinations:
                queue.put(combo)
            print(Fore.GREEN + f"[+] Generated {len(combinations)} combinations")
        else:
            # Single wordlist
            try:
                with open(args.wordlist, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        queue.put(line.strip())
                print(Fore.GREEN + f"[+] Loaded wordlist: {args.wordlist}")
            except FileNotFoundError:
                print(Fore.RED + f"[-] Error: Wordlist file '{args.wordlist}' not found")
                sys.exit(1)
            except Exception as e:
                print(Fore.RED + f"[-] Error reading wordlist: {e}")
                sys.exit(1)
    else:
        print(Fore.YELLOW + "[+] Reading wordlist from stdin...")
        for line in sys.stdin:
            queue.put(line.strip())

    print(Fore.CYAN + f"[+] Target URL: {args.target}")
    print(Fore.CYAN + f"[+] HTTP Method: {args.method}")
    if args.data:
        print(Fore.CYAN + f"[+] Request Data: {args.data}")
    print(Fore.CYAN + f"[+] Threads: {args.threads}")
    print(Fore.CYAN + f"[+] Total payloads: {queue.qsize()}")
    print(Fore.CYAN + f"[+] Verbose mode: {'Enabled' if args.verbose else 'Disabled'}")
    print(Fore.CYAN + "[+] Starting fuzzing...\n")

    # Start the threads and call the function fuzz_worker
    threads = []
    for _ in range(args.threads):
        t = threading.Thread(target=fuzz_worker, args=(queue, args, results))
        t.daemon = True
        t.start()
        threads.append(t)

    # Wait for all threads to complete
    queue.join()
    
    print(Fore.GREEN + f"\n[+] Fuzzing completed! Found {len(results)} interesting results")

    # In this stage the result of output is store in Json file given by user
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(Fore.CYAN + f"[+] Results saved to: {args.output}")

# main function the program start with this function
if __name__ == "__main__":
    main()
