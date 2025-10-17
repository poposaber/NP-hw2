import client_window
import os

window = client_window.ClientWindow()
try:
    window.run()
except Exception as e:
    print(f"Error occurred: {e}")
os.system("pause")