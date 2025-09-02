import json,uuid,random,time
from datetime import datetime,timezone
from urllib.request import Request,urlopen
API='http://127.0.0.1:8000/api/v1/transactions'
for i in range(500):
    body={"transactionId":str(uuid.uuid4()),"customerId":f"SIM{i%10}","amount":round(random.uniform(5,2000),2),"currency":"USD","merchantId":f"M{random.randint(1,20)}", "timestamp":datetime.now(timezone.utc).isoformat(),"channel":"CARD"}
    req=Request(API,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    try: 
        urlopen(req,timeout=3).read()
    except Exception as e: 
        print('err',e)
        time.sleep(0.02) 
