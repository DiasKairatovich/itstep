import subprocess
import sys

def list_available_wifi():
    try:
        # Run the nmcli command to list available Wi-Fi networks
        result = subprocess.run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi"],
                                 capture_output=True, text=True)
        if result.returncode == 0:
            networks = result.stdout.strip().split("\n")
            available_networks = []

            for i, network in enumerate(networks, start=1):
                # Skip empty lines
                if not network.strip():
                    continue

                # Split the line into components
                components = network.split(":")
                if len(components) == 3:
                    ssid, signal, security = components
                    ssid_display = ssid if ssid else "Hidden"
                    available_networks.append((ssid, security))
                else:
                    print(f"Skipping invalid line: {network}")

            return available_networks
        else:
            print("Error: Unable to fetch Wi-Fi networks.")
            print(result.stderr)
            return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def connect_to_wifi(ssid, password=None):
    try:
        print(f"Attempting to connect to Wi-Fi: {ssid}")
        # Use nmcli to connect to the specified SSID
        if password:
            result = subprocess.run(
                ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
                capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(
                ["nmcli", "dev", "wifi", "connect", ssid],
                capture_output=True,
                text=True
            )

        if result.returncode == 0:
            print(f"Successfully connected to Wi-Fi: {ssid}")
            sys.exit(0)  # Stop the entire script after successful connection
        else:
            print(f"Failed to connect to Wi-Fi: {ssid}")
            print(result.stderr)
    except Exception as e:
        print(f"An error occurred while connecting: {e}")

# Main script logic
if __name__ == "__main__":
    networks = list_available_wifi()
    if networks:
        print("\nSelect a network to connect to:")
        for i, (ssid, security) in enumerate(networks, start=1):
            print(f"{i}. SSID: {ssid if ssid else 'Hidden'}, Security: {security}")

        try:
            choice = int(input("\nEnter the number of the network to connect to: "))
            if 1 <= choice <= len(networks):
                ssid, security = networks[choice - 1]
                if security != "--":  # If the network requires a password

                    password_list = [
                        "T@rget@iMain2019",
                        "T@rget@iGuest2022",
                        "aifc2018expo",
                        "d:Quad6P)H"
                    ]
                    for password in password_list:
                        connect_to_wifi(ssid, password)
                else:  # Open network
                    connect_to_wifi(ssid)
            else:
                print("Invalid selection.")
        except ValueError:
            print("Please enter a valid number.")
    else:
        print("No networks found.")
