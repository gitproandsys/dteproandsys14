# -*- coding: utf-8 -*-


import requests
from requests.auth import HTTPBasicAuth
import json
import logging
import datetime
from json import JSONEncoder

logger = logging.getLogger(__name__)

"""This file implement conections for factual api, this api acept json request in http post. this webservice
need auth for any requests """

HEADERS = {'Content-type': 'application/json', 'Accept': 'text/plain'}

CAF_URL = 'manage/caf'
STATUS_BOOK = 'book/status'
GENERATE_BOOK = 'book'
GET_DTE_INFO = 'document/dteresult'
STATUS_DTE = 'document/dtestatus'
SEND_URL = 'document/dte'
GET_PDF = 'public/document/view'
TRANSFER_URL = 'document/transfer'
TRANSFER_STATUS_URL = 'document/transferstatus/'


class DateTimeEncoder(JSONEncoder):
    # Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        

def set_caf(url, data, user, passwd):
    r = requests.post(url + CAF_URL, data=json.dumps(data, indent=4, cls=DateTimeEncoder), auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def status_book(url, trackid, user, passwd):
    r = requests.get(url + STATUS_BOOK + '/' + trackid, auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def get_xml_book(url, trackid, user, passwd):
    r = requests.get(url + GENERATE_BOOK + '/' + trackid, auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def get_dte_info(url, rut, dte_type, folio, user, passwd):
    r = requests.get(url + GET_DTE_INFO + '/' + rut + '/' + dte_type + '/' + folio, auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def get_status(url, trackid, user, passwd):
    r = requests.get(url + STATUS_DTE + '/' + trackid, auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def get_dte(url, trackid, user, passwd):
    r = requests.get(url + SEND_URL + '/' + trackid, auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def get_pdf(url, trackid):
    r = requests.get(url[:-4] + GET_PDF + '/' + trackid, headers=HEADERS)
    return r.content


def get_pdf_cedible(url, trackid):
    r = requests.get(url[:-4] + GET_PDF + '/' + trackid + '/cedible', headers=HEADERS)
    return r.content


def get_transfer_dte(url, trackid, user, passwd):
    r = requests.get(url + TRANSFER_URL + '/' + trackid, auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def get_status_transfer(url, trackid, user, passwd):
    r = requests.get(url + TRANSFER_STATUS_URL + '/' + trackid, auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def send_transfer_dte(url, data, user, passwd):
    r = requests.post(url + TRANSFER_URL, data=json.dumps(data, indent=4, cls=DateTimeEncoder), auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)


def send_dte(url, data, user, passwd):
    HEADERS.update({'Direct': 'true'})
    r = requests.post(url + SEND_URL, data=json.dumps(data, indent=4, cls=DateTimeEncoder), auth=HTTPBasicAuth(user, passwd), headers=HEADERS)
    return json.loads(r.text)
