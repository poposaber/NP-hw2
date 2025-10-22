import client
import os

c = client.Client()
try:
    c.start()
except Exception as e:
    print(f"Error occurred: {e}")
os.system("pause")