import os
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime

# 域名到短名的映射
DOMAIN_SHORT_MAP = {
    "blog.csdn.net": "csdn",
    "www.csdn.net": "csdn",
    "zhuanlan.zhihu.com": "zhihu",
    "www.zhihu.com": "zhihu",
    "www.jianshu.com": "jianshu",
    "juejin.cn": "juejin",
    "www.cnblogs.com": "cnblogs",
    "segmentfault.com": "segfault",
    "www.oschina.net": "oschina",
    "mp.weixin.qq.com": "wechat",
    "www.infoq.cn": "infoq",
    "xie.infoq.cn": "infoq",
    "www.visual-paradigm.com": "vp",
    "boardmix.cn": "boardmix",
    "www.processon.com": "processon",
    "www.finebi.com": "finebi",
    "jingyan.baidu.com": "baidu",
    "www.feishu.cn": "feishu",
    "www.w3cschool.cn": "w3c",
    "www.runoob.com": "runoob",
}

class ArtifactsWriter:
    def _slug(self, title: str, url: str) -> str:
        t = (title or "untitled").strip().replace(" ", "-")
        t = re.sub(r'[<>:"/\\\|\?\*]', '_', t)
        t = re.sub(r'-{2,}', '-', t)
        h = hashlib.md5((url or "").encode("utf-8")).hexdigest()[:8]
        return f"{t[:60]}-{h}"
    
    def _get_domain_short(self, domain: str) -> str:
        """获取域名的短名"""
        if not domain:
            return "web"
        # 先查映射表
        if domain in DOMAIN_SHORT_MAP:
            return DOMAIN_SHORT_MAP[domain]
        # 否则取域名第一部分（去掉 www.）
        parts = domain.replace("www.", "").split(".")
        return parts[0][:10] if parts else "web"
    
    def _extract_content_slug(self, artifact: dict, type_id: str) -> str:
        """从 artifact 中提取 content_slug，生成文件名友好的格式"""
        if not artifact or not isinstance(artifact, dict):
            return None
        
        # 尝试获取 LLM 生成的 content_slug
        content_slug = artifact.get("content_slug", "")
        
        if content_slug:
            # 清理 slug：只保留英文字母、数字、下划线
            content_slug = re.sub(r'[^a-z0-9_]', '_', content_slug.lower())
            content_slug = re.sub(r'_+', '_', content_slug)  # 合并多个下划线
            content_slug = content_slug.strip('_')
            if len(content_slug) >= 5:  # 至少 5 个字符才有效
                return content_slug[:30]  # 最多 30 字符（给域名前缀留空间）
        
        return None
    
    def _generate_artifact_filename(self, type_id: str, artifact: dict, domain: str = None, url: str = None) -> str:
        """
        生成 artifact 文件名，格式：{type}_{domain}_{slug}_{hash}.json
        
        确保每个文件名唯一，即使多个来源产生相同的 content_slug
        """
        # 简化 type_id 用于文件名（diagrams.dfd.concepts -> dfd_concepts）
        type_short = type_id.replace('diagrams.', '').replace('.', '_')
        
        # 获取域名短名
        domain_short = self._get_domain_short(domain)
        
        # 生成 URL hash（确保唯一性）
        url_hash = hashlib.md5((url or "").encode('utf-8')).hexdigest()[:6]
        
        # 尝试从 artifact 获取 content_slug
        content_slug = self._extract_content_slug(artifact, type_id)
        
        if content_slug:
            return f"{type_short}_{domain_short}_{content_slug}_{url_hash}.json"
        else:
            return f"{type_short}_{domain_short}_{url_hash}.json"

    def _base_dir(self) -> Path:
        return Path("se_kb/artifacts")

    def write(self, domain: str, title: str, parsed: dict, document_text: str, t: str, artifact: dict, trace: dict, metadata: dict, metrics: dict, errors: list = None) -> dict:
        now = datetime.now()
        # 目录结构：artifacts/{YYYY}/{MM}/{DD}/{HH_MM}/{domain}/{slug}/
        # 精确到分钟，方便批量爬取后按时间段审核
        time_dir = now.strftime("%H_%M")  # 如 11_30, 14_05
        base = self._base_dir() / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d") / time_dir / (domain or "unknown")
        slug = self._slug(title, parsed.get("source_url") or parsed.get("url") or "")
        out = base / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "parsed.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "document.md").write_text(document_text or "", encoding="utf-8")
        (out / "trace.json").write_text(json.dumps(trace or {}, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "metrics.json").write_text(json.dumps(metrics or {}, ensure_ascii=False, indent=2), encoding="utf-8")
        if errors is not None:
            (out / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        
        artifact_filename = None
        if artifact is not None:
            # 使用新的文件名生成逻辑（包含域名前缀 + URL hash 确保唯一）
            url = parsed.get("source_url") or parsed.get("url") or ""
            artifact_filename = self._generate_artifact_filename(t, artifact, domain, url)
            (out / artifact_filename).write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"dir": str(out), "type": t, "artifact_file": artifact_filename}