from SmartApi import SmartConnect
import pyotp
from config import API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET

def angel_login():
    try:
        print("Connecting to Angel One...")

        obj = SmartConnect(api_key=API_KEY)

        # Generate TOTP automatically
        totp = pyotp.TOTP(TOTP_SECRET).now()

        print("Generating session...")

        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)

        if data['status']:
            print("Login Successful ✅")
            return obj
        else:
            print("Login Failed ❌")
            print(data)
            return None

    except Exception as e:
        print("Error during login:", e)
        return None