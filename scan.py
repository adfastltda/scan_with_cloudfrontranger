import socket
import ipaddress
import concurrent.futures
import os
import requests

def scan_port(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((ip, port))
    sock.close()
    if result == 0:
        return ip

def parse_ip_range(ip_range):
    ip_list = []
    if "-" in ip_range:
        start, end = ip_range.split("-")
        start_ip = ipaddress.IPv4Address(start.strip())
        end_ip = ipaddress.IPv4Address(end.strip())
        ip_list = [str(ipaddress.IPv4Address(ip)) for ip in range(int(start_ip), int(end_ip) + 1)]
    else:
        try:
            ip_net = ipaddress.IPv4Network(ip_range)
            ip_list.extend(str(ip) for ip in ip_net.hosts())
        except ipaddress.AddressValueError:
            print(f"Formato inválido: {ip_range}")
    return ip_list

def get_amazon_ip_ranges():
    ip_ranges = requests.get('https://ip-ranges.amazonaws.com/ip-ranges.json').json()['prefixes']
    amazon_ips = [item['ip_prefix'] for item in ip_ranges if item["service"] == "AMAZON"]
    ec2_ips = [item['ip_prefix'] for item in ip_ranges if item["service"] == "EC2"]

    amazon_ips_less_ec2 = []

    for ip in amazon_ips:
        if ip not in ec2_ips:
            amazon_ips_less_ec2.append(ip)

    with open('amazon_ips_temp.txt', 'w') as file:
        file.write('\n'.join(amazon_ips_less_ec2))

    print("Ranges da Amazon salvos em amazon_ips_temp.txt")

def main():
    get_amazon_ip_ranges()

    with open('amazon_ips_temp.txt', 'r') as file:
        ip_ranges = file.read().splitlines()

    try:
        num_threads = int(input("Digite o número de threads (padrão: 100): ") or 100)
    except ValueError:
        print("Entrada inválida. Usando 100 threads por padrão.")
        num_threads = 100

    all_open_ips = []

    print("\nAguarde enquanto o teste é executado...")

    for ip_range in ip_ranges:
        open_ips = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(scan_port, ip, 443) for ip in parse_ip_range(ip_range)]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()

                if result:
                    open_ips.append(result)

        if open_ips:
            print(f"Range {ip_range}: Sucesso nos seguintes IPs:")
            for ip in open_ips:
                print(ip)
        else:
            print(f"Range {ip_range}: Nenhum IP com sucesso!")

        all_open_ips.extend(open_ips)
        open_ips.clear()

    print("\nTeste concluído.")

    if all_open_ips:
        print("\nSucesso nos seguintes IPs:")
        for ip in all_open_ips:
            print(ip)
    os.remove('amazon_ips_temp.txt')

if __name__ == "__main__":
    main()
