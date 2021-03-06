#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys,io,base64
import traceback
import requests, time, re
import thread, subprocess
import json, xml.dom.minidom, mimetypes
import config, storage, out, tools,conf
from PIL import Image as pilimgtools, ImageTk  
from tkMessageBox import *
from PyQt4 import QtCore, QtGui
BASE_URL = config.BASE_URL


class client(object):
    def __init__(self):
        self.storageClass = storage.Storage()
        self.memberList = self.storageClass.memberList
        self.chatroomList = self.storageClass.chatroomList
        self.msgList = self.storageClass.msgList
        self.loginInfo = {}
        self.s = requests.Session()
        self.uuid = None
        self.downloadselfheadimg=True
    def auto_login(self,signal_p,signal_m):
        def open_QR():
            for get_count in range(10):
                print 'get QR-UUID'
                while not self.get_QRuuid(): time.sleep(1)
                print 'generate QR-Code Image'
                if self.get_QR(): break
                elif get_count >= 9:
                    print('Failed to get QR Code, please restart the program')
                    sys.exit()
            print('Please scan the QR Code')
        print '#######################start to bootstrap sys!#########################'
        print 'open QR-code'
        open_QR()
        signal_p([conf.QR_Path,conf.QR_width,conf.QR_height],1)
        print '#show Login UI'
        print '#########################scan the QR Code###############################'
        while 1:
            status = self.check_login(signal_=signal_p)
            if status == '200':
                signal_p([conf.updatedata],2)
                break
            elif status == '201':
                signal_p([conf.pleaselogin],2)
                out.print_line('content QR Code\n', True)
            elif status == '408':
                out.print_line('Reloading QR Code\n', True)
                signal_p([conf.qrreset],2)
                open_QR()
                signal_p([conf.QR_Path,conf.QR_width,conf.QR_height],1)
        print '########################### init login info #############################'
        print '#get login user info '
        userinfo=self.web_init()
        print userinfo
        print '#get mobile login info '
        self.show_mobile_login()
        #tools.clear_screen()
        print '###################get contract and chatrooms info #######################'
        print '#get contracts data! '
        contractslist=self.get_contract()
        print '#get chatrooms data! '
        chatrooms=self.get_chatrooms()
        for m in contractslist:
           if os.path.exists(os.path.join('dist',m["UserName"])):
              print 'file is exists'
           else:
              print 'download head image '+ m["UserName"]
              temp=self.get_head_img(m["UserName"]) 
              with open(os.path.join('dist',m["UserName"]), 'wb') as f:
                 for block in temp.iter_content(1024):
                     f.write(block)
        for m in chatrooms:
            if os.path.exists(os.path.join('dist',m["UserName"])):
                print 'file is exists'
            else:
                print 'download head image '+ m["UserName"]
                temp=self.get_head_img(m["UserName"]) 
                with open(os.path.join('dist',m["UserName"]), 'wb') as f:
                     for block in temp.iter_content(1024):
                         f.write(block)
        if self.downloadselfheadimg:
            print '#download self head image! '
            try:
                temp=self.getself_head_img(userinfo["HeadImgUrl"],userinfo["UserName"]) 
                im = pilimgtools.open(io.BytesIO(temp))
                im.save(os.path.join('dist',userinfo['UserName']),'png')
            except Exception:
                print u'加载自己的头像失败： '
        else:
            print '#self head image has download ! '
            im = pilimgtools.open(os.path.join('dist','self'))
            im.save(os.path.join('dist',userinfo['UserName']),'png')
        print '#init main ui data ! '
        signal_p([userinfo,contractslist,chatrooms],3)
        out.print_line('Login successfully as %s\n'%(self.storageClass.find_nickname(self.storageClass.userName)), False)
        print '#start to  receiving message! '
        self.start_receiving(signal_m)
    def get_QRuuid(self):
        url = '%s/jslogin'%BASE_URL
        payloads = {
            'appid': 'wx782c26e4c19acffb',
            'fun': 'new',
        }
        r = self.s.get(url, params = payloads)

        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)";'
        data = re.search(regx, r.text)
        if data and data.group(1) == '200': 
            self.uuid = data.group(2)
            return self.uuid
    def get_QR(self,uuid = None):
        try:
            if uuid == None: uuid = self.uuid
            url = '%s/qrcode/%s'%(BASE_URL, uuid)
            r = self.s.get(url, stream = True)
            QR_DIR = os.path.join('dist','QR.jpg')
            with open(QR_DIR, 'wb') as f: f.write(r.content)
            return True
        except:
            return False
    def check_login(self, uuid = None,signal_ = None):
        if uuid is None: uuid = self.uuid
        url = '%s/cgi-bin/mmwebwx-bin/login'%BASE_URL
        payloads = 'loginicon=true&tip=1&uuid=%s&_=%s'%(uuid, int(time.time()))
        r = self.s.get(url, params = payloads)
        regx = r'window.code=(\d+)'
        data = re.search(regx, r.text)
        if data and data.group(1) == '200':
            os.remove(os.path.join('dist','QR.jpg'))
            regx = r'window.redirect_uri="(\S+)";'
            self.loginInfo['url'] = re.search(regx, r.text).group(1)
            r = self.s.get(self.loginInfo['url'], allow_redirects=False)
            self.loginInfo['url'] = self.loginInfo['url'][:self.loginInfo['url'].rfind('/')]
            self.loginInfo['BaseRequest'] = {}
            print r.text
            for node in xml.dom.minidom.parseString(r.text).documentElement.childNodes:
                if node.nodeName == 'skey':
                    self.loginInfo['skey'] = self.loginInfo['BaseRequest']['Skey'] = node.childNodes[0].data.encode('utf8')
                elif node.nodeName == 'wxsid':
                    self.loginInfo['wxsid'] = self.loginInfo['BaseRequest']['Sid'] = node.childNodes[0].data.encode('utf8')
                elif node.nodeName == 'wxuin':
                    self.loginInfo['wxuin'] = self.loginInfo['BaseRequest']['Uin'] = node.childNodes[0].data.encode('utf8')
                elif node.nodeName == 'pass_ticket':
                    self.loginInfo['pass_ticket'] = self.loginInfo['BaseRequest']['DeviceID'] = node.childNodes[0].data.encode('utf8')
            return '200'
        elif data and data.group(1) == '201':
            if self.downloadselfheadimg:
                    str_img=r.text.replace('window.code=201;window.userAvatar = \'data:img/jpg;base64,','').replace('\';','')
                    with open(os.path.join('dist','self'), 'wb') as f:f.write(base64.b64decode(str_img)  )
                    self.downloadselfheadimg=False
                    signal_([],4)
                    signal_([conf.Self_Image_Path,conf.Self_Image_Width,conf.Self_Image_Height],1)
            return '201'
        elif data and data.group(1) == '408':
            return '408'
        else:
            print data and data.group(1)
            return '0'
    def web_init(self):
        url = '%s/webwxinit?r=%s' % (self.loginInfo['url'], int(time.time()))
        payloads = {
            'BaseRequest': self.loginInfo['BaseRequest']
        }
        headers = { 'ContentType': 'application/json; charset=UTF-8' }
        r = self.s.post(url, data = json.dumps(payloads), headers = headers)
        dic = json.loads(r.content.decode('utf-8', 'replace'))
        # deal with emoji
        dic['User'] = tools.emoji_dealer([dic['User']])[0]
        self.storageClass.userName = dic['User']['UserName']
        self.storageClass.nickName = dic['User']['NickName']
        self.storageClass.memberList.append(dic['User'])
        self.loginInfo['SyncKey'] = dic['SyncKey']
        self.loginInfo['synckey'] = '|'.join(['%s_%s' % (item['Key'], item['Val']) for item in dic['SyncKey']['List']])
        
        return dic['User']
    def get_batch_contract(self, userName):
        url = '%s/webwxbatchgetcontact?type=ex&r=%s' % (self.loginInfo['url'], int(time.time()))
        headers = { 'ContentType': 'application/json; charset=UTF-8' }
        payloads = {
            'BaseRequest': self.loginInfo['BaseRequest'],
            'Count': 1,
            'List': [{
                'UserName': userName,
                'ChatRoomId': '', }], }
        j = self.s.post(url, data = json.dumps(payloads), headers = headers).json()['ContactList'][0]
        j['isAdmin'] = j['OwnerUin'] == int(self.loginInfo['wxuin'])
        return j
    def get_contract(self, update = False):
        def download_atta(attaDir):
            cookiesList = {name:data for name,data in self.s.cookies.items()}
            url = 'https://file%s.wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetmedia'%('2' if '2' in self.loginInfo['url'] else '')
            payloads = {
                'sender': m['FromUserName'],
                'mediaid': m['MediaId'],
                'filename': m['FileName'],
                'fromuser': self.loginInfo['wxuin'],
                'pass_ticket': 'undefined',
                'webwx_data_ticket': cookiesList['webwx_data_ticket'],}
            r = self.s.get(url, params = payloads, stream = True)
            with open(attaDir, 'wb') as f:
                for block in r.iter_content(1024):
                    f.write(block)
        if 1 < len(self.memberList) and not update: return self.memberList
        
        url = '%s/webwxgetcontact?r=%s&seq=0&skey=%s' % (self.loginInfo['url'],int(time.time()), self.loginInfo['skey'])
        headers = { 'ContentType': 'application/json; charset=UTF-8' }
        r = self.s.get(url, headers = headers)
        memberList = json.loads(r.content.decode('utf-8', 'replace'))['MemberList']
        chatroomList = memberList[:]
        while 1:
            i = 0
            for m in chatroomList:
                if ('@@' in m['UserName'] and any([str(n) in m['UserName'] for n in range(10)]) and
                    any([chr(n) in m['UserName'] for n in (range(ord('a'), ord('z') + 1) + range(ord('A'), ord('Z') + 1))])):
                    continue
                else:chatroomList.remove(m);i+=1
            for m in memberList:
                if m['Sex'] != 0 or (m['VerifyFlag'] & 8 == 0 and '@' in m['UserName'] and not '@@' in m['UserName'] and
                    any([str(n) in m['UserName'] for n in range(10)]) and any([chr(n) in m['UserName'] for n in (
                        range(ord('a'), ord('z') + 1) + range(ord('A'), ord('Z') + 1))])): 
                    continue
                else:
                    memberList.remove(m);i+=1
            if i == 0: break
        # deal with emoji
        self.memberList = tools.emoji_dealer(memberList)
        self.chatroomList = chatroomList
        return memberList
    def get_chatrooms(self, update = False):
        if update: self.get_contract(update = True)
        return self.chatroomList
    def show_mobile_login(self):
        url = '%s/webwxstatusnotify'%self.loginInfo['url']
        payloads = {
                'BaseRequest': self.loginInfo['BaseRequest'],
                'Code': 3,
                'FromUserName': self.storageClass.userName,
                'ToUserName': self.storageClass.userName,
                'ClientMsgId': int(time.time()),
                }
        headers = { 'ContentType': 'application/json; charset=UTF-8' }
        r = self.s.post(url, data = json.dumps(payloads), headers = headers)
        print r.content.decode('utf-8', 'replace')
    def start_receiving(self,signal_m):
        def maintain_loop():
            i = self.__sync_check()
            count = 0
            pauseTime = 1
            while i and count <4:
                try:
                    if pauseTime < 5: pauseTime += 2
                    if i != '0': msgList = self.__get_msg()
                    if msgList: 
                        msgList = self.__produce_msg(msgList)

                        signal_m(msgList)
                        #for msg in msgList: 
                            #self.msgList.insert(0, msg)
                            
                        pauseTime = 1
                    time.sleep(pauseTime)
                    i = self.__sync_check()
                    count = 0
                except Exception, e:
                    count += 1
                    time.sleep(count*3)
            out.print_line('LOG OUT', False)
        thread.start_new_thread(maintain_loop, ())
    def __sync_check(self):
        url = '%s/synccheck'%self.loginInfo['url']
        payloads = {
                'r': int(time.time()),
                'skey': self.loginInfo['skey'],
                'sid': self.loginInfo['wxsid'],
                'uin': self.loginInfo['wxuin'],
                'deviceid': self.loginInfo['pass_ticket'],
                'synckey': self.loginInfo['synckey'],
                }
        r = self.s.get(url, params = payloads)

        regx = r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}'
        pm = re.search(regx, r.text)

        if pm.group(1) != '0' : return None
        return pm.group(2)
    def __get_msg(self):
        url = '%s/webwxsync?sid=%s&skey=%s'%(
            self.loginInfo['url'], self.loginInfo['wxsid'], self.loginInfo['skey'])
        payloads = {
            'BaseRequest': self.loginInfo['BaseRequest'],
            'SyncKey': self.loginInfo['SyncKey'],
            'rr': int(time.time()), }
        headers = { 'ContentType': 'application/json; charset=UTF-8' }
        r = self.s.post(url, data = json.dumps(payloads), headers = headers)

        dic = json.loads(r.content.decode('utf-8', 'replace'))
        self.loginInfo['SyncKey'] = dic['SyncKey']
        if dic['AddMsgCount'] != 0: return dic['AddMsgList']
    def __produce_msg(self, l):
        rl = []
        srl = [40, 43, 50, 52, 53, 9999]
        # 40 msg, 43 videochat, 50 VOIPMSG, 52 voipnotifymsg, 53 webwxvoipnotifymsg, 9999 sysnotice
        for m in l:
            if '@@' in m['FromUserName']: m = self.__produce_group_chat(m)
            if m['MsgType'] == 1: # words
                if m['Url']:
                    regx = r'(.+?\(.+?\))'
                    data = re.search(regx, m['Content'])
                    msg = {
                        'Type': 'Map',
                        'Text': data.group(1),}
                else:
                    msg = {
                        'Type': 'Text',
                        'Text': m['Content'],}
            elif m['MsgType'] == 3 or m['MsgType'] == 47: # picture
                def download_picture(picDir):
                    url = '%s/webwxgetmsgimg'%self.loginInfo['url']
                    payloads = {
                        'MsgID': m['NewMsgId'],
                        'skey': self.loginInfo['skey'],}
                    r = self.s.get(url, params = payloads, stream = True)
                    with open(picDir, 'wb') as f:
                        for block in r.iter_content(1024):
                            f.write(block)
                msg = {
                    'Type': 'Picture',
                    'Text': download_picture,}
            elif m['MsgType'] == 34: # voice
                def download_voice(voiceDir):
                    url = '%s/webwxgetvoice'%self.loginInfo['url']
                    payloads = {
                        'msgid': m['NewMsgId'],
                        'skey': self.loginInfo['skey'],}
                    r = self.s.get(url, params = payloads, stream = True)
                    with open(voiceDir, 'wb') as f:
                        for block in r.iter_content(1024):
                            f.write(block)
                msg = {
                    'Type': 'Recording',
                    'Text': download_voice,}
            elif m['MsgType'] == 37: # friends
                msg = {
                    'Type': 'Friends',
                    'Text': {
                        'Status': m['Status'],
                        'UserName': m['RecommendInfo']['UserName'],
                        'Ticket': m['Ticket'], }, }
            elif m['MsgType'] == 42: # name card
                msg = {
                    'Type': 'Card',
                    'Text': m['RecommendInfo'], }
            elif m['MsgType'] == 49: # sharing
                if m['AppMsgType'] == 6:
                    def download_atta(attaDir):
                        cookiesList = {name:data for name,data in self.s.cookies.items()}
                        url = 'https://file%s.wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetmedia'%('2' if '2' in self.loginInfo['url'] else '')
                        payloads = {
                            'sender': m['FromUserName'],
                            'mediaid': m['MediaId'],
                            'filename': m['FileName'],
                            'fromuser': self.loginInfo['wxuin'],
                            'pass_ticket': 'undefined',
                            'webwx_data_ticket': cookiesList['webwx_data_ticket'],}
                        r = self.s.get(url, params = payloads, stream = True)
                        with open(attaDir, 'wb') as f:
                            for block in r.iter_content(1024):
                                f.write(block)
                    msg = {
                        'Type': 'Attachment',
                        # 'FileName': m['FileName'],
                        'Text': download_atta, }
                elif m['AppMsgType'] == 17:
                    msg = {
                        'Type': 'Note',
                        'Text': m['FileName'], }
                elif m['AppMsgType'] == 2000:
                    regx = r'\[CDATA\[(.+?)\].+?\[CDATA\[(.+?)\]'
                    data = re.search(regx, m['Content'])
                    msg = {
                        'Type': 'Note',
                        'Text': data.group(2), }
                else:
                    msg = {
                        'Type': 'Sharing',
                        'Text': m['FileName'], }
            elif m['MsgType'] == 51: # phone init
                msg = {
                    'Type': 'Init',
                    'Text': m['ToUserName'], }
            elif m['MsgType'] == 62: # tiny video
                def download_video(videoDir):
                    url = '%s/webwxgetvideo'%self.loginInfo['url']
                    payloads = {
                        'msgid': m['MsgId'],
                        'skey': self.loginInfo['skey'],}
                    headers = { 'Range:': 'bytes=0-'}
                    r = self.s.get(url, params = payloads, headers = headers, stream = True)
                    with open(videoDir, 'wb') as f: 
                        for chunk in r.iter_content(chunk_size = 1024):
                            if chunk:
                                f.write(chunk)
                                f.flush()
                                os.fsync(f.fileno())
                msg = {
                    'Type': 'Video',
                    'Text': download_video, }
            elif m['MsgType'] == 10000:
                msg = {
                    'Type': 'Note',
                    'Text': m['Content'],}
            elif m['MsgType'] == 10002:
                regx = r'\[CDATA\[(.+?)\]\]'
                data = re.search(regx, m['Content'])
                msg = {
                    'Type': 'Note',
                    'Text': data.group(1).replace('\\', ''), }
            elif m['MsgType'] in srl:
                msg = {
                    'Type': 'Useless',
                    'Text': 'UselessMsg', }
            else:
                out.print_line('MsgType Unknown: %s\n%s'%(m['MsgType'], str(m)), False)
                srl.append(m['MsgType'])
                msg = {
                    'Type': 'Useless',
                    'Text': 'UselessMsg', }
            m = dict(m, **msg)
            rl.append(m)
        return rl
    def __produce_group_chat(self, msg):
        def get_msg_from_raw(content):
            regex = re.compile('(@[0-9a-z]*?):<br/>(.*)$')
            r = re.findall(regex, content)
            if r:
                return r[0][0], r[0][1]
            else:
                return '', content
        ActualUserName, Content = get_msg_from_raw(msg['Content'])
        isAt = self.storageClass.nickName in Content
        if '\342\200\205'.decode('utf8') in Content: Content = Content.split('\342\200\205'.decode('utf8'))[1]
        try:
            self.storageClass.groupDict[msg['FromUserName']][ActualUserName]
        except:
            groupMemberList = self.get_batch_contract(msg['FromUserName'])['MemberList']
            self.storageClass.groupDict[msg['FromUserName']] = {member['UserName']: member for member in groupMemberList}
        ActualNickName = self.storageClass.groupDict[msg['FromUserName']][ActualUserName]['NickName']
        additionalItems = {
            'ActualUserName': ActualUserName,
            'ActualNickName': ActualNickName,
            'isAt': isAt,
            'Content': Content, }
        return dict(msg, **additionalItems)
    def send_msg(self, msg = 'Test Message', toUserName = None):
        url = '%s/webwxsendmsg'%self.loginInfo['url']
        payloads = {
                'BaseRequest': self.loginInfo['BaseRequest'],
                'Msg': {
                    'Type': 1,
                    'Content': msg.encode('utf8') if isinstance(msg, unicode) else msg,
                    'FromUserName': self.storageClass.userName.encode('utf8'),
                    'ToUserName': (toUserName if toUserName else self.storageClass.userName).encode('utf8'),
                    'LocalID': int(time.time()),
                    'ClientMsgId': int(time.time()),
                    },
                }
        headers = { 'ContentType': 'application/json; charset=UTF-8' }
        r = self.s.post(url, data = json.dumps(payloads, ensure_ascii = False), headers = headers)
    def __upload_file(self, fileDir, isPicture = False):
        if not tools.check_file(fileDir): return
        url = 'https://file%s.wx.qq.com/cgi-bin/mmwebwx-bin/webwxuploadmedia?f=json'%('2' if '2' in self.loginInfo['url'] else '')
        # save it on server
        fileSize = str(os.path.getsize(fileDir))
        cookiesList = {name:data for name,data in self.s.cookies.items()}
        fileType = mimetypes.guess_type(fileDir)[0] or 'application/octet-stream'
        files = {
                'id': (None, 'WU_FILE_0'),
                'name': (None, os.path.basename(fileDir)),
                'type': (None, fileType),
                'lastModifiedDate': (None, time.strftime('%a %b %d %Y %H:%M:%S GMT+0800 (CST)')),
                'size': (None, fileSize),
                'mediatype': (None, 'pic' if isPicture else 'doc'),
                'uploadmediarequest': (None, json.dumps({
                    'BaseRequest': self.loginInfo['BaseRequest'],
                    'ClientMediaId': int(time.time()),
                    'TotalLen': fileSize,
                    'StartPos': 0,
                    'DataLen': fileSize,
                    'MediaType': 4,
                    }, separators = (',', ':'))),
                'webwx_data_ticket': (None, cookiesList['webwx_data_ticket']),
                'pass_ticket': (None, 'undefined'),
                'filename' : (os.path.basename(fileDir), open(fileDir, 'rb'), fileType),
                }
        headers = { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.80 Safari/537.36', }
        r = self.s.post(url, files = files, headers = headers)
        return json.loads(r.text)['MediaId']
    def send_file(self, fileDir, toUserName = None):
        if toUserName is None: toUserName = self.storageClass.userName
        mediaId = self.__upload_file(fileDir)
        if mediaId is None: return False
        url = '%s/webwxsendappmsg?fun=async&f=json'%self.loginInfo['url']
        payloads = {
                'BaseRequest': self.loginInfo['BaseRequest'],
                'Msg': {
                    'Type': 6,
                    'Content': ("<appmsg appid='wxeb7ec651dd0aefa9' sdkver=''><title>%s</title>"%os.path.basename(fileDir) +
                        "<des></des><action></action><type>6</type><content></content><url></url><lowurl></lowurl>" +
                        "<appattach><totallen>%s</totallen><attachid>%s</attachid>"%(str(os.path.getsize(fileDir)), mediaId) +
                        "<fileext>%s</fileext></appattach><extinfo></extinfo></appmsg>"%os.path.splitext(fileDir)[1].replace('.','')
                        ).encode('utf8'),
                    'FromUserName': self.storageClass.userName.encode('utf8'),
                    'ToUserName': toUserName.encode('utf8'),
                    'LocalID': str(time.time() * 1e7),
                    'ClientMsgId': str(time.time() * 1e7), }, }
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.80 Safari/537.36',
            'Content-Type': 'application/json;charset=UTF-8', }
        r = self.s.post(url, data = json.dumps(payloads, ensure_ascii = False), headers = headers)
        return True
    def send_image(self, fileDir, toUserName = None):
        if toUserName is None: toUserName = self.storageClass.userName
        mediaId = self.__upload_file(fileDir, isPicture = not fileDir[-4:] == '.gif')
        if mediaId is None: return False
        url = '%s/webwxsendmsgimg?fun=async&f=json'%self.loginInfo['url']
        payloads = {
                'BaseRequest': self.loginInfo['BaseRequest'],
                'Msg': {
                    'Type': 3,
                    'MediaId': mediaId,
                    'FromUserName': self.storageClass.userName.encode('utf8'),
                    'ToUserName': toUserName.encode('utf8'),
                    'LocalID': str(time.time() * 1e7),
                    'ClientMsgId': str(time.time() * 1e7), }, }
        if fileDir[-4:] == '.gif':
            url = '%s/webwxsendemoticon?fun=sys'%self.loginInfo['url']
            payloads['Msg']['Type'] = 47
            payloads['Msg']['EmojiFlag'] = 2
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.80 Safari/537.36',
            'Content-Type': 'application/json;charset=UTF-8', }
        r = self.s.post(url, data = json.dumps(payloads, ensure_ascii = False), headers = headers)
        return True
    def add_friend(self, Status, UserName, Ticket):
        url = '%s/webwxverifyuser?r=%s&pass_ticket=%s'%(self.loginInfo['url'], int(time.time()), self.loginInfo['pass_ticket'])
        payloads = {
            'BaseRequest': self.loginInfo['BaseRequest'],
            'Opcode': Status,
            'VerifyUserListSize': 1,
            'VerifyUserList': [{
                'Value': UserName,
                'VerifyUserTicket': Ticket,
                }],
            'VerifyContent': '',
            'SceneListCount': 1,
            'SceneList': 33,
            'skey': self.loginInfo['skey'],}
        headers = { 'ContentType': 'application/json; charset=UTF-8' }
        r = self.s.post(url, data = json.dumps(payloads), headers = headers)
    def create_chatroom(self, memberList, topic = ''):
        url = ('%s/webwxcreatechatroom?pass_ticket=%s&r=%s'%(
                self.loginInfo['url'], self.loginInfo['pass_ticket'], int(time.time())))
        params = {
            'BaseRequest': self.loginInfo['BaseRequest'],
            'MemberCount': len(memberList),
            'MemberList': [{'UserName': member['UserName']} for member in memberList],
            'Topic': topic, }
        headers = {'content-type': 'application/json; charset=UTF-8'}

        r = self.s.post(url, data=json.dumps(params),headers=headers)
        dic = json.loads(r.content.decode('utf8', 'replace'))
        return dic['ChatRoomName']
    def delete_member_from_chatroom(self, chatRoomName, memberList):
        url = ('%s/webwxupdatechatroom?fun=delmember&pass_ticket=%s'%(
            self.loginInfo['url'], self.loginInfo['pass_ticket']))
        params = {
            'BaseRequest': self.loginInfo['BaseRequest'],
            'ChatRoomName': chatRoomName,
            'DelMemberList': ','.join([member['UserName'] for member in memberList]),}
        headers = {'content-type': 'application/json; charset=UTF-8'}
        return self.s.post(url, data=json.dumps(params),headers=headers)
    def add_member_into_chatroom(self, chatRoomName, memberList):
        url = ('%s/webwxupdatechatroom?fun=addmember&pass_ticket=%s'%(
            self.loginInfo['url'], self.loginInfo['pass_ticket']))
        params = {
            'BaseRequest': self.loginInfo['BaseRequest'],
            'ChatRoomName': chatRoomName,
            'AddMemberList': ','.join([member['UserName'] for member in memberList]),}
        headers = {'content-type': 'application/json; charset=UTF-8'}
        r = self.s.post(url, data=json.dumps(params),headers=headers)
    def getself_head_img(self,headurl,username=None):
        params = {
            'userName': username or self.storageClass.userName,
            'skey': self.loginInfo['skey'],
            }
        # 'type': 'big',
        url = 'https://wx2.qq.com'+headurl
        headers = { 'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36' }
        r = self.s.get(url, params=params, stream=True, headers=headers)
        tempStorage = io.BytesIO()
        for block in r.iter_content(1024):
            tempStorage.write(block)
        return tempStorage.getvalue()
    def get_head_img(self, userName=None, chatroomUserName=None, picDir=None):

        params = {
            'userName': userName or chatroomUserName or self.storageClass.userName,
            'skey': self.loginInfo['skey'],
          }
#   'type': 'big',
        url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgeticon'
        
        headers = { 'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36' }
        r = self.s.get(url, params=params, stream=True, headers=headers)
        return r
        
        #tempStorage = io.BytesIO()
        #for block in r.iter_content(1024):
        #    tempStorage.write(block)
        #if picDir is None:
        #    return tempStorage.getvalue()
        #with open(picDir, 'wb') as f:
        #    f.write(tempStorage.getvalue())
        #tempStorage.seek(0)
        #return ReturnValue({'BaseResponse': {
        #    'ErrMsg': 'Successfully downloaded',
        #    'Ret': 0, },
        #    'PostFix': utils.get_image_postfix(tempStorage.read(20)), })
if __name__ == '__main__':
    wcc = WeChatClient()
    wcc.login()
