import requests
import itertools
from itertools import cycle
import time
import multiprocessing as mp
from multiprocessing.queues import Queue
import threading
import json
import os
import random
import logging
import sys

retry_balance = []

logManager = logging.basicConfig(filename="Logs.log", filemode="w", level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

class ___():
    def __init__(self, roblosecurity=None):
        with requests.Session() as self.session:
            if os.path.exists("settings/listingData.json"):
                with open("settings/listingData.json", 'r') as f:
                    x = json.loads(f.read())
                    if x['signto___'] == True:
                        self.___auth = x['___AuthToken']
                        self.___hwid = x['___HwidToken']
                        self.auth = {'___AUTH': self.___auth, '___HWID': self.___hwid}

                        for cookie in open("settings/cookies.txt", 'r').readlines():
                            cookie = cookie.strip()
                            groups, userid, username = self.get_info(cookie)
                            cookie = cookie.replace('|', '%7C').replace(':', '%3A')
                            self.post_account(cookie, (-1 * userid), username)
                    else:
                        pass

            else:
                print("Missing json file")
                raise Exception

    def post_account(self, cookie, group, username):

        r = self.session.get(
            "https://___/api/reseller.php?type=list&cookie={}&group={}&comment={}".format(cookie, group, username),
            cookies=self.auth,
            data={'cookie': '{}'.format(cookie),
                  'group': '{}'.format(group),
                  'type': 'list',
                  'comment': '{}'.format(username)}
        )

    def get_info(self, cookie):
        headerInfo = {'content-type': 'application/json'}
        querystring = {"type": "groups", "cookie": "{}".format(cookie)}
        r = self.session.get("https://___/api/reseller.php", params=querystring, cookies=self.auth).json()

        if r['success'] == True:
            return r['groups'], r['userid'], r['username']
        else:
            print("___ failed:", r['message'])


class GroupFunds(___):
    def __init__(self):
        PROCESS_COUNT = 1
        THREAD_COUNT = 1
        self.DOWNTIME_BETWEEN_CHECKS = 168 #How many hours between refresh
        super().__init__()

        
        
        self.proxycycle = cycle([i.split(":")[2].strip() + ":" + i.split(":")[3].strip() + "@" + i.split(":")[
            0].strip() + ":" + i.split(":")[1].strip() for i in open("settings/proxies.txt", 'r').readlines()])

        self.roblosecurities = [{'.ROBLOSECURITY': f'{cookie.strip()}'} for cookie in
                                open("settings/cookies.txt", 'r').readlines()]

        self.groups = [self.get_groups(security) for security in self.roblosecurities]
        self.proxyDict = {
            "http": "http://" + str(next(self.proxycycle)),
            "https": "http://" + str(next(self.proxycycle))
        }

        queue = Queue(maxsize=-1, ctx=mp.get_context())
        for i in range(THREAD_COUNT):
            worker = threading.Thread(target=self.read_queue, args=(queue,))
            logging.info("starting worker thread")
            worker.start()
        
        logging.info("starting queue-fill ")
        task_fill_queue = mp.Process(target=self.fill_queue(queue))
        task_fill_queue.start()

    def get_x_csrf_token(self, groupid, roblosecurity, payload):
        logging.info(f"Grabbing X-CSRF-TOKEN for {groupid}")
        try:
            r = requests.post(f"https://groups.roblox.com/v1/groups/{groupid}/payouts", proxies=self.proxyDict,
                              cookies=roblosecurity, data=payload)
            print(r.headers)
            return {'x-csrf-token': r.headers['x-csrf-token']}
        except:
            self.rotateProxy()
            return self.get_x_csrf_token(groupid, roblosecurity, payload)

    def withdraw_to_user(self, roblosecurity, groupid, robux, userInfo, limit):
        try:
            userRobux = self.get_robux(userInfo['userid'], cookie=roblosecurity)
            logging.info(f"UserRobux: {userRobux}, GroupRobux: {robux}, GroupId: {groupid}, Limit: {limit}")
            if userRobux < limit:

                logging.info("user Robux less than limit")
                robux_till_limit = limit - userRobux  # 10
                if robux < robux_till_limit and robux != 0:

                    #self.write_to_log(groupid, robux, userInfo['userid'])

                    logging.info("Robux less than limit, withdrawing all current robux")
                    payload = {"PayoutType": "FixedAmount", "Recipients": [
                        {"recipientId": userInfo['userid'], "recipientType": "User", "amount": robux}]}
                    r = requests.post(f"https://groups.roblox.com/v1/groups/{groupid}/payouts",
                                      proxies=self.proxyDict, cookies=roblosecurity, json=payload,
                                      headers=self.get_x_csrf_token(groupid, roblosecurity, payload)
                                      )
                    logging.info(payload, r.json())

                elif robux_till_limit == 0:

                    #self.write_to_log(groupid, robux, userInfo['userid'])

                    logging.info("The amount of robux in user's balance is the same as limit, passing")
                    return

                elif robux >= robux_till_limit:
                    logging.info("Robux Greater than limit, withdrawing robux till limit")

                    #self.write_to_log(groupid, robux, userInfo['userid'])

                    payload = {"PayoutType": "FixedAmount", "Recipients": [
                        {"recipientId": userInfo['userid'], "recipientType": "User", "amount": robux_till_limit}]}
                    r = requests.post(f"https://groups.roblox.com/v1/groups/{groupid}/payouts",
                                      proxies=self.proxyDict, cookies=roblosecurity, json=payload,
                                      headers=self.get_x_csrf_token(groupid, roblosecurity, payload)
                                      )

                    logging.info(payload, r.json())

        except Exception as e:
            self.rotateProxy()
            return self.withdraw_to_user(roblosecurity, groupid, robux, userInfo, limit)

    def read_queue(self, queue):
        while True:
            counter = 0
            if queue.empty():

                logging.info("Empty Queue, waiting a few seconds")
                #time.sleep(30 * counter)
                time.sleep(30)
                counter += 1
            else:
                counter = 0

                logging.info(f"Handling a task: {queue.get()}")

                roblosecurity, groupid, robux, userInfo = queue.get()

                if self.available_to_refresh(groupid):
                    
                    self.withdraw_to_user(roblosecurity, groupid, robux, userInfo, limit=2500)
                
                else:
                    pass

    def fill_queue(self, queue):
        if len(globals()['retry_balance']) > 0:
            retry_balance = globals()['retry_balance']
        else:
            retry_balance = []

        for i in range(len(self.groups)):
            block = self.groups[i]

            for i in range(2, len(block)):
                try:

                    r = requests.get(f"https://economy.roblox.com/v1/groups/{block[i]['id']}/currency",
                                     proxies=self.proxyDict, cookies=block[0]).json()

                    task = (block[0], block[i]['id'], r['robux'], block[1])
                    logging.info("{:^13} | {:^15} |".format(block[i]["id"], r['robux']))
                    print(dict(block[i]['id'])['userid'], type(block[i]['id']))
                    self.write_to_log(block[i]["id"], r['robux'], block[1])

                    queue.put(task)

                except Exception as e:
                    logging.info(e)
                    if "TooManyRequests" in r['errors'][0]['message']:
                        logging.info(r)
                        logging.info("Exhausted Proxy, sending to a new loop")
                        retry_balance.append(block[i])
                        itertools.chain.from_iterable(retry_balance)
                        self.rotateProxy()

        logging.info("All cookies have been looped, restarting failed proxies")
        time.sleep(3600 * (self.DOWNTIME_BETWEEN_CHECKS/2))
        return self.fill_queue(queue)

    def rotateProxy(self):
        # print(ProxyPool)

        self.proxyDict = {
            "http": 'http://' + str(next(self.proxycycle)),
            "https": "http://" + str(next(self.proxycycle))
        }
        print("NEW PROXY:", self.proxyDict)

    def get_robux(self, id, cookie):
        try:
            r = requests.get(f"https://economy.roblox.com/v1/users/{id}/currency", cookies=cookie,
                             proxies=self.proxyDict).json()
            print(r)
            

            return r['robux']
        except KeyError as e:
            self.rotateProxy()

            return self.get_robux(id, cookie)

    def get_userInfo(self, cookie):
        try:
            r = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookie,
                             proxies=self.proxyDict).json()

            return r['id'], r['name']

        except:
            self.rotateProxy()
            print(r)
            return self.get_userInfo(cookie)

    def get_groups(self, cookie):
        """GRAB ID, NAME, AND DISPLAYNAME"""
        try:
            id, name = self.get_userInfo(cookie)
            """Grab Robux in Account"""
            userRobux = self.get_robux(id, cookie)
            """Grabbing the group listings"""
            r = requests.get(f"https://groups.roblox.com/v1/users/{id}/groups/roles", proxies=self.proxyDict).json()

        except:

            self.rotateProxy()
            return self.get_groups(cookie)

        choice = random.randint(0, 1)
        if choice == 0:
            return [cookie, {"userid": id, "userRobux": userRobux}] + [group['group'] for group in r['data']]
        else:
            return [cookie, {"userid": id, "userRobux": userRobux}] + [group['group'] for group in r['data'][::-1]]

    def write_to_log(self, groupid, robux, username):

        self.log_file = open('logs.txt', 'a+')
        logging.info(f"Logging {groupid}, {robux}, {username}")
        self.log_file.write(f"{username}:{robux}:{groupid}:{time.time()}\n")
        logging.info("SUCCESS!")
        self.log_file.close()

    def initialize_json(self):
        with open("data.json") as file:

            datafile = json.load(file)

            for cookie in self.roblosecurities:
                try:
                    r = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookie,
                                        proxies=self.proxyDict).json()
                    

                    datafile['users'].append(r)

                except:
                    self.rotateProxy()
                    r = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookie,
                                        proxies=self.proxyDict).json()
                    

                    datafile['users'].append(r)

    def available_to_refresh(self, groupid):
        self.log_file = open('logs.txt', 'r')
        for line in self.log_file.readlines():
            
            if f"{groupid}" in line:
                
                if int(line.split(":")[-1]) < time.time() - (3600 * self.DOWNTIME_BETWEEN_CHECKS):
                    logging.info("Int split True")
                    self.log_file.close()
                    return True
                else:
                    logging.info("Int split False")
                    self.log_file.close()
                    return False
            else:
                logging.info("Groupid not in line, returning True")
                self.log_file.close()
                return True

    

        

        




if __name__ == '__main__':
    ___ = ___()
    Groupfunds = GroupFunds()



