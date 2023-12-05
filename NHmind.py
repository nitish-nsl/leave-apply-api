import requests
import json


url="https://testnhm.nslhub.com/backend_services/api/start_new_chat_session"

third_party_url = "https://testnhm.nslhub.com/backend_services/api/external_endpoints/create_leave_record"

payload = json.dumps({
  "auth_token":"gAAAAABlbrXQCfF51EhEhzvXCLnDsObeNPTfFzD8uN8oAcHjVVnkYV89BUCSWRhgYH703VnDfcsyAgG8_F3gfojoHiq-EE0ZIR_YKVOexbgLx5pceY40pv8l__XxQ0CNgaj0Dc8wsPnp",
  "from_date": "04-12-2023",
  "to_date": "04-12-2023",
  "reason": "sick",
  "leave_type": 0,
  "partial_leaves": [],
  "attachment": None,
  "no_leaves": 1
})
headers = {
'Content-Type': 'application/json',
'Authorization': 'Token ade10f8ac2569168eb6735f548a52c1b9eb6039d'
}

try:
    response = requests.request("POST",url , headers=headers)

except Exception as e:
     print({"message": f"An error occurred: {e}"})

print("reper",response.text)