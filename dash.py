import http.server
import socketserver
import os
import time
import subprocess

STATUS_FILE = "/home/akhil/.config/pingstatus/device_status.conf"

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    CACHE_EXPIRY = 5  # Cache expiry time in seconds (5 seconds)
    last_read = 0  # The last time the status file was read
    devices_cache = []  # Cache for the device status

    def do_GET(self):
        if self.path == '/refresh':
            # Execute the bash command when the 'refresh' button is clicked
            print("Refresh button clicked, running sync command.")
            subprocess.call(['~/bin/pingstatus', '--sync'])
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            content = self.get_dashboard_content()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            content = self.get_dashboard_content()
            self.wfile.write(content.encode('utf-8'))

    def read_device_status(self):
        # Check if cache is still valid
        if time.time() - self.last_read < self.CACHE_EXPIRY:
            return self.devices_cache

        # If the cache is expired, read the status file and update the cache
        devices = []
        with open(STATUS_FILE, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    lan_info, wan_info, device_name = parts
                    lan_ip, lan_status = lan_info.split(':') + [""] * (2 - len(lan_info.split(':')))
                    wan_ip, wan_status = wan_info.split(':') + [""] * (2 - len(wan_info.split(':')))
                    devices.append({
                        'device_name': device_name,
                        'lan_ip': lan_ip,
                        'lan_status': lan_status,
                        'wan_ip': wan_ip,
                        'wan_status': wan_status
                    })
                else:
                    print("Invalid line:", line)
        # Update the cache and last read time
        self.devices_cache = devices
        self.last_read = time.time()

        return devices

    def render_dashboard(self):
        content = "<h1>Device Status</h1>"
        content += "<table border='1' class='device-table'>"  # Add class to the table
        content += "<tr>"
        content += "<th class='col1'>Device Name</th>"  # Assign class to header cells
        content += "<th class='col2'>LAN IP</th>"
        content += "<th class='col3'>LAN Status</th>"
        content += "<th class='col4'>WAN IP</th>"
        content += "<th class='col5'>WAN Status</th>"
        content += "</tr>"

        devices = self.read_device_status()

        for device in devices:
            content += "<tr>"
            content += "<td class='col1'>{}</td>".format(device['device_name'])

            # Wrap LAN IP in a hyperlink with target='_blank'
            lan_ip = device['lan_ip']
            lan_ip_link = "http://{}".format(lan_ip)
            content += "<td class='col2'><a href='{0}' target='_blank'>{1}</a></td>".format(lan_ip_link, lan_ip)

            status_color = 'green' if device['lan_status'] == 'Up' else 'red'
            content += "<td class='col3 status' style='color: {}'><b>{}</b></td>".format(status_color, device['lan_status'])
            # Wrap WAN IP in a hyperlink with target='_blank'
            wan_ip = device['wan_ip']
            if wan_ip != "NA":
                wan_ip_link = "http://{}".format(wan_ip)
                content += "<td class='col4'><a href='{0}' target='_blank'>{1}</a></td>".format(wan_ip_link, wan_ip)
            else:
                content += "<td class='col4'>{}</td>".format(wan_ip)

            if device['wan_status'] == 'NA':
                status_color = 'black'  # Or any color for 'NA' status
                content += "<td class='col5 status' style='color: {}'>{}</td>".format(status_color, device['wan_status'])
            else:
                status_color = 'green' if device['wan_status'] == 'Up' else 'red'
                content += "<td class='col5 status' style='color: {}'><b>{}</b></td>".format(status_color, device['wan_status'])

            content += "</tr>"

        content += "</table>"
        return content

    def get_dashboard_content(self):
        content = "<html><head><title>Dashboard</title>"
        content += "<meta http-equiv='refresh' content='5'>"  # Refresh every 5 seconds
        # Add CSS styles for the table with dynamic column widths
        content += "<style>"
        content += "table { width: 50%; border-collapse: collapse; }"
        content += "th, td { padding: 8px; border-bottom: 1px solid #ddd; }"
        content += "th { text-align: center; background-color: #f2f2f2; }"
        # Define column widths based on estimated content length
        content += ".device-table .col1 { width: 120px; }"  # Adjust width as needed
        content += ".device-table .col2 { width: 120px; }"  # Adjust width as needed
        content += ".device-table .col3 { width: 80px; }"  # Adjust width as needed
        content += ".device-table .col4 { width: 120px; }"  # Adjust width as needed
        content += ".device-table .col5 { width: 80px; }"  # Adjust width as needed
        content += ".status { color: black; text-align: center;}"  # Style for status class
        content += "</style>"
        content += "</head><body>"
        content += '<button onclick="location.href=\'/refresh\'" type="button">Refresh</button>'
        content += self.render_dashboard()
        content += "</body></html>"
        return content

    def end_headers(self):
        self.send_header('Content-type', 'text/html')
        http.server.BaseHTTPRequestHandler.end_headers(self)

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

# Set the IP address and port
IP = "192.168.0.151"
PORT = 8000

# Create a TCP server
httpd = socketserver.TCPServer((IP, PORT), DashboardHandler)

print("Dashboard server is running at http://{}:{}".format(IP, PORT))

try:
    # Start serving
    httpd.serve_forever()
except KeyboardInterrupt:
    # Stop serving when Ctrl+C is pressed
    httpd.shutdown()
    print("\nServer stopped.")
