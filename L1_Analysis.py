import paramiko
import subprocess
import re


def check_camera(rtsp_link):
    # Extract the IP address from the RTSP link
    ip_match = re.search(r'//(.*?)/', rtsp_link)
    if not ip_match:
        print("Invalid RTSP link.")
        return

    ip_address = ip_match.group(1)

    # SSH connection parameters
    ssh_key_path = input("Enter the path to your SSH key (e.g., /path/to/key): ")
    username = input("Enter your SSH username: ")

    # Connect via SSH
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ip_address, username=username, key_filename=ssh_key_path)

        print(f"Connected to {ip_address} via SSH.")

        # Perform ping
        ping_result = subprocess.run(["ping", "-c", "4", ip_address], capture_output=True, text=True)
        print("Ping Results:")
        print(ping_result.stdout)

        # Perform traceroute
        trace_result = subprocess.run(["traceroute", ip_address], capture_output=True, text=True)
        print("Traceroute Results:")
        print(trace_result.stdout)

    except Exception as e:
        print(f"Failed to connect to {ip_address} via SSH: {e}")
    finally:
        ssh_client.close()


if __name__ == "__main__":
    rtsp_link = input("Enter the RTSP link: ")
    check_camera(rtsp_link)
