"""
京东冰箱型号比对系统
主应用程序
"""
# ---- Windows asyncio loop policy fix: must run BEFORE importing streamlit/playwright ----
import sys, asyncio
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
# ----------------------------------------------------------------------------------------

import streamlit as st
import sys
import io
from pathlib import Path

# 添加 utils 目录到系统路径
sys.path.append(str(Path(__file__).parent))

from utils.excel_handler import ExcelHandler
from utils.brand_mapper import BrandMapper
from utils.model_comparator import ModelComparator
from utils.jd_scraper import JDScraper

# ================= 兼容旧版 Streamlit 的辅助函数 =================
def _st_version_tuple():
    v = getattr(st, "__version__", "0")
    try:
        parts = v.split(".")
        major = int(parts[0]); minor = int(parts[1])
    except Exception:
        major, minor = 0, 0
    return major, minor

def safe_button(label, **kwargs):
    """
    兼容旧版 st.button：
    - 自动丢弃旧版不支持的参数（如 type、use_container_width、disabled）
    - 保留低版本可用参数（key, help, on_click, args, kwargs）
    """
    major, minor = _st_version_tuple()

    # 旧版稳定支持
    allowed = {"key", "help", "on_click", "args", "kwargs"}
    # 新一些版本才支持 disabled，这里做条件放行
    if (major, minor) >= (1, 18):
        allowed |= {"disabled"}

    filtered = {k: v for k, v in kwargs.items() if k in allowed}
    try:
        return st.button(label, **filtered)
    except TypeError:
        # 仍不支持时兜底
        return st.button(label)

def show_table_with_optional_link(df, link_col_name="商品链接"):
    """
    兼容老版本：若无 st.column_config.LinkColumn，则用普通 dataframe 渲染
    """
    try:
        if hasattr(st, "column_config") and hasattr(st.column_config, "LinkColumn"):
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={link_col_name: st.column_config.LinkColumn(link_col_name)}
            )
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True)
# ===============================================================


def init_session_state():
    """初始化 session state"""
    if 'excel_uploaded' not in st.session_state:
        st.session_state.excel_uploaded = False
    if 'excel_handler' not in st.session_state:
        st.session_state.excel_handler = None
    if 'scraping_in_progress' not in st.session_state:
        st.session_state.scraping_in_progress = False
    if 'scraping_results' not in st.session_state:
        st.session_state.scraping_results = None
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None
    if 'progress_logs' not in st.session_state:
        st.session_state.progress_logs = []


def add_progress_log(message: str):
    """添加进度日志"""
    st.session_state.progress_logs.append(message)


def main():
    """主函数"""
    st.set_page_config(
        page_title="京东冰箱型号比对系统",
        page_icon="🧊",
        layout="wide"
    )
    
    init_session_state()
    
    # 标题
    st.title("🧊 京东冰箱型号比对系统")
    st.markdown("---")
    
    # 说明
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 功能说明
        本系统自动从京东爬取冰箱新品型号，并与您上传的 Excel 表格进行比对，找出 Excel 中缺失的型号。
        
        ### 使用步骤
        1. **上传 Excel 文件**：包含 7 个品牌 Sheet（Haier, Casarte, Colmo, Hisense&Ronshen, Midea, BSH, Meiling）
        2. **点击"开始比对"按钮**：系统将自动爬取京东数据并进行比对
        3. **查看结果**：在页面下方查看缺失型号列表
        4. **下载结果**：将结果导出为 Excel 文件
        
        ### Excel 文件要求
        - 必须包含 7 个 Sheet（顺序不限）
        - 每个 Sheet 的第 9 行存储该品牌的所有型号
        - 型号在第 9 行横向排列（每个单元格一个型号）
        
        ### 品牌映射关系
        - Haier → 海尔
        - Casarte → 卡萨帝
        - Colmo → COLMO
        - Hisense&Ronshen → 海信、容声
        - Midea → 美的
        - BSH → 西门子、博世
        - Meiling → 美菱
        """)
    
    # 第一步：上传 Excel 文件
    st.header("📁 步骤 1: 上传 Excel 文件")
    
    uploaded_file = st.file_uploader(
        "请上传包含型号数据的 Excel 文件",
        type=['xlsx', 'xls'],
        help="文件必须包含 7 个品牌 Sheet，每个 Sheet 的第 9 行存储型号数据"
    )
    
    if uploaded_file is not None:
        # 读取文件内容
        file_content = uploaded_file.read()
        
        # 创建 Excel 处理器
        excel_handler = ExcelHandler()
        
        # 验证 Excel 文件
        is_valid, message = excel_handler.validate_excel(file_content)
        
        if is_valid:
            st.success(f"✅ {message}")
            
            # 读取型号数据
            models_by_brand = excel_handler.read_models_from_row_9()
            models_count = excel_handler.get_models_count()
            
            # 显示统计信息
            st.subheader("📊 Excel 文件统计")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Haier", models_count.get('Haier', 0))
                st.metric("Casarte", models_count.get('Casarte', 0))
            
            with col2:
                st.metric("Colmo", models_count.get('Colmo', 0))
                st.metric("Hisense&Ronshen", models_count.get('Hisense&Ronshen', 0))
            
            with col3:
                st.metric("Midea", models_count.get('Midea', 0))
                st.metric("BSH", models_count.get('BSH', 0))
            
            with col4:
                st.metric("Meiling", models_count.get('Meiling', 0))
                total = sum(models_count.values())
                st.metric("**总计**", total)
            
            # 保存到 session state
            st.session_state.excel_uploaded = True
            st.session_state.excel_handler = excel_handler
            
        else:
            st.error(f"❌ {message}")
            st.session_state.excel_uploaded = False
    
    st.markdown("---")
    
    # 第二步：开始爬取和比对
    st.header("🚀 步骤 2: 开始爬取和比对")
    
    if not st.session_state.excel_uploaded:
        st.warning("⚠️ 请先上传并验证 Excel 文件")
    else:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            start_button = safe_button(
                "🎯 开始比对",
                type="primary",
                disabled=st.session_state.scraping_in_progress,
                use_container_width=True
            )
        
        with col2:
            if st.session_state.scraping_in_progress:
                st.info("⏳ 正在爬取和比对中，请耐心等待...")
            else:
                st.info("💡 点击按钮开始爬取京东数据并进行比对（预计需要 10-30 分钟）")
        
        if start_button:
            # 开始爬取
            st.session_state.scraping_in_progress = True
            st.session_state.progress_logs = []
            
            # 创建进度显示区域
            progress_container = st.container()
            
            with progress_container:
                st.subheader("📝 实时进度")
                progress_text = st.empty()
                log_container = st.empty()
            
            # 定义进度更新函数（在 try 块外部，确保 except 块可以访问）
            def update_progress():
                if st.session_state.progress_logs:
                    latest_log = st.session_state.progress_logs[-1]
                    progress_text.text(f"最新状态: {latest_log}")
                    
                    # 显示所有日志
                    log_text = "\n".join(st.session_state.progress_logs[-20:])  # 只显示最近 20 条
                    log_container.code(log_text, language=None)
            
            try:
                # 创建爬虫
                scraper = JDScraper(progress_callback=add_progress_log)
                
                # 开始爬取
                add_progress_log("开始爬取京东冰箱新品数据...")
                update_progress()
                
                jd_products = scraper.scrape_all_products(max_pages=50)
                
                add_progress_log(f"爬取完成！共获取 {sum(len(v) for v in jd_products.values())} 个商品数据")
                update_progress()
                
                # 品牌映射
                add_progress_log("开始品牌映射...")
                update_progress()
                
                brand_mapper = BrandMapper()
                mapped_products = {}
                
                for jd_brand, products in jd_products.items():
                    sheet_name = brand_mapper.map_to_sheet(jd_brand)
                    
                    if sheet_name:
                        add_progress_log(f"映射: {jd_brand} → {sheet_name}")
                        
                        if sheet_name not in mapped_products:
                            mapped_products[sheet_name] = []
                        
                        # 过滤有效型号
                        for model, link in products:
                            if ModelComparator.is_valid_model(model):
                                mapped_products[sheet_name].append((model, link))
                    else:
                        add_progress_log(f"跳过非目标品牌: {jd_brand}")
                
                update_progress()
                
                # 型号比对
                add_progress_log("开始型号比对...")
                update_progress()
                
                excel_handler = st.session_state.excel_handler
                excel_models = {}
                
                for sheet_name in ExcelHandler.REQUIRED_SHEETS:
                    excel_models[sheet_name] = excel_handler.get_normalized_models(sheet_name)
                
                missing_models = ModelComparator.compare_models(mapped_products, excel_models)
                
                add_progress_log(f"比对完成！找到 {sum(len(v) for v in missing_models.values())} 个缺失型号")
                update_progress()
                
                # 保存结果
                st.session_state.scraping_results = mapped_products
                st.session_state.comparison_results = missing_models
                st.session_state.scraping_in_progress = False
                
                st.success("✅ 爬取和比对完成！")
                st.rerun()
                
            except Exception as e:
                st.session_state.scraping_in_progress = False
                st.error(f"❌ 爬取过程出错: {str(e)}")
                add_progress_log(f"错误: {str(e)}")
                update_progress()
    
    st.markdown("---")
    
    # 第三步：显示结果
    if st.session_state.comparison_results is not None:
        st.header("📊 步骤 3: 比对结果")
        
        missing_models = st.session_state.comparison_results
        total_missing = sum(len(v) for v in missing_models.values())
        
        if total_missing == 0:
            st.success("🎉 恭喜！Excel 中包含了所有京东新品型号，没有缺失项。")
        else:
            st.warning(f"⚠️ 发现 {total_missing} 个缺失型号")
            
            # 显示每个品牌的缺失型号
            for brand, models in sorted(missing_models.items()):
                if models:
                    with st.expander(f"🔍 {brand} - {len(models)} 个缺失型号", expanded=True):
                        # 创建表格数据
                        table_data = []
                        for model, link in models:
                            table_data.append({
                                "型号": model,
                                "商品链接": link
                            })
                        
                        import pandas as pd
                        df = pd.DataFrame(table_data)
                        show_table_with_optional_link(df, link_col_name="商品链接")
            
            # 下载结果
            st.subheader("📥 下载结果")
            
            if safe_button("生成 Excel 下载文件", type="primary"):
                try:
                    from utils.excel_exporter import ExcelExporter
                    
                    exporter = ExcelExporter()
                    excel_buffer = exporter.export_results(missing_models)
                    
                    st.download_button(
                        label="⬇️ 下载缺失型号 Excel 文件",
                        data=excel_buffer,
                        file_name="京东冰箱缺失型号.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("✅ Excel 文件生成成功！点击上方按钮下载。")
                    
                except Exception as e:
                    st.error(f"❌ 生成 Excel 文件失败: {str(e)}")


if __name__ == "__main__":
    main()
