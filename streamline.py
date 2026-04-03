import streamlit as st
import requests
import sys
import os
import time
import subprocess
from pathlib import Path

REFRESH_SCRIPT = Path("./import_excel.py")   # ← 改成你的脚本，比如 import_excel.py
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def run_refresh_script():
    """运行刷新脚本，并返回 (return_code, log_path, output_text)"""
    if not REFRESH_SCRIPT.exists():
        return 999, None, f"脚本不存在：{REFRESH_SCRIPT.resolve()}"


    log_path = LOG_DIR / f"refresh_{int(time.time())}.log"
    # 推荐用当前环境的 python（避免 windows 上 python 指向不一致）
    cmd = [os.environ.get("PYTHON", "python"), str(REFRESH_SCRIPT)]
    preferred_encoding = "gbk" if sys.platform.startswith("win") else "utf-8"
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30分钟超时，按需改
            encoding=preferred_encoding,
            errors="replace",
        )
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        log_path.write_text(output, encoding="utf-8")
        return proc.returncode, str(log_path), output

    except subprocess.TimeoutExpired:
        msg = "刷新脚本运行超时（TimeoutExpired），请检查脚本是否卡住。"
        log_path.write_text(msg, encoding="utf-8")
        return 124, str(log_path), msg

    except Exception as e:
        msg = f"运行脚本异常：{e!r}"
        log_path.write_text(msg, encoding="utf-8")
        return 500, str(log_path), msg

if "refresh_running" not in st.session_state:
    st.session_state.refresh_running = False
if "refresh_last_status" not in st.session_state:
    st.session_state.refresh_last_status = None
if "refresh_last_log" not in st.session_state:
    st.session_state.refresh_last_log = None
if "refresh_last_output" not in st.session_state:
    st.session_state.refresh_last_output = ""



# with st.expander("🧾 刷新日志（最近一次）", expanded=False):
#     if st.session_state.refresh_last_log:
#         st.write(f"日志文件：{st.session_state.refresh_last_log}")
#     if st.session_state.refresh_last_output:
#         st.code(st.session_state.refresh_last_output, language="text")
#     else:
#         st.info("暂无日志")


API_BASE = "http://127.0.0.1:5000"

st.set_page_config(page_title="公众号文章监测系统", layout="wide")

st.markdown("""
<style>
/* sidebar 整体缩进适当减小 */
section[data-testid="stSidebar"] > div:first-child {
    padding-left: 0rem !important;
    padding-right: 0 rem !important;
    padding-top: 0 rem !important;
}

/* 按钮之间的间距 */
section[data-testid="stSidebar"] button {
    margin-top: 0px !important;
    margin-bottom: -10px !important;
}

/* checkbox / radio 等 */
section[data-testid="stSidebar"] .stCheckbox,
section[data-testid="stSidebar"] .stRadio {
    margin-bottom: 0px !important;
}


/* 1) 压缩 sidebar 内每个组件容器的下边距（关键） */
section[data-testid="stSidebar"] .element-container {
    margin-bottom: -5px !important;   /* 默认一般更大，调sidebar的紧凑程度*/
}

/* 2) 压缩 popover/按钮自身高度（更紧凑） */
section[data-testid="stSidebar"] button {
    padding: 4px 4px !important;
    font-size: 10px ;
    line-height: 2 !important;
}

section[data-testid="stSidebar"] button * {
    font-size: 18px !important;
    line-height: 1.2 !important;
}


/* 3) 可选：让 sidebar 顶部也更紧一点 */
section[data-testid="stSidebar"] {
    padding-top: 0rem;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* 只影响 sidebar 里的 subheader */
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    margin-top: 14px !important;   /* 和上面拉开距离 */
    margin-bottom: 6px !important;   //调《事故与安全》文章占比 与上方间距
}
</style>
""", unsafe_allow_html=True)

# ================================
# Sidebar：分类选择器 & 蒂升电梯过滤
# ================================
st.sidebar.title("📚 筛选条件")

TARGET_CATEGORIES = [
    "政策与法规", "政府行政令", "事故与安全", "召回", "惩罚",
    "曳引机", "制动器", "控制柜", "地方政策与补助", "模式创新与进展",
    "电梯企业项目", "合作与展会", "国际标准与人才", "技术与产品创新",
    "设计", "安装", "维保", "企业调研与地域发展", "广告", "其他"
]

selected_category = st.sidebar.selectbox(
    "选择文章分类（模糊包含匹配）",
    ["全部"] + TARGET_CATEGORIES
)

# 蒂升电梯筛选框
enable_tissen_filter = st.sidebar.checkbox("仅显示与 蒂升电梯 相关的文章（标题可匹配）")

keyword = st.sidebar.text_input("关键词搜索（标题/内容）")




# ================================
# 调用后端 API
# ================================
def load_articles(keyword=None):
    params = {}
    if keyword:
        params["q"] = keyword

    try:
        res = requests.get(f"{API_BASE}/api/articles", params=params, timeout=10)
        return res.json()
    except:
        st.error("无法连接后端 API")
        return []


articles_raw = load_articles(keyword)
articles_total= load_articles()


# ================================
# 分类过滤器（包含 substring 匹配）
# ================================
def filter_by_category(articles, category):
    if category == "全部":
        return articles
    return [a for a in articles if category in a.get("category", "")]


articles = filter_by_category(articles_raw, selected_category)

# ================================
# 蒂升电梯过滤器（多关键词匹配）
# ================================
TISSEN_KEYWORDS = [
    "蒂升", "蒂森", "蒂森克虏伯", "ThyssenKrupp",
    "TK Elevator", "曼隆蒂升", "蒂升电梯"
]


def is_tissen_related(article):
    text = (article.get("content", "") + " " +
            article.get("category", "") + " " +
            article.get("title", ""))
    return any(key in text for key in TISSEN_KEYWORDS)
def is_otis_related(article):
    text = (article.get("content", "") + " " +
            article.get("category", "") + " " +
            article.get("title", ""))
    return any(key in text for key in ["奥的斯","otis","OTIS"])
def is_Schindler_related(article):
    text = (article.get("content", "") + " " +
            article.get("category", "") + " " +
            article.get("title", ""))
    return any(key in text for key in ["迅达","Schindler"])
def is_kone_related(article):
    text = (article.get("content", "") + " " +
            article.get("category", "") + " " +
            article.get("title", ""))
    return any(key in text for key in ["通力","kone","KONE"])

def is_accident_category(article):
    # 你的分类是“事故与安全”，这里用包含匹配保持一致
    return "事故与安全" in (article.get("category", "") or "")

# ================================
# 左侧事故与安全 以及文章弹窗
# ================================
def render_accident_tissen(articles_base):
    """
    articles_base：用于统计的文章集合（建议用 articles_raw，不受“仅蒂升”勾选影响）
    """
    accident_articles = [a for a in articles_base if is_accident_category(a)]
    total = len(accident_articles)

    if total == 0:
        st.info("当前条件下没有『事故与安全』分类文章，无法生成占比图。")
        return

    tissen_count = sum(1 for a in accident_articles if is_tissen_related(a))
    other_count = total - tissen_count
    ratio = tissen_count / total * 100

    st.sidebar.subheader("📊 『事故与安全』中相关文章占比")

    # 指标卡更直观
    st.sidebar.metric("事故与安全相关文章总数", total)

    #c2.metric("其中：蒂升相关", tissen_count)

    tissen_articles=[a for a in accident_articles if is_tissen_related(a)]
    tissen_num=sum(1 for a in accident_articles if is_tissen_related(a))
    with st.sidebar.popover(f"蒂升相关文章数:  {tissen_num}", use_container_width=True):
        if not tissen_articles:
            st.info("没有找到相关文章。")
        else:
            for a in tissen_articles[:50]:  # 防止太长
                st.markdown(f"- [{a.get('title', '(无标题)')}]({a.get('url', '#')})")

    #c3.metric("其中：奥的斯相关", sum(1 for a in accident_articles if is_otis_related(a)))

    otis_articles=[a for a in accident_articles if is_otis_related(a)]
    otis_num=sum(1 for a in accident_articles if is_otis_related(a))
    with st.sidebar.popover(f"奥的斯相关文章数:  {otis_num}", use_container_width=True):
        if not otis_articles:
            st.info("没有找到相关文章。")
        else:
            for a in otis_articles[:50]:  # 防止太长
                st.markdown(f"- [{a.get('title', '(无标题)')}]({a.get('url', '#')})")

    #c4.metric("其中：迅达相关", sum(1 for a in accident_articles if is_Schindler_related(a)))

    Schindler_articles=[a for a in accident_articles if is_Schindler_related(a)]
    Schindler_num=sum(1 for a in accident_articles if is_Schindler_related(a))
    with st.sidebar.popover(f"迅达相关文章数:  {Schindler_num}", use_container_width=True):
        if not Schindler_articles:
            st.info("没有找到相关文章。")
        else:
            for a in Schindler_articles[:50]:  # 防止太长
                st.markdown(f"- [{a.get('title', '(无标题)')}]({a.get('url', '#')})")

    #c5.metric("其中：通力相关", sum(1 for a in accident_articles if is_kone_related(a)))

    kone_articles=[a for a in accident_articles if is_kone_related(a)]
    kone_num=sum(1 for a in accident_articles if is_kone_related(a))
    with st.sidebar.popover(f"通力相关文章数:  {kone_num}", use_container_width=True):
        if not kone_articles:
            st.info("没有找到相关文章。")
        else:
            for a in kone_articles[:50]:  # 防止太长
                st.markdown(f"- [{a.get('title', '(无标题)')}]({a.get('url', '#')})")

    st.sidebar.metric("蒂升事故文章占比", f"{ratio:.1f}%")

#刷新数据库,管理权限
    REFRESH_PASSWORD = "admin123"

    if "refresh_unlocked" not in st.session_state:
        st.session_state.refresh_unlocked = False
    with st.sidebar:
        st.subheader("🔐 管理权限")

        pwd = st.text_input(
            "输入密码解锁刷新数据库",
            type="password",
            key="refresh_pwd_simple"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("解锁", use_container_width=True):
                if pwd == REFRESH_PASSWORD:
                    st.session_state.refresh_unlocked = True
                    st.success("✅ 已解锁")
                else:
                    st.error("❌ 密码错误")

        with col2:
            if st.button("锁定", use_container_width=True):
                st.session_state.refresh_unlocked = False
                st.info("已锁定")

    with st.sidebar:
        # 固定在底部的按钮区域
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)

        disabled_refresh = (
                st.session_state.refresh_running
                or not st.session_state.refresh_unlocked
        )

        clicked=st.button("🔄 刷新数据库（运行脚本）",disabled=disabled_refresh, use_container_width=True)
        with st.popover(
            "查看脚本导入Log",
             use_container_width=True,
            disabled=st.session_state.refresh_running):
                if st.session_state.refresh_last_log:
                    st.write(f"日志文件：{st.session_state.refresh_last_log}")
                if st.session_state.refresh_last_output:
                    st.code(st.session_state.refresh_last_output, language="text")
                else:
                    st.info("暂无日志")



        st.markdown("</div>", unsafe_allow_html=True)

        # 可选：在 sidebar 底部上方显示上次刷新状态
        if st.session_state.refresh_last_status is not None:
            code = st.session_state.refresh_last_status
            if code == 0:
                st.success("✅ 上次刷新成功")
            else:
                st.error(f"❌ 上次刷新失败（code={code}）")

    # 点击触发刷新
    if clicked:
        st.session_state.refresh_running = True
        with st.sidebar.spinner("正在刷新数据库，请稍候..."):
            code, log_path, output = run_refresh_script()

        st.session_state.refresh_last_status = code
        st.session_state.refresh_last_log = log_path
        st.session_state.refresh_last_output = output
        st.session_state.refresh_running = False

        # 刷新完成后，建议清理/更新缓存，让页面数据变“最新”
        st.cache_data.clear()
        st.rerun()

    # # 饼图不画了
    # fig, ax = plt.subplots(figsize=(4.5, 4.5))
    # labels = [f"蒂升相关 ({tissen_count})", f"非蒂升 ({other_count})"]
    # sizes = [tissen_count, other_count]
    # colors = ["#FF6B6B", "#4D96FF"]
    #
    # ax.pie(
    #     sizes,
    #     labels=labels,
    #     autopct="%1.1f%%",
    #     startangle=90,)
render_accident_tissen(articles_total)

def filter_by_tissen(articles):
    result = []
    for a in articles:
        text = (a.get("content", "") + " " +
                a.get("category", "") + " " +
                a.get("title", ""))
       # print(a.keys())

        if any(key in text for key in TISSEN_KEYWORDS):
            result.append(a)
    return result


if enable_tissen_filter:
    articles = filter_by_tissen(articles)

# st.title("📘 公众号文章监测系统（Streamlit 前端）")
# # ================================
# # 展示文章
# # ================================
# st.write(f"🔎 共 {len(articles)} 篇文章符合筛选条件")
#
# for a in articles:
#     st.subheader(a["title"])
#     st.write(f"📂 分类：{a['category']} | 🕒 发布时间：{a['publish_time']}")
#     st.markdown(f"🔗 {a['url']}")
#
#     # if st.button("查看全文", key=f"detail_{a['id']}"):
#     #     detail = requests.get(f"{API_BASE}/api/article/{a['id']}").json()
#     #     st.markdown("### 📄 正文内容")
#     #     st.write(detail.get("content", ""))
#
#     with st.expander("查看全文"):
#         detail = requests.get(f"{API_BASE}/api/article/{a['id']}").json()
#         st.markdown("### 📄 正文内容")
#         st.write(detail.get("content", ""))
#
#     st.markdown("---")

import math

PAGE_SIZE = 50  # 每页显示多少条，可改 50/100/200

st.title("📘 公众号文章监测系统（Streamlit 前端）")

# ================================
# 分页状态初始化
# ================================
if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0  # 0-based

total = len(articles)
total_pages = max(1, math.ceil(total / PAGE_SIZE))

# 防止越界（比如筛选条件变化后总页数变少）
st.session_state.page_idx = min(max(st.session_state.page_idx, 0), total_pages - 1)

# ================================
# 分页控件
# ================================
st.write(f"🔎 共 {total} 篇文章符合筛选条件")



# 当前页数据切片
start = st.session_state.page_idx * PAGE_SIZE
end = min(start + PAGE_SIZE, total)
page_articles = articles[start:end]


# ================================
# 详情接口：缓存（避免重复请求）
# ================================
@st.cache_data(ttl=600, show_spinner=False)  # 10分钟缓存，可按需调整
def fetch_detail(article_id: int):
    resp = requests.get(f"{API_BASE}/api/article/{article_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


# ================================
# 展示当前页文章
# ================================
for a in page_articles:
    st.subheader(a.get("title", ""))

    st.write(f"📂 分类：{a.get('category', '')} | 🕒 发布时间：{a.get('publish_time', '')}")
    # 你的要求里提过“不要裸 URL”，主页面展示你如果希望也隐藏裸 URL，可以改成 st.link_button 或 markdown 超链接
    st.markdown(f"🔗 [{a.get('url', '')}]({a.get('url', '')})")

    # ✅ 懒加载：只有展开时才请求详情（关键提速点）
    exp_key = f"exp_{a.get('id')}"
    with st.expander("查看全文", expanded=False):
        # 只有展开时才拉
        if st.session_state.get(exp_key, False) is False:
            st.caption("展开后加载正文（已开启缓存）")

        # Streamlit 没有直接提供 expander 是否展开的状态，
        # 但 expander 内部代码只有在渲染时执行（每次 rerun 会执行），
        # 所以我们采用按钮触发来做到“真正按需加载”（更稳）
        if st.button("📄 加载正文", key=f"load_{a.get('id')}"):
            with st.spinner("正在加载正文..."):
                detail = fetch_detail(int(a["id"]))
            st.markdown("### 📄 正文内容")
            st.write(detail.get("content", ""))

    st.markdown("---")
c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

with c1:
    if st.button("⬅️ 上一页", disabled=st.session_state.page_idx <= 0, use_container_width=True):
        st.session_state.page_idx -= 1
        st.rerun()

with c2:
    if st.button("下一页 ➡️", disabled=st.session_state.page_idx >= total_pages - 1, use_container_width=True):
        st.session_state.page_idx += 1
        st.rerun()

with c3:
    # 跳转页码（1-based）
    goto = st.number_input(
        "跳转到页码（从1开始）",
        min_value=1,
        max_value=total_pages,
        value=st.session_state.page_idx + 1,
        step=1,
        key="goto_page",
    )
    target = int(goto) - 1
    if target != st.session_state.page_idx:
        st.session_state.page_idx = target
        st.rerun()

with c4:
    start = st.session_state.page_idx * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    st.markdown(f"**显示 {start + 1}-{end} / 共 {total} 条**（第 {st.session_state.page_idx + 1}/{total_pages} 页）")