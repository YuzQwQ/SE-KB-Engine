import os

from service_boundary.auth import Role
from service_boundary.flask_support import require_role


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
    """Compatibility wrapper over the shared strict bearer policy."""
    return require_role(Role.ADMIN if admin_only else Role.READ)
