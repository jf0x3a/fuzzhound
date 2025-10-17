import argparse
import sys
import requests
import time
import json
import threading
from queue import Queue
from colorama import Fore, Style, init
from pyfiglet import Figlet

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

def fuzz_worker(queue, args, results):
    # Use while loop to read word from Queue
    while not queue.empty():
        word = queue.get().strip()
        # If there is no word then continue
        if not word:
            continue
        # Replace FUZZ word enter in target url with wordlist
        if "FUZZ" in args.target:
            url = args.target.replace("FUZZ", word)
        elif args.data and "FUZZ" in args.data:
            url = args.target
        else:
            url = f"{args.target.rstrip('/')}/{word}"

        headers = {}
        if args.headers:
            for h in args.headers.split(","):
                if ":" in h:
                    k, v = h.split(":", 1)
                    headers[k.strip()] = v.strip()

        try:
            if args.data:
                data = args.data.replace("FUZZ", word)
                # Send http or https requests
                res = requests.request(args.method, url, headers=headers, data=data, timeout=5)
            else:
                res = requests.request(args.method, url, headers=headers, timeout=5)

            status = res.status_code
            color = (
                Fore.GREEN if status == 200 else
                Fore.YELLOW if status in (301, 302) else
                Fore.RED if status == 403 else
                Fore.MAGENTA if status >= 500 else
                Fore.WHITE
            )

            if status != 404:
                try:
                    response_data = res.json()
                except Exception:
                    response_data = res.text[:100]
                line = f"[{status}] {url} -> {response_data}"
                print(color + line + Style.RESET_ALL)
                results.append({"payload": word, "url": url, "status": status, "response": response_data})

        except Exception as e:
            print(Fore.CYAN + f"[!] Error on '{word}': {e}")
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
    parser.add_argument("-w", "--wordlist", help="Wordlist File", required=False)
    parser.add_argument("-H", "--headers", help="Custom headers (e.g: 'Authorization: Bearer TOKEN, User-Agent: Test')", required=False)
    parser.add_argument("-X", "--method", help="HTTP method", default="GET", choices=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
    parser.add_argument("-d", "--data", help="POST/PUT data", required=False)
    parser.add_argument("-t", "--threads", help="Number of threads (default=10)", type=int, default=10)
    parser.add_argument("--delay", help="Delay between requests (seconds)", type=float, default=0)
    parser.add_argument("-o", "--output", help="Save results to JSON file", required=False)
    args = parser.parse_args()

    # Validate that either wordlist file or stdin is provided
    if not args.wordlist and sys.stdin.isatty():
        print(Fore.RED + "[-] Error: Either provide a wordlist file with -w or pipe input through stdin")
        sys.exit(1)

    # In this stage wordlist is read and put every word it into a Queue
    results = []
    queue = Queue()
    
    if args.wordlist:
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
    print(Fore.CYAN + f"[+] Threads: {args.threads}")
    print(Fore.CYAN + f"[+] Total payloads: {queue.qsize()}")
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
