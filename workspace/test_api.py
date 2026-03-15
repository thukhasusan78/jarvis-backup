import requests
import json

keys = [
    "AIzaSyC525g-82iG05Ta22RB68r576ri4BK29mI", "AIzaSyAt9ZqxVvKuMdvGwHnRfEUO7ql_NBTDL00",
    "AIzaSyASbD67pRD3ZEMWENxvqiQdzOMpXJPytKg", "AIzaSyDdZN1aRZJW9GKgKiULuyVruUUIExTXdQ4",
    "AIzaSyD5UFGzH2B9KFhWAP9uR3AP7RlxKmptoSw", "AIzaSyCjh4JbRUTD_9xiJrse03AYpS1QNIPcS4o",
    "AIzaSyB1OKkD6Ddon7fHEGSZstpxKMn469jP0WI", "AIzaSyBr94CfIoYCwMiasHCDJ6bEGXgBekT9Mc0",
    "AIzaSyCqyPKwnxuUfI_MpBFzfoM3si9qC9ZlNL0", "AIzaSyBD-sHpbFaLUkZyBRIcOQ_5easygowo3eM",
    "AIzaSyDu_sh_IMygXTWjBZJrhMHEz9wDBdeeKns", "AIzaSyBxWGKXv1-U7NWV3Y-xQHKPO-YeUMKUVe0",
    "AIzaSyAOsg1dIY9uTitQEAgE02DBzCsdans4-TY", "AIzaSyAWBYoacrjHt1rK3aiwFTxhap6WetKid9Y",
    "AIzaSyAfIeecHqZsdYPqu8NQNJf19TMQtqGyiE0"
]

def test_key(key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts":[{"text": "hi"}]}]}
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return "✅ Working"
        elif response.status_code == 429:
            return "❌ Rate Limited"
        else:
            return f"⚠️ Error: {response.status_code}"
    except Exception as e:
        return f"🔥 Failed: {str(e)}"

print("--- Gemini API Key Test Results ---")
for key in keys:
    status = test_key(key)
    print(f"Key: {key[:15]}... | Status: {status}")
