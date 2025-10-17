import argparse
import sys
import requests
import time
import json
import threading
import re
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

def should_display_response(args, status, content_length, response_text):
    """Check if response should be displayed based on filters"""
    if args.filter_status:
        status_codes = []
        for status_range in args.filter_status.split(','):
            if '-' in status_range:
                start, end = map(int, status_range.split('-'))
                status_codes.extend(range(start, end + 1))
            else:
                status_codes.append(int(status_range))
        if status not in status_codes:
            return False
    
    if args.filter_size:
        size_ranges = args.filter_size.split(',')
        size_match = False
        for size_range in size_ranges:
            if '-' in size_range:
                min_size, max_size = map(int, size_range.split('-'))
                if min_size <= content_length <= max_size:
                    size_match = True
                    break
            elif size_range.startswith('>'):
                min_size = int(size_range[1:])
                if content_length > min_size:
                    size_match = True
                    break
            elif size_range.startswith('<'):
                max_size = int(size_range[1:])
                if content_length < max_size:
                    size_match = True
                    break
            else:
                exact_size = int(size_range)
                if content_length == exact_size:
                    size_match = True
                    break
        if not size_match:
            return False
    
    if args.filter_content:
        patterns = args.filter_content.split(',')
        for pattern in patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                return True
        return False
    
    if args.exclude_content:
        patterns = args.exclude_content.split(',')
        for pattern in patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                return False
    
    return True

def fuzz_worker(queue, args, results):
    # Use while loop to read word from Queue
    while not queue.empty():
        item = queue.get()
        
        if isinstance(item, tuple):
            word_combinations = item
            if "FUZZ" in args.target:
                url = args.target.replace("FUZZ", word_combinations[0])
            elif args.data:
                url = args.target
                data = args.data
                for i, word in enumerate(word_combinations):
                    placeholder = f"wordlist_{i+1}"
                    data = data.replace(placeholder, word)
            else:
                url = f"{args.target.rstrip('/')}/{word_combinations[0]}"
            payload_display = " | ".join(word_combinations)
        else:
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
            if args.data:
                if isinstance(item, tuple):
                    pass
                else:
                    data = args.data.replace("FUZZ", word)
                
                res = requests.request(args.method, url, headers=headers, data=data, timeout=5)
            else:
                res = requests.request(args.method, url, headers=headers, timeout=5)

            status = res.status_code
            content_length = len(res.content)
            response_text = res.text
            

            should_display = should_display_response(args, status, content_length, response_text)
            

            color = (
                Fore.YELLOW if status == 200 else
                Fore.GREEN if status in (201, 202, 204) else
                Fore.YELLOW if status in (301, 302) else
                Fore.RED if status == 403 else
                Fore.MAGENTA if status >= 500 else
                Fore.WHITE
            )

            if (status != 404 or args.verbose) and should_display:
                line = f"[{status}] {url} [Size: {content_length}]"
                
                if args.verbose:
                    line = f"[{status}] {url} [Size: {content_length}] [Payload: {payload_display}]"
                
                print(color + line)

                if status != 404:
                    results.append({
                        "payload": payload_display, 
                        "url": url, 
                        "status": status,
                        "size": content_length,
                        "data_sent": data if args.data else None
                    })

        except Exception as e:
            if not args.quiet_errors:
                print(Fore.CYAN + f"[!] Error on '{payload_display}': {e}")
        finally:
            queue.task_done()

        if args.delay:
            time.sleep(args.delay)

def main():
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
    
    # Filtering arguments
    parser.add_argument("--filter-status", help="Filter by status code(s). Examples: 200, 200-299, 404,500", required=False)
    parser.add_argument("--filter-size", help="Filter by response size. Examples: 100-500, >1000, <100, 2048", required=False)
    parser.add_argument("--filter-content", help="Filter by content pattern (regex). Examples: 'success|logged', 'error'", required=False)
    parser.add_argument("--exclude-content", help="Exclude by content pattern (regex). Examples: 'not found', 'error'", required=False)
    parser.add_argument("--quiet-errors", help="Don't display error messages", action="store_true")
    
    args = parser.parse_args()


    if not args.wordlist and sys.stdin.isatty():
        print(Fore.RED + "[-] Error: Either provide a wordlist file with -w or pipe input through stdin")
        sys.exit(1)


    results = []
    queue = Queue()
    
    if args.wordlist:
        if ',' in args.wordlist:
            print(Fore.YELLOW + "[+] Multiple wordlists detected, generating combinations...")
            combinations = load_wordlists(args.wordlist)
            
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
    
    # Display filter information
    if args.filter_status:
        print(Fore.CYAN + f"[+] Status filter: {args.filter_status}")
    if args.filter_size:
        print(Fore.CYAN + f"[+] Size filter: {args.filter_size}")
    if args.filter_content:
        print(Fore.CYAN + f"[+] Content filter: {args.filter_content}")
    if args.exclude_content:
        print(Fore.CYAN + f"[+] Exclude content: {args.exclude_content}")
    
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


    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(Fore.CYAN + f"[+] Results saved to: {args.output}")

if __name__ == "__main__":
    main()
