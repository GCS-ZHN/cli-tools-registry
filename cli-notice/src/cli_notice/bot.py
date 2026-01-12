# -*- coding: utf-8 -*-
# @Author  : GCS-ZHN
# @Time    : 2025-12-25 15:35:28

"""
Webhook bots for sending notifications.
"""


from abc import ABC, abstractmethod
from functools import wraps

import hashlib
import base64
import hmac
import time
import requests


class Bot(ABC):
    """Basic class for webhook bot"""
    def __init__(self, webhook_url: str|None = None, signature_secret: str|None = None, access_token: str | None = None):
        if webhook_url is None and access_token is None:
            raise ValueError("Webhoook url or access token must be provided.")
        if webhook_url is not None and access_token is not None:
            raise ValueError("Webhook url and access token cannot be provided at the same time ")
        self._webhook_url = webhook_url
        self._signature_secret = signature_secret
        self._access_token = access_token
        self._client = requests.Session()

    @abstractmethod
    def get_url(self) -> str:
        """Get webhook url"""
        raise NotImplementedError

    @abstractmethod
    def get_signature(self):
        """
        get signature with secret.
        """
        raise NotImplementedError

    @abstractmethod
    def send_message(self, message: str, at: tuple[str] = tuple()):
        """
        Send message.
        
        Parameters
        ----------
            message: str
               The message to send.

            at: tuple[str]
               user id to at if provided.
        
        Raises
        ------
            BotError
                If the request fails
        """
        raise NotImplementedError
    

class BotError(RuntimeError):
    pass


class MaxRetryError(RuntimeError):
    pass

def retry(max_try: int = 3, delay: int = 1):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_try):
                try:
                    return func(*args, **kwargs)
                except (BotError, requests.HTTPError) as e:
                    time.sleep(delay)
                    err = e
            else:
                raise MaxRetryError(
                    f"Max retry {max_try} reached due to '{err}'") from err
        return wrapper

    return decorator


class FeishuBot(Bot):
    """
    Feishu Webhook bot, See detail at
    https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
    """
    def get_url(self):
        if self._webhook_url:
            return self._webhook_url

        return f'https://open.feishu.cn/open-apis/bot/v2/hook/{self._access_token}'
    
    def get_signature(self):
        if not self._signature_secret:
            return {}
        timestamp = time.time()
        timestamp = str(int(timestamp))
        string_to_sign = f'{timestamp}\n{self._signature_secret}'
        hmac_code = hmac.new(
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return {
            'timestamp': timestamp,
            'sign': sign
        }

    @retry(max_try=3, delay=5)
    def send_message(self, message: str, at: tuple[str] = tuple()):
        if at:
            temp = '<at user_id="{}">{}</at>'
            at = set(at)
            if 'all' in at:
                at = {'all'}
            at_msg = ''.join([temp.format(user_id, user_id) for user_id in at])
            message += at_msg
        msg_body = {
            **self.get_signature(),
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        res = self._client.post(
            self.get_url(),
            json=msg_body
        )
        res.raise_for_status()
        res_body = res.json()
        if 'code' in res_body and res_body['code'] != 0:
            raise BotError(f"Error: {res_body['msg']}")


class DingTalkBot(Bot):
    """
    DingTalk webhook bot, see detail at
    https://open.dingtalk.com/document/dingstart/custom-bot-to-send-group-chat-messages
    """

    def get_url(self):
        sign_data  = self.get_signature()
        if self._webhook_url:
            base_url = self._webhook_url
        else:
            base_url = f'https://oapi.dingtalk.com/robot/send?access_token={self._access_token}'
        
        if self._signature_secret:
            base_url += '&timestamp=' + sign_data['timestamp']
            base_url += '&sign=' + sign_data['sign']
        
        return base_url
    
    def get_signature(self):
        """
        get signature with secret.
        """

        if not self._signature_secret:
            return {}
        timestamp = time.time() * 1000
        timestamp = str(int(timestamp))
        string_to_sign = f'{timestamp}\n{self._signature_secret}'
        hmac_code = hmac.new(
            self._signature_secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return {
            'timestamp': timestamp,
            'sign': sign
        }

    @retry(max_try=3, delay=5)
    def send_message(self, message: str, at: tuple[str] = tuple()):
        msg_body = {
            'msgtype': 'text',
            'text': {
                'content': message
            }
        }

        at = list(set(at))
        if at:
            msg_body['at'] = {
                'isAtAll': 'all' in at,
            }
            if not msg_body['at']['isAtAll']:
                msg_body['at']['atUserIds'] = at

        res = self._client.post(
            self.get_url(),
            json=msg_body
        )
        res.raise_for_status()
        res_body = res.json()
        if res_body['errcode'] != 0:
            raise BotError(f"Error: {res_body['errmsg']}")


class TelegramBot(Bot):
    """
    Telegram bot, using bot token and chat id, see detail at
    https://core.telegram.org/bots/api. Actually, telegram does
    not provided a direct webhook url like feishu or dingtalk
    to send message because official bot api is more flexible.
    """
    def get_url(self):
        if self._webhook_url:
            return self._webhook_url
        return f'https://api.telegram.org/bot{self._access_token}/sendMessage'

    def get_signature(self):
        """Telegram do not require signature"""
        pass

    @retry(max_try=3, delay=5)
    def send_message(self, message: str, at: tuple[str]):
        if not at:
            raise BotError(
                'Telegram bot must specify `chat_id` in `at`, query your chat_id from @userinfobot')
        
        for chat_id in set(at):
            msg_body = {
                'text': message,
                'parse_mode': 'MarkdownV2',
                'chat_id': chat_id
            }

            res = self._client.post(
                self.get_url(),
                json=msg_body
            )
            res.raise_for_status()
            res_body = res.json()
            if not res_body['ok']:
                raise BotError(f"Error: {res_body['description']}")

