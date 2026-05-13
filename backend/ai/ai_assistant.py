"""
AI辅助识别和纠正模块
支持 DeepSeek、通义千问、SiliconFlow、Gemini、Claude 和 Ollama 本地推理
自动级联降级：主模型超时/失败 → 自动切换备用模型
"""
import os
import time
from typing import Dict, Any, List, Optional
from backend.ai.ai_providers import (
    AIProvider, DeepSeekProvider, QwenProvider, SiliconFlowProvider,
    GeminiProvider, ClaudeProvider, OllamaProvider,
    ALL_PROVIDERS, AUTO_PRIORITY, DEFAULT_TIMEOUT
)


class AIAssistant:
    """AI助手，用于OCR纠正和题目解析，支持多模型级联降级"""

    def __init__(self, provider: str = None):
        """
        初始化AI助手
        :param provider: AI提供商名称或 'auto'（自动级联选择）
        支持的提供商: deepseek, qwen, siliconflow, gemini, claude, ollama, auto
        """
        self.provider_name = provider or os.getenv('AI_PROVIDER', 'auto')
        self.provider: Optional[AIProvider] = None
        self._fallback_providers: List[AIProvider] = []  # 降级备用列表
        self._all_providers_info: List[Dict] = []  # 所有可用 Provider 信息
        self._init_providers()

    def _init_providers(self):
        """初始化AI提供商，支持级联降级"""
        if self.provider_name == 'auto':
            self._init_auto_cascade()
        else:
            self._init_single_provider(self.provider_name)

    def _init_auto_cascade(self):
        """自动级联初始化：按优先级尝试，主模型不可用则切换下一个"""
        print("🔄 AI助手: 自动选择模式，扫描可用模型...")
        for name in AUTO_PRIORITY:
            provider_cls = ALL_PROVIDERS.get(name)
            if not provider_cls:
                continue
            try:
                provider = provider_cls()
                info = {
                    'name': name,
                    'available': provider.is_available(),
                    'provider_name': provider.get_provider_name(),
                }
                if provider.is_available():
                    info.update(provider.get_model_info())
                self._all_providers_info.append(info)

                if provider.is_available():
                    if self.provider is None:
                        # 第一个可用的作为主 Provider
                        self.provider = provider
                        self.provider_name = name
                        print(f"✅ AI助手: 主模型 → {provider.get_provider_name()}")
                    else:
                        # 后续可用的作为降级备选
                        self._fallback_providers.append(provider)
                        print(f"   备用模型 → {provider.get_provider_name()}")
            except Exception as e:
                print(f"   ⚠️ {name} 初始化失败: {e}")

        if self.provider is None:
            print("⚠️ AI助手: 无可用的AI提供商")
            print("   可尝试: 1.设置DEEPSEEK_API_KEY 2.设置DASHSCOPE_API_KEY "
                  "3.设置SILICONFLOW_API_KEY 4.设置GOOGLE_API_KEY 5.启动Ollama")

    def _init_single_provider(self, name: str):
        """初始化指定的单个 Provider"""
        provider_cls = ALL_PROVIDERS.get(name.lower())
        if not provider_cls:
            print(f"❌ 未知的AI提供商: {name} (支持: {', '.join(ALL_PROVIDERS.keys())})")
            return

        try:
            provider = provider_cls()
            if provider.is_available():
                self.provider = provider
                self.provider_name = name.lower()
                print(f"✅ AI助手: 使用 {provider.get_provider_name()}")
            else:
                print(f"❌ {name} 不可用")
                # 即使主模型不可用，也初始化降级列表
                self._init_fallback_from_others(name.lower())
        except Exception as e:
            print(f"❌ {name} 初始化失败: {e}")
            self._init_fallback_from_others(name.lower())

    def _init_fallback_from_others(self, exclude_name: str):
        """从其他 Provider 中寻找降级备选"""
        for name in AUTO_PRIORITY:
            if name == exclude_name:
                continue
            provider_cls = ALL_PROVIDERS.get(name)
            if not provider_cls:
                continue
            try:
                provider = provider_cls()
                if provider.is_available():
                    self._fallback_providers.append(provider)
                    print(f"   降级备选 → {provider.get_provider_name()}")
                    # 如果主模型不可用，自动提升第一个备选为主模型
                    if self.provider is None:
                        self.provider = provider
                        self.provider_name = name
                        print(f"   ✅ 自动提升为主模型: {provider.get_provider_name()}")
            except Exception:
                pass

    def is_available(self) -> bool:
        """检查AI助手是否可用"""
        return self.provider is not None and self.provider.is_available()

    def get_provider_info(self) -> Dict[str, Any]:
        """获取当前提供商信息"""
        result = {
            'available': self.is_available(),
            'provider': None,
            'provider_code': self.provider_name,
            'fallback_count': len(self._fallback_providers),
            'fallback_names': [p.get_provider_name() for p in self._fallback_providers],
        }
        if self.is_available():
            result['provider'] = self.provider.get_provider_name()
            result.update(self.provider.get_model_info())
        return result

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """获取所有可用的AI提供商列表"""
        providers = []
        if self.is_available():
            info = {'name': self.provider_name}
            info.update(self.provider.get_model_info())
            providers.append(info)
        for p in self._fallback_providers:
            if p.is_available():
                info = {'name': p.get_provider_name().lower()}
                info.update(p.get_model_info())
                providers.append(info)
        return providers

    def _call_with_fallback(self, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        带降级策略的方法调用
        主模型失败/超时 → 依次尝试备用模型
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用，请配置API Key或启动Ollama',
            }

        # 尝试主模型
        start_time = time.time()
        try:
            method = getattr(self.provider, method_name)
            result = method(*args, **kwargs)
            if result.get('success', False):
                elapsed = time.time() - start_time
                result['elapsed_seconds'] = round(elapsed, 2)
                return result
            # 主模型返回失败，记录错误
            primary_error = result.get('error', '未知错误')
            print(f"⚠️ {self.provider.get_provider_name()} {method_name} 失败: {primary_error}")
        except Exception as e:
            primary_error = str(e)
            print(f"⚠️ {self.provider.get_provider_name()} {method_name} 异常: {primary_error}")

        # 主模型失败，尝试降级备选
        for fallback in self._fallback_providers:
            if not fallback.is_available():
                continue
            try:
                print(f"   降级尝试 → {fallback.get_provider_name()}")
                method = getattr(fallback, method_name)
                result = method(*args, **kwargs)
                if result.get('success', False):
                    elapsed = time.time() - start_time
                    result['elapsed_seconds'] = round(elapsed, 2)
                    result['fallback_from'] = self.provider.get_provider_name()
                    result['provider'] = fallback.get_provider_name()
                    print(f"   ✅ 降级成功 → {fallback.get_provider_name()} ({elapsed:.1f}s)")
                    return result
                else:
                    print(f"   ❌ {fallback.get_provider_name()} 也失败: {result.get('error', '')}")
            except Exception as e:
                print(f"   ❌ {fallback.get_provider_name()} 异常: {e}")

        # 所有模型都失败
        elapsed = time.time() - start_time
        return {
            'success': False,
            'error': f'所有AI模型均失败 (已尝试 {1 + len(self._fallback_providers)} 个模型，耗时 {elapsed:.1f}s)',
            'primary_error': primary_error,
            'elapsed_seconds': round(elapsed, 2),
        }

    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        """使用AI纠正OCR识别的文本（带级联降级）"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用',
                'corrected_text': ocr_text,
                'original_text': ocr_text
            }
        result = self._call_with_fallback('correct_ocr_text', ocr_text, confidence)
        # 确保 corrected_text 字段存在
        if not result.get('success') and 'corrected_text' not in result:
            result['corrected_text'] = ocr_text
            result['original_text'] = ocr_text
        return result

    def parse_questions(self, text: str) -> Dict[str, Any]:
        """使用AI智能解析和提取题目（带级联降级）"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用',
                'questions': []
            }
        result = self._call_with_fallback('parse_questions', text)
        if not result.get('success') and 'questions' not in result:
            result['questions'] = []
        return result

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """分析单个题目，提取详细信息（带级联降级）"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用'
            }
        return self._call_with_fallback('analyze_question', question_text)

    def batch_correct_questions(self, questions: List[str]) -> Dict[str, Any]:
        """批量纠正和分析题目"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用',
                'questions': questions
            }

        results = []
        for idx, question in enumerate(questions):
            try:
                analysis = self.analyze_question(question)
                if analysis['success']:
                    results.append({
                        'original': question,
                        'analysis': analysis,
                        'index': idx
                    })
                else:
                    results.append({
                        'original': question,
                        'error': analysis.get('error'),
                        'index': idx
                    })
            except Exception as e:
                results.append({
                    'original': question,
                    'error': str(e),
                    'index': idx
                })

        return {
            'success': True,
            'questions': results,
            'total': len(results),
            'provider': self.provider.get_provider_name() if self.provider else None
        }
