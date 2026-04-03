import pandas as pd
import sqlite3
import glob


DB_PATH = "articles.db"

def import_excel(file_path):
    conn = sqlite3.connect(DB_PATH)

    # 跳过前两行（它们不是表头）
    df = pd.read_excel(file_path, engine="openpyxl", skiprows=1)

    # 字段映射（与你的 Excel 完全匹配）
    mapping = {
        "序号": "seq",
        "文章分类": "category",
        "公众号名称": "account_name",
        "文章标题": "title",
        "文章超链接地址": "url",
        "文章发布时间": "publish_time",
        "文章文字全文内容": "content"
    }

    # 只保留需要的字段
    df = df.rename(columns=mapping)

    # 过滤掉缺少 URL 的行（避免脏数据）
    df = df[df["url"].notnull()]

    df["source_file"] = file_path

    # 自动跳过重复 url（SQLite）
    for _, row in df.iterrows():
        conn.execute("""
        INSERT OR IGNORE INTO articles
        (seq, category, account_name, title, url, publish_time, content, source_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("seq"),
            row.get("category"),
            row.get("account_name"),
            row.get("title"),
            row.get("url"),
            row.get("publish_time"),
            row.get("content"),
            row.get("source_file")
        ))

    conn.commit()
    conn.close()
    print(f"导入成功：{file_path}")



def import_folder(folder="./data"):
    files = glob.glob(f"{folder}/*.xlsx")
    print(f"在目录 {folder} 下发现 {len(files)} 个文件")

    for f in files:
        try:
            print(f"\n开始导入：{f}")
            import_excel(f)
            print(f"成功导入：{f}")
        except Exception as e:
            print(f"❌ 导入失败：{f}")
            print(f"错误信息：{e}")
            # 可选：将错误写入日志文件
            with open("import_errors.log", "a", encoding="utf-8") as log:
                log.write(f"文件：{f}\n错误：{e}\n\n")

if __name__ == "__main__":
    import_folder()
