## 👨 Author
**John Fiel Brosas**  
- 🌐 GitHub: [jf0x3a](https://github.com/jf0x3a)  
- 🛡️ HackTheBox: [physx](https://app.hackthebox.com/profile/2686492)
- 💼 Cybersecurity Enthusiant
- 🛡️ Penetration Tester

"This project represents my ongoing journey in ethical hacking and cybersecurity, combining practical coding skills with security testing methodologies."


## 🚀 What is FuzzHound?
A **high-performance, multithreaded API Fuzzer** built in Python 🐍 designed to discover hidden endpoints and API routes through intelligent fuzzing techniques. Perfect for penetration testers, bug bounty hunters, and security researchers!

## 🎯 How It Works
The tool automatically replaces the FUZZ keyword in your target URL with words from a specified wordlist, systematically testing for valid endpoints that might be hidden from normal view.

---

✨ Features
- 🎨 Core Capabilities
- 🔍 **Smart Fuzzing** → Replace FUZZ keyword in URLs, query parameters, or request body
- ⚡ **Multithreading** → Lightning-fast parallel requests with configurable thread count
- 🛡️ **Multiple HTTP Methods** → Support for GET, POST, PUT, DELETE, PATCH, and more
- 📊 **Intelligent Filtering** → Filter responses by status codes, size, or content

🔧 Advanced Options
- 📋 **Custom Headers Support** → Add authentication tokens, custom user agents, etc.
- ⏱️ **Request Throttling** → Control request rate with precise delay timing
- 💾 **Flexible Output** → Save results in JSON format for further analysis
- 🎨 **Visual Feedback** → Color-coded terminal output for easy result interpretation
- 📏 **Response Analysis** → Filter by response size, status codes, or content patterns


## ⚡ Installation

### Clone the repo
```bash
git clone https://github.com/jf0x3a/fuzzhound.git
cd fuzzhound
```
1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```
2.Install Dependencies
  ```bash
  pip install -r requirements.txt
  ```
3.Run the Project
  ```bash
  python3 fuzzhound.py -u http://target.com/FUZZ -w text.txt
```
## ⚡ Usage

#### 🔐 Fuzzing with Authentication
  ```bash
  python3 fuzzhound.py -u http://target.com/FUZZ -w wordlist.txt
```

#### 📝 POST Request Fuzzing
  ```bash
  python3 fuzzhound.py -u https://api.target.com/v1/FUZZ -w common_paths.txt -H "Authorization: Bearer your_token_here" -t 10
```

#### ⚡ High-Speed Fuzzing
  ```bash
  python3 fuzzhound.py -u http://target.com/FUZZ -w big_wordlist.txt -t 20 --delay 0.1
```

#### 🗂️ Directory Bruteforcing
  ```bash
  python3 fuzzhound.py -u "http://target.com/FUZZ" \
  -w directory-list-2.3-medium.txt \
  -t 10 \
  -o discovered_directories.json
```

#### ⏱️  Rate-Limited Testing
  ```bash
  python3 fuzzhound.py -u "http://target.com/FUZZ" \
  -w common.txt \
  -t 5 \
  -o careful_scan.json
```

#### 🎯  Fuzzing Password Field (JSON)
  ```bash
  python3 fuzzhound.py -u "http://target.com/login" -X POST \
  -d '{"username":"admin","password":"FUZZ"}' \
  -w passwords.txt \
  -H "Content-Type: application/json"
```

#### 🎯  Fuzzing Password Field (Form-Encoded POST)
  ```bash
  python3 fuzzhound.py -u "http://target.com/login" -X POST \
  -d '{"username":"admin","password":"FUZZ"}' \
  -w passwords.txt \
  -H "Content-Type: application/x-www-form-urlencoded"
```

#### 🎯  Fuzzing Multiple Fields
  ```bash
  python3 fuzzhound.py -u "http://target.com/login" -X POST \
  -d '{"username":"wordlist_1","password":"wordlist_2"}' \
  -w usernames.txt,passwords.txt \
  -H "Content-Type: application/json" \
  -v
```

#### 🎯  Find large responses (potential data leaks)
  ```bash
  python3 fuzzhound.py -u "http://target.com/api/FUZZ" \
  -w wordlists.txt \
  --filter-size ">5000"
```

#### 🎯  Find specific error patterns
  ```bash
  python3 fuzzhound.py -u "http://target.com/api/FUZZ" \
  -w wordlists.txt \
  --filter-status 500 --filter-content "sql|database"
```



Built with ❤️ by John Fiel Brosas as part of the cybersecurity learning journey

    

