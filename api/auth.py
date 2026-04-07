import os
from functools import wraps
from flask import request, jsonify


def get_api_keys():
    """获取配置的 API Keys"""
    # 格式: "key1,key2"
    read_keys = os.getenv("KB_READ_KEYS", "").split(",")
    admin_keys = os.getenv("KB_ADMIN_KEYS", "").split(",")

    # 移除空字符串
    read_keys = [k.strip() for k in read_keys if k.strip()]
    admin_keys = [k.strip() for k in admin_keys if k.strip()]

    return read_keys, admin_keys


def require_api_key(admin_only=False):
    """API Key 鉴权装饰器"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取请求头中的 Authorization
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"code": 401, "message": "Missing Authorization header"}), 401

            # 格式: Bearer <token>
            # 兼容处理：如果用户没加 Bearer 前缀，直接取整个 Header 尝试验证
            if " " in auth_header:
                try:
                    token_type, token = auth_header.split(" ", 1)
                    if token_type.lower() != "bearer":
                        # 可能是其他类型，或者是带空格的 Key？暂时当做格式错误
                        token = auth_header
                except ValueError:
                    token = auth_header
            else:
                # 没有空格，假设就是纯 Token
                token = auth_header

            read_keys, admin_keys = get_api_keys()

            # 如果没有配置 Key，视为开发模式警告（或拒绝，生产环境建议默认拒绝）
            if not read_keys and not admin_keys:
                # 生产环境应默认拒绝，这里为了方便调试暂时放行，但在日志中警告
                # print("WARNING: No API Keys configured!")
                pass

            is_admin = token in admin_keys
            is_read = token in read_keys

            if admin_only:
                if not is_admin:
                    return jsonify({"code": 403, "message": "Admin permission required"}), 403
            else:
                if not (is_admin or is_read):
                    return jsonify({"code": 403, "message": "Invalid or expired API Key"}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator
