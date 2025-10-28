# 京东冰箱型号比对系统

## 项目概述

这是一个基于 Streamlit 和 Playwright 的自动化工具，用于：
1. 从京东网站爬取冰箱新品型号信息
2. 与用户上传的 Excel 表格进行比对
3. 找出 Excel 中缺失的型号
4. 生成比对结果报告

## 技术架构

### 前端
- **Streamlit**: Web 界面框架
- 提供文件上传、进度显示、结果展示功能

### 后端
- **Playwright**: 浏览器自动化，爬取京东数据
- **openpyxl**: Excel 文件读取
- **pandas**: 数据处理
- **xlsxwriter**: Excel 结果导出

### 核心模块

1. **utils/excel_handler.py**
   - 处理 Excel 文件上传和验证
   - 读取第 9 行的型号数据
   - 标准化型号格式

2. **utils/brand_mapper.py**
   - 京东品牌名到 Excel Sheet 的映射
   - 支持 7 个品牌：海尔、卡萨帝、COLMO、海信/容声、美的、西门子/博世、美菱

3. **utils/model_comparator.py**
   - 型号标准化（去除空格、转大写）
   - 型号有效性验证（BCD-/MR- 开头）
   - 比对逻辑实现

4. **utils/jd_scraper.py**
   - Playwright 浏览器自动化
   - 京东筛选条件应用
   - 分页遍历
   - 商品详情提取

5. **utils/excel_exporter.py**
   - 生成 Excel 比对结果
   - 包含汇总 Sheet 和各品牌 Sheet

## Excel 数据格式

### 必需的 Sheet（共 7 个）
- Haier
- Casarte
- Colmo
- Hisense&Ronshen
- Midea
- BSH
- Meiling

### 数据位置
每个 Sheet 的第 9 行存储该品牌的所有型号，横向排列（每个单元格一个型号）。

## 品牌映射关系

```python
BRAND_MAPPING = {
    'Haier': ['海尔', 'Haier'],
    'Casarte': ['卡萨帝', 'Casarte'],
    'Colmo': ['COLMO', 'Colmo'],
    'Hisense&Ronshen': ['海信', 'Hisense', '容声', 'Ronshen'],
    'Midea': ['美的', 'Midea'],
    'BSH': ['西门子', 'Siemens', '博世', 'Bosch'],
    'Meiling': ['美菱', 'Meiling']
}
```

## 京东爬取流程

1. 访问京东冰箱搜索页
2. 点击"新品"筛选
3. 点击"更多"按钮
4. 取消"仅显示有货"选项
5. 遍历所有分页（最多 50 页）
6. 进入每个商品详情页
7. 提取品牌和"能效网规格型号"
8. 只保留以 BCD- 或 MR- 开头的型号

## 比对逻辑

1. 标准化京东型号和 Excel 型号（去除空格、转大写）
2. 将京东品牌映射到对应的 Excel Sheet
3. 对于不在 7 个目标品牌中的商品，自动忽略
4. 找出京东型号集合 - Excel 型号集合 = 缺失型号

## 运行说明

### 启动应用
```bash
streamlit run app.py --server.port 5000
```

### 使用流程
1. 上传包含 7 个 Sheet 的 Excel 文件
2. 系统验证文件格式
3. 点击"开始比对"按钮
4. 等待爬取完成（10-30 分钟）
5. 查看结果并下载 Excel 文件

## 已知限制

1. **运行时间长**：爬取所有商品需要 10-30 分钟
2. **反爬虫风险**：可能被京东反爬虫机制拦截
3. **网络依赖**：需要稳定的网络连接
4. **浏览器资源**：Playwright 占用一定系统资源

## 最近更改

### 2025-10-27
- 创建项目初始版本
- 实现所有核心功能
- 配置 Streamlit 工作流
- 完成项目文档

## 开发环境

- Python 3.11
- Streamlit (已安装)
- Playwright (已安装 + Chromium 浏览器)
- openpyxl (已安装)
- pandas (已安装)
- xlsxwriter (已安装)
- trafilatura (已安装，未使用)

## 用户偏好

- 语言：中文
- 使用场景：定期比对京东新品型号与现有型号库
- 输出格式：网页显示 + Excel 下载
