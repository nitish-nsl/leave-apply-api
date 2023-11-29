from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn
import redis
import re
from datetime import datetime

r = redis.Redis(host='127.0.0.1', port=6379, db=1, decode_responses=True)

app = FastAPI()


class Data(BaseModel):
    auth_token: str
    user_resp: str


invalidResponseQuestions = {"start_date": "please enter in following format(YYYY-MM-DD)",
                            "end_date": "please enter in following format (YYYY-MM-DD)",
                            "reason": "Please mention the reason",
                            "leave_type": "Please enter either consolidated or special only",
                            "apply_partial_leave": "Any partial leaves?(yes or No)",
                            "partial_leaves_date": "please enter the date in following format((YYYY-MM-DD))",
                            "partial_leaves_time": "please enter the time(forenoon or Afternoon or Working)",
                            }

invalidDatavalidationQuestions = {"end_date": "The end date must be greater than or equal to start date",
                                  "partial_leaves_date": "The leave date must fall within the range of the start and end dates"}


regexforEachQuestions = {"start_date": re.compile(r"(([0-9]{4}))(\/|-)(1[0-2]|0?[1-9])\3(3[01]|[12][0-9]|0?[1-9])"),
                         "end_date": re.compile(r"(([0-9]{4}))(\/|-)(1[0-2]|0?[1-9])\3(3[01]|[12][0-9]|0?[1-9])"),
                         "reason": re.compile("[a-zA-Z]+"),
                         "leave_type": re.compile(r'consolidated|special', re.IGNORECASE),
                         "apply_partial_leave": re.compile(r'yes|No', re.IGNORECASE),
                         "partial_leaves_date": re.compile(r"(([0-9]{4}))(\/|-)(1[0-2]|0?[1-9])\3(3[01]|[12][0-9]|0?[1-9])"),
                         "partial_leaves_time": re.compile(r'forenoon|Afternoon|Working', re.IGNORECASE),

                         }
questionsList = ["start_date", "end_date", "reason", "leave_type", "apply_partial_leave",
                 "partial_leaves_date", "partial_leaves_time"]

ttl_in_seconds = 86400  # one day


def validate_the_response(key, response):
    pattermatch = regexforEachQuestions[key].search(response)
    if (pattermatch):
        extractedData = pattermatch.group()
        return [True, extractedData]
    return [False]


def validate_date(key, data, response):
    startDate = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
    if (key == "end_date"):
        endDate = datetime.strptime(response, "%Y-%m-%d").date()
        if (startDate > endDate):
            raise ("Invalid date expection")
    elif (key == "partial_leaves_date"):
        endDate = datetime.strptime(data['end_date'], "%Y-%m-%d").date()
        partialDate = datetime.strptime(response, "%Y-%m-%d").date()
        if (partialDate < startDate or partialDate > endDate):
            raise ("Invalid date expection")


def get_all(user_id):
    response = r.hgetall(user_id)
    return response


def store(user_id, arg, response):
    curr_value = get_all(user_id)

    if (arg == "end_date" or arg == "partial_leaves_date"):
        validate_date(arg, curr_value, response)

    if (arg == "partial_leaves_date" or arg == "partial_leaves_time"):
        curr_value[arg] = curr_value[arg]+response+","
    else:
        curr_value[arg] = response

    r.hset(user_id, mapping=curr_value)
    #print(curr_value)


def create_user(user_id):
    mapping = {
        "start_date": "",
        "end_date": "",
        "reason": "",
        "leave_type": "",
        "apply_partial_leave": "",
        "partial_leaves_date": "",
        "partial_leaves_time": "",
        "attachment": "",
        "index": 0,

    }
    r.hset(user_id, mapping=mapping)
    r.expire(user_id, ttl_in_seconds)


def get_question_for_key(key):
    mapping = {"start_date": "What is the start date? (YYYY-MM-DD)",
               "end_date": "What is the end date? (YYYY-MM-DD)",
               "reason": "Please mention the reason",
               "leave_type": "Do you want to apply for consolidated or special leave?",
               "apply_partial_leave": "Any partial leaves?",
               "partial_leaves_date": "Enter the date in following format (YYYY-MM-DD)",
               "partial_leaves_time": "Specify the time (forenoon or Afternoon or Working)",
                "other_partial_leave":"Any other partial leaves"
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


def get_next_question(user_id):
    param = get_next_param(user_id)
    if param:
        question = get_question_for_key(param)
        return question
    else:
        data = get_all(user_id)

        body = {}
        partialLeaveCount = 0

        for key in data:
            if key == "partial_leaves_date" or key == "partial_leaves_time" or key == "index":
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
                        partialLeaveCount = partialLeaveCount-1
                    else:
                        partialLeaveCount = partialLeaveCount+0.5

                body[key] = partialLeaveData
            elif key == "leave_type":
                body[key] = 0 if (data[key].lower() == "consolidated") else 1
            else:
                body[key] = data[key]

        body["attachment"] = "None"

        # No Of leaves
        startDate = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        endDate = datetime.strptime(data['end_date'], "%Y-%m-%d").date()
        noOfDays = (endDate-startDate).days+1-partialLeaveCount
        body['no_leaves'] = noOfDays

        # Call NHmind Apply leave post request

        return body


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
        patternMatch = validate_the_response(param, user_resp)
        if (patternMatch[0]):
            try:
                store(user_id, param, patternMatch[1])
            except:
                return invalidDatavalidationQuestions[param]
        else:
            return invalidResponseQuestions[param]
    else:
        create_user(user_id)

    next_question = get_next_question(user_id)
    return next_question

if __name__ == '__main__':
    uvicorn.run('lms_main:app', host='127.0.0.1',
                port=6969, log_level="info", reload=True)
