import http.server
import socketserver
import os
import time
import subprocess
import socket

STATUS_FILE = "/home/akhil/.config/pingstatus/device_status.conf"

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    CACHE_EXPIRY = 5  # Cache expiry time in seconds (5 seconds)
    last_read = 0  # The last time the status file was read
    devices_cache = []  # Cache for the device status

    def do_GET(self):
        if self.path == '/refresh':
            try:
                print("Refresh endpoint hit")
                subprocess.call(['pingstatus', '--sync'])
                print("Command executed successfully")
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                content = self.get_dashboard_content(force_update=True)
                self.wfile.write(content.encode('utf-8'))
            except subprocess.CalledProcessError as e:
                print("Error executing command (CalledProcessError):", e)
                self.send_response(500)
                self.end_headers()
            except Exception as e:
                print("Error executing command:", e)
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            content = self.get_dashboard_content()
            self.wfile.write(content.encode('utf-8'))

    def read_device_status(self, force_update=False):
        # Check if cache is still valid unless force_update is True
        if not force_update and time.time() - self.last_read < self.CACHE_EXPIRY:
            return self.devices_cache

        # If the cache is expired or force_update is True, read the status file and update the cache
        devices = []
        with open(STATUS_FILE, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    lan_info, wan_info, device_name = parts
                    lan_ip, lan_status = lan_info.split(':') + [""] * (2 - len(lan_info.split(':')))
                    wan_ip, wan_status = wan_info.split(':') + [""] * (2 - len(wan_info.split(':')))
                    devices.append((device_name, lan_ip, lan_status, wan_ip, wan_status))
        self.devices_cache = devices
        self.last_read = time.time()
        return devices

    def get_dashboard_content(self, force_update=False):
        devices = self.read_device_status(force_update)
        content = (
            "<!DOCTYPE html>"
            "<html>"
            "<head>"
            "<meta charset=\"UTF-8\">"
            "<title>Device Dashboard</title>"
            "<link rel=\"icon\" href=\"/themes/custom/ribbon/images/favicon.ico\" type=\"image/vnd.microsoft.icon\">"
            "<link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.6.0/css/bootstrap.min.css\">"
            "<style>"
            "body { padding: 20px; }"
            ".device-table th, .device-table td { text-align: center; }"
            ".status-up { color: green; font-weight: bold; }"
            ".status-down { color: red; font-weight: bold; }"
            "</style>"
            "<script>"
            "function refreshDashboard() {"
            "    fetch('/refresh', { method: 'GET' })"
            "    .then(response => {"
            "        if (!response.ok) {"
            "            throw new Error('Network response was not ok: ' + response.status);"
            "        }"
            "        return response.text();"
            "    })"
            "    .then(data => {"
            "        var parser = new DOMParser();"
            "        var doc = parser.parseFromString(data, 'text/html');"
            "        var newTable = doc.querySelector('.device-table tbody').innerHTML;"
            "        document.querySelector('.device-table tbody').innerHTML = newTable;"
            "        console.log('Dashboard refreshed successfully');"
            "    })"
            "    .catch(error => {"
            "        console.error('There has been a problem with your fetch operation:', error);"
            "        alert('Failed to refresh dashboard. Check console for details.');"
            "    });"
            "}"
            "function fetchPeriodicData() {"
            "    fetch('/?timestamp=' + new Date().getTime(), { method: 'GET' })"
            "    .then(response => {"
            "        if (!response.ok) {"
            "            throw new Error('Network response was not ok: ' + response.status);"
            "        }"
            "        return response.text();"
            "    })"
            "    .then(data => {"
            "        var parser = new DOMParser();"
            "        var doc = parser.parseFromString(data, 'text/html');"
            "        var newTable = doc.querySelector('.device-table tbody').innerHTML;"
            "        document.querySelector('.device-table tbody').innerHTML = newTable;"
            "        console.log('Page updated successfully');"
            "    })"
            "    .catch(error => {"
            "        console.error('There has been a problem with your fetch operation:', error);"
            "    });"
            "}"
            "setInterval(fetchPeriodicData, 5000);"
            "fetchPeriodicData();"
            "</script>"
            "</head>"
            "<body>"
            "<div class=\"container\">"
            "<div class=\"row\">"
            "<div class=\"col\"><h1>Device Dashboard</h1></div>"
            "<div class=\"col text-right\"><button class=\"btn btn-primary\" onclick=\"refreshDashboard()\">Refresh</button></div>"
            "</div>"
            "<table class=\"table table-bordered device-table mt-3\">"
            "<thead>"
            "<tr>"
            "<th>Device Name</th>"
            "<th>LAN IP</th>"
            "<th>LAN Status</th>"
            "<th>WAN IP</th>"
            "<th>WAN Status</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
        )
        for device in devices:
            lan_status_class = "status-up" if device[2].lower() == "up" else "status-down" if device[2].lower() == "down" else ""
            wan_status_class = "status-up" if device[4].lower() == "up" else "status-down" if device[4].lower() == "down" else ""
            content += (
                "<tr>"
                "<td>{}</td>"
                "<td>{}</td>"
                "<td class=\"{}\">{}</td>"
                "<td>{}</td>"
                "<td class=\"{}\">{}</td>"
                "</tr>"
            ).format(device[0], device[1], lan_status_class, device[2], device[3], wan_status_class, device[4])
        content += (
            "</tbody>"
            "</table>"
            "</div>"
            "</body>"
            "</html>"
        )
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

# Create a TCP server with SO_REUSEADDR option
httpd = socketserver.TCPServer((IP, PORT), DashboardHandler)
httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

print("Dashboard server is running at http://{}:{}".format(IP, PORT))

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    httpd.shutdown()
    print("\nServer stopped.")
