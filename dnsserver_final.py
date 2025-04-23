import socket
import csv
import os
import struct
import random
from datetime import datetime, timedelta
import threading

CACHE_FILE = 'dns_cache.csv'
GOOGLE_DNS = ('8.8.8.8', 53)

def build_dns_query(domain_name, query_type):
    transaction_id = random.randint(0, 65535)
    flags = 0x0100  # standard query with recursion desired
    questions = 1
    answer_rrs = authority_rrs = additional_rrs = 0

    dns_header = struct.pack(">HHHHHH", transaction_id, flags, questions, answer_rrs, authority_rrs, additional_rrs)

    # Encode domain name
    query_name = b''
    for label in domain_name.split('.'):
        query_name += bytes([len(label)]) + label.encode()
    query_name += b'\x00'
    
    dns_question = struct.pack(">HH", query_type, 1)  # 1 = IN class

    return dns_header + query_name + dns_question

def send_dns_query(domain_name, server_address, record_type):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    query = build_dns_query(domain_name, record_type)
    sock.sendto(query, server_address)
    response, _ = sock.recvfrom(512)
    sock.close()
    return response

def parse_name(response, offset):
    labels = []
    jumped = False
    original_offset = offset
    
    while True:
        length = response[offset]
        if length == 0:
            offset += 1
            break
        if (length & 0xC0) == 0xC0:  # Pointer
            pointer = struct.unpack(">H", response[offset:offset+2])[0] & 0x3FFF
            if not jumped:
                jumped = True
                original_offset = offset + 2
            offset = pointer
        else:
            offset += 1
            labels.append(response[offset:offset + length].decode())
            offset += length
    
    return '.'.join(labels), original_offset if jumped else offset

def parse_dns_response(response):
    try:
        header_size = 12
        qdcount = struct.unpack(">H", response[4:6])[0]
        ancount = struct.unpack(">H", response[6:8])[0]
        nscount = struct.unpack(">H", response[8:10])[0]
        arcount = struct.unpack(">H", response[10:12])[0]
        
        offset = header_size

        # Skip question section
        for _ in range(qdcount):
            _, offset = parse_name(response, offset)
            offset += 4  # QTYPE + QCLASS

        results = []
        
        # Process answer section
        for _ in range(ancount):
            name, offset = parse_name(response, offset)
            rtype, rclass, ttl, rdlength = struct.unpack(">HHIH", response[offset:offset+10])
            offset += 10
            rdata_offset = offset
            
            if rtype == 1 and rdlength == 4:  # A
                ip = '.'.join(map(str, response[rdata_offset:rdata_offset+4]))
                results.append(f"A Record: {ip}")
            elif rtype == 28 and rdlength == 16:  # AAAA
                ipv6_parts = []
                for i in range(0, 16, 2):
                    ipv6_parts.append(f"{response[rdata_offset+i]:02x}{response[rdata_offset+i+1]:02x}")
                ipv6 = ':'.join(ipv6_parts)
                results.append(f"AAAA Record: {ipv6}")
            elif rtype == 5:  # CNAME
                cname, _ = parse_name(response, rdata_offset)
                results.append(f"CNAME Record: {cname}")
            elif rtype == 2:  # NS
                ns, _ = parse_name(response, rdata_offset)
                results.append(f"NS Record: {ns}")
            elif rtype == 15:  # MX
                preference = struct.unpack(">H", response[rdata_offset:rdata_offset+2])[0]
                exchange, _ = parse_name(response, rdata_offset + 2)
                results.append(f"MX Record: {exchange} (Preference: {preference})")
            elif rtype == 16:  # TXT
                txt_offset = rdata_offset
                txt_records = []
                while txt_offset < rdata_offset + rdlength:
                    txt_len = response[txt_offset]
                    txt_offset += 1
                    txt = response[txt_offset:txt_offset + txt_len].decode(errors='ignore')
                    txt_records.append(txt)
                    txt_offset += txt_len
                results.append(f'TXT Record: "{" ".join(txt_records)}"')
            else:
                results.append(f"Unhandled Record Type {rtype}")
                
            offset = rdata_offset + rdlength
            
        return results
    except Exception as e:
        return [f"Error parsing response: {e}"]

def check_cache(domain):
    if not os.path.exists(CACHE_FILE):
        return None
    
    with open(CACHE_FILE, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0] == domain:
                # Check if cache entry is expired (TTL in seconds)
                cache_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                ttl = int(row[2])
                if datetime.now() - cache_time < timedelta(seconds=ttl):
                    return row[3:]  # Return all records
                break
    return None

def update_cache(domain, records, ttl=3600):
    # Create file if doesn't exist
    file_exists = os.path.exists(CACHE_FILE)
    
    with open(CACHE_FILE, 'a' if file_exists else 'w') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Domain', 'Timestamp', 'TTL', 'Records'])
        
        # Combine all records into one string for CSV storage
        record_str = '\n'.join(records)
        writer.writerow([domain, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ttl, record_str])

def handle_client(conn, addr):
    try:
        domain = conn.recv(1024).decode().strip()
        print(f"Received query for: {domain}")
        
        # Check cache first
        cached_records = check_cache(domain)
        if cached_records:
            print("Serving from cache")
            conn.sendall('\n'.join(cached_records).encode())
            return
            
        # Not in cache, query Google DNS
        print("Querying Google DNS")
        record_types = {'A': 1, 'AAAA': 28, 'MX': 15, 'CNAME': 5, 'NS': 2, 'TXT': 16}
        all_records = []
        
        for rt_name, rt_code in record_types.items():
            try:
                response = send_dns_query(domain, GOOGLE_DNS, rt_code)
                records = parse_dns_response(response)
                all_records.extend(records)
            except Exception as e:
                all_records.append(f"{rt_name} Record: Error querying ({e})")
        
        # Store in cache
        if all_records:
            update_cache(domain, all_records)
        
        # Send response to client
        conn.sendall('\n'.join(all_records).encode())
        
    except Exception as e:
        print(f"Error handling client: {e}")
        conn.sendall(f"Error: {str(e)}".encode())
    finally:
        conn.close()

def start_server():
    # Initialize cache file if it doesn't exist
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['Domain', 'Timestamp', 'TTL', 'Records'])
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('<Server IP Address>', 5354))
        s.listen()
        print("DNS Server running on port 5354...")
        
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()