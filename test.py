import re

invalidResponseQuestions={"start_date": "please enter in following format(YYYY-MM-DD)",
               "end_date": "please enter in following format (YYYY-MM-DD)",
               "reason": "Please mention the reason",
               "leave_type": "Please enter either consolidated or special only",
               "partial_leaves": "Any partial leaves?",
               "no_leaves": "please enter the numerical value ",
               "attachment": "Any attachments?"}

regexforEachQuestions={"start_date": re.compile(r"(([0-9]{4}))(\/|-)(1[0-2]|0?[1-9])\3(3[01]|[12][0-9]|0?[1-9])"),
               "end_date":re.compile(r"(([0-9]{2})?[0-9]{2})(\/|-)(1[0-2]|0?[1-9])\3(3[01]|[12][0-9]|0?[1-9])"),
               "reason": re.compile("[a-zA-Z]+"),
               "leave_type": re.compile(r'consolidated|special', re.IGNORECASE),
               "partial_leaves": "Any partial leaves?",
               "no_leaves": re.compile("[0-9]+"),
               "attachment": "Any attachments?"

}

def validate_the_response(key,response):
    pattermatch=regexforEachQuestions[key].search(response)
    if(pattermatch):
        print(pattermatch.group())
        return True
    return False


mapping = {"start_date": "What is the start date? (YYYY-MM-DD)",
            "end_date": "What is the end date? (YYYY-MM-DD)",
            "reason": "Please mention the reason",
            "leave_type": "Do you want to apply for consolidated or special leave?",
            "partial_leaves": "Any partial leaves?",
            "no_leaves": "What is the number of leaves?",
            "attachment": "Any attachments?"}


mapping_keys=[key for key in mapping]
i=0
while(i<len(mapping_keys)):
    inp=input(mapping[mapping_keys[i]])
    while(validate_the_response(mapping_keys[i],inp)==False):
        inp=input(invalidResponseQuestions[mapping_keys[i]])
    
    i=i+1

    
