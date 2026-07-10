"""
reusable alert utility to email me error messages on automated scheduled scripts
"""
import win32com.client
from pathlib import Path
import json

with open(Path(__file__).parent.parent / "internal/config.json") as f:
    config = json.load(f)

def send_alert(subject, message):
	outlook = win32com.client.Dispatch("Outlook.Application")
	mail = outlook.CreateItem(0)
	mail.To = config["cc_me"]
	mail.Subject = subject
	mail.Body = message 
	mail.Send()

if __name__ == "__main__":
	send_alert("test", "test")