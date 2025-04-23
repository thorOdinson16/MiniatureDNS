import socket
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading

class DNSClientGUI:
    def __init__(self, root):
        self.root = root
        root.title("DNS Lookup Tool")
        self.server_address = ('<Server IP Address>', 5354)  # Change to your server's IP if needed
        
        # Input Section
        input_frame = ttk.Frame(root, padding=10)
        input_frame.pack(fill='x')
        
        ttk.Label(input_frame, text="Domain:").pack(side='left')
        self.domain_entry = ttk.Entry(input_frame, width=30)
        self.domain_entry.pack(side='left', padx=5)
        self.domain_entry.bind('<Return>', lambda e: self.start_lookup())
        
        self.lookup_btn = ttk.Button(input_frame, text="Lookup", command=self.start_lookup)
        self.lookup_btn.pack(side='left')
        
        # Results Display
        self.results_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=15)
        self.results_area.pack(padx=10, pady=5, fill='both', expand=True)
        
        # Status Bar
        self.status = ttk.Label(root, text="Ready", relief=tk.SUNKEN)
        self.status.pack(side=tk.BOTTOM, fill='x')

    def start_lookup(self):
        domain = self.domain_entry.get().strip()
        if not domain:
            return
        
        self.lookup_btn.config(state='disabled')
        self.status.config(text="Querying...")
        self.results_area.delete('1.0', tk.END)
        
        threading.Thread(target=self.perform_lookup, args=(domain,), daemon=True).start()

    def perform_lookup(self, domain):
        try:
            # Connect to our DNS server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(self.server_address)
                s.sendall(domain.encode())
                response = s.recv(4096).decode()
            
            records = response.split('\n') if response else []
            self.show_results(records)
            self.status.config(text="Query completed")
            
        except Exception as e:
            self.status.config(text=f"Error: {str(e)}")
        finally:
            self.lookup_btn.config(state='normal')

    def show_results(self, records):
        self.results_area.tag_configure('header', foreground='blue', font=('TkDefaultFont', 10, 'bold'))
        self.results_area.tag_configure('record', foreground='black')
        
        if not records:
            self.results_area.insert(tk.END, "No records found\n", 'header')
            return
            
        self.results_area.insert(tk.END, f"DNS Records for {self.domain_entry.get()}\n", 'header')
        for record in records:
            self.results_area.insert(tk.END, f"• {record}\n", 'record')

if __name__ == "__main__":
    root = tk.Tk()
    app = DNSClientGUI(root)
    root.mainloop()