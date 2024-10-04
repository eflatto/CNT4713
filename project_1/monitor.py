import sys
import socket
import ssl
from urllib.parse import urlparse, urljoin
import re

def parse_url(url):
    parsed_url = urlparse(url)
    
    protocol = parsed_url.scheme
    host = parsed_url.netloc
    path = parsed_url.path if parsed_url.path else '/'
    port = 80 if protocol == 'http' else 443
    
    return protocol, host, path, port

def parse_http_response(response):
    try:
        headers, body = response.split(b'\r\n\r\n', 1)
        status_line = headers.split(b'\r\n')[0].decode('utf-8')
        parts = status_line.split(' ', 2)
        if len(parts) >= 3:
            status_code = parts[1]
            status_phrase = ' '.join(parts[2:])
            return status_code, status_phrase, headers, body
        else:
            return None, "Unknown Status", headers, body
    except Exception:
        return None, "Unable to parse response", b'', b''

def get_redirect_url(headers, url):
    header_lines = headers.split(b'\r\n')
    for line in header_lines:
        if line.lower().startswith(b'location:'):
            redirect_url = line.split(b':', 1)[1].strip().decode('utf-8')
            return urljoin(url, redirect_url)
    return None

def extract_image_urls(html_content, url):
    img_pattern = re.compile(r'<img[^>]+src=["\'](.*?)["\']', re.IGNORECASE)
    img_urls = img_pattern.findall(html_content.decode('utf-8', errors='ignore'))
    return [urljoin(url, img_url) for img_url in img_urls]

def check_url(url, is_redirect=False):
    protocol, host, path, port = parse_url(url)
    
    if not is_redirect:
        print(f"URL: {url}") 
    
    sock = None
    try:
        # create client socket, connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        if protocol == 'https':
            context = ssl.create_default_context()
            sock = context.wrap_socket(sock, server_hostname=host)

        # Construct HTTP request message
        request = f'GET {path} HTTP/1.1\r\n'
        request += f'Host: {host}\r\n'
        request += 'Connection: close\r\n'
        request += 'User-agent: Mozilla/5.0\r\n'
        request += 'Accept-Language: en-US\r\n'
        request += '\r\n'

        # Send HTTP request
        sock.sendall(request.encode('utf-8'))

        # Receive HTTP response
        response = b''
        while True:
            data = sock.recv(4096)
            if not data:
                break
            response += data
        
        status_code, status_phrase, headers, body = parse_http_response(response)
        print(f"Status: {status_code} {status_phrase}")

        if status_code == '200':
            img_urls = extract_image_urls(body, url)
            for img_url in img_urls:
                print(f"Referenced URL: {img_url}")
                check_url(img_url, is_redirect=True)

        elif status_code in ('301', '302'):
            redirect_url = get_redirect_url(headers, url)
            if redirect_url:
                print(f"Redirected URL: {redirect_url}")
                check_url(redirect_url, is_redirect=True)

    except Exception as e:
        print("Status: Network Error")
    finally:
        if sock:
            sock.close()

def main():
    if len(sys.argv) != 2:
        print('Usage: python monitor.py urls_file')
        sys.exit(1)

    urls_file = sys.argv[1] # urls.txt

    try:
        with open(urls_file, 'r') as file:
            for line in file:
                url = line.strip()
                check_url(url, is_redirect=False)
                print()
    except FileNotFoundError:
        print(f"Error: File '{urls_file}' not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()