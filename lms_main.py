from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn
import inspect
import redis
import re

r = redis.Redis(host='127.0.0.1', port=6379, db=1, decode_responses=True)

app = FastAPI()

class Data(BaseModel):
    auth_token: str
    user_resp : str 



invalidResponseQuestions={"start_date": "please enter in following format(YYYY-MM-DD)",
               "end_date": "please enter in following format (YYYY-MM-DD)",
               "reason": "Please mention the reason",
               "leave_type": "Please enter either consolidated or special only",
               "apply_partial_leave": "Any partial leaves?",
               "partial_leaves_date":"please enter the date in following format((YYYY-MM-DD))",
               "partial_leaves_time":"please enter the time(forenoon or Afternoon)",
               "no_leaves": "please enter the numerical value ",
               "attachment": "Any attachments?"}

regexforEachQuestions={"start_date": re.compile(r"(([0-9]{4}))(\/|-)(1[0-2]|0?[1-9])\3(3[01]|[12][0-9]|0?[1-9])"),
               "end_date":re.compile(r"(([0-9]{4}))(\/|-)(1[0-2]|0?[1-9])\3(3[01]|[12][0-9]|0?[1-9])"),
               "reason": re.compile("[a-zA-Z]+"),
               "leave_type": re.compile(r'consolidated|special', re.IGNORECASE),
               "apply_partial_leave": re.compile(r'yes|No', re.IGNORECASE),
               "partial_leaves_date":re.compile(r"(([0-9]{4}))(\/|-)(1[0-2]|0?[1-9])\3(3[01]|[12][0-9]|0?[1-9])"),
               "partial_leaves_time":re.compile(r'forenoon|Afternoon', re.IGNORECASE),
               "no_leaves": re.compile("[0-9]+"),
               "attachment": re.compile("[a-zA-Z]+")

}
questionsList=["start_date","end_date","reason","leave_type","apply_partial_leave","partial_leaves_date","partial_leaves_time","no_leaves","attachment"]






def validate_the_response(key,response):
    pattermatch=regexforEachQuestions[key].search(response)
    if(pattermatch):
        extractedData=pattermatch.group()
        return [True,extractedData]
    
    return [False]



def get_all(user_id):
    response = r.hgetall(user_id)
    return response

def store(user_id, arg, response):
    curr_value = get_all(user_id)
    curr_value[arg] = response
    r.hset(user_id, mapping=curr_value)
    print(curr_value,"redi store")


def create_user(user_id):
    mapping = {
        "start_date": "",
        "end_date": "",
        "reason": "",
        "leave_type": "",
        "apply_partial_leave":"",
        "partial_leaves_date":"",
        "partial_leaves_time":"",
        "no_leaves": "",
        "attachment":"",
        "index":0
    }
    r.hset(user_id, mapping=mapping)



def get_question_for_key(key):
    mapping = {"start_date": "What is the start date? (YYYY-MM-DD)",
               "end_date": "What is the end date? (YYYY-MM-DD)",
               "reason": "Please mention the reason",
               "leave_type": "Do you want to apply for consolidated or special leave?",
               "apply_partial_leave": "Any partial leaves?",
               "partial_leaves_date":"Enter the date in following format (YYYY-MM-DD)",
                "partial_leaves_time":"Specify the time (forenoon or Afternoon)",
               "no_leaves": "What is the number of leaves?",
               "attachment": "Any attachments?"}
    return mapping[key]


def get_curr_param(user_id):
    mapping = get_all(user_id)
    ind=int(mapping['index'])
    return questionsList[ind-1]

#O(1) operation 
def get_next_param(user_id):
    mapping = get_all(user_id)
    ind=int(mapping['index'])

    if(ind==5):
        if mapping['apply_partial_leave']=="No":
            ind=ind+2

    mapping["index"]=ind+1
    r.hset(user_id, mapping=mapping)

    if ind>=len(questionsList):
        return None
    
    
    return questionsList[ind]


def get_next_question(user_id):
    
    param = get_next_param(user_id)
    
    if param:
        question = get_question_for_key(param)
        return question
    else:
        data = get_all(user_id)
        ## Call NHmind Apply leave post request 
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
        param = get_curr_param(user_id)
        patternMatch=validate_the_response(param,user_resp)
        if(patternMatch[0]):
           store(user_id, param, patternMatch[1])
        else:
            return invalidResponseQuestions[param]
    else:
        create_user(user_id)
 

    next_question = get_next_question(user_id)
    return next_question

if __name__ == '__main__':
    uvicorn.run('lms_main:app', host='127.0.0.1', port=6969, log_level="info", reload=True)