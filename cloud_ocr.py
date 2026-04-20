"""
云端 OCR API 接口
支持百度、腾讯云、阿里云 OCR
"""
import base64
import json
import requests
import hashlib
import hmac
import time
from datetime import datetime
from typing import List, Dict
import cv2
import numpy as np


class BaiduOCR:
    """百度 OCR API"""
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
    
    def _get_access_token(self):
        """获取访问令牌"""
        if self.access_token:
            return self.access_token
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        response = requests.post(url, params=params)
        if response.status_code == 200:
            result = response.json()
            self.access_token = result.get("access_token")
            return self.access_token
        else:
            raise Exception(f"获取百度 access_token 失败: {response.text}")
    
    def recognize_image(self, image: np.ndarray) -> List[str]:
        """
        识别图像中的文字
        
        Args:
            image: OpenCV 图像 (numpy array)
            
        Returns:
            识别出的文字列表
        """
        # 将图像编码为 base64
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # 调用 API
        url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        params = {"access_token": self._get_access_token()}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {"image": image_base64}
        
        response = requests.post(url, params=params, headers=headers, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if "words_result" in result:
                return [item["words"] for item in result["words_result"]]
            else:
                return []
        else:
            raise Exception(f"百度 OCR 识别失败: {response.text}")


class TencentOCR:
    """腾讯云 OCR API"""
    
    def __init__(self, secret_id: str, secret_key: str, region: str = "ap-guangzhou"):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.service = "ocr"
        self.host = "ocr.tencentcloudapi.com"
        self.version = "2018-11-19"
    
    def _sign(self, params: Dict) -> str:
        """生成签名"""
        # 腾讯云 API v3 签名方法
        algorithm = "TC3-HMAC-SHA256"
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        # 拼接规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json\nhost:{self.host}\n"
        signed_headers = "content-type;host"
        payload = json.dumps(params)
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_request_payload}"
        
        # 拼接待签名字符串
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        # 计算签名
        secret_date = hmac.new(("TC3" + self.secret_key).encode("utf-8"), date.encode("utf-8"), hashlib.sha256).digest()
        secret_service = hmac.new(secret_date, self.service.encode("utf-8"), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, "tc3_request".encode("utf-8"), hashlib.sha256).digest()
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # 拼接 Authorization
        authorization = f"{algorithm} Credential={self.secret_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        return authorization, timestamp
    
    def recognize_image(self, image: np.ndarray) -> List[str]:
        """
        识别图像中的文字
        
        Args:
            image: OpenCV 图像 (numpy array)
            
        Returns:
            识别出的文字列表
        """
        # 将图像编码为 base64
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # 构建请求参数
        params = {
            "ImageBase64": image_base64
        }
        
        # 生成签名
        authorization, timestamp = self._sign(params)
        
        # 构建请求头
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": self.host,
            "X-TC-Action": "GeneralBasicOCR",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version,
            "X-TC-Region": self.region
        }
        
        # 发送请求
        url = f"https://{self.host}"
        response = requests.post(url, headers=headers, json=params)
        
        if response.status_code == 200:
            result = response.json()
            if "Response" in result and "TextDetections" in result["Response"]:
                return [item["DetectedText"] for item in result["Response"]["TextDetections"]]
            else:
                return []
        else:
            raise Exception(f"腾讯云 OCR 识别失败: {response.text}")


class AliyunOCR:
    """阿里云 OCR API"""
    
    def __init__(self, access_key_id: str, access_key_secret: str, region: str = "cn-shanghai"):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region = region
    
    def recognize_image(self, image: np.ndarray) -> List[str]:
        """
        识别图像中的文字
        
        Args:
            image: OpenCV 图像 (numpy array)
            
        Returns:
            识别出的文字列表
        """
        try:
            from alibabacloud_ocr_api20210707.client import Client
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_ocr_api20210707 import models as ocr_models
            from alibabacloud_tea_util import models as util_models
            
            # 创建客户端
            config = open_api_models.Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret,
                region_id=self.region
            )
            config.endpoint = f'ocr-api.{self.region}.aliyuncs.com'
            client = Client(config)
            
            # 将图像编码为 base64
            _, buffer = cv2.imencode('.jpg', image)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # 构建请求
            request = ocr_models.RecognizeGeneralRequest(
                body=image_base64
            )
            runtime = util_models.RuntimeOptions()
            
            # 调用 API
            response = client.recognize_general_with_options(request, runtime)
            
            # 解析结果
            if response.body and response.body.data:
                texts = []
                for item in response.body.data.split('\n'):
                    if item.strip():
                        texts.append(item.strip())
                return texts
            return []
            
        except ImportError:
            raise Exception("阿里云 OCR SDK 未安装。请运行: pip install alibabacloud-ocr-api20210707")
        except Exception as e:
            raise Exception(f"阿里云 OCR 识别失败: {str(e)}")


class CloudOCRProcessor:
    """云端 OCR 处理器"""
    
    def __init__(self, provider: str, config: Dict):
        """
        初始化云端 OCR 处理器
        
        Args:
            provider: 提供商名称 (baidu, tencent, aliyun)
            config: API 配置信息
        """
        self.provider = provider
        
        if provider == "baidu":
            self.ocr = BaiduOCR(
                api_key=config["api_key"],
                secret_key=config["secret_key"]
            )
        elif provider == "tencent":
            self.ocr = TencentOCR(
                secret_id=config["secret_id"],
                secret_key=config["secret_key"],
                region=config.get("region", "ap-guangzhou")
            )
        elif provider == "aliyun":
            self.ocr = AliyunOCR(
                access_key_id=config["access_key_id"],
                access_key_secret=config["access_key_secret"],
                region=config.get("region", "cn-shanghai")
            )
        else:
            raise ValueError(f"不支持的 OCR 提供商: {provider}")
    
    def process_frames(self, frames: List[np.ndarray]) -> List[str]:
        """
        处理视频帧，提取文字
        
        Args:
            frames: 视频帧列表
            
        Returns:
            识别出的文字列表
        """
        try:
            from log_stream import log_stream
            has_log_stream = True
        except:
            has_log_stream = False
        
        all_texts = []
        total = len(frames)
        
        print(f"\n{'=' * 70}")
        print(f"🔍 {self.provider.upper()} OCR 文字识别")
        print(f"{'=' * 70}")
        print(f"   待识别帧数: {total}")
        print(f"{'=' * 70}\n")
        
        if has_log_stream:
            log_stream.add_log("═" * 50, "header")
            log_stream.add_log(f"🔍 {self.provider.upper()} OCR 识别", "header")
            log_stream.add_log(f"待识别: {total} 帧", "info")
        
        for idx, frame in enumerate(frames):
            try:
                texts = self.ocr.recognize_image(frame)
                all_texts.extend(texts)
                
                if (idx + 1) % 5 == 0:
                    print(f"已识别 {idx + 1}/{total} 帧...")
                    if has_log_stream:
                        log_stream.add_log(f"已识别 {idx + 1}/{total} 帧", "info")
            
            except Exception as e:
                print(f"⚠️  第 {idx + 1} 帧识别失败: {str(e)}")
                if has_log_stream:
                    log_stream.add_log(f"⚠️  第 {idx + 1} 帧失败", "warning")
        
        print(f"\n✓ OCR 识别完成")
        print(f"   共识别: {len(all_texts)} 行文字\n")
        
        if has_log_stream:
            log_stream.add_log(f"✓ 识别完成: {len(all_texts)} 行", "success")
        
        return all_texts
