from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn
import inspect
import redis

r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)

app = FastAPI()

class Data(BaseModel):
    auth_token: str
    user_resp : str

def get_all(user_id):
    response = r.hgetall(user_id)
    return response

def store(user_id, arg, response):
    curr_value = get_all(user_id)
    curr_value[arg] = response
    r.hset(user_id, mapping=curr_value)

def create_user(user_id):
    mapping = {
        "start_date": "",
        "end_date": "",
        "reason": "",
        "leave_type": "",
        "partial_leaves": "",
        "no_leaves": "",
        "attachment": ""
    }
    r.hset(user_id, mapping=mapping)

def get_question_for_key(key):
    mapping = {"start_date": "What is the start date? (YYYY-MM-DD)",
               "end_date": "What is the end date? (YYYY-MM-DD)",
               "reason": "Please mention the reason",
               "leave_type": "Do you want to apply for consolidated or special leave?",
               "partial_leaves": "Any partial leaves?",
               "no_leaves": "What is the number of leaves?",
               "attachment": "Any attachments?"}
    return mapping[key]

def get_next_param(user_id):
    mapping = get_all(user_id)
    for key in mapping:
        if mapping[key] == "":
            return key
    return None

def get_next_question(user_id):
    param = get_next_param(user_id)
    if param:
        question = get_question_for_key(param)
        return question
    else:
        data = get_all(user_id)
        data["status"] = "leave applied"
        return data
        
def user_exists(user_id):
    if r.exists(user_id) == 1:
        return True
    else:
        return False

@app.get('/health_check')
async def health_check():
    return {'health_status': 'ok'}

@app.post("/apply_leave")
async def apply_leave(data: Data):
    user_id = data.auth_token
    user_resp = data.user_resp
    if user_exists(user_id):                                       
        param = get_next_param(user_id)
        store(user_id, param, user_resp)
    else:
        create_user(user_id)
    next_question = get_next_question(user_id)
    return next_question

for key in r.keys():
    print(key)

# if __name__ == '__main__':
#     uvicorn.run('lms_main:app', host='0.0.0.0', port=6969, log_level="info", reload=True)