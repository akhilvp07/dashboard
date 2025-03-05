import http.server
import socketserver
import os
import time
import subprocess
import socket

STATUS_FILE = "/home/akhil/.config/pingstatus/device_status_itp.conf"
CONFIG_FILE = "/home/akhil/.config/pingstatus/devices_itp.conf"

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
                # Set cache control headers to prevent caching
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
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
            # Remove the self.finish() call
            # self.finish()  # Close the connection after handling the request

    def do_POST(self):
        if self.path == '/add':
            # Handle adding a new entry
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            device_name, lan_ip, wan_ip = post_data.split(',')
            new_entry = "{},{},{}\n".format(lan_ip, wan_ip, device_name)
            new_status_entry = "{}:{},".format(lan_ip, "unknown") + "{}:{},".format(wan_ip, "unknown") + "{}\n".format(device_name)
            
            # Update CONFIG_FILE
            with open(CONFIG_FILE, 'r') as file:
                config_lines = file.readlines()
            config_lines.append(new_entry)
            config_lines.sort(key=lambda x: tuple(map(int, x.split(',')[0].split('.'))))
            with open(CONFIG_FILE, 'w') as file:
                file.writelines(config_lines)
            
            # Update STATUS_FILE
            with open(STATUS_FILE, 'r') as file:
                status_lines = file.readlines()
            status_lines.append(new_status_entry)
            status_lines.sort(key=lambda x: tuple(map(int, x.split(',')[0].split(':')[0].split('.'))))
            with open(STATUS_FILE, 'w') as file:
                file.writelines(status_lines)
            
            self.send_response(200)
            self.end_headers()
        elif self.path == '/delete':
            # Handle deleting an entry
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            device_name = post_data.strip()
            with open(STATUS_FILE, 'r') as file:
                lines = file.readlines()
            with open(STATUS_FILE, 'w') as file:
                for line in lines:
                    if device_name not in line:
                        file.write(line)
            with open(CONFIG_FILE, 'r') as file:
                lines = file.readlines()
            with open(CONFIG_FILE, 'w') as file:
                for line in lines:
                    if device_name not in line:
                        file.write(line)
            self.send_response(200)
            self.end_headers()
        elif self.path == '/edit':
            # Handle editing an entry
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            old_device_name, new_device_name, lan_ip, wan_ip = post_data.split(',')
            new_status_entry = "{}:{},".format(lan_ip, "unknown") + "{}:{},".format(wan_ip, "unknown") + "{}\n".format(new_device_name)
            new_config_entry = "{},{},{}\n".format(lan_ip, wan_ip, new_device_name)
            
            # Update STATUS_FILE
            with open(STATUS_FILE, 'r') as file:
                status_lines = file.readlines()
            with open(STATUS_FILE, 'w') as file:
                for line in status_lines:
                    if old_device_name in line:
                        file.write(new_status_entry)
                    else:
                        file.write(line)
            
            # Update CONFIG_FILE
            with open(CONFIG_FILE, 'r') as file:
                config_lines = file.readlines()
            with open(CONFIG_FILE, 'w') as file:
                for line in config_lines:
                    if old_device_name in line:
                        file.write(new_config_entry)
                    else:
                        file.write(line)
            
            # Sort STATUS_FILE
            with open(STATUS_FILE, 'r') as file:
                status_lines = file.readlines()
            status_lines.sort(key=lambda x: tuple(map(int, x.split(',')[0].split(':')[0].split('.'))))
            with open(STATUS_FILE, 'w') as file:
                file.writelines(status_lines)
            
            # Sort CONFIG_FILE
            with open(CONFIG_FILE, 'r') as file:
                config_lines = file.readlines()
            config_lines.sort(key=lambda x: tuple(map(int, x.split(',')[0].split('.'))))
            with open(CONFIG_FILE, 'w') as file:
                file.writelines(config_lines)
            
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

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
            "<link rel=\"icon\" href=\"https://cdn-icons-png.flaticon.com/128/8323/8323511.png\" type=\"image/vnd.microsoft.icon\">"
            "<link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.6.0/css/bootstrap.min.css\">"
            "<style>"
            "body { padding: 20px; }"
            ".device-table th, .device-table td { text-align: center; }"
            ".status-up { color: green; font-weight: bold; }"
            ".status-down { color: red; font-weight: bold; }"
            ".btn-sm { padding: 0.25rem 0.5rem; font-size: 0.875rem; line-height: 1.5; border-radius: 0.2rem; }"
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
            "function addDevice() {"
            "    var deviceName = prompt('Enter device name:');"
            "    var lanIp = prompt('Enter LAN IP:');"
            "    var wanIp = prompt('Enter WAN IP (optional):');"
            "    var data = deviceName + ',' + lanIp + ',' + wanIp;"
            "    fetch('/add', { method: 'POST', body: data })"
            "    .then(response => {"
            "        if (!response.ok) {"
            "            throw new Error('Network response was not ok: ' + response.status);"
            "        }"
            "        refreshDashboard();"
            "    })"
            "    .catch(error => {"
            "        console.error('There has been a problem with your fetch operation:', error);"
            "        alert('Failed to add device. Check console for details.');"
            "    });"
            "}"
            "function deleteDevice(deviceName) {"
            "    fetch('/delete', { method: 'POST', body: deviceName })"
            "    .then(response => {"
            "        if (!response.ok) {"
            "            throw new Error('Network response was not ok: ' + response.status);"
            "        }"
            "        refreshDashboard();"
            "    })"
            "    .catch(error => {"
            "        console.error('There has been a problem with your fetch operation:', error);"
            "        alert('Failed to delete device. Check console for details.');"
            "    });"
            "}"
            "function editDevice(oldDeviceName) {"
            "    var newDeviceName = prompt('Enter new device name:', oldDeviceName);"
            "    var lanIp = prompt('Enter new LAN IP:');"
            "    var wanIp = prompt('Enter new WAN IP (optional):');"
            "    var data = oldDeviceName + ',' + newDeviceName + ',' + lanIp + ',' + wanIp;"
            "    fetch('/edit', { method: 'POST', body: data })"
            "    .then(response => {"
            "        if (!response.ok) {"
            "            throw new Error('Network response was not ok: ' + response.status);"
            "        }"
            "        refreshDashboard();"
            "    })"
            "    .catch(error => {"
            "        console.error('There has been a problem with your fetch operation:', error);"
            "        alert('Failed to edit device. Check console for details.');"
            "    });"
            "}"
            "</script>"
            "</head>"
            "<body>"
            "<div class=\"container\">"
            "<div class=\"row\">"
            "<div class=\"col\"><h1>Device Dashboard</h1></div>"
            "<div class=\"col text-right\">"
            "<button class=\"btn btn-primary\" onclick=\"refreshDashboard()\">Refresh</button>"
            "<button class=\"btn btn-success\" onclick=\"addDevice()\">Add Device</button>"
            "</div>"
            "</div>"
            "<table class=\"table table-bordered device-table mt-3\">"
            "<thead>"
            "<tr>"
            "<th>Device Name</th>"
            "<th>LAN IP</th>"
            "<th>LAN Status</th>"
            "<th>WAN IP</th>"
            "<th>WAN Status</th>"
            "<th>Actions</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
        )
        for device in devices:
            lan_status_class = "status-up" if device[2].lower() == "up" else "status-down" if device[2].lower() == "down" else ""
            wan_status_class = "status-up" if device[4].lower() == "up" else "status-down" if device[4].lower() == "down" else ""
            # Convert LAN and WAN IPs to clickable URLs
            lan_ip_url = "http://" + device[1]
            if device[3] != "NA":
                wan_ip_url = "http://" + device[3]
                content += (
                    "<tr>"
                    "<td style=\"text-align: left; font-weight: bold\">{}</td>"
                    "<td><a href=\"{}\" target=\"_blank\">{}</a></td>"
                    "<td class=\"{}\">{}</td>"
                    "<td><a href=\"{}\" target=\"_blank\">{}</a></td>"
                    "<td class=\"{}\">{}</td>"
                    "<td>"
                    "<button class=\"btn btn-warning btn-sm\" onclick=\"editDevice('{}')\">"
                    "<i class=\"fas fa-edit\"></i></button>"
                    "<button class=\"btn btn-danger btn-sm\" onclick=\"deleteDevice('{}')\">"
                    "<i class=\"fas fa-trash-alt\"></i></button>"
                    "</td>"
                    "</tr>"
                ).format(device[0], lan_ip_url, device[1], lan_status_class, device[2], wan_ip_url, device[3], wan_status_class, device[4], device[0], device[0])
            else:
                content += (
                    "<tr>"
                    "<td style=\"text-align: left; font-weight: bold\">{}</td>"
                    "<td><a href=\"{}\" target=\"_blank\">{}</a></td>"
                    "<td class=\"{}\">{}</td>"
                    "<td>{}</td>"
                    "<td class=\"{}\">{}</td>"
                    "<td>"
                    "<button class=\"btn btn-warning btn-sm\" onclick=\"editDevice('{}')\">"
                    "<i class=\"fas fa-edit\"></i></button>"
                    "<button class=\"btn btn-danger btn-sm\" onclick=\"deleteDevice('{}')\">"
                    "<i class=\"fas fa-trash-alt\"></i></button>"
                    "</td>"
                    "</tr>"
                ).format(device[0], lan_ip_url, device[1], lan_status_class, device[2], device[3], wan_status_class, device[4], device[0], device[0])
        content += (
            "</tbody>"
            "</table>"
            "</div>"
            "<script src=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/js/all.min.js\"></script>"
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
        self.finish() # Close the connection after handling the request

# Set the IP address and port
IP = "192.168.0.151"
PORT = 8080

# Create a TCP server with SO_REUSEADDR option
httpd = socketserver.TCPServer((IP, PORT), DashboardHandler)
httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

print("Dashboard server is running at http://{}:{}".format(IP, PORT))

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    httpd.shutdown()
    print("\nServer stopped.")
