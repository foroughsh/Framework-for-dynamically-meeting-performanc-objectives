# https://realpython.com/python-concurrency/
import asyncio
import time
import random
import aiohttp
# import pika
import numpy as np

np.random.seed(0)

# The parameters of the load generator
MIN_INTERVAL = 0.05    # Minimum interval between two requests on the real system
CLIENTS_NO = 1
LD_ID = 1

def periodic_step(t, T, lam0, A):
    r = t % (2 * T)
    if (r < T):
        y = lam0 + A
    else:
        y = lam0 - A
    return y

def constant(t, T, lam0, A):
    return lam0

def poisson_modulated_by_f(name):

    Time = 7200
    t = 0
    k = 0
    intervals = []

    lam0 = 30
    A = 10
    T = 1200
    S = []

    lam = lam0 + A + 1

    S.append(t)
    t_old = 0

    while (t < Time):
        r = random.random()
        t = t - np.log(r) / lam
        if (t > Time):
            break
        s = random.random()
        # The average of the Poisson  process as a function (Poisson  process modulated by function f- constant or sin)
        lamT = constant(t, T, lam0, A)
        # A * np.sin((2 * np.pi * t) / (T))
        if (s<=(lamT / lam)):
            k = k + 1
            t_old = S[-1]
            S.append(t)
            intervals.append(t - t_old)
    interval_a = np.array(intervals)
    interval_a = interval_a
    print("min: ", min(interval_a))
    print("max: ", max(interval_a))
    print("avg: ", np.mean(interval_a))
    current_time = time.time()
    times = []
    times.append(current_time)
    delays = [interval_a[0]]
    sum_delays = interval_a[0]
    for i in range(len(interval_a)):
        current_time += interval_a[i]
        times.append(current_time)
        sum_delays += interval_a[i]
        delays.append(sum_delays)
    with open(name, 'w') as f:
        for item in times:
            f.write("%s\n" % item)
    f.close()
    return times, delays


# Generated load pattern saved in a file
timing, intervals = poisson_modulated_by_f("time_index_async_LG_pre.txt")

# Sending requests
async def do_find_one(wait_time, counter):
    custom_header = {"Accept": "*/*", "Connection": "keep-alive", "Cache-Control": "max-age=0",
                     "Upgrade-Insecure-Requests": "1", "Origin": "http://cluster-IP-address:30036",
                     "Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "http://cluster-IP-address:30036/searchpage?u=normal"}

    d = dict()
    d["username"] = "premium"
    d["passwd"] = "1234"
    jar = aiohttp.CookieJar(unsafe=True)
    await asyncio.sleep(wait_time)
    start = time.time()
    async with aiohttp.ClientSession(trust_env=True,headers=custom_header,requote_redirect_url=True, cookie_jar=jar) as session:
        sent_text = dict()
        async with session.post('http://cluster-IP-address:30036/login', data=d) as response:
            sent_text["timesentout"] = start
            sent_text["timestamp"] = time.time()
            sent_text["ID"] = counter
            sent_text["LD_ID"] = LD_ID
            with open("load_pre.txt","a") as load_file:
                load_file.write(str(sent_text)+"\n")
                load_file.flush()
            load_file.close()
            document = await response.text()
            print(document)
    end = time.time()
    sent_response = dict()
    sent_response["timestamp"] = str(time.time())
    sent_response["response"] = (end - start)
    sent_response["requestID"] = counter
    sent_response["LD_ID"] = LD_ID
    if ("(fetch2)" in document):
        sent_response["Node"] = 2
    elif ("(fetch3)" in document):
        sent_response["Node"] = 1
    else:
        sent_response["Node"] = 0
    if ("429 Too Many Requests" in document):
        sent_response["code"] = 429
    else:
        sent_response["code"] = 200
    print("start:{} response time:{}".format(str(start), str(end - start)))
    if (sent_response["response"] > 0):
        with open("response_foo.txt", "a") as response_file:
            response_file.write(str(sent_response) + "\n")
            response_file.flush()
    response_file.close()
    await session.close()


async def main():
    tasks = []
    print("max waiting time:{}".format(max(intervals)))
    counter = 0
    for j in intervals:
        counter += 1
        current_time = time.time()
        task = asyncio.ensure_future(do_find_one(j, counter))
        tasks.append(task)

    print("gather start")
    await asyncio.gather(*tasks, return_exceptions=True)
    print("gather end")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
