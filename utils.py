#!/usr/bin/python
import calendar
import csv
import datetime
import json
import logging
import os
import re
import shutil
import smtplib
import ssl
import telnetlib
import time
import traceback
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from glob import iglob
from pathlib import Path
import paramiko
import requests
import socket

# from utils_v2 import data

subsys_csv_fn = "m2_subsystem.csv"
contacts_fn = "m2_email_contacts.csv"
apiheaders = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-api-key': 'NjQ3M2VmZGY2YjgwNGJh',
    'Cookie': 'connect.sid=s%3AL5Oh8GP6pSzHhnCMx_xNSZQE_x-sLQ9F.mtpCtMWtpGLsm%2Fsz3BSgCxXbiKniGcB3S5zXxB9FPJQ'
}
token = 'ectivisecloudDBAuthCode%3Ab84846daf467cede0ee462d04bcd0ade'
timestamp_day = str(datetime.now().strftime("%Y%m%d"))
timestamp_date = str(datetime.now().strftime("%Y-%m-%d"))
timestamp_hour = str(datetime.now().strftime("%Y%m%d%H"))
dtime = str(datetime.now())
dtime = dtime[:-7]
cmd_fn = "ont_cmds_all.txt"
ip_fn = "ont_ip_all.txt"
ont_env_fn = "ont_env.json"
alllog_fn = "all.log"
output_fn = "ontinfo_test_ovh"
ontinfo_ovh_fn = "ontinfo_ovh"

debug = True
set_ip_name = False
checkPing = True
apendFile = False
ip_only = False

date_time = str(datetime.now().strftime("%Y-%m-%d"))
date_time1 = str(datetime.now().strftime("%Y%m%d"))
date_time_h = str(datetime.now().strftime("%Y-%m-%d %H:%M"))
time_stamp = str(datetime.now().strftime("%Y%m%d%H%m"))
ts = calendar.timegm(time.gmtime())
date_time_m = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

gponbasefn = "m2ontinfosum*.txt"
gponrootdir = "gponfiles"

logging.basicConfig(level=logging.DEBUG,
                    filename=alllog_fn,
                    # filename='ontinfo_ovh.log',
                    filemode='a',
                    format=
                    '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                    )


def pingOk(sHost):
    import subprocess, platform
    try:
        output = subprocess.check_output(
            "ping -{} 1 {}".format('n' if platform.system().lower() == "windows" else 'c', sHost), shell=True)
    except Exception as e:
        return False

    return True


def get_ont_name(the_rx_dict, the_lines):
    match = get_matched(the_rx_dict, the_lines, 'ont_name')
    if match:
        return match.string.split('#')[0]
    return None


def get_matched(the_rx_dict, the_lines, the_key):
    for line in the_lines:
        key, match = parse_line(the_rx_dict, line)
        if key == the_key:
            return match
    return None


def parse_line(rx_dict, line):
    """
    Do a regex search against all defined regexes and
    return the key and match result of the first matching regex
    """
    for key, rx in rx_dict.items():
        match = rx.search(line)
        if match:
            return key, match
    # if there are no matches
    return None, None


def validate_ipv4(ipv4, debug=False):
    import ipaddress
    import sys
    isIP = False
    try:
        ip = ipaddress.ip_address(ipv4)
        print('%s is a correct IP%s address.' % (ip, ip.version)) if debug else None
        isIP = True
    except ValueError as e:
        logging.error('address/netmask is invalid: %s' % sys.argv[1])
        # traceback.print_exc()
    finally:
        return isIP


def set_ip_json(input_all, rx_dict, ip):
    ont = {"ip": ip}
    lines = input_all.decode("utf-8")
    linesarr = ''.join(lines).split('\r\n')
    # n = get_ont_name(rx_dict, linesarr)
    ont["name"] = get_ont_name(rx_dict, linesarr)
    return ont


def cmd_scroll(tn, length=0):
    tn.write(b"scroll %s " % length + b"\n")
    tn.read_until(b":", 5)
    tn.write(b"" + b"\n")
    time.sleep(0.5)


def cmd_undoscroll(tn):
    tn.write(b"undo scroll" + b"\n")
    tn.read_until(b":", 5)
    tn.write(b"" + b"\n")
    time.sleep(0.5)


def filter_line(original, rekey=r'^\s*$'):
    return list(filter(lambda x: not re.match(rekey, x), original))


def ssh_login(hostip='192.168.190.5', port=22, user='nmsuser2', pwd='ESPL888espl'):
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostip, port=port, username=user, password=pwd, compress=True)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Successfully logged into OLT")
    command = ssh.invoke_shell()
    command.send("enable \n")
    command.send("scroll \n\n")
    return command


class GetONTInfo:
    format = "%d/%m/%Y %H:%M:%S"
    username = "root"
    unamepw = "mduadmin"
    cmdlist = []
    iplist = []
    iplist_json = []
    sleeptime = 1
    output_all = []
    output = []
    rx_dict = {
        'ont_name': re.compile(r'^.*#')
    }

    def __init__(self, output_fn, cmd_fn, ip_fn, username=None, unamepw=None):
        self.tn = None
        if username is not None:
            self.username = username
        if unamepw is not None:
            self.unamepw = unamepw
        self.output_fn = output_fn
        with open(cmd_fn, 'r') as _file:
            _file.seek(0)
            self.cmdlist = _file.readlines()
        with open(ip_fn, 'r') as _file:
            _file.seek(0)
            self.iplist = _file.readlines()
        _iplist = [ip.strip('\n') for ip in self.iplist]
        _cmdlist = [cmd.strip('\n') for cmd in self.cmdlist]
        _iplist = list(filter(lambda x: len(x) > 0, _iplist))
        _cmdlist = list(filter(lambda x: len(x) > 0, _cmdlist))
        self.iplist = [i.strip() for i in _iplist]
        self.cmdlist = [c.strip() for c in _cmdlist]
        # self.cmdlist.append("quit")
        # self.cmdlist.append("quit")
        # print(self.iplist)
        print(self.cmdlist)

    def get_result(self):
        try:
            for ipv4 in self.iplist:
                try:
                    # start ip loop
                    if ipv4 == '' or not validate_ipv4(ipv4):
                        print("This ip address %s is invalid" % ipv4)
                        logging.error("This ip address %s is invalid" % ipv4)
                        continue
                    if checkPing and not pingOk(ipv4):
                        print("Cannot ping this ip address %s " % ipv4)
                        logging.error("Cannot ping this ip address %s " % ipv4)
                        continue
                    _tn = None
                    try:
                        _tn = telnetlib.Telnet(ipv4)
                        _tn.read_until(b":", 5)
                        _tn.write(self.username.encode('ascii') + b"\n")
                        _tn.read_until(b":", 5)
                        _tn.write(self.unamepw.encode('ascii') + b"\n")
                        _tn.write(b" \n")
                        t = str(datetime.now().strftime(self.format))
                        print("Started logging %s @ " % ipv4 + t) if debug else None
                        # logging.info("Started logging %s @ " % ipv4 + t) if debug else None
                        _tn.write(b"enable" + b"\n")
                        # _tn.write(b"scroll" + b"\n")
                        # _tn.read_until(b":", 5)
                        # _tn.write(b"" + b"\n")
                        _tn.write(b"config" + b"\n")
                    except TimeoutError:
                        # not ruuning?
                        print('err 10110: telnet login time out IP=%s' % ipv4)
                        logging.error('err 10110: telnet login time out IP=%s' % ipv4)
                        _tn = None
                        # end except
                    # finally:
                    if _tn is None:
                        logging.error('err 101010: telnet login time out IP=%s' % ipv4)
                        continue
                    time.sleep(1)
                    for cmd in self.cmdlist:
                        if cmd == '':
                            continue
                        _cmd = cmd + "\r\n\n"
                        print("command = " + cmd) if debug else None
                        _tn.write(_cmd.encode('ascii'))
                        time.sleep(self.sleeptime)
                        self.output = _tn.read_very_eager()
                        self.output_all.append(self.output.decode('ascii'))
                        if apendFile:
                            # TODO: append ok, but need to know which node has been checked
                            # append to the file to save the temp results
                            # 1) may need a index list with status checked or not
                            # 2) also need to know it is RE-RUN or CONTINUE last running
                            # Save the status in local db? or local file?
                            # or go to currently
                            outputfn = self.output_fn + "_new.txt"
                            with open(outputfn, 'a') as f:
                                f.write(''.join(self.output_all))
                            # end apend file
                    _cmd = cmd + "quit\r\n\n"
                    _cmd = cmd + "y"
                    self.output = _tn.read_very_eager()
                    self.output_all.append(self.output.decode('ascii'))
                    t = str(datetime.now().strftime(self.format))
                    if set_ip_name:
                        o = set_ip_json(self.output, self.rx_dict, ipv4)
                        self.iplist_json.append(o)
                    if apendFile:
                        # TODO:  also append the ip json file
                        #        this file can be used for validate which devices have been scanned
                        pass
                    print("completed @ " + t) if debug else None
                    # logging.info("completed @ " + t) if debug else None
                    # end ip loop
                except Exception as e:
                    print('err0404: IP=%s' % ipv4)
                    logging.error('err0404: IP=%s' % ipv4)
                    # traceback.print_exc()
            print("------------------------------------------------------------------------------")
        except:
            traceback.print_exc()

    def save_results(self, fn=None):
        json_fn = "ont_ip.json"
        if fn is not None:
            self.output_fn = fn
        ts = calendar.timegm(time.gmtime())
        filename = self.output_fn + str(ts) + ".txt"

        try:
            if len(self.iplist_json) > 0:
                with open(json_fn, 'w') as f:
                    json.dump(self.iplist_json, f)
            if len(self.output_all) < 1:
                print("empty output")
                return
            result = ''.join(self.output_all)
            # print(result)
            if not ip_only:
                with open(filename, 'wb') as newfile:
                    print("------ output_all will be saved to " + filename) if debug else None
                    logging.info("------ output_all will be saved to " + filename) if debug else None
                    newfile.write(result.encode('ascii'))
        except Exception as e:
            # logging.error("err0202:" + e.strerror)
            traceback.print_exc()


def jsonfile_dump(allontlist, file_nm="opticsovh_ont.json"):
    if len(allontlist) < 0:
        print("empty data?")
        return
    with open(file_nm, 'w') as f:
        json.dump(allontlist, f)


def jsonfile_load(fn):
    # print("jsonfile_load:", fn)
    with open(fn, 'r') as f:
        try:
            jsonobject = json.load(f)
        except Exception as e:
            print("error", e, f)
    return jsonobject


def is_mdu(ont):
    return ont["status"] != "offline" and ont["type"] in ["5626", "EA5821"]


def read_csv(filename):
    with open(filename, 'r') as f:
        # reads csv into a list of lists
        lines = csv.reader(f, delimiter=',')
        return list(lines)[1:]  # removes the header row # removes the header


def write_csv(row_list, filename):
    """
    format:
    row_list = [["SN", "Name", "Contribution"],
             [1, "Linus Torvalds", "Linux Kernel"],
             [2, "Tim Berners-Lee", "World Wide Web"],
             [3, "Guido van Rossum", "Python Programming"]]
    :param datelines:
    :param filename:
    :return:
    """
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(row_list)


# use tuple format
def write_csv1(datalines, filename):
    with open(filename, 'w') as csvfile:
        fieldnames = ['first_name', 'last_name']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerow({'first_name': 'Baked', 'last_name': 'Beans'})
        writer.writerow({'first_name': 'Lovely', 'last_name': 'Spam'})
        writer.writerow({'first_name': 'Wonderful', 'last_name': 'Spam'})


# write directly into the file
def write_csv2(*argv, filename):
    for arg in argv:
        print(arg)
    # TODO how to extract the columes
    # np.savetxt('data.csv', (col1_array, col2_array, col3_array), delimiter=',')


def write_csv3(lines, filename):
    with open(filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        for line in lines:
            csvwriter.writerow(line)


def func(*args):
    x = []  # emplty list
    for i in args:
        i = i * 2
        x.append(i)
        y = tuple(x)  # converting back list into tuple
    return y


def concatenate(**kwargs):
    result = ""
    # Iterating over the Python kwargs dictionary
    for arg in kwargs.values():
        result += arg
    return result


# print(concatenate(a="Real", b="Python", c="Is", d="Great", e="!"))

def get_vlandata(site: str):
    vlan_data = jsonfile_load('uob_vlan.json')
    if site.find('feb') > -1:
        _site = 'feb'
    if site.find('m2') > -1:
        _site = 'm2'
    return vlan_data[_site]


def clean_data(data, fsp, ontid, vlanid):
    # Process csv into python readable format
    # data = read_csv(filename)

    # Check that none of the column is empty
    data = list(
        filter(lambda x: x[0] != "" and x[1] != "" and x[2] != "" and x[3] != "" and x[4] != "" and x[5] != "", data))
    # another way using a second filter
    # data = list(filter(lambda x: len(list(filter(lambda y:y!="",x)))==6,data))

    # Check that movie is within timespan
    # data = list(filter(lambda x: 1990<= int(x[5])<=2019, data))
    data = list(filter(lambda x: x[0] == fsp and x[1] == ontid, data))

    # Check that movie rating is within range
    data = list(filter(lambda x: 0 <= float(x[4]) <= 10, data))

    # Check that movie rating is higher than 9
    data = list(filter(lambda x: float(x[4]) >= 9, data))

    # Returns only a list of movie names
    return list(map(lambda x: x[3], data))


def set_env():
    """
    # read env file
    # https://stackoverflow.com/questions/40216311/reading-in-environment-variables-from-an-environment-file
    :return:
    """
    with open('token.txt', 'r') as fh:
        vars_dict = dict(tuple((line.strip().split('='))) for line in fh.readlines() if not line.startswith('#'))
    os.environ.update(vars_dict)


def read_txt_file():
    env_vars = []
    with open("token.txt") as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            key, value = line.strip().split('=', 1)
            env_vars.append({'name': key, 'value': value})
    return env_vars


def sendmails(content_fn='m2_subsystem.csv', contacts_file_fn="m2_email_contacts.csv"):
    global email
    subject = "M2 Sub-system Summary of the day"
    with open(contacts_file_fn) as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row
        for name, email in reader:
            print(format(datetime.now().strftime("%Y-%m-%d %H:%M")),
                  f"Sending email to {name}")
            mailbody = ""
            lines = open(content_fn).readlines()
            mailbody += ''.join(lines)
            send_email(mailbody)
            time.sleep(5)


def send_email(mailbody, email_address='liqin@hotmail.sg', subject='M2 Sub-system Summary of the day'):
    port = 587  # For starttls
    smtp_server = "smtp.gmail.com"
    sender_email = "ectiviseservice@gmail.com"
    receiver_email = email_address
    password = "ESPL888espl"
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    part2 = MIMEText(mailbody, "html")
    message.attach(part2)
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        try:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        except smtplib.SMTPException:
            print("Error: unable to get email")


def get_filename(base_filenm):
    file_list = [optic_fn for optic_fn in iglob(base_filenm) if os.path.isfile(optic_fn)]
    root_dir = './'
    try:
        assert len(file_list) > 0, 'no file found'
        return file_list[len(file_list) - 1]
    except:
        pass


def get_filename_data_fullpath(base_filenm, root_dir='.\\', lastone=-1):
    _basefilenm = '.\\%s\\%s' % (root_dir, base_filenm)
    file_list = [optic_fn for optic_fn in iglob(_basefilenm)]
    if len(file_list) > lastone + 1:
        fn = file_list[len(file_list) + lastone]
        jsonobj = jsonfile_load(fn)
        return fn, jsonobj


def get_2filename(base_filenm):
    file_list = [optic_fn for optic_fn in iglob(base_filenm) if os.path.isfile(optic_fn)]
    assert len(file_list) > 0, 'no file found'
    return file_list[len(file_list) - 1], file_list[len(file_list) - 2]


def read_file(filename):
    with open(filename, 'r') as FILE:
        return FILE.readlines()


def read_csv_file(csv_fn):
    data = []
    try:
        with open(csv_fn, encoding='utf-8') as csvf:
            csvReader = csv.DictReader(csvf)
            for rows in csvReader:
                d = {}
                for k, v in rows.items():
                    # print(k,v)
                    d[k] = v
                data.append(d)
    except:
        print(csv_fn)
    finally:
        return data


def gmsend(email_address, mailbody):
    port = 587  # For starttls
    smtp_server = "smtp.gmail.com"
    sender_email = "ectiviseservice@gmail.com"
    # receiver_email = "nmsectivise@gmail.com"
    receiver_email = email_address
    password = "ESPL888espl"
    message = MIMEMultipart("alternative")
    message["Subject"] = "M2 Sub System Summary update "
    part2 = MIMEText(mailbody, "html")
    message.attach(part2)
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        try:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        except smtplib.SMTPException:
            print("Error: unable to send email to %s" % email_address)
            traceback.print_exc()


def copy_file(src, dst):
    shutil.copyfile(src, dst)


def textfile_read(input_txt_fn):
    with open(input_txt_fn, 'r') as _file:
        _file.seek(0)
        ontinfo_txt_lines = _file.readlines()
    return ontinfo_txt_lines


def textfile_write(out_txt_fn, txtdata):
    with open(out_txt_fn, 'w') as _file:
        _file.write(txtdata)


def get_session(un='nmsuser2'):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname='192.168.190.5', port=22, username=un, password='ESPL888espl', compress=True)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Successfully logged into OLT")
    command = ssh.invoke_shell()
    command.send("enable \n")
    command.send("scroll \n\n")
    return command, ssh


def get_session_v2(ipv4='192.168.190.5', un='nmsuser2', pwd='ESPL888espl'):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ipv4, port=22, username=un, password=pwd, compress=True)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print("Successfully logged into OLT %s" % ipv4)
        command = ssh.invoke_shell()
        command.send("enable \n")
        command.send("scroll \n\n")

        assert command is not None
        assert ssh is not None

        return command, ssh
    except:
        return None, None


def telegram_bot_sendtext(bot_message, parse_mode='Markdownv2',
                          bot_token='1064925388%3AAAFH1YRPLABL6lq9rqrdtlIopsJIypJZWhg', bot_chatID='-409097351',
                          dbg=False):
    send_text = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&parse_mode=%s&text=%s' % (
        bot_token, bot_chatID, parse_mode, bot_message)
    response = requests.get(send_text)
    msg = response.json()
    msg = msg['ok']
    print(response.text) if dbg else None
    return msg


def send_telegram_api(msg='[TEST MSG,PLS IGNORE 20210918-02]',
                      teletoken='1064925388%3AAAFH1YRPLABL6lq9rqrdtlIopsJIypJZWhg', chatid='-409097351', mydebug=True):
    url = "https://telegrambot.ectivisecloud.com/v2/telegrambot"

    payload = 'token=%s&chatid=%s&message=%s' % (teletoken, chatid, msg)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text) if mydebug else None


def full_filename(base_fn='m2ontinfosum%s.txt' % ts, root_dir='gponfiles'):
    return '.\\%s\\%s' % (root_dir, base_fn)


def full_filename_alarm(base_fn='m2ontinfosum%s.txt' % ts, root_dir='alarmfiles'):
    return '.\\%s\\%s' % (root_dir, base_fn)


class FileName:
    def __init__(self, base_fn='m2ontinfosum%s.txt' % ts, root_dir='gponfiles'):
        self.full_fn = '.\\%s\\%s' % (root_dir, base_fn)

    @property
    def full_name(self):
        return self.full_fn


class GponFileName:
    def __init__(self, base_fn='m2ontinfosum*.txt', root_dir='gponfiles'):
        _f = '.\\%s\\%s' % (root_dir, base_fn)
        self._txt_fn = get_filename(_f)
        _ts = self._txt_fn[-14:-4]
        self._gpn_fn = '.\\%s\\m2_gpon%s.json' % (root_dir, _ts)
        self._csv_fn = '.\\%s\\m2_gpon%s.csv' % (root_dir, _ts)
        self.dt = datetime.fromtimestamp(int(_ts)).strftime('%Y-%m-%d')

    @property
    def txt_fn(self):
        return self._txt_fn

    @property
    def gpon_fn(self):
        return self._gpn_fn

    @property
    def csv_fn(self):
        return self._csv_fn


class FEBGponFileName:
    def __init__(self, base_fn='febontinfosum*.txt', root_dir='gponfiles'):
        _f = '.\\%s\\%s' % (root_dir, base_fn)
        self._txt_fn = get_filename(_f)
        _ts = self._txt_fn[-14:-4]
        self._gpn_fn = '.\\%s\\feb_gpon%s.json' % (root_dir, _ts)
        self._csv_fn = '.\\%s\\feb_gpon%s.csv' % (root_dir, _ts)
        self.dt = datetime.fromtimestamp(int(_ts)).strftime('%Y-%m-%d')

    @property
    def txt_fn(self):
        return self._txt_fn

    @property
    def gpon_fn(self):
        return self._gpn_fn

    @property
    def csv_fn(self):
        return self._csv_fn


class AlarmFileName:
    def __init__(self, base_fn='m2ontinfosum*.txt', root_dir='gponfiles'):
        _f = '.\\%s\\%s' % (root_dir, base_fn)
        self._txt_fn = get_filename(_f)
        _ts = self._txt_fn[-14:-4]
        self._gpn_fn = '.\\%s\\m2_gpon%s.json' % (root_dir, _ts)
        self._csv_fn = '.\\%s\\m2_gpon%s.csv' % (root_dir, _ts)
        self.dt = datetime.fromtimestamp(int(_ts)).strftime('%Y-%m-%d')

    @property
    def txt_fn(self):
        return self._txt_fn

    @property
    def gpon_fn(self):
        return self._gpn_fn

    @property
    def csv_fn(self):
        return self._csv_fn


def tecent_sendmail(mailbody, subject, emailaddress):
    sender = 'liqin@ectivisecloud.com'
    msg = MIMEMultipart()
    msg.set_unixfrom('author')
    msg['From'] = 'liqin@ectivisecloud.com'
    msg['Subject'] = subject
    msg.attach(MIMEText(mailbody, "html"))
    mailserver = smtplib.SMTP_SSL('hwsmtp.exmail.qq.com', 465)
    mailserver.ehlo()
    mailserver.login('liqin@ectivisecloud.com', 'ESPL888espl')
    mailserver.sendmail(sender, emailaddress, msg.as_string())
    mailserver.quit()


def tecent_sendmail_attachment(message, subject, send_to, files=[]):
    sender = 'liqin@ectivisecloud.com'
    assert isinstance(files, list)
    username = 'liqin@ectivisecloud.com'
    password = 'ESPL888espl'
    msg = MIMEMultipart()
    msg['From'] = sender
    # msg['To'] = send_to
    msg['To'] = ' '.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(message, "html"))

    for path in files:
        part = MIMEBase('application', "octet-stream")
        with open(path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename={}'.format(Path(path).name))
        msg.attach(part)

    smtp = smtplib.SMTP_SSL('hwsmtp.exmail.qq.com', 465)
    smtp.login(username, password)
    smtp.sendmail(sender, send_to, msg.as_string())
    smtp.quit()


def godaddy_sendmail(mailbody, subject, emailaddress, sender='liqin@boonarthur.com'):
    msg = MIMEMultipart()
    msg.set_unixfrom('author')
    msg['From'] = 'liqin@boonarthur.com'
    msg['Subject'] = subject
    msg.attach(MIMEText(mailbody, "html"))
    mailserver = smtplib.SMTP_SSL('smtpout.secureserver.net', 465)
    mailserver.ehlo()
    mailserver.login('liqin@boonarthur.com', 'Il0vesingap0re')
    mailserver.sendmail(sender, emailaddress, msg.as_string())
    mailserver.quit()


def godaddy_sendmail_attachment(send_from, send_to, subject, message, files=[]):
    """Compose and send email with provided info and attachments.
    Args:
        send_from (str): from name
        send_to (list[str]): to name(s)
        subject (str): message title
        message (str): message body
        files (list[str]): list of file paths to be attached to email
    """
    # assert isinstance(send_to, list)
    assert isinstance(files, list)
    godaddy_username = 'liqin@boonarthur.com'
    godaddy_password = 'Il0vesingap0re'
    msg = MIMEMultipart()
    msg['From'] = send_from
    # msg['To'] = send_to
    msg['To'] = ' '.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(message, "html"))

    for path in files:
        part = MIMEBase('application', "octet-stream")
        with open(path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename={}'.format(Path(path).name))
        msg.attach(part)

    smtp = smtplib.SMTP_SSL('smtpout.secureserver.net', 465)
    smtp.login(godaddy_username, godaddy_password)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.quit()


def get_dict_value(a_dic):
    for key, value in a_dic.items():
        print(key, '->', value)
    return list(map(lambda key: a_dic[key], a_dic.keys()))[0]


def onteq(obj1: dict, obj2: dict):
    return obj1['id'] == obj2['id'] and obj1['port'] == obj2['port']


def onteq1(obj1: dict, obj2: dict):
    return onthash(obj1) == onthash(obj2)


def onthash(obj1: dict):
    return hash(('id', obj1['id'], 'port', obj1['port']))


def merge_ont_data(ont_data1, ont_data2):
    """
    merge two ont data into one
    :return merged ont list:
    """
    data0 = [x for x in ont_data1 if x["status"] == 'online']
    data1 = [x for x in ont_data2 if x["status"] == 'online']
    data = data0 + data1
    d = []
    for x in ont_data1:
        for y in data:
            fd = False
            # ee = onthash(x, y)
            if onteq(x, y):
                fd = True
                break
        if not fd:
            # print(x)
            d.append(x)
    return data + d


def assignolt(ont, olt=''):
    ont['oltid'] = olt
    return ont


def merge_ont_data_4(oltlist):
    """
    merge two ont data into one
    :return merged ont list, online ont list
    """
    ont_data1 = oltlist[0]["ont"]
    ont_data2 = oltlist[1]["ont"]
    ont_data1 = list(map(lambda x: assignolt(x, '1'), ont_data1))
    ont_data2 = list(map(lambda x: assignolt(x, '2'), ont_data2))
    data1 = [x for x in ont_data1 if x["status"] == 'online']
    data2 = [x for x in ont_data2 if x["status"] == 'online']
    # data1 = list(map(lambda x: assignolt(x, '1'), data1))
    # data2 = list(map(lambda x: assignolt(x, '2'), data2))
    dataonline = data1 + data2
    d = []
    for x in ont_data1:
        for y in dataonline:
            fd = False
            # ee = onthash(x, y)
            if onteq(x, y):
                fd = True
                break
        if not fd:
            # print(x)
            x['oltid'] = '-'  # offline ont
            d.append(x)
    return dataonline + d, dataonline


def merge_ont_data_3(oltlist):
    """
    merge two ont data into one
    :return merged ont list, online ont list
    """
    ont_data1 = oltlist[0]["ont"]
    ont_data2 = oltlist[1]["ont"]
    data0 = [x for x in ont_data1 if x["status"] == 'online']
    data1 = [x for x in ont_data2 if x["status"] == 'online']
    data = data0 + data1
    d = []
    for x in ont_data1:
        for y in data:
            fd = False
            # ee = onthash(x, y)
            if onteq(x, y):
                fd = True
                break
        if not fd:
            # print(x)
            d.append(x)
    return data + d, data


def merge_ont_data_2(ont_data1, ont_data2):
    """
    merge two ont data into one
    :return merged ont list:
    """
    data0 = [x for x in ont_data1 if x["status"] == 'online']
    data1 = [x for x in ont_data2 if x["status"] == 'online']
    data = data0 + data1
    d = []
    for x in ont_data1:
        for y in data:
            fd = False
            # ee = onthash(x, y)
            if onteq(x, y):
                fd = True
                break
        if not fd:
            # print(x)
            d.append(x)
    return data + d, data


def remove_ont_item(onts=[], items=[]):
    """
    remove from ont list
    :param onts: ont list
    :param items: ont list been removed
    :return:
    """
    for item in items:
        for ont in onts:
            ei = onthash(item)
            eo = onthash(ont)
            if onteq(item, ont):
                onts.remove(item)


def get_level(ontnm):
    return ontnm.split('-')[1]


def get_sshclient():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


def closesession(command, ssh):
    command.send("q\n")
    command.send("y\n")
    ssh.close()


def getsession(debug, oltip, ssh):
    ssh.connect(hostname=oltip, port=22, username='nmsuser2', password='ESPL888espl', compress=True)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Successfully logged into OLT %s" % oltip) if debug else None
    command = ssh.invoke_shell()
    command.send("enable \n")
    command.send("scroll \n\n")
    return command


def generate_ont_cmds(ont_data):
    """
    check ont json data and generate cmd
    :param ont_data:
    :return merged ont list:
    """
    data0 = [x for x in ont_data if x["status"] == 'online']
    cmds = []
    for x in ont_data:
        if x['status'] == 'offline':
            continue
        cmds.append('display mac-address ont %s %s' % (x['port'], x['id']))
    return cmds


def generate_mac_cmd_list(ontdata1, ontdata2):
    cmds1 = '\n'.join(generate_ont_cmds(ontdata1))
    textfile_write("m2cmds_mac_olt1.txt", cmds1)
    cmds2 = '\n'.join(generate_ont_cmds(ontdata2))
    textfile_write("m2cmds_mac_olt2.txt", cmds2)
    return cmds1, cmds2


def func2(ll):
    llarr = ll.split(' ')
    llarr1 = [x for x in llarr if len(str(x).strip()) > 0]
    linkstate = llarr1[-2]
    return linkstate != '-'


def func1(x, lvl, svc):
    l, s, u = x[0], x[5], x[6]
    return x[0] == lvl and x[5] == svc and u == 'up'


def print_ont_ports(ont_ports: dict):
    for port in ont_ports:
        for key, Value in port.items():
            print(f"{key} : {Value}")


def get_linkstate_cmd(ont):
    portarr = str(ont['port']).split('/')
    cmd = 'display ont port state %s %s eth-port all' % (portarr[-1], ont['id'])
    return cmd


def generate_ontportstate_cmds(oltlist):
    """
    check ont json data and generate cmd
    :param oltlist:
    :return:
    """
    for olt in oltlist:
        for ont in olt["ont"]:
            ont['linkstat_cmds'] = get_linkstate_cmd(ont)


def get_snmp_desc(ipv4='192.168.190.1', communitystr='espl888espl', oid='1.3.6.1.2.1.1.1.0', debug=True):
    print("snmp test ipv4=%s" % ipv4)
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(communitystr),
        UdpTransportTarget((ipv4, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )
    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    if errorIndication:
        print(errorIndication) if debug else None
        return -1

    elif errorStatus:
        print('%s at %s' % (
        errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex) - 1][0] or '?')) if debug else None
        return -2
    else:
        for varBind in varBinds:
            print(' = '.join([x.prettyPrint() for x in varBind]))
        return 0


def findont(alarm, fn="gpon_fn"):
    gponjsonobj = jsonfile_load(fn)
    params = alarm['params'].split(',')
    f = params[0].split(' ')
    f = f[-1]
    s = params[1].split(' ')
    s = s[-1]
    p = params[2].split(' ')
    p = p[-1]
    d = params[3].split(' ')
    d = d[-1]
    onts = [x for x in gponjsonobj if x['id'] == d and x['port'] == '%s/%s/%s' % (f, s, p)]
    try:
        assert len(onts) == 1
    except:
        return None
    return onts[0]


alarm_rx_dict = {
    'alarmid': re.compile(r'ALARM \d+.*'),
    'alarmnm': re.compile(r'ALARM NAME.*'),
    'desc': re.compile(r'DESCRIPTION.*'),
    'params': re.compile(r'PARAMETERS  .*'),
    'cause': re.compile(r'CAUSE  .*'),
    'advice': re.compile(r'ADVICE  .*'),
    'sr': re.compile(r'SRVEFF  .*'),
    'emu': re.compile(r'EMU.*'),
    'end': re.compile(r'END.*'),
}


def get_doc(ontnameportvlan_fn=''):
    ontnmport_lines = read_csv_file(ontnameportvlan_fn)
    return ontnmport_lines


def get_feb_doc():
    ontnameportvlan_fn = r'febname_port_vlan.csv'
    ontnmport_lines = read_csv_file(ontnameportvlan_fn)
    return ontnmport_lines


def map_ontport(line, ontnm): return line['ONT Label'] == ontnm


def assign_ontports(oltlist):
    """
    assign ont ports to the ont according to the DOC
    with attributes of vlanid, subsys name
    dynamic data "status" initialized value -
    :param oltlist:
    :return:
    """
    ontnmport_lines = get_feb_doc()
    for olt in oltlist:
        for ont in olt["ont"]:
            ontnm = ont['description']
            nmpline = list(filter(lambda x: map_ontport(x, ontnm), ontnmport_lines))
            ont["level"] = nmpline[0]['Level']
            portlist = []
            for i in range(0, 8):
                p = nmpline[i]
                port = {"eth_num": p['ONT Port'], "vlanid": p['VLAN ID'], "system": p['System'], "status": "-"}
                portlist.append(port)
            ont["ethports"] = portlist


def striplist(mylist: list):
    return [x for x in mylist if len(x) > 0]


def get_ontport_linkstate(oltlist, oltusername='root', sleeptime=3, debug=debug):
    for olt in oltlist:
        command, ssh = get_session_v2(ipv4=olt['ip'], un=oltusername)
        try:
            assert command is not None and ssh is not None
            cmd = "config"
            cmd += '\n\n'
            command.send(cmd)
            cmd = "interface gpon 0/1"
            cmd += '\n\n'
            command.send(cmd)
            time.sleep(0.5)
            for ont in olt["ont"]:
                if ont["status"] == "offline":
                    print("offline ont %s. olt: %s" % (ont["description"], olt["ip"])) if debug1 else None
                    continue
                cmd = get_linkstate_cmd(ont)
                print("cmd=", cmd)
                cmd += "\n\n"
                command.send(cmd)
                time.sleep(sleeptime)
                output = command.recv(65535)
                print(output.decode("ascii")) if debug else None
                result = output.decode('ascii')
                process_linkstate(result, ont["ethports"])
            closesession(command, ssh)
        except Exception as e:
            print(e)


def process_linkstate(linkstate_data, ont_ports):
    lines = linkstate_data.splitlines()
    portstat = [x for x in lines if x.find('   display ont port state') > -1 and x.find(' eth-port all')]
    if len(portstat) <= 0:
        print("err01", ont_ports, linkstate_data)
        telegram_bot_sendtext("m2 ont update err01", parse_mode='html')
        return
    index = lines.index(portstat[0])
    _lines = lines[index + 5: index + 5 + 8]
    for i in range(0, 8):
        try:
            ll = _lines[i]
        except:
            print("err02", ont_ports, linkstate_data)
            telegram_bot_sendtext("m2 ont update err02", parse_mode='html')
        llarr = ll.split(' ')
        llarr1 = [x for x in llarr if len(x.strip()) > 0]
        # assert int(llarr1[1]) == i + 1
        linkstate = llarr1[-2]
        if linkstate == 'up' or linkstate == 'down':
            eth = ont_ports[i]
            eth["status"] = linkstate
    # print(ont_ports) if debug else None
    print(json.dumps(ont_ports)) if debug1 else None


def get_contacts(isTest=True):
    contacts_file_fn = "email_contacts.csv" if not isTest else "email_contacts_test.csv"
    contacts = read_file(contacts_file_fn)
    contacts = [str.split(x)[-1] for x in contacts[1:] if x.find('#') < 0 and len(x) > 0]
    return contacts


def check_socket(host, port):
    from contextlib import closing
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex((host, port)) == 0:
                print(f"Host {host}:{port} is open") if debug else None
                return True
            else:
                print(f"Host {host}:{port} is not open") if debug else None
                return False
    except:
        return False


def get_apiurl(localhost, cloudhost, endpoint, localport=8082, cloudport=443):
    cloudurl = f"https://{cloudhost}" + endpoint
    localurl = f"http://{cloudhost}:{localport}" + endpoint
    from utils_v1 import internet_ok
    apiurllist = []
    if check_socket('espl8082', localport):
        espl8082 = "http://espl8082:8082" + endpoint
        apiurllist.append(espl8082)
    elif check_socket(localhost, int(localport)):
        apiurllist.append(localurl)
    if internet_ok and check_socket(cloudhost, cloudport):
        apiurllist.append(cloudurl)
    assert len(apiurllist) > 0, 'apiurl list should not be empty'
    return apiurllist


def get_empty_ont(): return jsonfile_load('files/ont_init.json')


def get_empty_ports():
    portlist = []
    for i in range(0, 8):
        port = {"eth_num": i + 1,
                "vlanid": '-',
                "system": '-',
                "status": "-",
                "traffic": {"in_traffic": "", "out_traffic": ""},
                "mac_address": []
                }
        portlist.append(port)
    return portlist


def get_ont_data(ip, dbg=True):
    global oltusername
    command, ssh = get_session_v2(ipv4=ip, un='nmsuser2')
    try:
        assert command is not None
        assert ssh is not None
        cmd = "display ont info summary 0"
        print("cmd=", cmd) if dbg else None
        cmd += '\n\n'
        command.send(cmd)
        _sleep = 6
        # if not isTest:
        #     _sleep = 30
        time.sleep(_sleep)
        output = command.recv(65535)
        print(output.decode("ascii")) if dbg else None
        command.send("q\n")
        command.send("y\n")
        ssh.close()
        return output.decode("ascii")
    except:
        return []

def ont_dataget_v0927(oltlist, sitename, debug=debug):
    from uob_vlan import UOBVlan
    from uob_dataClean import data_clean
    vlans = UOBVlan(sitename)
    # ontnmport_lines = get_doc(ontnameportvlan_fn)
    for olt in oltlist:
        txtdata = get_ont_data(olt["ip"], dbg=debug)
        if len(txtdata) > 0:
            olt["ont"] = data_clean(txtdata=txtdata.splitlines())
            for ont in olt["ont"]:
                sfp, ontid = ont["port"], ont["id"]
                # ontnm = ont['description']
                try:
                    # assert len(nmpline) > 0  # only the documented ont has ethports definition
                    # ont["level"] = nmpline[0]['Level']  # by doc
                    ont["ethports"] = get_empty_ports()
                    # portlist = []
                    for eth in ont['ethports']:
                        ethid = eth['eth_num']
                        myvlan = [x for x in vlans.ethports_configged if
                                  x["sfp"] == sfp and x["ontid"] == ontid and ethid == int(x["ethid"])]
                        assert len(myvlan) == 1 or len(myvlan) == 0, 'only one vlan config'
                        if len(myvlan) == 1:
                            eth["vlanid"], eth["system"], eth['status'] = myvlan[0]['vlanid'], myvlan[0]['vlanname'], ''
                except AssertionError as e:
                    pass
                except Exception as e:
                    print("error7086", e)
                    traceback.print_exc()

testmessage = """
*bold \*text*
_italic \*text_
__underline__
~strikethrough~
*bold _italic bold ~italic bold strikethrough~ __underline italic bold___ bold*
[inline URL](http://www.example.com/)
[inline mention of a user](tg://user?id=123456789)
`inline fixed-width code`
```
pre-formatted fixed-width code block
```
```python
pre-formatted fixed-width code block written in the Python programming language
```
"""

if __name__ == '__main__':
    exit(0)

    # row_list = [["SN", "Name", "Contribution"],
    #             [1, "Linus Torvalds", "Linux Kernel"],
    #             [2, "Tim Berners-Lee", "World Wide Web"],
    #             [3, "Guido van Rossum", "Python Programming"]]
    # write_csv(row_list, "atest.csv")
    # a, b = get_filename_data_fullpath('m2_gpon*.json', 'gponfiles')
    # send_telegram_api()
    # sendmails()
    exit(100)
    cmd_fn = cmd_fn
    ip_fn = ip_fn
    logging.info('start the ont info collection @ ' + str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    with open(ont_env_fn, 'r') as myfile:
        jsonArray = myfile.read()
    cred = json.loads(jsonArray)
    username = cred["username"]
    unamepw = cred["password"]
    getontinfo = GetONTInfo(output_fn=output_fn, cmd_fn=cmd_fn, ip_fn=ip_fn,
                            username=username,
                            unamepw=unamepw)
    getontinfo.get_result()
    getontinfo.save_results(ontinfo_ovh_fn)

    # import ontDataClean_ovh_txt_v1124
    # ovhont = ONTDataClean_OVH(filepath='ontinfo_ovh1606139733.txt')
    # ovhont.parse_file()
