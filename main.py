import requests
from web3 import Web3
from typing import List, Dict
from decimal import Decimal
import time
from datetime import datetime

# Constants
WETH_ADDRESS_ETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
WETH_ADDRESS_BASE = "0x4200000000000000000000000000000000000006"
ETH_DECIMALS = 18
ETHERSCAN_API_KEY = "EZPXB4V2CK5671P3PUW7M89YJQI5TRRW4N"
BASESCAN_API_KEY = "DC3X2P7WBSZUCZAPVTMR31N394IF1FGJ6K"
RATE_LIMIT_DELAY = 0.25
MIN_TOTAL_BALANCE = Decimal('0.0002')  # Minimum total balance threshold

# Initialize Web3 providers
eth_w3 = Web3(Web3.HTTPProvider('https://ethereum.publicnode.com'))
base_w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

def get_eth_balance(address: str, w3: Web3) -> Decimal:
    """Get ETH balance for an address"""
    time.sleep(RATE_LIMIT_DELAY)
    balance_wei = w3.eth.get_balance(address)
    return Decimal(balance_wei) / Decimal(10 ** ETH_DECIMALS)

def get_weth_balance(address: str, chain: str) -> Decimal:
    """Get WETH balance for an address on specified chain"""
    time.sleep(RATE_LIMIT_DELAY)
    weth_address = WETH_ADDRESS_ETH if chain == 'ethereum' else WETH_ADDRESS_BASE
    api_key = ETHERSCAN_API_KEY if chain == 'ethereum' else BASESCAN_API_KEY
    base_url = 'https://api.etherscan.io/api' if chain == 'ethereum' else 'https://api.basescan.org/api'
    
    params = {
        'module': 'account',
        'action': 'tokenbalance',
        'contractaddress': weth_address,
        'address': address,
        'tag': 'latest',
        'apikey': api_key
    }
    
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == '1':
            balance = Decimal(data['result']) / Decimal(10 ** ETH_DECIMALS)
            return balance
    return Decimal(0)

def calculate_total_balance(address_info: Dict) -> Decimal:
    """Calculate total balance across all chains and tokens"""
    total = Decimal(0)
    
    # Initialize all balances to 0
    eth_balance = Decimal(0)
    eth_weth = Decimal(0)
    base_balance = Decimal(0)
    base_weth = Decimal(0)
    
    # Get Ethereum balances if available
    if address_info['ethereum'] != 'Error':
        eth_balance = address_info['ethereum']['eth']
        eth_weth = address_info['ethereum']['weth']
    
    # Get Base balances if available
    if address_info['base'] != 'Error':
        base_balance = address_info['base']['eth']
        base_weth = address_info['base']['weth']
    
    # Calculate total
    total = eth_balance + eth_weth + base_balance + base_weth
    return total

def generate_balance_report(addresses: List[str]) -> Dict:
    """Generate a comprehensive balance report for unique addresses"""
    # Remove duplicates while preserving order
    unique_addresses = list(dict.fromkeys(addresses))
    
    report = {
        'ethereum': {
            'total_eth': Decimal(0),
            'total_weth': Decimal(0)
        },
        'base': {
            'total_eth': Decimal(0),
            'total_weth': Decimal(0)
        },
        'address_details': []
    }
    
    total_addresses = len(unique_addresses)
    start_time = time.time()
    filtered_addresses = 0
    
    for idx, address in enumerate(unique_addresses, 1):
        elapsed_time = time.time() - start_time
        avg_time_per_address = elapsed_time / idx
        remaining_addresses = total_addresses - idx
        estimated_remaining_time = avg_time_per_address * remaining_addresses
        
        print(f"\nProcessing address {idx}/{total_addresses} ({(idx/total_addresses)*100:.1f}%)")
        print(f"Estimated time remaining: {estimated_remaining_time/60:.1f} minutes")
        print(f"Address: {address}")
        
        address_info = {'address': address}
        
        # Ethereum balances
        try:
            eth_balance = get_eth_balance(address, eth_w3)
            eth_weth = get_weth_balance(address, 'ethereum')
            
            address_info['ethereum'] = {
                'eth': eth_balance,
                'weth': eth_weth
            }
            print(f"  ETH (Ethereum): {eth_balance:.6f}")
            print(f"  WETH (Ethereum): {eth_weth:.6f}")
            
        except Exception as e:
            print(f"  Error fetching Ethereum balances: {str(e)}")
            address_info['ethereum'] = 'Error'
        
        # Base balances
        try:
            base_balance = get_eth_balance(address, base_w3)
            base_weth = get_weth_balance(address, 'base')
            
            address_info['base'] = {
                'eth': base_balance,
                'weth': base_weth
            }
            print(f"  ETH (Base): {base_balance:.6f}")
            print(f"  WETH (Base): {base_weth:.6f}")
            
        except Exception as e:
            print(f"  Error fetching Base balances: {str(e)}")
            address_info['base'] = 'Error'
        
        # Calculate total balance and filter if below threshold
        total_balance = calculate_total_balance(address_info)
        address_info['total_balance'] = total_balance
        
        if total_balance >= MIN_TOTAL_BALANCE:
            # Add to totals only if above threshold
            if address_info['ethereum'] != 'Error':
                report['ethereum']['total_eth'] += eth_balance
                report['ethereum']['total_weth'] += eth_weth
            if address_info['base'] != 'Error':
                report['base']['total_eth'] += base_balance
                report['base']['total_weth'] += base_weth
            
            report['address_details'].append(address_info)
        else:
            filtered_addresses += 1
            print(f"  Skipped: Total balance ({total_balance:.6f}) below threshold")
    
    # Sort addresses by total balance
    report['address_details'].sort(key=lambda x: x['total_balance'], reverse=True)
    
    # Add wallet numbers after sorting
    for idx, addr_info in enumerate(report['address_details'], 1):
        addr_info['wallet_number'] = idx
    
    report['execution_time'] = time.time() - start_time
    report['duplicate_addresses_removed'] = len(addresses) - len(unique_addresses)
    report['filtered_addresses'] = filtered_addresses
    return report

def save_report(report: Dict, filename: str):
    """Save the report to a text file"""
    with open(filename, 'w') as f:
        f.write("=== BALANCE REPORT ===\n\n")
        f.write(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total execution time: {report['execution_time']/60:.2f} minutes\n")
        if report['duplicate_addresses_removed'] > 0:
            f.write(f"Duplicate addresses removed: {report['duplicate_addresses_removed']}\n")
        f.write(f"Addresses filtered (below {MIN_TOTAL_BALANCE} total balance): {report['filtered_addresses']}\n")
        f.write("\n")
        
        f.write("ETHEREUM TOTALS:\n")
        f.write(f"Total ETH: {report['ethereum']['total_eth']:.6f}\n")
        f.write(f"Total WETH: {report['ethereum']['total_weth']:.6f}\n\n")
        
        f.write("BASE TOTALS:\n")
        f.write(f"Total ETH: {report['base']['total_eth']:.6f}\n")
        f.write(f"Total WETH: {report['base']['total_weth']:.6f}\n\n")
        
        f.write("WALLET DETAILS (Sorted by total balance, minimum threshold: 0.0002):\n")
        for address_info in report['address_details']:
            f.write(f"\nWallet #{address_info['wallet_number']}")
            f.write(f"\nTOTAL: {address_info['total_balance']:.6f}")
            f.write(f"\nAddress: {address_info['address']}\n")
            f.write(f"Address: {address_info['address']}\n")
            if address_info['ethereum'] != 'Error':
                f.write("  Ethereum:\n")
                f.write(f"    ETH: {address_info['ethereum']['eth']:.6f}\n")
                f.write(f"    WETH: {address_info['ethereum']['weth']:.6f}\n")
            if address_info['base'] != 'Error':
                f.write("  Base:\n")
                f.write(f"    ETH: {address_info['base']['eth']:.6f}\n")
                f.write(f"    WETH: {address_info['base']['weth']:.6f}\n")

def print_report(report: Dict):
    """Print a formatted balance report"""
    print("\n=== BALANCE REPORT ===\n")
    print(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total execution time: {report['execution_time']/60:.2f} minutes")
    if report['duplicate_addresses_removed'] > 0:
        print(f"Duplicate addresses removed: {report['duplicate_addresses_removed']}")
    print(f"Addresses filtered (below {MIN_TOTAL_BALANCE} total balance): {report['filtered_addresses']}")
    print()
    
    print("ETHEREUM TOTALS:")
    print(f"Total ETH: {report['ethereum']['total_eth']:.6f}")
    print(f"Total WETH: {report['ethereum']['total_weth']:.6f}")
    
    print("\nBASE TOTALS:")
    print(f"Total ETH: {report['base']['total_eth']:.6f}")
    print(f"Total WETH: {report['base']['total_weth']:.6f}")
    
    print("\nWALLET DETAILS (Sorted by total balance, minimum threshold: 0.0002):")
    for address_info in report['address_details']:
        print(f"\nWallet #{address_info['wallet_number']}")
        print(f"TOTAL: {address_info['total_balance']:.6f}")
        print(f"Address: {address_info['address']}")
        if address_info['ethereum'] != 'Error':
            print("  Ethereum:")
            print(f"    ETH: {address_info['ethereum']['eth']:.6f}")
            print(f"    WETH: {address_info['ethereum']['weth']:.6f}")
        if address_info['base'] != 'Error':
            print("  Base:")
            print(f"    ETH: {address_info['base']['eth']:.6f}")
            print(f"    WETH: {address_info['base']['weth']:.6f}")

if __name__ == "__main__":
    try:
        with open('addresses.txt', 'r') as file:
            addresses = [addr.strip() for addr in file.readlines() if addr.strip()]
            
        if not addresses:
            print("No addresses found in addresses.txt")
            exit(1)
        
        unique_addresses = len(set(addresses))
        print(f"Loaded {len(addresses)} addresses from addresses.txt")
        if len(addresses) > unique_addresses:
            print(f"Found {len(addresses) - unique_addresses} duplicate addresses that will be removed")
        
        total_requests = unique_addresses * 4  # 4 API calls per address
        estimated_time = (total_requests * RATE_LIMIT_DELAY) / 60  # in minutes
        print(f"Will make {total_requests} API calls")
        print(f"Estimated minimum time: {estimated_time:.2f} minutes")
        print(f"Minimum balance threshold: {MIN_TOTAL_BALANCE} ETH")
        input("Press Enter to continue...")
        
        report = generate_balance_report(addresses)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'balance_report_{timestamp}.txt'
        
        save_report(report, output_filename)
        print_report(report)
        print(f"\nReport saved to: {output_filename}")
        
    except FileNotFoundError:
        print("Error: addresses.txt file not found")
        exit(1)
    except Exception as e:
        print(f"Error reading addresses.txt: {str(e)}")
        exit(1)