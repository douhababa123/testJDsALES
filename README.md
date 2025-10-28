# 京东冰箱型号比对系统

一个自动化工具，用于爬取京东冰箱新品型号并与本地 Excel 表格进行比对，找出缺失的型号。

## 🎯 功能特点

- **后台爬取**：使用轻量级 HTTP 爬虫后台拉取京东冰箱新品数据，减少浏览器指纹暴露
- **智能品牌映射**：自动将京东品牌名称映射到对应的 Excel Sheet
- **精准比对**：忽略大小写和空格，准确比对型号
- **实时进度**：显示爬取和比对的实时进度
- **结果导出**：将缺失型号导出为 Excel 文件

## 📋 系统要求

- Python 3.11+
- Streamlit
- Playwright
- openpyxl
- pandas
- xlsxwriter

## 🚀 使用方法

### 1. 启动应用

应用已配置为自动启动，访问 `http://0.0.0.0:5000` 即可使用。

### 2. 准备 Excel 文件

Excel 文件必须包含以下 7 个 Sheet（顺序不限）：

- `Haier` - 海尔品牌
- `Casarte` - 卡萨帝品牌
- `Colmo` - COLMO 品牌
- `Hisense&Ronshen` - 海信和容声品牌
- `Midea` - 美的品牌
- `BSH` - 西门子和博世品牌
- `Meiling` - 美菱品牌

每个 Sheet 的 **第 9 行** 存储该品牌的所有型号，每个单元格一个型号，横向排列。

示例：
```
A9: BCD-001
B9: BCD-002
C9: BCD-003
...
```

### 3. 上传文件并开始比对

1. 在网页界面上传准备好的 Excel 文件
2. 系统会自动验证文件格式和 Sheet
3. 点击"开始比对"按钮
4. 等待爬取和比对完成（约 10-30 分钟）
5. 查看结果并下载缺失型号列表

## 🔍 工作原理

### 1. Excel 数据读取

- 验证 Excel 文件包含所有必需的 Sheet
- 从每个 Sheet 的第 9 行读取型号数据
- 标准化型号（去除空格，转换大写）

### 2. 京东数据爬取

新版爬虫不再依赖浏览器，而是通过 JD 的搜索接口后台拉取商品列表，并异步访问商品详情页。

核心步骤：

1. 调用 `https://search.jd.com/s_new.php` 获取分页商品列表
2. 解析 `data-sku` 列表拿到商品 SKU
3. 异步请求 PC 端和移动端详情页，提取品牌、门店和“能效网规格型号”
4. 内置重试、限速和代理轮换逻辑，降低触发风控的概率

### 2.1 反爬策略

- **限速**：默认请求间隔 1s，带抖动，防止出现固定频率
- **重试**：指数退避，自动重试网络失败或 403
- **指纹分散**：随机 UA、Referer，支持自定义请求头
- **代理轮换**：可传入代理池实现出口 IP 轮换
- **多端兜底**：优先解析 PC 详情页，缺失型号时回退到移动端详情页

### 3. 品牌映射

系统使用以下映射关系：

| Excel Sheet | 京东品牌 |
|-------------|----------|
| Haier | 海尔 |
| Casarte | 卡萨帝 |
| Colmo | COLMO |
| Hisense&Ronshen | 海信、容声 |
| Midea | 美的 |
| BSH | 西门子、博世 |
| Meiling | 美菱 |

### 4. 型号比对

- 只比对以 `BCD-` 或 `MR-` 开头的型号
- 标准化后进行比对（忽略大小写和空格）
- 找出京东有但 Excel 中没有的型号

### 5. 结果输出

- 网页显示：按品牌分组展示缺失型号和商品链接
- Excel 下载：
  - 汇总 Sheet：包含所有品牌的缺失型号
  - 品牌 Sheet：每个品牌单独一个 Sheet

### 6. 后台爬虫调用示例

```python
from utils.jd_scraper import JDScraper, ScraperConfig

config = ScraperConfig(keyword="冰箱", max_pages=5, proxy_pool=["http://user:pass@proxy:8888"])

async with JDScraper(config) as scraper:
    async for product in scraper.iter_products():
        print(product.sku, product.brand, product.model)
```

## 🛠️ 开发调试

如需在本地使用 VS Code 进行调试，请参考 [VS Code 调试指南](./VSCODE_SETUP.md)。

## 📁 项目结构

```
.
├── app.py                      # Streamlit 主应用
├── utils/
│   ├── excel_handler.py        # Excel 文件处理
│   ├── brand_mapper.py         # 品牌映射逻辑
│   ├── model_comparator.py     # 型号比对逻辑
│   ├── jd_scraper.py          # 京东后台异步爬虫
│   └── excel_exporter.py       # Excel 结果导出
├── .streamlit/
│   └── config.toml            # Streamlit 配置
└── README.md                  # 项目文档
```

## ⚙️ 核心模块说明

### ExcelHandler

负责处理 Excel 文件的上传、验证和数据读取。

**主要功能：**
- 验证 Excel 文件包含所有必需的 Sheet
- 从第 9 行读取型号数据
- 标准化型号格式

### BrandMapper

负责将京东品牌名称映射到 Excel Sheet 名称。

**主要功能：**
- 提取品牌名（处理"海尔（Haier）"格式）
- 品牌名映射到 Sheet
- 判断是否为目标品牌

### ModelComparator

负责比对京东型号和 Excel 型号。

**主要功能：**
- 标准化型号（去除空格、转大写）
- 验证型号有效性（BCD-/MR- 开头）
- 比对找出缺失型号
- 生成统计信息

### JDScraper

使用 Playwright 自动化浏览器爬取京东数据。

**主要功能：**
- 启动无头浏览器
- 应用筛选条件（新品、取消仅显示有货）
- 遍历所有分页
- 提取商品详情（品牌、型号）
- 实时进度反馈

### ExcelExporter

将比对结果导出为 Excel 文件。

**主要功能：**
- 生成汇总 Sheet
- 为每个品牌创建单独 Sheet
- 格式化表格（表头、链接等）

## 🛠️ 技术栈

- **Streamlit**: Web 界面框架
- **Playwright**: 浏览器自动化
- **openpyxl**: Excel 文件读取
- **pandas**: 数据处理
- **xlsxwriter**: Excel 文件导出

## ⚠️ 注意事项

1. **运行时间**：爬取过程可能需要 10-30 分钟，取决于商品数量
2. **网络要求**：需要稳定的网络连接访问京东网站
3. **反爬虫**：系统已实现随机延迟和真实用户模拟，但仍可能被反爬虫机制拦截
4. **数据准确性**：确保 Excel 文件格式正确，第 9 行数据完整
5. **浏览器资源**：Playwright 会占用一定的系统资源

## 🔧 故障排除

### 问题：上传 Excel 文件失败

**解决方案：**
- 检查文件格式是否为 .xlsx 或 .xls
- 确认包含所有 7 个必需的 Sheet
- 确认 Sheet 名称拼写正确

### 问题：爬取过程中断

**解决方案：**
- 检查网络连接是否稳定
- 重新点击"开始比对"按钮
- 如果多次失败，可能是京东反爬虫机制，建议稍后重试

### 问题：找不到型号

**解决方案：**
- 确认商品详情页包含"能效网规格型号"字段
- 检查型号是否以 BCD- 或 MR- 开头
- 查看进度日志了解具体错误信息

## 📊 示例输出

### 网页显示

```
🔍 Haier - 15 个缺失型号

型号                    商品链接
BCD-602WGHFD2BGWU1     https://item.jd.com/10187984028937.html
BCD-520WDPZU1          https://item.jd.com/...
...
```

### Excel 文件

**汇总 Sheet:**

| 品牌 | 型号 | 商品链接 |
|------|------|----------|
| Haier | BCD-602WGHFD2BGWU1 | https://... |
| Casarte | BCD-520... | https://... |

**各品牌 Sheet:**

每个品牌一个独立 Sheet，包含该品牌的所有缺失型号。

## 📝 更新日志

### v1.0.0 (2025-10-27)

- ✅ 初始版本发布
- ✅ 支持 7 个品牌的型号比对
- ✅ Playwright 自动化爬取
- ✅ 实时进度显示
- ✅ Excel 结果导出

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**开发时间**: 2025年10月27日
**技术支持**: 基于 Streamlit 和 Playwright 构建
