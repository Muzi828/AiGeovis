"""
数据服务 - 使用 metaknowledge 读取 WoS 数据，pandas 进行数据操作
"""

from core.i18n import ZH

import os
import sys
import ssl
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter

# 配置SSL证书验证 - 修复SSL证书验证失败问题
try:
    import certifi
    # 创建使用certifi证书的SSL上下文
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    # 设置默认SSL上下文
    ssl._create_default_https_context = lambda: ssl_context
except ImportError:
    # 如果certifi未安装，禁用SSL验证（不推荐，但可以临时解决）
    ssl._create_default_https_context = ssl._create_unverified_context

# Disable logging to prevent log file creation
import logging
logging.basicConfig(level=logging.CRITICAL, handlers=[])  # Disable all logging handlers
# Remove any existing file handlers
for handler in logging.root.handlers[:]:
    if isinstance(handler, logging.FileHandler):
        logging.root.removeHandler(handler)

# Patch metaknowledge before importing to handle missing data files in packaged app
def _patch_metaknowledge_modules():
    """Patch metaknowledge modules to handle missing data files gracefully."""
    import importlib.util
    
    # Pre-create empty modules to prevent download attempts
    class FakeGenderModule:
        mappingDict = {}
        targetFilePath = ""
        
        @staticmethod
        def getMapping(useUK=False):
            return {}
        
        @staticmethod
        def downloadData(useUK=False):
            pass
        
        @staticmethod
        def nameStringGender(s, noExcept=False):
            return 'Unknown'
        
        @staticmethod
        def recordGenders(R):
            return {}
    
    # Check if we're running in a frozen (packaged) environment
    if getattr(sys, 'frozen', False):
        # Insert fake module before metaknowledge tries to use it
        sys.modules['metaknowledge.genders.nameGender'] = FakeGenderModule()

_patch_metaknowledge_modules()

import metaknowledge as mk

# Disable metaknowledge logging after import
# Set metaknowledge logger to CRITICAL level to prevent log file creation
try:
    mk_logger = logging.getLogger('metaknowledge')
    mk_logger.setLevel(logging.CRITICAL)
    mk_logger.propagate = False
    # Remove all handlers from metaknowledge logger
    for handler in mk_logger.handlers[:]:
        mk_logger.removeHandler(handler)
except:
    pass
import pandas as pd
import numpy as np


class DataService:
    """WoS 数据服务类"""
    
    # WoS 字段映射到友好名称
    FIELD_NAMES = {
        'TI': 'Title',
        'AU': 'Authors',
        'AF': 'Authors Full',
        'SO': 'Source',
        'PY': 'Year',
        'DT': 'Document Type',
        'DE': 'Author Keywords',
        'ID': 'Keywords Plus',
        'AB': 'Abstract',
        'TC': 'Times Cited',
        'NR': 'Num References',
        'DI': 'DOI',
        'WC': 'WoS Categories',
        'SC': 'Research Areas',
        'C1': 'Addresses',
        'RP': 'Reprint Address',
        'EM': 'Email',
        'OA': 'Open Access',
        'UT': 'Accession Number',
    }
    
    def __init__(self):
        self._record_collection: Optional[mk.RecordCollection] = None
        self._df: Optional[pd.DataFrame] = None
        self._file_path: Optional[str] = None
        self._data_version: int = 0  # 数据版本号，每次加载新数据时递增
        # 引文解析统计
        self._citations_parsed_count: int = 0  # 解析得到的总引文数（去重前）
        self._citations_filtered_count: int = 0  # 被过滤掉的引文数（逗号数不足）
        self._citations_shown_count: int = 0  # 去重后显示的引文数（初始状态）
        
    @property
    def is_loaded(self) -> bool:
        """是否已加载数据"""
        return self._record_collection is not None
    
    @property
    def data_version(self) -> int:
        """数据版本号，每次加载新数据时递增"""
        return self._data_version
    
    @property
    def record_count(self) -> int:
        """记录数量"""
        return len(self._record_collection) if self._record_collection else 0
    
    def get_filtered_record_collection(self, filtered_df: pd.DataFrame, remove_derived_fields: bool = False) -> Optional[mk.RecordCollection]:
        """
        根据过滤后的 DataFrame 创建 RecordCollection
        
        Args:
            filtered_df: 过滤后的 DataFrame
            remove_derived_fields: 是否移除衍生字段（用于WoS格式导出）
            
        Returns:
            过滤后的 RecordCollection，如果原始 RecordCollection 不存在则返回 None
        """
        if self._record_collection is None or filtered_df.empty:
            return None
        
        try:
            # 获取过滤后的记录的索引（使用 DataFrame 的原始索引）
            # 注意：如果 DataFrame 被重置过索引，需要使用其他方法匹配
            filtered_indices = set(filtered_df.index)
            
            # 定义衍生字段列表（这些字段不应该出现在WoS格式文件中）
            derived_fields = {'POS', 'NAU', 'NAUI', 'NAUC', 'NDE', 'NID', 'RID', '_PDF'}
            
            # 创建新的 RecordCollection，只包含过滤后的记录
            filtered_records = []
            for idx, record in enumerate(self._record_collection):
                # 如果 DataFrame 的索引是连续的，直接使用索引
                # 否则需要通过其他字段（如 UT）来匹配
                if idx in filtered_indices:
                    # 如果需要移除衍生字段，创建一个新的record副本
                    if remove_derived_fields:
                        # 创建record的副本，移除衍生字段
                        # metaknowledge的Record对象支持字典式访问和修改
                        clean_record = {}
                        for tag in record.keys():
                            if tag not in derived_fields:
                                value = record.get(tag)
                                # 处理列表类型的字段
                                if isinstance(value, (list, tuple)):
                                    clean_record[tag] = value
                                else:
                                    clean_record[tag] = value
                        # 使用mk.Record创建新record
                        # metaknowledge的Record可以从字典创建
                        try:
                            # 尝试使用mk.Record构造函数
                            new_record = mk.Record(clean_record)
                            filtered_records.append(new_record)
                        except (TypeError, AttributeError):
                            # 如果mk.Record不可用，尝试复制原record并删除字段
                            try:
                                # 复制record并删除衍生字段
                                new_record = record.copy()
                                for field in derived_fields:
                                    if field in new_record:
                                        del new_record[field]
                                filtered_records.append(new_record)
                            except:
                                # 最后尝试：直接使用字典（RecordCollection可能接受）
                                filtered_records.append(clean_record)
                    else:
                        filtered_records.append(record)
            
            # 创建新的 RecordCollection
            if filtered_records:
                return mk.RecordCollection(filtered_records)
            else:
                return mk.RecordCollection([])
        except Exception as e:
            print(f"[DataService] Error creating filtered RecordCollection: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def load_directory(self, directory: str, use_cache: bool = True) -> int:
        """
        加载目录下所有 WoS 文件
        
        Args:
            directory: WoS 文件目录路径
            use_cache: 是否启用 metaknowledge 缓存（默认启用）
            
        Returns:
            加载的记录数量
        """
        try:
            path = Path(directory)
            if not path.exists():
                raise FileNotFoundError(f"Directory not found: {directory}")
            
            print(f"{ZH.S_93e3430d8a}{directory}")
            print(f"{ZH.S_b974fd0d1a}{path.exists()}")
            
            # 在打包环境中禁用缓存，避免路径不匹配和权限问题
            if getattr(sys, 'frozen', False):
                use_cache = False
            
            print(f"{ZH.S_1906446269}{use_cache}")
            print(f"{ZH.S_19e9a630de}")
            
            # 使用 metaknowledge 加载目录
            self._record_collection = mk.RecordCollection(str(path), cached=use_cache)
            self._file_path = str(path)
            
            print(f"{ZH.S_10f13709c0}{len(self._record_collection)}")
            
            # 构建 DataFrame
            print(f"{ZH.S_6f5ecb4859}")
            self._build_dataframe()
            print(f"{ZH.S_63636580bf}{len(self._df)}")
            
            # 更新数据版本号
            self._data_version += 1
            print(f"{ZH.S_0e4abc04ea}{self._data_version}")
            
            return self.record_count
        except Exception as e:
            print(ZH.S_err_load_dir)
            print(f"{ZH.S_92740e4266}{type(e).__name__}")
            print(f"{ZH.S_7a8e552018}{str(e)}")
            print(f"{ZH.S_d3f1c641d3}")
            traceback.print_exc()
            raise
    
    def load_file(self, filepath: str, use_cache: bool = True) -> int:
        """
        加载单个 WoS 文件
        
        Args:
            filepath: WoS 文件路径
            use_cache: 是否启用 metaknowledge 缓存（默认启用）
            
        Returns:
            加载的记录数量
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # 在打包环境中禁用缓存
        if getattr(sys, 'frozen', False):
            use_cache = False
            
        self._record_collection = mk.RecordCollection(filepath, cached=use_cache)
        self._file_path = filepath
        self._build_dataframe()
        
        # 更新数据版本号
        self._data_version += 1
        
        return self.record_count
    
    def _build_dataframe(self):
        """构建 pandas DataFrame"""
        try:
            if not self._record_collection:
                self._df = pd.DataFrame()
                return
            
            print(f"{ZH.S_9449fc6faa}{len(self._record_collection)}")
            
            # 使用 metaknowledge 内置方法转换为 DataFrame
            print(f"{ZH.S_d90dbff5fc}")
            self._df = self._record_collection.makeDict()
            print(f"{ZH.S_ffde352c58}{type(self._df)}")
            
            self._df = pd.DataFrame(self._df)
            print(f"{ZH.S_8f351ee448}{self._df.shape}")
            
            # 转置使每行为一条记录
            if not self._df.empty:
                # 获取所有记录的字典列表
                records_list = []
                record_count = 0
                print(f"{ZH.S_89339c2bdc}{len(self._record_collection)}")
                
                for idx, record in enumerate(self._record_collection):
                    try:
                        record_dict = {}
                        for tag in record.keys():
                            value = record.get(tag)
                            # 处理列表类型的字段
                            if isinstance(value, (list, tuple)):
                                if tag == 'C3':
                                    # C3 是自由文本机构列表，metaknowledge 按“物理行”返回，
                                    # 长机构名折行时会被拆成多元素。此处必须用空格拼接续行
                                    # （真正的机构分隔符 ";" 已在文本中），否则会在折行处误插
                                    # ";" 把机构名切碎（如 "...(NIH) -" + "USA"）。
                                    record_dict[tag] = ' '.join(str(v).strip() for v in value if str(v).strip())
                                else:
                                    record_dict[tag] = '; '.join(str(v) for v in value)
                            else:
                                record_dict[tag] = value
                        records_list.append(record_dict)
                        record_count += 1
                        
                        # 每处理100条记录输出一次进度
                        if (idx + 1) % 100 == 0:
                            print(f"{ZH.S_1cec709824}{idx + 1}/{len(self._record_collection)}{ZH.S_53d2ea9fcb}")
                    except IndexError as e:
                        print(f"{ZH.S_fd5bf370e1}{idx}{ZH.S_33936daaca}")
                        print(f"{ZH.S_a06bfbaa06}{record}")
                        print(f"{ZH.S_7a8e552018}{str(e)}")
                        traceback.print_exc()
                        raise
                    except Exception as e:
                        print(f"{ZH.S_fd5bf370e1}{idx}{ZH.S_6dcbb0970a}")
                        print(f"{ZH.S_a06bfbaa06}{record}")
                        print(f"{ZH.S_92740e4266}{type(e).__name__}")
                        print(f"{ZH.S_7a8e552018}{str(e)}")
                        traceback.print_exc()
                        raise
                
                print(f"{ZH.S_866306f543}{record_count}{ZH.S_53d2ea9fcb}")
                print(f"{ZH.S_ed66551897}")
                self._df = pd.DataFrame(records_list)
                print(f"{ZH.S_5ed37cb9e6}{self._df.shape}")
                # 确保列名保持原始大小写（metaknowledge返回的字段标签通常是大写的）
                if not self._df.empty:
                    print(f"{ZH.S_218dc60913}{list(self._df.columns)[:10]}...")  # 打印前10个列名
                
                # 字段衍生：生成所有需要的字段
                print(f"{ZH.S_b248610462}")
                self._derive_fields()
                print(f"{ZH.S_aebadf691f}{self._df.shape}")
                
                # 数值字段转换为int类型
                print(f"{ZH.S_0509d65bbd}")
                self._convert_numeric_fields()
                print(f"{ZH.S_510a0c262b}")
                
                # 清洗C1字段中的国家名称
                print(f"{ZH.S_276eac722d}")
                self._clean_country_names()
                print(f"{ZH.S_218030a5e8}")
        except Exception as e:
            print(ZH.S_err_build_df)
            print(f"{ZH.S_92740e4266}{type(e).__name__}")
            print(f"{ZH.S_7a8e552018}{str(e)}")
            print(f"{ZH.S_d3f1c641d3}")
            traceback.print_exc()
            raise
    
    def _derive_fields(self):
        """字段衍生：基于已有字段生成所有需要的字段"""
        if self._df is None or self._df.empty:
            return
        
        # 添加POS字段（行号，从1开始）
        self._df.insert(0, 'POS', range(1, len(self._df) + 1))
        
        # 计算NAU - Number of Authors
        if 'AU' in self._df.columns:
            self._df['NAU'] = self._df['AU'].apply(
                lambda x: len([a.strip() for a in str(x).split(';')]) if pd.notna(x) and str(x).strip() else 0
            )
        else:
            self._df['NAU'] = 0
        
        # 计算NAUI - Number of Authors' Institutions
        if 'C1' in self._df.columns:
            def count_institutions(c1_str):
                if pd.isna(c1_str) or not str(c1_str).strip():
                    return 0
                institutions = set()
                for addr in str(c1_str).split(';'):
                    addr_clean = addr.split(']')[1] if ']' in addr else addr
                    parts = addr_clean.split(',')
                    if parts:
                        inst = parts[0].strip().lower()
                        if inst:
                            institutions.add(inst)
                return len(institutions)
            self._df['NAUI'] = self._df['C1'].apply(count_institutions)
        else:
            self._df['NAUI'] = 0
        
        # 计算NAUC - Number of Authors' Regions/Countries
        if 'C1' in self._df.columns:
            def count_countries(c1_str):
                if pd.isna(c1_str) or not str(c1_str).strip():
                    return 0
                countries = set()
                for addr in str(c1_str).split(';'):
                    parts = addr.strip().rstrip('.').split(',')
                    if parts:
                        country = parts[-1].strip().lower()
                        if country:
                            countries.add(country)
                return len(countries)
            self._df['NAUC'] = self._df['C1'].apply(count_countries)
        else:
            self._df['NAUC'] = 0
        
        # 计算NDE - Number of Keywords
        if 'DE' in self._df.columns:
            self._df['NDE'] = self._df['DE'].apply(
                lambda x: len([k.strip() for k in str(x).split(';')]) if pd.notna(x) and str(x).strip() else 0
            )
        else:
            self._df['NDE'] = 0
        
        # 计算NID - Number of Keywords Plus
        if 'ID' in self._df.columns:
            self._df['NID'] = self._df['ID'].apply(
                lambda x: len([k.strip() for k in str(x).split(';')]) if pd.notna(x) and str(x).strip() else 0
            )
        else:
            self._df['NID'] = 0
        
        # 计算FAU - First Author（从AU字段提取第一个作者）
        if 'AU' in self._df.columns:
            self._df['FAU'] = self._df['AU'].apply(
                lambda x: str(x).split(';')[0].strip() if pd.notna(x) and str(x).strip() else ''
            )
        else:
            self._df['FAU'] = ''
        
        # 计算RID - Records Id（使用索引+1）
        self._df['RID'] = self._df.index + 1
        
        # 确保所有字段都存在（如果不存在则填充空值）
        required_fields = [
            'TI', 'SO', 'AB', 'AU', 'DI', 'DE', 'DT', 'EM', 'LA', 'NR', 'PT',
            'SC', 'SN', 'WC', 'PY', 'PD', 'IS', 'VL', 'BP', 'EP', 'PG',
            'TC', 'U1', 'U2', 'Z9', 'PU', 'PI', 'PA', 'RP', 'AF', 'CR', 'C1', 'C3'
        ]
        
        for field in required_fields:
            if field not in self._df.columns:
                self._df[field] = ''
    
    def _convert_numeric_fields(self):
        """将数值字段转换为int类型"""
        if self._df is None or self._df.empty:
            return
        
        # 数值字段列表
        numeric_fields = [
            'POS', 'NR', 'PY', 'TC', 'U1', 'U2', 'Z9', 
            'NAU', 'NAUI', 'NAUC', 'NDE', 'NID', 'RID',
            'IS', 'VL', 'BP', 'EP', 'PG'
        ]
        
        for field in numeric_fields:
            if field in self._df.columns:
                # 尝试转换为数值，无法转换的设为0
                self._df[field] = pd.to_numeric(self._df[field], errors='coerce').fillna(0).astype(int)
    
    def _clean_country_names(self):
        """清洗C1字段中的国家名称，统一各种变体"""
        if self._df is None or self._df.empty or 'C1' not in self._df.columns:
            return
        
        def normalize_country(country: str) -> str:
            """标准化单个国家名称"""
            import re
            
            if not country:
                return country
            
            country = country.strip().rstrip('.')
            lower_country = country.lower()
            
            # 美国州缩写列表（用于识别邮编格式）
            us_states = {
                'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
                'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
                'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
                'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
                'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy',
                'dc', 'pr', 'vi', 'gu', 'as', 'mp'  # 包括DC和美国领地
            }
            
            # 检测美国邮编格式：州缩写 + 空格 + 数字（如 "Pa 19104"、"Ny 14853"、"Dc 20036"）
            # 格式1：纯邮编如 "Pa 19104"
            zip_pattern = re.match(r'^([a-zA-Z]{2})\s+(\d{5}(?:-\d{4})?)$', country.strip())
            if zip_pattern:
                state_abbr = zip_pattern.group(1).lower()
                if state_abbr in us_states:
                    return 'USA'
            
            # 格式2：州全名或缩写后跟邮编，如 "Pennsylvania 19104" 或 "New York 10001"
            # 这种格式更少见，但也要处理
            if re.search(r'\d{5}(?:-\d{4})?$', country):
                # 以5位数字结尾，很可能是美国地址
                return 'USA'
            
            # 美国的各种变体 - 包含数字邮编形式如 "Tn 37209 Usa"
            usa_patterns = ['usa', 'u.s.a.', 'u.s.a', 'us', 'u.s.', 'u.s', 
                           'united states', 'united states of america', 'america',
                           'the united states', 'the usa']
            # 检查是否以 "usa" 结尾（处理 "Tn 37209 Usa" 这种情况）
            if lower_country in usa_patterns or lower_country.endswith(' usa') or lower_country.endswith(' us'):
                return 'USA'
            
            # 中国的各种变体
            china_patterns = ['china', 'peoples r china', "people's republic of china",
                             'p.r. china', 'pr china', 'p r china', 'prc',
                             "people's r china", 'peoples republic of china']
            if lower_country in china_patterns:
                return 'China'
            
            # 英国的各种变体
            uk_patterns = ['uk', 'u.k.', 'u.k', 'united kingdom', 'great britain',
                          'england', 'scotland', 'wales', 'northern ireland',
                          'britain', 'the uk', 'the united kingdom']
            if lower_country in uk_patterns:
                return 'UK'
            
            # 韩国的各种变体
            korea_patterns = ['south korea', 'korea', 'republic of korea', 'rok',
                             's korea', 'korea south', 'korean']
            if lower_country in korea_patterns:
                return 'South Korea'
            
            # 其他国家映射
            mappings = {
                'germany': 'Germany', 'fed rep ger': 'Germany', 'federal republic of germany': 'Germany',
                'france': 'France', 'japan': 'Japan', 'canada': 'Canada', 'australia': 'Australia',
                'india': 'India', 'italy': 'Italy', 'spain': 'Spain', 'netherlands': 'Netherlands',
                'the netherlands': 'Netherlands', 'holland': 'Netherlands', 'brazil': 'Brazil',
                'russia': 'Russia', 'russian federation': 'Russia', 'taiwan': 'Taiwan(China)',
                'switzerland': 'Switzerland', 'sweden': 'Sweden', 'poland': 'Poland',
                'belgium': 'Belgium', 'austria': 'Austria', 'norway': 'Norway', 'denmark': 'Denmark',
                'finland': 'Finland', 'portugal': 'Portugal', 'greece': 'Greece', 'ireland': 'Ireland',
                'singapore': 'Singapore', 'israel': 'Israel', 'mexico': 'Mexico', 'turkey': 'Turkey',
                'turkiye': 'Turkey', 'iran': 'Iran', 'islamic republic of iran': 'Iran',
                'saudi arabia': 'Saudi Arabia', 'malaysia': 'Malaysia', 'thailand': 'Thailand',
                'indonesia': 'Indonesia', 'vietnam': 'Vietnam', 'viet nam': 'Vietnam',
                'pakistan': 'Pakistan', 'egypt': 'Egypt', 'south africa': 'South Africa',
                'nigeria': 'Nigeria', 'argentina': 'Argentina', 'chile': 'Chile', 'colombia': 'Colombia',
                'new zealand': 'New Zealand', 'czech republic': 'Czech Republic', 'czechia': 'Czech Republic',
                'hungary': 'Hungary', 'romania': 'Romania', 'ukraine': 'Ukraine', 'hong kong': 'Hong Kong(China)',
                'macau': 'Macau(China)',
                'philippines': 'Philippines', 'bangladesh': 'Bangladesh', 'sri lanka': 'Sri Lanka',
                'nepal': 'Nepal', 'peru': 'Peru', 'venezuela': 'Venezuela', 'cuba': 'Cuba',
                'north korea': 'North Korea', 'dprk': 'North Korea', 'syria': 'Syria',
                'uzbekistan': 'Uzbekistan',
            }
            
            if lower_country in mappings:
                return mappings[lower_country]
            
            return country
        
        def clean_c1_field(c1_str):
            """清洗整个C1字段"""
            if pd.isna(c1_str) or not str(c1_str).strip():
                return c1_str
            
            cleaned_parts = []
            for addr in str(c1_str).split(';'):
                addr = addr.strip()
                if not addr:
                    continue
                
                # 分割地址
                parts = addr.rstrip('.').split(',')
                if parts:
                    # 标准化最后一个部分（国家）
                    country = parts[-1].strip()
                    normalized = normalize_country(country)
                    parts[-1] = ' ' + normalized  # 保持原有的空格格式
                    cleaned_parts.append(','.join(parts))
            
            return '; '.join(cleaned_parts) if cleaned_parts else c1_str
        
        # 应用清洗
        self._df['C1'] = self._df['C1'].apply(clean_c1_field)
    
    def get_dataframe(self) -> pd.DataFrame:
        """获取完整的 DataFrame"""
        return self._df.copy() if self._df is not None else pd.DataFrame()
    
    def get_records_page(self, page: int = 1, page_size: int = 50) -> pd.DataFrame:
        """
        获取分页数据
        
        Args:
            page: 页码（从1开始）
            page_size: 每页记录数
            
        Returns:
            当前页的 DataFrame
        """
        if self._df is None or self._df.empty:
            return pd.DataFrame()
            
        start = (page - 1) * page_size
        end = start + page_size
        return self._df.iloc[start:end].copy()
    
    def get_display_dataframe(self, columns: List[str] = None) -> pd.DataFrame:
        """
        获取用于显示的 DataFrame（选择特定列）
        
        Args:
            columns: 要显示的列名列表
            
        Returns:
            筛选后的 DataFrame
        """
        if self._df is None or self._df.empty:
            return pd.DataFrame()
            
        if columns is None:
            # 默认显示列
            columns = ['TI', 'SO', 'AU', 'DI', 'NR', 'PY', 'TC']
            
        # 只选择存在的列
        available_cols = [c for c in columns if c in self._df.columns]
        return self._df[available_cols].copy()
    
    # ==================== 统计分析方法 ====================
    
    def get_publication_years(self) -> pd.Series:
        """
        获取发表年份统计
        
        Returns:
            年份计数的 Series，索引为年份
        """
        if self._df is None or 'PY' not in self._df.columns:
            return pd.Series(dtype=int)
            
        years = self._df['PY'].dropna().astype(int)
        return years.value_counts().sort_index()
    
    def get_source_titles(self, top_n: int = None) -> pd.Series:
        """
        获取来源期刊统计
        
        Args:
            top_n: 返回前N个，None表示全部
            
        Returns:
            期刊计数的 Series
        """
        if self._df is None or 'SO' not in self._df.columns:
            return pd.Series(dtype=int)
            
        sources = self._df['SO'].dropna().str.lower()
        counts = sources.value_counts()
        return counts.head(top_n) if top_n else counts
    
    def get_authors(self, top_n: int = None) -> pd.Series:
        """
        获取所有作者统计
        
        Args:
            top_n: 返回前N个
            
        Returns:
            作者计数的 Series
        """
        if self._df is None or 'AU' not in self._df.columns:
            return pd.Series(dtype=int)
            
        # 展开作者列表
        authors = []
        for au_str in self._df['AU'].dropna():
            if isinstance(au_str, str):
                authors.extend([a.strip().lower() for a in au_str.split(';')])
                
        counts = pd.Series(authors).value_counts()
        return counts.head(top_n) if top_n else counts
    
    def get_first_authors(self, top_n: int = None) -> pd.Series:
        """
        获取第一作者统计
        
        Args:
            top_n: 返回前N个
            
        Returns:
            第一作者计数的 Series
        """
        if self._df is None or 'AU' not in self._df.columns:
            return pd.Series(dtype=int)
            
        first_authors = []
        for au_str in self._df['AU'].dropna():
            if isinstance(au_str, str):
                parts = au_str.split(';')
                if parts:
                    first_authors.append(parts[0].strip().lower())
                    
        counts = pd.Series(first_authors).value_counts()
        return counts.head(top_n) if top_n else counts
    
    def get_wos_categories(self, top_n: int = None) -> pd.Series:
        """
        获取 WoS 学科分类统计
        
        Args:
            top_n: 返回前N个
            
        Returns:
            分类计数的 Series
        """
        if self._df is None or 'WC' not in self._df.columns:
            return pd.Series(dtype=int)
            
        categories = []
        for wc_str in self._df['WC'].dropna():
            if isinstance(wc_str, str):
                categories.extend([c.strip().lower() for c in wc_str.split(';')])
                
        counts = pd.Series(categories).value_counts()
        return counts.head(top_n) if top_n else counts
    
    def get_research_areas(self, top_n: int = None) -> pd.Series:
        """
        获取研究领域统计
        
        Args:
            top_n: 返回前N个
            
        Returns:
            研究领域计数的 Series
        """
        if self._df is None or 'SC' not in self._df.columns:
            return pd.Series(dtype=int)
            
        areas = []
        for sc_str in self._df['SC'].dropna():
            if isinstance(sc_str, str):
                areas.extend([a.strip().lower() for a in sc_str.split(';')])
                
        counts = pd.Series(areas).value_counts()
        return counts.head(top_n) if top_n else counts
    
    def get_organizations(self, top_n: int = None) -> pd.Series:
        """
        获取机构统计
        
        Args:
            top_n: 返回前N个
            
        Returns:
            机构计数的 Series
        """
        if self._df is None or 'C1' not in self._df.columns:
            return pd.Series(dtype=int)
            
        orgs = []
        for c1_str in self._df['C1'].dropna():
            if isinstance(c1_str, str):
                # C1 格式: [Author] Org, City, Country.
                for addr in c1_str.split(';'):
                    # 提取机构名
                    if ']' in addr:
                        addr = addr.split(']')[1]
                    parts = addr.split(',')
                    if parts:
                        orgs.append(parts[0].strip().lower())
                        
        counts = pd.Series(orgs).value_counts()
        return counts.head(top_n) if top_n else counts
    
    def get_countries(self, top_n: int = None) -> pd.Series:
        """
        获取国家/地区统计（每条记录中同一国家只统计一次）
        
        Args:
            top_n: 返回前N个
            
        Returns:
            国家计数的 Series
        """
        if self._df is None or 'C1' not in self._df.columns:
            return pd.Series(dtype=int)
            
        countries = []
        for c1_str in self._df['C1'].dropna():
            if isinstance(c1_str, str):
                # 使用集合确保每条记录中同一国家只计数一次
                record_countries = set()
                for addr in c1_str.split(';'):
                    # 国家通常在地址末尾
                    parts = addr.strip().rstrip('.').split(',')
                    if parts:
                        country = parts[-1].strip().lower()
                        # 标准化国家名
                        country = self._normalize_country(country)
                        if country:
                            record_countries.add(country)
                # 将该记录的唯一国家添加到总列表
                countries.extend(record_countries)
                            
        counts = pd.Series(countries).value_counts()
        return counts.head(top_n) if top_n else counts
    
    def _normalize_country(self, country: str) -> str:
        """标准化国家名称"""
        import re
        
        if not country:
            return country
        
        country = country.strip().rstrip('.')
        lower_country = country.lower()
        
        # 美国州缩写列表（用于识别邮编格式）
        us_states = {
            'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
            'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
            'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
            'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
            'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy',
            'dc', 'pr', 'vi', 'gu', 'as', 'mp'  # 包括DC和美国领地
        }
        
        # 检测美国邮编格式：州缩写 + 空格 + 数字（如 "pa 19104"、"ny 14853"）
        zip_pattern = re.match(r'^([a-zA-Z]{2})\s+(\d{5}(?:-\d{4})?)$', country.strip())
        if zip_pattern:
            state_abbr = zip_pattern.group(1).lower()
            if state_abbr in us_states:
                return 'usa'
        
        # 以5位数字结尾，很可能是美国地址
        if re.search(r'\d{5}(?:-\d{4})?$', country):
            return 'usa'
        
        # 纯州缩写（如 "Mo"、"Dc"）- 两个字母且在州列表中
        if len(lower_country) == 2 and lower_country in us_states:
            return 'usa'
        
        country_map = {
            'peoples r china': 'china',
            'pr china': 'china',
            'p r china': 'china',
            'prc': 'china',
            "people's r china": 'china',
            'united states': 'usa',
            'united states of america': 'usa',
            'u s a': 'usa',
            'u.s.a.': 'usa',
            'u.s.a': 'usa',
            'u.s.': 'usa',
            'us': 'usa',
            'america': 'usa',
            'england': 'uk',
            'united kingdom': 'uk',
            'scotland': 'uk',
            'wales': 'uk',
            'north ireland': 'uk',
            'northern ireland': 'uk',
            'great britain': 'uk',
            'south korea': 'korea',
            'republic of korea': 'korea',
            'rok': 'korea',
            'deutschland': 'germany',
            'fed rep ger': 'germany',
            'russian federation': 'russia',
            'turkiye': 'turkey',
        }
        return country_map.get(lower_country, country)
    
    def get_document_types(self) -> pd.Series:
        """
        获取文档类型统计
        
        Returns:
            文档类型计数的 Series
        """
        if self._df is None or 'DT' not in self._df.columns:
            return pd.Series(dtype=int)
            
        return self._df['DT'].dropna().str.lower().value_counts()
    
    def get_author_keywords(self, top_n: int = None) -> pd.Series:
        """
        获取作者关键词统计
        
        Args:
            top_n: 返回前N个
            
        Returns:
            关键词计数的 Series
        """
        if self._df is None or 'DE' not in self._df.columns:
            return pd.Series(dtype=int)
            
        keywords = []
        for de_str in self._df['DE'].dropna():
            if isinstance(de_str, str):
                keywords.extend([k.strip().lower() for k in de_str.split(';')])
                
        counts = pd.Series(keywords).value_counts()
        return counts.head(top_n) if top_n else counts
    
    def get_keywords_plus(self, top_n: int = None) -> pd.Series:
        """
        获取 Keywords Plus 统计
        
        Args:
            top_n: 返回前N个
            
        Returns:
            关键词计数的 Series
        """
        if self._df is None or 'ID' not in self._df.columns:
            return pd.Series(dtype=int)
            
        keywords = []
        for id_str in self._df['ID'].dropna():
            if isinstance(id_str, str):
                keywords.extend([k.strip().lower() for k in id_str.split(';')])
                
        counts = pd.Series(keywords).value_counts()
        return counts.head(top_n) if top_n else counts
    
    def get_open_access_stats(self) -> pd.Series:
        """
        获取开放获取统计
        
        Returns:
            OA 类型计数的 Series
        """
        if self._df is None or 'OA' not in self._df.columns:
            return pd.Series(dtype=int)
            
        oa = self._df['OA'].fillna('Not OA')
        return oa.value_counts()
    
    def get_citation_stats(self) -> Dict[str, Any]:
        """
        获取引用统计
        
        Returns:
            包含各种引用指标的字典
        """
        if self._df is None or 'TC' not in self._df.columns:
            return {}
            
        tc = pd.to_numeric(self._df['TC'], errors='coerce').dropna()
        
        return {
            'total_citations': int(tc.sum()),
            'mean_citations': round(tc.mean(), 2),
            'median_citations': int(tc.median()),
            'max_citations': int(tc.max()),
            'h_index': self._calculate_h_index(tc),
        }
    
    def _calculate_h_index(self, citations: pd.Series) -> int:
        """计算 h-index"""
        sorted_citations = citations.sort_values(ascending=False).reset_index(drop=True)
        h = 0
        for i, c in enumerate(sorted_citations):
            if c >= i + 1:
                h = i + 1
            else:
                break
        return h
    
    # ==================== 筛选方法 ====================
    
    def filter_by_years(self, start_year: int = None, end_year: int = None) -> 'DataService':
        """
        按年份筛选
        
        Args:
            start_year: 起始年份
            end_year: 结束年份
            
        Returns:
            新的 DataService 实例
        """
        if self._df is None:
            return self
            
        filtered = self._df.copy()
        
        if 'PY' in filtered.columns:
            py = pd.to_numeric(filtered['PY'], errors='coerce')
            if start_year:
                filtered = filtered[py >= start_year]
            if end_year:
                filtered = filtered[py <= end_year]
                
        new_service = DataService()
        new_service._df = filtered
        new_service._record_collection = self._record_collection
        return new_service
    
    def filter_by_source(self, sources: List[str]) -> 'DataService':
        """
        按来源期刊筛选
        
        Args:
            sources: 期刊名称列表
            
        Returns:
            新的 DataService 实例
        """
        if self._df is None or 'SO' not in self._df.columns:
            return self
            
        sources_lower = [s.lower() for s in sources]
        filtered = self._df[self._df['SO'].str.lower().isin(sources_lower)]
        
        new_service = DataService()
        new_service._df = filtered
        new_service._record_collection = self._record_collection
        return new_service
    
    def search(self, query: str, fields: List[str] = None) -> 'DataService':
        """
        搜索记录
        
        Args:
            query: 搜索关键词
            fields: 搜索字段列表，默认搜索标题和摘要
            
        Returns:
            新的 DataService 实例
        """
        if self._df is None or not query:
            return self
            
        if fields is None:
            fields = ['TI', 'AB', 'DE', 'ID']
            
        query_lower = query.lower()
        mask = pd.Series([False] * len(self._df))
        
        for field in fields:
            if field in self._df.columns:
                field_mask = self._df[field].fillna('').str.lower().str.contains(query_lower, regex=False)
                mask = mask | field_mask
                
        filtered = self._df[mask]
        
        new_service = DataService()
        new_service._df = filtered
        new_service._record_collection = self._record_collection
        return new_service
    
    # ==================== 网络分析数据 ====================
    
    def get_coauthorship_data(self, top_n: int = 50) -> Tuple[List[Dict], List[Dict]]:
        """
        获取合作作者网络数据
        
        Args:
            top_n: 返回前N个作者
            
        Returns:
            (nodes, edges) 节点和边的列表
        """
        if self._df is None or 'AU' not in self._df.columns:
            return [], []
            
        # 统计作者
        author_counts = self.get_authors(top_n)
        top_authors = set(author_counts.index)
        
        # 构建节点
        nodes = [
            {'id': i, 'label': author, 'size': int(count)}
            for i, (author, count) in enumerate(author_counts.items())
        ]
        author_to_id = {author: i for i, author in enumerate(author_counts.index)}
        
        # 构建边（共同作者关系）
        edge_counts = Counter()
        for au_str in self._df['AU'].dropna():
            if isinstance(au_str, str):
                authors = [a.strip().lower() for a in au_str.split(';')]
                # 只保留 top 作者
                authors = [a for a in authors if a in top_authors]
                # 生成作者对
                for i, a1 in enumerate(authors):
                    for a2 in authors[i+1:]:
                        edge_counts[(min(a1, a2), max(a1, a2))] += 1
                        
        edges = [
            {'source': author_to_id[a1], 'target': author_to_id[a2], 'weight': count}
            for (a1, a2), count in edge_counts.items()
            if a1 in author_to_id and a2 in author_to_id
        ]
        
        return nodes, edges
    
    def get_cocitation_data(self, top_n: int = 50) -> Tuple[List[Dict], List[Dict]]:
        """
        获取共被引网络数据
        
        Args:
            top_n: 返回前N个被引文献
            
        Returns:
            (nodes, edges) 节点和边的列表
        """
        if self._record_collection is None:
            return [], []
            
        # 使用 metaknowledge 的共被引分析
        try:
            citation_network = self._record_collection.coCiteNetwork(nodeType='full')
            # 转换为我们的格式
            nodes = []
            edges = []
            node_map = {}
            
            for i, node in enumerate(citation_network.nodes()):
                if i >= top_n:
                    break
                nodes.append({
                    'id': i,
                    'label': str(node)[:50],  # 截断长标签
                    'size': citation_network.degree(node)
                })
                node_map[node] = i
                
            for source, target, data in citation_network.edges(data=True):
                if source in node_map and target in node_map:
                    edges.append({
                        'source': node_map[source],
                        'target': node_map[target],
                        'weight': data.get('weight', 1)
                    })
                    
            return nodes, edges
        except Exception as e:
            print(f"Error building co-citation network: {e}")
            return [], []
    
    def get_country_collaboration_data(self, top_n: int = 20) -> Tuple[List[Dict], List[Dict]]:
        """
        获取国家合作网络数据
        
        Args:
            top_n: 返回前N个国家
            
        Returns:
            (nodes, edges) 节点和边的列表
        """
        if self._df is None or 'C1' not in self._df.columns:
            return [], []
            
        # 统计国家
        country_counts = self.get_countries(top_n)
        top_countries = set(country_counts.index)
        
        # 构建节点
        nodes = [
            {'id': i, 'label': country, 'size': int(count)}
            for i, (country, count) in enumerate(country_counts.items())
        ]
        country_to_id = {country: i for i, country in enumerate(country_counts.index)}
        
        # 构建边（国家合作关系）
        edge_counts = Counter()
        for c1_str in self._df['C1'].dropna():
            if isinstance(c1_str, str):
                countries_in_paper = set()
                for addr in c1_str.split(';'):
                    parts = addr.strip().rstrip('.').split(',')
                    if parts:
                        country = self._normalize_country(parts[-1].strip().lower())
                        if country in top_countries:
                            countries_in_paper.add(country)
                            
                # 生成国家对
                countries_list = list(countries_in_paper)
                for i, c1 in enumerate(countries_list):
                    for c2 in countries_list[i+1:]:
                        edge_counts[(min(c1, c2), max(c1, c2))] += 1
                        
        edges = [
            {'source': country_to_id[c1], 'target': country_to_id[c2], 'weight': count}
            for (c1, c2), count in edge_counts.items()
            if c1 in country_to_id and c2 in country_to_id
        ]
        
        return nodes, edges
    
    def parse_cited_references(self, progress_callback=None, min_commas: int = 4, remove_duplicates: bool = True) -> pd.DataFrame:
        """
        解析CR字段，提取引文信息并聚合统计
        使用metaknowledge的Citation对象进行解析
        
        Args:
            progress_callback: Optional callback function(percent: float) for progress reporting (0-100)
            min_commas: Minimum number of commas required in ROW field (default: 4)
            remove_duplicates: Whether to remove duplicate citations (default: True)
        
        Returns:
            包含以下列的DataFrame:
            - POS: 位置（从1开始）
            - CRA: Cited Reference Author（引文作者）
            - CRY: Cited Reference Year（引文年份）
            - CRS: Cited Reference Source（引文来源）
            - DOI: Digital Object Identifier（DOI，可点击链接）
            - CRV: Cited Reference Volume
            - CRP: Cited Reference Page
            - COUNT: 引文在文献中出现的总次数（基于DOI和CRS唯一性）
            - ROW: 原始的引文格式
        """
        if self._record_collection is None:
            print("[DataService] RecordCollection is None")
            return pd.DataFrame(columns=['POS', 'CRA', 'CRY', 'CRS', 'DOI', 'CRV', 'CRP', 'COUNT', 'ROW'])
        
        # 解析统计初始化
        self._citations_parsed_count = 0
        self._citations_filtered_count = 0
        self._citations_shown_count = 0
        
        # 存储所有解析后的引文
        all_citations = []
        
        # Read citations from DataFrame CR field (most reliable)
        if self._df is not None and 'CR' in self._df.columns:
            total_rows = len(self._df)
            print(f"[DataService] Reading CR field from DataFrame, total records={total_rows}")
            try:
                filtered_count = 0
                from metaknowledge import Citation
                
                for row_idx, (idx, row) in enumerate(self._df.iterrows()):
                    # Report progress
                    if progress_callback and row_idx % 50 == 0:
                        percent = (row_idx / total_rows) * 100
                        progress_callback(percent)
                    
                    cr_value = row.get('CR')
                    if pd.isna(cr_value) or not str(cr_value).strip():
                        continue
                    
                    cr_str = str(cr_value).strip()
                    # CR field usually separates multiple citations with semicolons
                    citation_strings = [c.strip() for c in cr_str.split(';') if c.strip()]
                    
                    for cit_str in citation_strings:
                        if not cit_str:
                            continue
                        
                        # Filter citations: must have at least min_commas commas
                        if cit_str.count(',') < min_commas:
                            filtered_count += 1
                            continue
                        
                        # Try creating Citation object from string
                        try:
                            citation = Citation(cit_str)
                            # Extract information using Citation object attributes
                            parsed = {
                                'CRA': self._get_citation_author(citation),
                                'CRY': self._get_citation_year(citation),
                                'CRS': self._get_citation_source(citation),
                                'DOI': self._get_citation_doi(citation),
                                'CRV': self._get_citation_volume(citation),
                                'CRP': self._get_citation_page(citation),
                                'ROW': citation.original if hasattr(citation, 'original') and citation.original else cit_str
                            }
                            all_citations.append(parsed)
                        except Exception as e1:
                            # If Citation creation fails, skip this citation
                            continue
                
                # Final progress update
                if progress_callback:
                    progress_callback(100)
                
                self._citations_parsed_count = len(all_citations)
                self._citations_filtered_count = filtered_count
                print(f"[DataService] Finished parsing from DataFrame, parsed {len(all_citations)} citations, filtered {filtered_count} citations with <{min_commas} commas")
            except Exception as e:
                print(f"[DataService] Error reading CR field from DataFrame: {e}")
                import traceback
                traceback.print_exc()
        
        if not all_citations:
            total_records = len(self._df) if self._df is not None else (len(self._record_collection) if self._record_collection else 0)
            print(f"[DataService] No citation data found. Total records={total_records}")
            # Check if CR field exists
            if self._df is not None and 'CR' in self._df.columns:
                cr_count = self._df['CR'].notna().sum()
                cr_non_empty = (self._df['CR'].astype(str).str.strip() != '').sum()
                print(f"[DataService] CR field statistics: non-null values={cr_count}, non-empty strings={cr_non_empty}")
            return pd.DataFrame(columns=['POS', 'CRA', 'CRY', 'CRS', 'DOI', 'CRV', 'CRP', 'COUNT', 'ROW'])
        
        # 转换为DataFrame
        citations_df = pd.DataFrame(all_citations)
        
        # 计算COUNT：使用四个字段（CRY、CRA、CRS、DOI）的一致性作为唯一性标识
        def get_unique_key(row):
            # 去重基于四个字段：年份(CRY)、作者(CRA)、来源(CRS)、DOI
            cry = str(row.get('CRY', '')).strip().lower() if pd.notna(row.get('CRY')) and str(row.get('CRY', '')).strip() else ''
            cra = str(row.get('CRA', '')).strip().lower() if pd.notna(row.get('CRA')) and str(row.get('CRA', '')).strip() else ''
            crs = str(row.get('CRS', '')).strip().lower() if pd.notna(row.get('CRS')) and str(row.get('CRS', '')).strip() else ''
            doi = str(row.get('DOI', '')).strip().lower() if pd.notna(row.get('DOI')) and str(row.get('DOI', '')).strip() else ''
            return f"{cry}|{cra}|{crs}|{doi}"
        
        citations_df['_unique_key'] = citations_df.apply(get_unique_key, axis=1)
        
        # 统计每个唯一引文的出现次数
        count_dict = citations_df['_unique_key'].value_counts().to_dict()
        citations_df['COUNT'] = citations_df['_unique_key'].map(count_dict)
        
        # 根据参数决定是否去重
        if remove_duplicates:
            # 去重：基于四个字段（CRY、CRA、CRS、DOI）的一致性
            citations_df = citations_df.drop_duplicates(subset=['_unique_key'], keep='first')
            print(f"[DataService] Removed duplicates based on CRY+CRA+CRS+DOI, remaining {len(citations_df)} unique citations")
        
        # 保存去重后的初始数据条数（用于Info窗口显示）
        self._citations_shown_count = len(citations_df)
        
        # 删除临时列
        citations_df = citations_df.drop(columns=['_unique_key'])
        
        # 添加POS列
        citations_df.insert(0, 'POS', range(1, len(citations_df) + 1))
        
        # 按COUNT降序排序
        citations_df = citations_df.sort_values('COUNT', ascending=False).reset_index(drop=True)
        
        # 更新POS
        citations_df['POS'] = range(1, len(citations_df) + 1)
        
        # 确保所有列都存在
        required_columns = ['POS', 'CRA', 'CRY', 'CRS', 'DOI', 'CRV', 'CRP', 'COUNT', 'ROW']
        for col in required_columns:
            if col not in citations_df.columns:
                citations_df[col] = ''
        
        # 重新排列列顺序
        citations_df = citations_df[required_columns]
        
        return citations_df
    
    def _get_citation_author(self, citation) -> str:
        """Extract author from Citation object"""
        try:
            # metaknowledge Citation uses 'author' attribute (not 'authors')
            if hasattr(citation, 'author') and citation.author:
                return str(citation.author)
        except Exception as e:
            pass
        return ''
    
    def _get_citation_year(self, citation) -> str:
        """Extract year from Citation object"""
        try:
            if hasattr(citation, 'year') and citation.year:
                return str(citation.year)
        except:
            pass
        return ''
    
    def _get_citation_source(self, citation) -> str:
        """Extract source/journal from Citation object"""
        try:
            if hasattr(citation, 'journal') and citation.journal:
                return str(citation.journal)
        except:
            pass
        return ''
    
    def _get_citation_doi(self, citation) -> str:
        """Extract DOI from Citation object"""
        try:
            if hasattr(citation, 'DOI') and citation.DOI:
                return str(citation.DOI)
        except:
            pass
        return ''
    
    def _get_citation_volume(self, citation) -> str:
        """Extract volume from Citation object"""
        try:
            # metaknowledge Citation uses 'V' attribute (not 'volume')
            if hasattr(citation, 'V') and citation.V:
                # V may include 'V' prefix, remove it
                vol = str(citation.V)
                if vol.startswith('V'):
                    vol = vol[1:]
                return vol
        except:
            pass
        return ''
    
    def _get_citation_page(self, citation) -> str:
        """Extract page from Citation object"""
        try:
            # metaknowledge Citation uses 'P' attribute (not 'pages')
            if hasattr(citation, 'P') and citation.P:
                # P may include 'P' prefix, remove it
                page = str(citation.P)
                if page.startswith('P'):
                    page = page[1:]
                return page
        except:
            pass
        return ''
    
    def _parse_citation_string(self, citation: str) -> Optional[Dict[str, str]]:
        """
        解析单个引文字符串
        
        Args:
            citation: 引文字符串，格式如 "author, year, source, volume, page, doi"
            
        Returns:
            包含解析后字段的字典，如果解析失败返回None
        """
        import re
        
        if not citation or not citation.strip():
            return None
        
        citation = citation.strip()
        result = {
            'CRA': '',
            'CRY': '',
            'CRS': '',
            'DOI': '',
            'CRV': '',
            'CRP': ''
        }
        
        # 尝试提取DOI（通常格式为 "doi 10.xxx" 或 "DOI: 10.xxx"）
        doi_pattern = r'doi\s*:?\s*(10\.\d+/[^\s,;]+)'
        doi_match = re.search(doi_pattern, citation, re.IGNORECASE)
        if doi_match:
            result['DOI'] = doi_match.group(1).strip()
            # 从原始字符串中移除DOI部分以便后续解析
            citation = re.sub(doi_pattern, '', citation, flags=re.IGNORECASE).strip()
        
        # 按逗号分割（但要注意引文格式可能不一致）
        parts = [p.strip() for p in citation.split(',')]
        
        if len(parts) >= 1:
            # 第一部分通常是作者
            result['CRA'] = parts[0]
        
        if len(parts) >= 2:
            # 第二部分可能是年份
            year_part = parts[1]
            # 尝试提取年份（4位数字）
            year_match = re.search(r'\b(19|20)\d{2}\b', year_part)
            if year_match:
                result['CRY'] = year_match.group(0)
            else:
                # 如果不是年份，可能是来源的一部分
                result['CRS'] = year_part
        
        if len(parts) >= 3:
            # 第三部分可能是来源或年份
            third_part = parts[2]
            year_match = re.search(r'\b(19|20)\d{2}\b', third_part)
            if year_match and not result['CRY']:
                result['CRY'] = year_match.group(0)
            elif not result['CRS']:
                result['CRS'] = third_part
        
        # 如果CRS还没找到，尝试从剩余部分提取
        if not result['CRS'] and len(parts) >= 3:
            # 合并第3部分及之后的部分作为来源（直到遇到卷号）
            source_parts = []
            for i in range(2, len(parts)):
                part = parts[i]
                # 如果遇到卷号标识（v, vol, volume等），停止
                if re.search(r'\b(v|vol|volume)\s*\d+', part, re.IGNORECASE):
                    break
                source_parts.append(part)
            if source_parts:
                result['CRS'] = ', '.join(source_parts)
        
        # 提取卷号（格式如 "v436", "vol 52", "volume 1"）
        volume_pattern = r'\b(?:v|vol|volume)\s*(\d+)\b'
        volume_match = re.search(volume_pattern, citation, re.IGNORECASE)
        if volume_match:
            result['CRV'] = volume_match.group(1)
        
        # 提取页码（格式如 "p900", "pp 855", "page 8"）
        page_pattern = r'\b(?:p|pp|page)\s*(\d+)\b'
        page_match = re.search(page_pattern, citation, re.IGNORECASE)
        if page_match:
            result['CRP'] = page_match.group(1)
        
        # 如果没有提取到年份，尝试从整个字符串中查找
        if not result['CRY']:
            year_match = re.search(r'\b(19|20)\d{2}\b', citation)
            if year_match:
                result['CRY'] = year_match.group(0)
        
        # 如果没有提取到来源，使用除作者、年份、DOI外的其他部分
        if not result['CRS']:
            # 移除作者、年份、DOI、卷号、页码后的剩余部分
            temp = citation
            if result['CRA']:
                temp = temp.replace(result['CRA'], '', 1).strip()
            if result['CRY']:
                temp = temp.replace(result['CRY'], '', 1).strip()
            if result['DOI']:
                temp = temp.replace(result['DOI'], '', 1).strip()
            if result['CRV']:
                temp = re.sub(r'\b(?:v|vol|volume)\s*' + result['CRV'], '', temp, flags=re.IGNORECASE).strip()
            if result['CRP']:
                temp = re.sub(r'\b(?:p|pp|page)\s*' + result['CRP'], '', temp, flags=re.IGNORECASE).strip()
            # 清理多余的逗号和空格
            temp = re.sub(r'^[,;\s]+|[,;\s]+$', '', temp)
            if temp:
                result['CRS'] = temp
        
        return result


# 全局单例
_data_service_instance: Optional[DataService] = None


def get_data_service() -> DataService:
    """获取数据服务单例"""
    global _data_service_instance
    if _data_service_instance is None:
        _data_service_instance = DataService()
    return _data_service_instance
