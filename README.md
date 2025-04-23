# 🧠 DNS Lookup System with Caching

This project implements a custom DNS resolver system using Python. It includes a DNS server that queries real DNS records, 
caches them for future use, and a GUI-based client for end users to make domain queries.

## 📂 Project Structure

- `dnsserver_final.py`: Python-based multithreaded DNS server with caching support.
- `dnsclient_final.py`: A Tkinter-based desktop client for DNS lookups.
- `dns_cache.csv`: Auto-generated cache file storing previously fetched DNS records.

## 🚀 Features

- Resolves various DNS record types (A, AAAA, MX, CNAME, NS, TXT).
- Implements local DNS caching with TTL (Time-To-Live).
- GUI client with real-time lookup and output display.
- Communicates over TCP sockets between client and server.
- Multi-threaded server to handle concurrent queries.

## Update < Server IP Address > in dnsserver_final.py and dnsclient_final.py to the server's IP


