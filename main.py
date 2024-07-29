import os
import threading
import sqlite3
import numpy as np
import time
from web3 import Web3
from concurrent.futures import ThreadPoolExecutor

# Initialize Web3
web3 = Web3()

# SQLite setup
db_file = 'eth_addresses.db'

def initialize_db():
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS addresses (
                private_key TEXT PRIMARY KEY,
                eth_address TEXT UNIQUE
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_eth_address ON addresses (eth_address)
        ''')
        conn.commit()

def save_to_db(private_key, eth_address):
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO addresses (private_key, eth_address) VALUES (?, ?)
        ''', (private_key, eth_address))
        conn.commit()

def generate_eth_address(private_key):
    account = web3.eth.account.from_key(private_key)
    return account.address

def process_private_key_range(start_key, end_key):
    num_keys = end_key - start_key + 1
    private_keys = [hex(start_key + i)[2:].zfill(64) for i in range(num_keys)]
    
    with ThreadPoolExecutor() as executor:
        futures = []
        for private_key in private_keys:
            future = executor.submit(generate_eth_address, private_key)
            futures.append((private_key, future))
        
        for private_key, future in futures:
            eth_address = future.result()
            executor.submit(save_to_db, private_key, eth_address)

def search_by_wallet_address(eth_address):
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT private_key FROM addresses WHERE eth_address = ?
        ''', (eth_address,))
        result = cursor.fetchone()
        if result:
            return result[0]  # Return the private key
        else:
            return None

if __name__ == '__main__':
    initialize_db()
    
    # Get input and record start time
    start_key = int(input("Enter start private key (in hex, without 0x): "), 16)
    end_key = int(input("Enter end private key (in hex, without 0x): "), 16)
    
    start_time = time.time()  # Record start time
    
    # Number of threads for parallel processing
    num_threads = os.cpu_count()
    key_range = (end_key - start_key + 1) // num_threads

    threads = []
    for i in range(num_threads):
        start = start_key + i * key_range
        end = start + key_range - 1 if i != num_threads - 1 else end_key
        t = threading.Thread(target=process_private_key_range, args=(start, end))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    
    end_time = time.time()  # Record end time
    
    # Print elapsed time
    elapsed_time = end_time - start_time
    print(f"Processing time: {elapsed_time:.2f} seconds")

    # Example search
    address_to_search = input("Enter Ethereum address to search: ")
    private_key = search_by_wallet_address(address_to_search)
    if private_key:
        print(f"Private key for address {address_to_search}: {private_key}")
    else:
        print("Address not found.")
        
