from binance.client import Client
from . utils import *
import sys, os
import logging
logger_binance = logging.getLogger('binance')

def place_order_binance(symbol_id,side,order_type,quantity=0.01,duration="day",binance=None,stop_loss=None,limit_price=None):
    print(">>>>>>>>>>>>>>>>>> price",limit_price)
    is_testnet = True  if binance.is_paper_account else False
    client = Client(str(decrypt_keyids(binance.key_id)), str(decrypt_binance(binance.secret_id)), tld='com', testnet= is_testnet)
    print("------------------",order_type)
    if order_type == "market":
        try:
            response = client.futures_create_order(symbol=str(symbol_id), side=side.upper(), type=client.ORDER_TYPE_MARKET, quantity=quantity)
            print(">>>> market ordre +*++**+*+*+*+*+*.response",response)
            return response
        except Exception as e:
            exc_type, exe_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
            logger_binance.exception(str(e))
    elif order_type == "limit":
        response = client.futures_create_order(symbol=str(symbol_id), side=side.upper(), type=client.ORDER_TYPE_LIMIT, quantity=quantity,price=limit_price,timeInForce=client.TIME_IN_FORCE_GTC)
        print(">>>> limit order *-*-*-*-*-.response",response)
        return response


def cancel_active_order(binance,orderId,symbol,origClientOrderId):
    try:
        is_testnet = True  if binance.is_paper_account else False
        client = Client(str(decrypt_keyids(binance.key_id)), str(decrypt_binance(binance.secret_id)), tld='com', testnet= is_testnet)
        response = client.futures_cancel_order(symbol=str(symbol),orderId=orderId, origClientOrderId=origClientOrderId,recvWindow = 5000000)
        return response
    except Exception as e:
        exc_type, exe_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
        logger_binance.exception(str(e))