# -*- coding: utf-8 -*-


import requests
from requests.auth import HTTPBasicAuth
 
import json
import logging
logger = logging.getLogger(__name__)

"""This file implement conections for factual api, this api acept json request in http post. this webservice 
need auth for any requests """

HEADERS= {'Content-type': 'application/json', 'Accept': 'text/plain'}

NOTIFICATION_URL = 'manage/notification'
COMPANY_DATA_URL = 'manage/company'
COMPANY_IMG = 'manage/logo'
CERT_URL = 'manage/certificate'


def set_notification(url, data, user, passwd):
	r = requests.post(url + NOTIFICATION_URL, data=json.dumps(data), auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
	return json.loads(r.text)


def set_company(url, data, user, passwd):
	r = requests.post(url + COMPANY_DATA_URL, data=json.dumps(data), auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
	return json.loads(r.text)


def set_com_img(url, img, rut, user, passwd):
	heads = {'Content-type': 'application/octet-stream', 'Accept': 'text/plain'}
	r = requests.post(url + COMPANY_IMG + '/' + rut, data=img, auth=HTTPBasicAuth(user, passwd), headers=heads)
	return json.loads(r.text)


def set_cert(url, data, user, passwd):
	r = requests.post(url + CERT_URL, data=json.dumps(data), auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
	return json.loads(r.text)
