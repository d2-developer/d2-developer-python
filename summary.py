import imp
import json
import sys, os
import logging
import csv
from binance.client import Client
from . utils import *

logger_binance = logging.getLogger('binance')

def get_binance_summary(binance):
    is_testnet = True  if binance.is_paper_account else False
    # client = Client(binance.key_id, binance.secret_id, tld='com', testnet= is_testnet)
    client = Client(str(decrypt_keyids(binance.key_id)), str(decrypt_binance(binance.secret_id)), tld='com', testnet= is_testnet)

    # print("+++++++ open order",client.futures_get_open_orders(recvWindow = 5000000))
    try:
        summary = client.futures_account(recvWindow = 5000000)
        data = client.futures_position_information()

        datas =  [item for item in data if float(item.get('positionAmt', '0')) != 0 ]
        summary['positions']= datas
        # print(">>>>>>>>>>>>>>>>>. open position",summary)
        return summary
    except Exception as e:
        exc_type, exe_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
        logger_binance.exception(str(e))
        return None


def get_open_orders(client):
    aa = client.futures_get_open_orders()
    return aa
    
def close_open_order(client):
    z = get_open_orders(client)
    if len(z)> 0:
        for i in z:
            client.futures_cancel_all_open_orders(symbol=i['symbol'])
    # aa = client.futures_cancel_all_open_orders    ()
    return "success"

def close_all_positions(client):
    data = client.futures_position_information()
    
    datas =  [item for item in data if float(item.get('positionAmt', '0')) != 0 ]
    if len(datas)> 0:
        for d in datas:
            if float(d['positionAmt']) < 0:
                side = "BUY"
            else:
                side = "SELL"    
            client.futures_create_order(symbol=d['symbol'], side=side.upper(), type=client.ORDER_TYPE_MARKET, quantity=d['positionAmt'])
    return True


def get_open_order_position(binance):
    try:
        is_testnet = True  if binance.is_paper_account else False
        client = Client(str(decrypt_keyids(binance.key_id)), str(decrypt_binance(binance.secret_id)), tld='com', testnet= is_testnet)
        open_order = client.futures_get_open_orders(recvWindow = 5000000)
        # open_order = client.futures_get_open_orders()
    
        # print(">>>>>>>>>>>>>> open order",open_order)
        return open_order
    except Exception as e:
        exc_type, exe_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
        logger_binance.exception(str(e))
