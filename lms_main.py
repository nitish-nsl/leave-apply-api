from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn
import redis
import re
from datetime import datetime
import json
import requests
import time

r = redis.Redis(host='127.0.0.1', port=6379, db=1, decode_responses=True)

app = FastAPI()


class Data(BaseModel):
    auth_token: str
    question: str
    fromSource: str
    prev_questions:list
    employee_id :str
    session_id :int


invalidResponseQuestions = {"from_date": "please enter in following format(DD-MM-YYY)",
                            "to_date": "please enter in following format (DD-MM-YYYY)",
                            "reason": "Please mention the reason",
                            "leave_type": "Please enter either consolidated or special only",
                            "apply_partial_leave": "Any partial leaves?(yes or No)",
                            "partial_leaves_date": "please enter the date in following format((DD-MM-YYYY))",
                            "partial_leaves_time": "please enter the time(Forenoon or Afternoon or Working)",
                            }

invalidDatavalidationQuestions = {"to_date": "The end date must be greater than or equal to start date",
                                  "partial_leaves_date": "The Partial leave date must fall within the range of the start and end dates"}


regexforEachQuestions = {"from_date": re.compile(r"((3[01]|[12][0-9]|0?[1-9]))(\/|-)(1[0-2]|0?[1-9])\3([0-9]{4,4})"),
                         "to_date": re.compile(r"((3[01]|[12][0-9]|0?[1-9]))(\/|-)(1[0-2]|0?[1-9])\3([0-9]{4,4})"),
                         "reason": re.compile("[a-zA-Z]+"),
                         "leave_type": re.compile(r'consolidated|special', re.IGNORECASE),
                         "apply_partial_leave": re.compile(r'yes|No', re.IGNORECASE),
                         "partial_leaves_date": re.compile(r"((3[01]|[12][0-9]|0?[1-9]))(\/|-)(1[0-2]|0?[1-9])\3([0-9]{4,4})"),
                         "partial_leaves_time": re.compile(r'forenoon|Afternoon|Working', re.IGNORECASE),

                         }
questionsList = ["from_date", "to_date", "reason", "leave_type", "apply_partial_leave",
                 "partial_leaves_date", "partial_leaves_time"]

ttl_in_seconds = 86400  # one day

third_party_url = "https://testnhm.nslhub.com/backend_services/api/external_endpoints/create_leave_record"

headers = {
    'Content-Type': 'application/json',

    }

def validate_the_response(key, response):
    pattermatch = regexforEachQuestions[key].search(response)
    if (pattermatch):
        extractedData = pattermatch.group()
        return [True, extractedData]
    return [False]


def validate_date(key, data, response):
    startDate = datetime.strptime(data["from_date"], "%d-%m-%Y").date()
    
    if (key == "to_date"):
        endDate = datetime.strptime(response, "%d-%m-%Y").date()
        if (startDate > endDate):
            raise ("Invalid date expection")
        
    elif (key == "partial_leaves_date"):
        endDate = datetime.strptime(data['to_date'], "%d-%m-%Y").date()
        partialDate = datetime.strptime(response, "%d-%m-%Y").date()
        if (partialDate < startDate or partialDate > endDate):
            raise ("Invalid date expection")


def get_all(user_id):
    response = r.hgetall(user_id)
    return response


def store(user_id, arg, response):
    curr_value = get_all(user_id)

    if (arg == "to_date" or arg == "partial_leaves_date"):
        validate_date(arg, curr_value, response)

    if (arg == "partial_leaves_date" or arg == "partial_leaves_time"):
        curr_value[arg] = curr_value[arg]+response+","
    else:
        curr_value[arg] = response

    r.hset(user_id, mapping=curr_value)
    #print(curr_value)


def create_user(auth_token, employee_id):
    mapping = {
        "auth_token":auth_token, 
        "from_date": "",
        "to_date": "",
        "reason": "",
        "leave_type": "",
        "apply_partial_leave": "",
        "partial_leaves_date": "",
        "partial_leaves_time": "",
        "attachment": "",
        "index": 0,

    }
    r.hset(employee_id, mapping=mapping)
    r.expire(employee_id, ttl_in_seconds)


def get_question_for_key(key):
    mapping = {"from_date": "What is the start date? (DD-MM-YYYY)",
               "to_date": "What is the end date? (DD-MM-YYYY)",
               "reason": "Please mention the reason",
               "leave_type": "Do you want to apply for consolidated or special leave?",
               "apply_partial_leave": "Any partial leaves?",
               "partial_leaves_date": "Enter the date in following format (DD-MM-YYYY)",
               "partial_leaves_time": "Specify the time (Forenoon or Afternoon or Working)",
                "other_partial_leave":"Any other partial leaves ?"
               }
    return mapping[key]


def get_curr_param(user_id):
    mapping = get_all(user_id)
    ind = int(mapping['index'])
    return questionsList[ind-1]



# O(1) operation
def get_next_param(user_id):
    mapping = get_all(user_id)
    ind = int(mapping['index'])
    partialleaveDateIndex = questionsList.index("partial_leaves_date")
    partialLeaveIndex = questionsList.index("apply_partial_leave")
    partialleave = mapping['apply_partial_leave'].lower()
    
    #print(ind,partialleave,partialleaveDateIndex)

    if (ind == partialleaveDateIndex and partialleave == "no"):
        ind=0
        return None
    
    if (ind == len(questionsList) and partialleave == "yes"):
        ind = ind-3

    mapping["index"] = (ind+1)

        
    r.hset(user_id, mapping=mapping)

    if (ind == partialLeaveIndex and len(mapping['partial_leaves_date'])>=1):
        #print(mapping['partial_leaves_date'])
        return "other_partial_leave"

    return questionsList[ind]


def saveData(user_id):
    data = get_all(user_id)
    body = {}
    partialLeaveCount = 0

    for key in data:
        if key == "partial_leaves_date" or key == "partial_leaves_time" or key == "index" :
            continue

        elif key == "apply_partial_leave":
            partialLeavesDates = data["partial_leaves_date"].split(',')
            partialLeavesTime = data["partial_leaves_time"].split(',')
            partialLeaveData = []

            for i in range(0, len(partialLeavesTime)-1):
                dic = {}
                dic["date"] = partialLeavesDates[i]
                dic["time"] = partialLeavesTime[i]
                partialLeaveData.append(dic)

                # PartialLeaveCount
                if (partialLeavesTime[i].lower() == "working"):
                    partialLeaveCount = partialLeaveCount+1
                else:
                    partialLeaveCount = partialLeaveCount+0.5

            body["partial_leaves"] = partialLeaveData
            
        elif key == "leave_type":
            body[key] = 0 if (data[key].lower() == "consolidated") else 1
        else:
            body[key] = data[key]

    body["attachment"] = None

    # No Of leaves
    startDate = datetime.strptime(data["from_date"], "%d-%m-%Y").date()
    endDate = datetime.strptime(data['to_date'], "%d-%m-%Y").date()
    noOfDays = (endDate-startDate).days+1-partialLeaveCount
    body['no_leaves'] = noOfDays
    
    
    ###
    

    print(body)
    
    payload = json.dumps(body)
    
    try:
        response = requests.request("POST", third_party_url,headers=headers, data=payload)
        print(response.json()['dt'])
        r.delete(user_id)
        return "Leave applied successfully"
        
    except Exception as e:
        try:
            #time.sleep(5) #sleep for 5 secs and retry 
            response = requests.request("POST", third_party_url, data=payload)
            print(response.json()['dt'])
            r.delete(user_id)
            return "Leave applied successfully"
        
        except Exception as e:
            r.delete(user_id)
            print("error is "+ e)
            return "An error occurred while applying leave. Please try again later."
                    

    
    
    # Call NHmind Apply leave post request
    # URL of the third-party endpoint
    

    
    

def get_next_question(user_id):
    param = get_next_param(user_id)
    if param:
        question = get_question_for_key(param)
        return question
    else:
        return saveData(user_id)
       


def user_exists(user_id):
    if r.exists(user_id) == 1:
        return True
    else:
        return False


@app.get('/health_check')
async def health_check():
    return {'health_status': 'ok'}


@app.post("/action/apply_leave")
async def apply_leave(data: Data):
    auth_token = data.auth_token
    user_resp = data.question[4:].strip()
    employee_id=data.employee_id

    if user_exists(employee_id):
        param = get_curr_param(employee_id)
        patternMatch = validate_the_response(param, user_resp)
        if (patternMatch[0]):
            try:
                store(employee_id, param, patternMatch[1])
            except:
                return {"answer": invalidDatavalidationQuestions[param],
                        "confidence_high":True,
                        "response_type":"text"
                        }
                        
        else:
            return {"answer": invalidResponseQuestions[param],
                    "confidence_high":True,
                    "response_type":"text"}
        
    else:
        create_user(auth_token, employee_id)

    next_question = get_next_question(employee_id)
    return {"answer":next_question,
            "confidence_high":True,
            "response_type":"text"}

if __name__ == '__main__':
    uvicorn.run('lms_main:app', host='127.0.0.1',
                port=6969, log_level="info", reload=True)
