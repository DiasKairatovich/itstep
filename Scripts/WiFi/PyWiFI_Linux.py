import subprocess
import sys

def list_available_wifi():
    """Fetch a list of available Wi-Fi networks using nmcli."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi"],
            capture_output=True,
            text=True,
            check=True
        )
        networks = result.stdout.strip().split("\n")
        available_networks = []

        for network in networks:
            if not network.strip():  # Skip empty lines
                continue
            components = network.split(":")
            if len(components) == 3:
                ssid, signal, security = components
                ssid_display = ssid if ssid else "Hidden"
                available_networks.append((ssid_display, signal, security))
            else:
                print(f"Skipping invalid network entry: {network}")

        return available_networks
    except subprocess.CalledProcessError as e:
        print("Error: Unable to fetch Wi-Fi networks.")
        print(e.stderr)
        return []
    except Exception as e:
        print(f"An error occurred while fetching Wi-Fi networks: {e}")
        return []


def connect_to_wifi(ssid, password=None):
    """Connect to a specified Wi-Fi network."""
    try:
        print(f"\nAttempting to connect to Wi-Fi: {ssid}")
        # command = ["nmcli", "dev", "wifi", "connect", ssid]
        command = ["sudo", "-S", "nmcli", "dev", "wifi", "connect", ssid]
        if password:
            command.extend(["password", password])

        # Send the sudo password automatically to stdin
        result = subprocess.run(command, input="DunkBall17!\n", capture_output=True, text=True)

        if result.returncode == 0:
            print(f"Successfully connected to Wi-Fi: {ssid}")
            sys.exit(0)  # Exit after successful connection
        else:
            print(f"Failed to connect to Wi-Fi: {ssid}")
            print(result.stderr)
    except Exception as e:
        print(f"An error occurred while connecting: {e}")


def main():
    networks = list_available_wifi()
    if networks:
        print("\nAvailable Wi-Fi Networks:")
        for i, (ssid, signal, security) in enumerate(networks, start=1):
            print(f"{i}. SSID: {ssid}, Signal Strength: {signal}, Security: {security}")

        print("\nEnter the number of the network to connect to (or 0 to quit):")
        try:
            choice = int(input("Your choice: "))
            if choice == 0:
                print("Exiting program.")
                sys.exit(0)
            elif 1 <= choice <= len(networks):
                ssid, _, security = networks[choice - 1]
                if security != "--":  # Network requires a password
                    print("\nThis network requires a password.")
                    password_list = [
                        "T@rget@iMain2019",
                        "T@rget@iGuest2022",
                        "aifc2018expo",
                        "d:Quad6P)H"
                    ]
                    for password in password_list:
                        print(f"Trying password: {password}")
                        connect_to_wifi(ssid, password)
                else:  # Open network
                    print("\nThis is an open network. Connecting...")
                    connect_to_wifi(ssid)
            else:
                print("Invalid selection. Please select a valid option.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")
    else:
        print("No networks found. Please ensure your Wi-Fi is enabled.")


if __name__ == "__main__":
    main()
