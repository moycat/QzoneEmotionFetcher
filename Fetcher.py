# -*- coding: utf-8 -*-

import re
import json
import os
import sys
import datetime
import time
import logging
from HttpClient import HttpClient

# 每页保存后休息时间（秒）
fetchFrequency = 0.2
# 每次抓取条数
fetchAmount = 20

Client = HttpClient()
Referer = 'http://user.qzone.qq.com/'
QzoneLoginUrl = 'http://xui.ptlogin2.qq.com/cgi-bin/xlogin?proxy_url=http%3A//qzs.qq.com/qzone/v6/portal/proxy.html&daid=5&pt_qzone_sig=1&hide_title_bar=1&low_login=0&qlogin_auto_login=1&no_verifyimg=1&link_target=blank&appid=549000912&style=22&target=self&s_url=http%3A%2F%2Fqzs.qq.com%2Fqzone%2Fv5%2Floginsucc.html%3Fpara%3Dizone&pt_qr_app=%E6%89%8B%E6%9C%BAQQ%E7%A9%BA%E9%97%B4&pt_qr_link=http%3A//z.qzone.com/download.html&self_regurl=http%3A//qzs.qq.com/qzone/v6/reg/index.html&pt_qr_help_link=http%3A//z.qzone.com/download.html'

# [%s %s %d %d %d] => [QQ号 QQ号 开始条数 抓取条数 g_tk]
EmotionURL = "http://h5.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6?uin=%s&inCharset=utf-8&outCharset=utf-8&hostUin=%s&notice=0&sort=0&pos=%d&num=%d&cgi_host=http://taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6&code_version=1&format=jsonp&need_private_comment=1&g_tk=%d"

logging.basicConfig(filename='log.log', level=logging.ERROR,
                    format='%(asctime)s  %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
output = None

# -----------------
# 工具函数
# -----------------
def e(msg, level = "info", output = True):
    if not level == "":
        getattr(logging, level)(msg)
    else:
        level = "info"
    if output:
        print time.strftime("[%Y-%m-%d %X] ", time.localtime()) +\
              "[" + level + "] " + msg


def getURL(start, fetch = fetchAmount):
    return EmotionURL % (qq.UID, qq.UID, start, fetch, qq.gtk)



def date_to_millis(d):
    return int(time.mktime(d.timetuple())) * 1000


def getReValue(html, rex, er, ex):
    v = re.search(rex, html)
    if v is None:
        e(er, "error")
        if ex:
            raise Exception, er
        return ''
    return v.group(1)


def utf8_unicode(c):
    if len(c) == 1:
        return ord(c)
    elif len(c) == 2:
        n = (ord(c[0]) & 0x3f) << 6
        n += ord(c[1]) & 0x3f
        return n
    elif len(c) == 3:
        n = (ord(c[0]) & 0x1f) << 12
        n += (ord(c[1]) & 0x3f) << 6
        n += ord(c[2]) & 0x3f
        return n
    else:
        n = (ord(c[0]) & 0x0f) << 18
        n += (ord(c[1]) & 0x3f) << 12
        n += (ord(c[2]) & 0x3f) << 6
        n += ord(c[3]) & 0x3f
        return n


def getGTK(skey):
    hash = 5381
    for i in range(0, len(skey)):
        hash += (hash << 5) + utf8_unicode(skey[i])
    return hash & 0x7fffffff


# -----------------
# 页面类
# -----------------

class Emotion():
    __count = 0

    id = 0
    tid = ""
    content = ""
    post_time = 0
    secret = False
    source = ""
    likes = list()


    def __init__(self, emotion):
        self.id = Emotion.__count
        Emotion.__count += 1
        self.tid = emotion["tid"]
        self.content = emotion["content"].encode("UTF8")
        self.post_time = emotion["created_time"]
        self.secret = (emotion["secret"] == 1)
        self.source = emotion["source_name"].encode("UTF8")
        #self.likes


# -----------------
# 页面类
# -----------------
class Page():
    start = 0
    amount = 0
    URL = ""
    data = []

    def __init__(self, start, amount = fetchAmount):
        self.start = int(start)
        self.amount = int(amount)
        self.URL = getURL(start, amount)

    def fetch(self):
        raw_data = ""
        while len(raw_data) < 12 or not raw_data.startswith("_Callback("):
            raw_data = Client.Get(self.URL)
        self.data = json.loads(raw_data[10:-2])
        return self.data


# -----------------
# 登录类
# -----------------
class Login(HttpClient):
    MaxTryTime = 5
    skey = 0
    UID = 0
    gtk = 0

    def __init__(self, vpath):
        global output
        self.VPath = vpath  # QRCode保存路径
        e("Fetching Login Page...", "critical")
        self.setCookie('_qz_referrer', 'qzone.qq.com', 'qq.com')
        self.Get(QzoneLoginUrl, 'http://qzone.qq.com/')
        StarTime = date_to_millis(datetime.datetime.utcnow())
        T = 0
        ret = []
        while True:
            T = T + 1
            self.Download('http://ptlogin2.qq.com/ptqrshow?appid=549000912&e=2&l=M&s=3&d=72&v=4&daid=5', self.VPath)
            LoginSig = self.getCookie('pt_login_sig')
            e('[{0}] Got QR Code! Scan "v.png" with Your Mobile QQ.'.format(T), "info")
            while True:
                html = self.Get(
                    'http://ptlogin2.qq.com/ptqrlogin?u1=http%3A%2F%2Fqzs.qq.com%2Fqzone%2Fv5%2Floginsucc.html%3Fpara%3Dizone&ptredirect=0&h=1&t=1&g=1&from_ui=1&ptlang=2052&action=0-0-{0}&js_ver=10131&js_type=1&login_sig={1}&pt_uistyle=32&aid=549000912&daid=5&pt_qzone_sig=1'.format(
                        date_to_millis(datetime.datetime.utcnow()) - StarTime, LoginSig), QzoneLoginUrl)
                ret = html.split("'")
                if len(ret) > 1 and (ret[1] == '65' or ret[1] == '0'):  # 65: QRCode 失效, 0: 验证成功, 66: 未失效, 67: 验证中
                    break
                time.sleep(2)
            # DEBUG
            if ret[1] == '0' or T > self.MaxTryTime:
                break

        if ret[1] != '0':
            raise ValueError, "QR RetCode = " + ret[1]
        e("QR Picture Scanned, Logging in...", "critical")

        # 删除QRCode文件
        if os.path.exists(self.VPath):
            os.remove(self.VPath)

        # 记录登录账号的昵称
        tmpUserName = ret[11]

        self.Get(ret[5])
        self.UIN = getReValue(ret[5], r'uin=([0-9]+?)&', 'Fail to get the QQ number!', 1)
        self.skey = self.getCookie('p_skey')
        self.gtk = getGTK(self.skey)
        e("Logging in Successfully! QQ Number: " + str(self.UIN), "")
        e("Logging in Successfully! QQ Number: " + str(self.UIN) +\
          " Nickname: " + tmpUserName, "critical", False)
        output = open(self.UIN + ".out", "w")


# -----------------
# 主函数
# -----------------
def welcome():
    global total
    account_data_page = Page(0, 1)
    account_data = account_data_page.fetch()
    total = int(account_data["total"])
    print ""
    e("Total: " + str(total))
    print "Press Enter to Start Fetching..."
    tmp = raw_input()


# -----------------
# 主程序
# -----------------
if __name__ == "__main__":
    vpath = './v.png'

    try:
        qq = Login(vpath)
    except Exception, exp:
        e(str(e), "critical")
        sys.exit(1)
    errtime = 0
    welcome()

    now_id = 0
    while now_id + fetchAmount < total:
        try:
            if errtime > 5:
                break

            this_page = Page(now_id)
            data = this_page.fetch()
            emotions = data["msglist"]
            for emotion in emotions:
                this_emotion = Emotion(emotion)
                output.write("ID: " + str(this_emotion.id) + "\nPost time: " +
                             str(this_emotion.post_time) + "\nContent:\n" +
                             this_emotion.content + "\nFrom: " + this_emotion.source + "\n\n")

            output.flush()
            e("Successfully Output Emotions %d to %d" %
              (now_id, now_id + fetchAmount), "info")
            time.sleep(fetchFrequency)
            errtime = 0
        except Exception, exp:
            e("Fetching %d to %d" % (now_id, now_id + fetchAmount) + str(exp), "error")
            errtime = errtime + 1
        now_id += fetchAmount