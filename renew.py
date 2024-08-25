# Cron Job Setup for Developers
#
# To run this script automatically every 2 months, you can set up a cron job.
#
# 1. Edit the cron table:
#    $ crontab -e
#
# 2. Add the following line to schedule the script to run every 2 months:
#
#    # Run the script on the 1st day of every other month at 2 AM
#    0 2 1 */2 * /usr/bin/python3 /path/to/your_script.py
#
#    - '0 2 1 */2 *': Runs at 2:00 AM on the 1st day of every second month.
#    - '/usr/bin/python3': Path to the Python 3 interpreter.
#    - '/path/to/your_script.py': Path to this Python script.
#
# 3. Ensure your script is executable:
#    $ chmod +x /path/to/your_script.py
#
# 4. Verify your cron job:
#    $ crontab -l
#
# Check cron logs in /var/log/cron or /var/log/syslog for debugging if needed.
import requests
import json
import os
import subprocess

# Configuration
api_key = 'YOUR_ZEROSSL_API_KEY'
email = 'YOUR_EMAIL'
domains = [
    {'domain': 'example.com', 'cert_dir': '/path/to/your/example_com'},
    {'domain': 'example.org', 'cert_dir': '/path/to/your/example_org'}
]
nginx_container_name = 'nginx_container_name'

# API Endpoints
api_base_url = 'https://api.zerossl.com/acme'
certificates_url = f'{api_base_url}/certificates'
orders_url = f'{api_base_url}/orders'

# Helper function to perform API requests
def api_request(endpoint, method='GET', data=None):
    headers = {'Content-Type': 'application/json'}
    params = {'access_key': api_key}
    response = requests.request(method, endpoint, headers=headers, params=params, data=json.dumps(data))
    if response.status_code != 200:
        raise Exception(f'API request failed with status code {response.status_code}: {response.text}')
    return response.json()

# Step 1: Create a new certificate order
def create_certificate_order(domain):
    data = {
        'common_name': domain['domain'],
        'subject_alt_names': [domain['domain']],
        'email': email
    }
    response = api_request(certificates_url, method='POST', data=data)
    return response

# Step 2: Get the order details to fetch the CSR and other information
def get_order_details(order_id):
    order_url = f'{orders_url}/{order_id}'
    response = api_request(order_url)
    return response

# Step 3: Download the issued certificate
def download_certificate(cert_url, output_path):
    response = requests.get(cert_url)
    if response.status_code != 200:
        raise Exception(f'Failed to download certificate with status code {response.status_code}: {response.text}')
    with open(output_path, 'wb') as file:
        file.write(response.content)

# Combine certificate and CA bundle into fullchain.pem using the cat command
def combine_certificates(cert_path, ca_bundle_path, fullchain_path):
    # Run the `cat` command to combine the certificates
    command = f'cat {cert_path} {ca_bundle_path} > {fullchain_path}'
    subprocess.run(command, shell=True, check=True)

# Reload Nginx container
def reload_nginx():
    print(f'Reloading Nginx container: {nginx_container_name}')
    subprocess.run(['docker', 'exec', nginx_container_name, 'nginx', '-s', 'reload'], check=True)

# Main logic
def renew_certificates():
    for domain in domains:
        cert_path = os.path.join(domain['cert_dir'], 'certificate.crt')
        ca_bundle_path = os.path.join(domain['cert_dir'], 'ca_bundle.crt')
        fullchain_path = os.path.join(domain['cert_dir'], 'fullchain.pem')

        # Create a new certificate order
        print(f'Creating new certificate order for domain: {domain["domain"]}')
        order_response = create_certificate_order(domain)
        order_id = order_response['order_id']
        print(f'Order created with ID: {order_id}')

        # Get the order details
        print(f'Fetching order details for order ID: {order_id}')
        order_details = get_order_details(order_id)
        cert_url = order_details['certificates'][0]['url']
        ca_bundle_url = order_details['ca_bundle_url']  # Adjust based on actual API response
        print(f'Certificate URL: {cert_url}')
        print(f'CA Bundle URL: {ca_bundle_url}')

        # Prepare paths
        os.makedirs(domain['cert_dir'], exist_ok=True)

        # Download the certificate and CA bundle
        print(f'Downloading certificate for domain: {domain["domain"]}')
        download_certificate(cert_url, cert_path)
        print(f'Certificate downloaded to {cert_path}')

        print(f'Downloading CA bundle for domain: {domain["domain"]}')
        download_certificate(ca_bundle_url, ca_bundle_path)
        print(f'CA bundle downloaded to {ca_bundle_path}')

        # Combine certificate and CA bundle into fullchain.pem
        print(f'Combining certificate and CA bundle into fullchain.pem for domain: {domain["domain"]}')
        combine_certificates(cert_path, ca_bundle_path, fullchain_path)
        print(f'Fullchain.pem created at {fullchain_path}')

    # Reload Nginx container to apply new certificates
    reload_nginx()

if __name__ == '__main__':
    renew_certificates()
