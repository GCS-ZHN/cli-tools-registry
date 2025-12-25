# -*- coding: utf-8 -*-
# @Author  : GCS-ZHN
# @Time    : 2025-12-25 15:35:28

"""
Webhook bots for sending notifications.
"""


from abc import ABC, abstractmethod

import hashlib
import base64
import hmac
import time
import requests


class Bot(ABC):
    """Basic class for webhook bot"""
    def __init__(self, webhook_url: str, signature_secret: str|None = None):
        self.webhook_url = webhook_url
        self.signature_secret = signature_secret
        self.client = requests.Session()

    @abstractmethod
    def get_signature(self):
        """
        Get signature for webhook request.
        """
        raise NotImplementedError

    @abstractmethod
    def send_message(self, message: str):
        """
        Send message.
        
        Parameters
        ----------
            message: str
               The message to send.
        
        Raises
        ------
            BotError
                If the request fails
        """
        raise NotImplementedError
    

class BotError(RuntimeError):
    pass


class FeishuBot(Bot):
    """
    Feishu Webhook bot, See detail at
    https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
    """
    def get_signature(self):
        if not self.signature_secret:
            return {}
        timestamp = str(int(time.time()))
        string_to_sign = f'{timestamp}\n{self.signature_secret}'
        hmac_code = hmac.new(
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return {
            'timestamp': timestamp,
            'sign': sign
        }
    
    def send_message(self, message: str):
        msg_body = {
            **self.get_signature(),
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        res = self.client.post(
            self.webhook_url,
            json=msg_body
        )
        res.raise_for_status()
        res_body = res.json()
        if 'code' in res_body and res_body['code'] != 0:
            raise BotError(f"Error: {res_body['msg']}")

