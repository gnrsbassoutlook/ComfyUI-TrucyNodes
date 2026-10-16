"""TrucyLLM · LLM 客户端（合并自 ComfyUI-TrucyLLM）。

三种LLM接口一致（describe / chat），节点侧可互换：
  TrucyBrain      远程：LM Studio / 任何 OpenAI 兼容端点（requests）
  TrucyLocalBrain 本地：ComfyUI/models/LLM 下的 GGUF（llama.cpp + mmproj）
"""
import ipaddress
import os
from urllib.parse import urlparse

import requests


def _日志(msg):
    print(f"[TrucyLLM·LLM] {msg}")


def _是否内网地址(api_base):
    """判断 api_base 是否指向局域网/本机。

    为什么需要：requests 默认信任系统代理（HTTP_PROXY 等），用户机器上常开
    clash/v2ray 等代理，会把发往 192.168.x.x 的局域网请求当公网流量拦下来，
    返回 502「upstream connect failed」——LLM明明在线却「连不上」。
    内网地址必须绕过代理直连；公网 API（DeepSeek 等）保留环境代理不动。
    """
    try:
        host = (urlparse(str(api_base or "")).hostname or "").strip()
    except Exception:
        return False
    if not host:
        return False
    if host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local"):
        return True
    # 无点主机名（http://mac-studio:1234）= 内网机器名
    if "." not in host:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # 域名（api.deepseek.com 等）走外网代理
    return ip.is_private or ip.is_loopback or ip.is_link_local


def 规范化api_base(api_base):
    """把用户填的各种地址写法归一成可用的 base（省得手动拼 /v1、/chat/completions）。

    接受（举例）:
        https://api.deepseek.com                        → https://api.deepseek.com/v1
        https://api.deepseek.com/                       → https://api.deepseek.com/v1
        https://api.deepseek.com/v1                     → 原样
        https://api.deepseek.com/v1/chat/completions    → https://api.deepseek.com/v1
        http://192.168.1.112:1234                       → http://192.168.1.112:1234/v1
        http://host:8000/api                            → 原样（显式路径尊重不动）
    """
    url = str(api_base or "").strip().rstrip("/")
    if not url:
        return ""
    # 1. 剥掉完整的 completions/responses 路径（用户整条 API 地址粘过来也行）
    for suffix in ("/chat/completions", "/completions", "/responses"):
        if url.lower().endswith(suffix):
            url = url[: -len(suffix)].rstrip("/")
            break
    # 2. 裸域名（scheme://host[:port]，无路径）→ 自动补 /v1（OpenAI 兼容惯例）
    #    带显式路径的（如 /api）尊重原样，不擅加
    scheme, sep, rest = url.partition("://")
    if sep and "/" not in rest and not url.lower().endswith("/v1"):
        url = url.rstrip("/") + "/v1"
    return url


class TrucyBrainError(Exception):
    """LLM调用失败（携带可读的中文原因）。"""


class TrucyBrain:
    """局域网 LLM LLM（LM Studio / OpenAI 兼容端点）。"""

    def __init__(self, api_base="http://192.168.1.112:1234/v1", api_key="lm-studio",
                 model="gemma-4-e4b-it", timeout=300):
        self.api_base = 规范化api_base(api_base)
        self.api_key = api_key or ""
        self.model = (model or "").strip()
        try:
            self.timeout = int(timeout)
        except Exception:
            self.timeout = 300
        if self.timeout < 10:
            self.timeout = 10
        # 内网地址：独立 Session 关掉 trust_env，绕过系统代理直连
        # （代理会把局域网请求拦成 502）；公网地址：None = 用 requests 默认（走环境代理）
        self._session = None
        if _是否内网地址(self.api_base):
            self._session = requests.Session()
            self._session.trust_env = False

    def describe(self):
        return f"{self.model} @ {self.api_base}"

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get(self, url, **kw):
        if self._session is not None:
            return self._session.get(url, **kw)
        return requests.get(url, **kw)

    def _post(self, url, **kw):
        if self._session is not None:
            return self._session.post(url, **kw)
        return requests.post(url, **kw)

    def list_models(self):
        """GET {api_base}/models —— 返回模型 id 列表；不可达时返回空列表。"""
        try:
            resp = self._get(
                f"{self.api_base}/models", headers=self._headers(), timeout=15
            )
            if resp.ok:
                data = resp.json()
                return [m.get("id") for m in data.get("data", []) if m.get("id")]
        except Exception:
            pass
        return []

    def chat(self, messages, temperature=0.7, max_tokens=4096, images=None, 媒体部分=None, model=None):
        """
        执行一次 chat completion。

        参数:
            messages:   [{"role": "system"|"user"|"assistant", "content": str|list}, ...]
            temperature:采样温度
            max_tokens: 最大生成 token（推理型模型会先思考再作答，建议 >= 2048）
            images:     可选，base64 字符串列表，自动挂到最后一条 user 消息上（多模态）
            媒体部分:    可选，OpenAI 多模态 content parts 列表（文字标签+图片，
                       由 trucy_media 构建；优先于 images）
            model:      可选，覆盖LLM默认模型

        返回:
            (content_text, usage_dict)
        抛出:
            TrucyBrainError —— 附带中文可读原因
        """
        model_name = (model or self.model or "").strip()
        if not model_name:
            raise TrucyBrainError("未指定模型。请在LLM节点填写 Model（如 gemma-4-e4b-it）。")
        if not self.api_base:
            raise TrucyBrainError("未指定 API Base。请填写局域网地址，如 http://192.168.1.112:1234/v1")

        msgs = [dict(m) for m in messages]
        if 媒体部分:
            msgs = _挂载媒体部分(msgs, 媒体部分)
        elif images:
            msgs = self._attach_images(msgs, images)

        payload = {
            "model": model_name,
            "messages": msgs,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }

        # 主候选 + 兜底：端点只写了域名没写 /v1 时（如 https://api.deepseek.com），404 后自动补 /v1 重试
        candidates = [f"{self.api_base}/chat/completions"]
        if not self.api_base.endswith("/v1"):
            candidates.append(f"{self.api_base}/v1/chat/completions")
        try:
            resp = None
            for url in candidates:
                resp = self._post(
                    url, headers=self._headers(), json=payload, timeout=self.timeout
                )
                if resp.status_code != 404 or url == candidates[-1]:
                    break
        except requests.exceptions.ConnectionError:
            raise TrucyBrainError(
                f"连不上LLM {self.api_base}。请确认 Mac Studio 已开机、LM Studio 已启动并加载模型，"
                f"且地址/端口填写正确（当前: {self.api_base}）。"
            )
        except requests.exceptions.Timeout:
            raise TrucyBrainError(
                f"LLM响应超时（{self.timeout}s）。推理型模型生成较慢，可在LLM节点调大“请求超时(秒)”。"
            )
        except Exception as exc:
            raise TrucyBrainError(f"请求LLM时发生未知错误: {exc}")

        if not resp.ok:
            if resp.status_code == 401:
                raise TrucyBrainError(
                    "LLM返回 HTTP 401：API Key 无效或未授权。请检查LLM节点 api_key"
                    "（LM Studio 可填任意非空值；DeepSeek/OpenAI 需真实 key）。"
                )
            detail = resp.text[:300]
            try:
                err = resp.json()
                if isinstance(err, dict):
                    err = err.get("error", err)
                    if isinstance(err, dict):
                        detail = err.get("message", detail)
                    elif isinstance(err, str):
                        detail = err
            except Exception:
                pass
            raise TrucyBrainError(f"LLM返回 HTTP {resp.status_code}: {detail}")

        try:
            data = resp.json()
        except Exception:
            raise TrucyBrainError(f"LLM返回了无法解析的内容: {resp.text[:200]}")

        choices = data.get("choices") or []
        if not choices:
            raise TrucyBrainError("LLM响应中没有 choices 字段。")

        message = choices[0].get("message", {}) or {}
        content = message.get("content") or ""
        # 推理型模型（如 gemma-4-e4b-it）可能把正文放在 reasoning_content；
        # content 为空时回退取用，避免节点看起来“没有输出”。
        if not str(content).strip():
            fallback = message.get("reasoning_content") or ""
            if str(fallback).strip():
                content = fallback
        usage = data.get("usage", {}) or {}
        return str(content), usage

    @staticmethod
    def _attach_images(messages, images):
        """兼容旧调用：转模块级 _挂载图片。"""
        return _挂载图片(messages, images)


def _挂载图片(messages, images):
    """把 base64 图片挂到最后一条 user 消息上，转为 OpenAI 多模态格式。

    远程（requests）与本地（llama.cpp）两种LLM都接受这个格式。
    """
    msgs = [dict(m) for m in messages]
    idx = None
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i].get("role") == "user":
            idx = i
            break
    if idx is None:
        msgs.append({"role": "user", "content": "请分析这些图片。"})
        idx = len(msgs) - 1

    text = msgs[idx].get("content")
    if not isinstance(text, str):
        text = ""
    parts = []
    if text.strip():
        parts.append({"type": "text", "text": text})
    for img_b64 in images:
        img_b64 = str(img_b64 or "").strip()
        if not img_b64:
            continue
        if img_b64.startswith("data:"):
            url = img_b64
        else:
            url = f"data:image/jpeg;base64,{img_b64}"
        parts.append({"type": "image_url", "image_url": {"url": url}})
    if parts:
        msgs[idx]["content"] = parts
    return msgs


def _挂载媒体部分(messages, parts):
    """把 trucy_media 构建的多模态 parts（文字标签+图片）挂到最后一条 user 消息。

    远程（requests）与本地（llama.cpp）两种LLM都接受这个 OpenAI 多模态格式。
    空槽位素材压根不会出现在 parts 里——LLM看不到不存在的参考。
    """
    msgs = [dict(m) for m in messages]
    idx = None
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i].get("role") == "user":
            idx = i
            break
    if idx is None:
        msgs.append({"role": "user", "content": ""})
        idx = len(msgs) - 1

    content = msgs[idx].get("content")
    if isinstance(content, list):
        merged = list(content)
    else:
        merged = []
        if isinstance(content, str) and content.strip():
            merged.append({"type": "text", "text": content})
    merged.extend(parts)
    msgs[idx]["content"] = merged
    return msgs


# ---------------------------------------------------------------------------
# GGUF 扫描（ComfyUI/models/LLM，含子文件夹）
# ---------------------------------------------------------------------------
def 扫描gguf文件():
    """递归扫描 ComfyUI/models/LLM（含子文件夹）下的 gguf 文件。

    返回: (主模型列表, 投影模型列表, 扫描根目录列表)
          列表元素为相对根目录的路径（如 "Qwen3.8/Qwen3.8-27B-UD-IQ2_XXS.gguf"）。
    """
    roots = []
    try:
        import folder_paths
        for p in folder_paths.get_folder_paths("LLM"):
            if p and os.path.isdir(p) and p not in roots:
                roots.append(p)
    except Exception:
        pass
    try:
        fallback = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "models", "LLM")
        )
        if os.path.isdir(fallback) and fallback not in roots:
            roots.append(fallback)
    except Exception:
        pass

    主模型, 投影模型 = [], []
    for root in roots:
        for dirpath, _dirs, files in os.walk(root):
            for fn in sorted(files):
                if not fn.lower().endswith(".gguf"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), root).replace("\\", "/")
                if "mmproj" in fn.lower():
                    if rel not in 投影模型:
                        投影模型.append(rel)
                elif rel not in 主模型:
                    主模型.append(rel)
    主模型.sort()
    投影模型.sort()
    return 主模型, 投影模型, roots


# ---------------------------------------------------------------------------
# 本地 GGUF LLM（llama.cpp）
# ---------------------------------------------------------------------------
class TrucyLocalBrain:
    """本地 GGUF LLM（llama.cpp，支持 CUDA 卸载 + mmproj 多模态投影）。

    与 TrucyBrain 接口一致（describe / chat），节点侧可互换。
    模型实例按 (gguf, mmproj, n_ctx, n_gpu_layers, chat_format) 缓存——
    批处理连续跑不反复加载模型，保连续性；换文件/参数才重新加载。
    """

    _模型缓存 = {}

    def __init__(self, gguf路径, mmproj路径="", n_ctx=8192, n_gpu_layers=-1,
                 n_batch=512, 模型根目录=None, enable_thinking=True,
                 reasoning_effort="medium"):
        self.gguf相对 = (gguf路径 or "").strip()
        self.mmproj相对 = (mmproj路径 or "").strip()
        if self.mmproj相对 in ("(无)", "无", "none", "None", "-"):
            self.mmproj相对 = ""
        try:
            self.n_ctx = max(2048, int(n_ctx))
        except Exception:
            self.n_ctx = 8192
        try:
            self.n_gpu_layers = int(n_gpu_layers)
        except Exception:
            self.n_gpu_layers = -1
        try:
            self.n_batch = max(128, int(n_batch))
        except Exception:
            self.n_batch = 512
        self.enable_thinking = bool(enable_thinking)
        self.reasoning_effort = str(reasoning_effort or "medium")
        if self.reasoning_effort not in ("xhigh", "medium", "low"):
            self.reasoning_effort = "medium"
        self.模型根目录 = list(模型根目录 or [])
        self._chat_format = None
        self._校验路径()

    def _校验路径(self):
        if not self.gguf相对:
            raise TrucyBrainError("未选择 GGUF 文件。")
        self.gguf绝对 = self._解析(self.gguf相对)
        self.mmproj绝对 = self._解析(self.mmproj相对) if self.mmproj相对 else ""
        try:
            import llama_cpp  # noqa: F401
        except Exception as e:
            raise TrucyBrainError(
                f"llama_cpp 未安装（{e}）。请安装 CUDA 版 llama-cpp-python。"
            )

    def _解析(self, rel):
        if os.path.isabs(rel):
            if os.path.isfile(rel):
                return rel
            raise TrucyBrainError(f"找不到 GGUF 文件: {rel}")
        for root in self.模型根目录:
            cand = os.path.join(root, rel)
            if os.path.isfile(cand):
                return cand
        if os.path.isfile(rel):
            return os.path.abspath(rel)
        raise TrucyBrainError(
            f"找不到 GGUF 文件: {rel}。请确认文件在 ComfyUI/models/LLM"
            "（或其子文件夹）下，然后刷新LLM节点下拉。"
        )

    def describe(self):
        name = os.path.basename(self.gguf绝对)
        if self.n_gpu_layers < 0:
            where = "本地GPU全卸载"
        elif self.n_gpu_layers == 0:
            where = "本地CPU"
        else:
            where = f"本地GPU({self.n_gpu_layers}层)"
        vision = "+视觉" if self.mmproj绝对 else ""
        think = "思考开" if self.enable_thinking else "思考关"
        return f"{name}{vision} @ {where} · {think}"

    def _是qwen38(self):
        """按文件名识别 Qwen3.8 系列（该系 GGUF 模板带思考/推理强度参数）。"""
        name = os.path.basename(self.gguf绝对).lower()
        return any(k in name for k in ("qwen3.8", "qwen3_8", "qwen38"))

    def _挂qwen38处理器(self, llm):
        """Qwen3.8 系列：用模型自带 chat template 挂 handler，注入思考/推理强度参数。

        方案与 comfyUI-llama-TE 一致（已验证）：
          - 有 mmproj：GenericMTMDChatHandler + extra_template_arguments
          - 纯文本：Jinja2ChatFormatter 闭包注入同名参数
        """
        metadata = getattr(llm, "metadata", {}) or {}
        template = metadata.get("tokenizer.chat_template")
        if not template:
            raise TrucyBrainError(
                "Qwen3.8 GGUF 缺少 tokenizer.chat_template，无法应用思考/推理强度设置。"
            )
        模板参数 = {
            "enable_thinking": bool(self.enable_thinking),
            "preserve_thinking": False,
            "reasoning_effort": str(self.reasoning_effort),
        }
        if self.mmproj绝对:
            from llama_cpp.llama_multimodal import GenericMTMDChatHandler

            for extra in ({**模板参数, "add_vision_id": True}, 模板参数):
                try:
                    llm.chat_handler = GenericMTMDChatHandler(
                        chat_format=template,
                        mmproj_path=self.mmproj绝对,
                        extra_template_arguments=extra,
                        verbose=False,
                    )
                    return
                except TypeError:
                    continue
            raise TypeError("GenericMTMDChatHandler 不接受 extra_template_arguments")
        else:
            from llama_cpp.llama_chat_format import (
                Jinja2ChatFormatter,
                chat_formatter_to_chat_completion_handler,
            )

            def token_text(token_id):
                if token_id == -1:
                    return ""
                try:
                    return llm._model.token_get_text(token_id)
                except Exception:
                    return ""

            eos_id = llm.token_eos()
            eot_id = llm.token_eot()
            stop_ids = [t for t in (eos_id, eot_id) if t != -1] or None
            formatter = Jinja2ChatFormatter(
                template=template,
                eos_token=token_text(eos_id),
                bos_token=token_text(llm.token_bos()),
                stop_token_ids=stop_ids,
            )

            def qwen38_formatter(*, messages, **kwargs):
                kwargs.update(模板参数)
                return formatter(messages=messages, **kwargs)

            llm.chat_handler = chat_formatter_to_chat_completion_handler(qwen38_formatter)

    def _获取模型(self, chat_format=None):
        key = (self.gguf绝对, self.mmproj绝对, self.n_ctx, self.n_gpu_layers,
               self.n_batch, chat_format, self.enable_thinking, self.reasoning_effort)
        llm = TrucyLocalBrain._模型缓存.get(key)
        if llm is not None:
            return llm
        import inspect

        from llama_cpp import Llama

        可用参数 = set(inspect.signature(Llama.__init__).parameters)
        kwargs = {
            "model_path": self.gguf绝对,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "n_batch": self.n_batch,
            "verbose": False,
        }
        # 关闭 KV 检查点（llama-TE 同款）：避免 MTMD 多模态时的
        # "non-consecutive token position" / hybrid cache 警告
        if "ctx_checkpoints" in 可用参数:
            kwargs["ctx_checkpoints"] = 0

        if self._是qwen38():
            # Qwen3.8：先不带 mmproj 构造，加载后按自带模板挂 handler
            try:
                llm = Llama(**kwargs)
                self._挂qwen38处理器(llm)
            except TypeError:
                # 旧版 llama-cpp-python 不接受 extra_template_arguments → 退回通用构造
                try:
                    llm.close()
                except Exception:
                    pass
                if self.mmproj绝对:
                    kwargs["mmproj_path"] = self.mmproj绝对
                llm = Llama(**kwargs)
        else:
            # llama-cpp-python >= 0.4：多模态直接传 mmproj_path，
            # 内部按 GGUF 自带的 tokenizer.chat_template 建 GenericMTMDChatHandler
            if self.mmproj绝对:
                kwargs["mmproj_path"] = self.mmproj绝对
            if chat_format:
                kwargs["chat_format"] = chat_format
            llm = Llama(**kwargs)
        TrucyLocalBrain._模型缓存[key] = llm
        _日志(f"本地模型已加载: {os.path.basename(self.gguf绝对)}"
              f"（ctx={self.n_ctx}, gpu_layers={self.n_gpu_layers},"
              f" 思考={'开' if self.enable_thinking else '关'}"
              f"{'/' + self.reasoning_effort if self.enable_thinking else ''}）")
        return llm

    def chat(self, messages, temperature=0.7, max_tokens=4096, images=None, 媒体部分=None, model=None):
        llm = self._获取模型(self._chat_format)
        msgs = [dict(m) for m in messages]
        if 媒体部分:
            msgs = _挂载媒体部分(msgs, 媒体部分)
        elif images:
            msgs = _挂载图片(msgs, images)
        try:
            resp = llm.create_chat_completion(
                messages=msgs, temperature=float(temperature), max_tokens=int(max_tokens)
            )
        except Exception as e:
            err = str(e)
            # 聊天模板自动识别失败 → 换 qwen 模板重试一次（Qwen 系 GGUF 常见；
            # Qwen3.8 走自带模板 handler，不适用此兜底）
            if (self._chat_format is None and not self._是qwen38()
                    and any(k in err.lower() for k in ("format", "template", "jinja"))):
                _日志("本地LLM: 自动聊天模板识别失败，改用 qwen 模板重试")
                self._chat_format = "qwen"
                llm = self._获取模型("qwen")
                try:
                    resp = llm.create_chat_completion(
                        messages=msgs, temperature=float(temperature), max_tokens=int(max_tokens)
                    )
                except Exception as e2:
                    raise TrucyBrainError(f"本地模型推理失败: {e2}")
            else:
                raise TrucyBrainError(
                    f"本地模型推理失败: {err}。若是显存不足，请调小 n_gpu_layers / n_ctx。"
                )
        choices = resp.get("choices") or []
        if not choices:
            raise TrucyBrainError("本地模型响应中没有 choices。")
        message = choices[0].get("message", {}) or {}
        content = message.get("content") or ""
        # 推理型模型正文可能在 reasoning_content（如 Qwen3 thinking）
        if not str(content).strip():
            content = message.get("reasoning_content") or ""
        usage = resp.get("usage", {}) or {}
        return str(content), usage

    @classmethod
    def 卸载全部(cls):
        """释放所有已加载的本地模型（显存/内存）。返回卸载的实例数。"""
        count = 0
        for key in list(cls._模型缓存.keys()):
            llm = cls._模型缓存.pop(key, None)
            count += 1
            try:
                del llm
            except Exception:
                pass
        try:
            import gc
            gc.collect()
        except Exception:
            pass
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        return count
