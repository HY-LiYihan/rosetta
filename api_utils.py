import streamlit as st
from openai import OpenAI
import json

# 各平台的配置信息
PLATFORM_CONFIG = {
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com",
        "key_name": "deepseek_api_key",
        "default_model": "deepseek-chat"
    },
    "kimi": {
        "name": "Kimi (Moonshot)",
        "url": "https://api.moonshot.cn/v1",
        "key_name": "kimi_api_key",
        "default_model": "kimi-k2-thinking"
    },
    "qwen": {
        "name": "Qwen (DashScope)",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "key_name": "qwen_api_key",
        "default_model": "qwen-plus"
    },
    "zhipuai": {
        "name": "Zhipu AI (GLM)",
        "url": "https://open.bigmodel.cn/api/paas/v4",
        "key_name": "zhipuai_api_key",
        "default_model": "glm-4.7"
    }
}

def get_client(platform, api_key):
    """获取指定平台的 OpenAI 兼容客户端"""
    if platform not in PLATFORM_CONFIG:
        return None
    
    return OpenAI(
        api_key=api_key,
        base_url=PLATFORM_CONFIG[platform]["url"]
    )

def probe_available_platforms():
    """
    根据 st.secrets 探测可用的平台。
    返回: dict {platform_id: {"name": str, "models": list, "api_key": str}}
    """
    available = {}
    
    for pid, config in PLATFORM_CONFIG.items():
        key_name = config["key_name"]
        
        # 1. 检查 secrets 中是否有 key
        if key_name in st.secrets and st.secrets[key_name]:
            api_key = st.secrets[key_name]
            
            try:
                # 2. 尝试获取模型列表进行验证
                client = get_client(pid, api_key)
                if not client:
                    continue
                
                model_list = client.models.list()
                model_ids = [m.id for m in model_list.data]
                
                # 针对特定平台进行模型过滤（可选）
                if pid == "kimi":
                    model_ids = [m for m in model_ids if "moonshot" in m or "kimi" in m]
                elif pid == "deepseek":
                    model_ids = [m for m in model_ids if "deepseek" in m]
                
                if model_ids:
                    model_ids.sort()
                    available[pid] = {
                        "name": config["name"],
                        "models": model_ids,
                        "api_key": api_key,
                        "default_model": config["default_model"]
                    }
            except Exception as e:
                # 验证失败，不加入可用列表
                print(f"探测平台 {pid} 失败: {str(e)}")
                continue
    
    return available

def get_chat_response(platform, api_key, model, messages, temperature=0.3):
    """统一的对话接口"""
    try:
        client = get_client(platform, api_key)
        if not client:
            raise ValueError(f"无法创建平台 {platform} 的客户端")
            
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"调用 {platform} 失败: {str(e)}")
