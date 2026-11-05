

# import pandas as pd
# import re
# from openai import OpenAI

# # ---------------------- DeepSeek 配置 ----------------------
# client = OpenAI(
#     api_key = "sk-62bdc20a05154fa08291a863f7c1766a",
#     base_url = "https://api.deepseek.com"
# )
# model_name = "deepseek-flash"

# def predict_category(title: str):
#     """根据商品标题，输出类目，只返回类目名称，不要多余文字"""
#     if not title or title.strip() == "":
#         return "未知类目"
#     sys_prompt = "你是电商类目分类助手，只输出最合适的一级类目，只输出类目本身，不要解释、不要标点、不要额外文字。候选类目：服饰、美妆、食品、家居、数码、母婴、运动、厨具、箱包"
#     user_prompt = f"商品标题：{title}"
#     try:
#         resp = client.chat.completions.create(
#             model=model_name,
#             messages=[
#                 {"role":"system","content":sys_prompt},
#                 {"role":"user","content":user_prompt}
#             ],
#             temperature=0.1
#         )
#         return resp.choices[0].message.content.strip()
#     except Exception as e:
#         print(f"类目调用失败：{e}")
#         return "类目待人工复核"
# # -------------------------------------------------------

# def is_valid_url(url):
#     if pd.isna(url) or str(url).strip() == "":
#         return True
#     pattern = r'^https?://'
#     if re.match(pattern, str(url).strip()):
#         return True
#     return False

# def main():
#     input_file = "goods.xlsx"
#     output_file = "output_goods.xlsx"

#     df_raw = pd.read_excel(input_file, sheet_name=0, dtype=str)
#     df_raw = df_raw.fillna("")
#     df = df_raw.copy()

#     # 清洗：去空格换行特殊字符
#     for col in df.columns:
#         df[col] = df[col].apply(lambda x: re.sub(r'[\n\r\t\s]+', ' ', str(x)).strip())

#     # 删除全空行
#     empty_mask = (df == "").all(axis=1)
#     df = df[~empty_mask].reset_index(drop=True)

#     # ====== 空类目自动调用DeepSeek补全 ======
#     def fill_cat(row):
#         cat = row["类目"].strip()
#         title = row["商品标题"].strip()
#         print(f"【调试】原始类目值: [{row['类目']}] , 清洗后cat=[{cat}] , 标题=[{title}]")
#         if cat == "":
#             print(f"🚀 触发大模型补全！")
#             return predict_category(title)
#         return cat
#     df["类目"] = df.apply(fill_cat, axis=1)
#     # =========================================

#     error_msg_list = []
#     for idx, row in df.iterrows():
#         err_list = []
#         sku = row["SKU"]
#         price_str = row["价格"]
#         stock_str = row["库存"]
#         img_link = row["图片链接"]

#         if sku == "":
#             err_list.append("SKU缺失")
#         try:
#             price = float(price_str)
#             if price <= 0:
#                 err_list.append("价格异常（<=0）")
#         except ValueError:
#             if price_str != "":
#                 err_list.append("价格不是有效数字")
#         try:
#             stock = int(stock_str)
#             if stock < 0:
#                 err_list.append("库存异常（负数）")
#         except ValueError:
#             if stock_str != "":
#                 err_list.append("库存不是有效数字")
#         if not is_valid_url(img_link):
#             err_list.append("图片链接格式异常")
#         error_msg_list.append("；".join(err_list))
#     df["error_msg"] = error_msg_list

#     dup_mask = df.duplicated(subset=["SKU"], keep="first")
#     df.loc[dup_mask, "error_msg"] = df.loc[dup_mask, "error_msg"].apply(lambda x: (x + "；" if x else "") + "SKU重复")

#     clean_df = df[df["error_msg"] == ""].drop(columns=["error_msg"]).reset_index(drop=True)
#     error_df = df[df["error_msg"] != ""].reset_index(drop=True)

#     total = len(df_raw)
#     after_clean_rows = len(df)
#     success_cnt = len(clean_df)
#     error_cnt = len(error_df)
#     summary_data = [
#         ["原始总行数", total],
#         ["去除空行后行数", after_clean_rows],
#         ["校验通过行数", success_cnt],
#         ["异常行数", error_cnt]
#     ]
#     summary_df = pd.DataFrame(summary_data, columns=["统计项", "数值"])

#     with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#         clean_df.to_excel(writer, sheet_name="clean_data", index=False)
#         error_df.to_excel(writer, sheet_name="error_data", index=False)
#         summary_df.to_excel(writer, sheet_name="summary", index=False)

#     print(f"✅ 处理完成！输出文件：{output_file}")
#     print(f"✅ 校验通过：{success_cnt} 条，异常：{error_cnt} 条")

# if __name__ == "__main__":
#     main()

import re
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ===================== 【配置区】全部词库在这里维护 =====================
API_KEY = "sk-62bdc20a05154fa08291a863f7c1766a"
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"

# 开关：测试演示时设置 False 关闭图片校验；正式使用改成 True
ENABLE_IMG_CHECK = False

# 允许类目枚举
ALLOW_CATEGORY = {"数码", "服饰", "美妆", "家居", "电器"}
# 营销词黑名单
MARKET_WORDS = {"爆款","特价","秒杀","热销","新款","网红","超值","福利"}
MARKET_PATTERN = "|".join(MARKET_WORDS)
# 违禁极限词库
FORBIDDEN_WORDS = {"最","第一","顶级","全网第一","国家级","最高级","首选","无敌","天花板","永久","100%有效"}
FORBIDDEN_PATTERN = "|".join(FORBIDDEN_WORDS)
# 图片探测配置
IMG_TIMEOUT = 5
IMG_RETRY_TIMES = 2
# ======================================================

img_session = requests.Session()
retry_strategy = Retry(total=IMG_RETRY_TIMES, backoff_factor=0.3)
img_session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
img_session.mount("http://", HTTPAdapter(max_retries=retry_strategy))

def check_img_url_available(url: str) -> str:
    if not ENABLE_IMG_CHECK:
        return ""
    url = url.strip()
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        return "链接不是http/https格式"
    try:
        resp = img_session.head(url, timeout=IMG_TIMEOUT, allow_redirects=True)
        if 200 <= resp.status_code < 300:
            return ""
        else:
            return f"状态码{resp.status_code}"
    except Exception:
        return "链接访问失败"

def clean_title(raw_title: str) -> str:
    if not isinstance(raw_title, str):
        return ""
    text = raw_title

    def remove_marketing_bracket(match):
        inner = match.group(1) or match.group(2) or match.group(3)
        if re.search(MARKET_PATTERN, inner):
            return ""
        return match.group(0)
    text = re.sub(r"【(.*?)】|\[(.*?)\]|《(.*?)》", remove_marketing_bracket, text)
    text = re.sub(r"[#@￥%&*！？，。；：]", "", text)
    words = text.split()
    filter_words = [w for w in words if w not in MARKET_WORDS]
    text = " ".join(filter_words)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def check_forbidden_word(text: str) -> str:
    hit = re.findall(FORBIDDEN_PATTERN, text)
    if hit:
        return ",".join(list(set(hit)))
    return ""

def llm_category_and_attr(title: str):
    prompt = """
任务：根据商品标题，输出类目+属性。
类目只能从【数码,服饰,美妆,家居,电器】里面选一个。
属性提取：颜色、尺寸、容量、版本，没有就写无。
输出严格格式：类目|颜色,尺寸,容量,版本
不要多余文字、不要解释。
示例1：
输入：无线蓝牙耳机
输出：数码|无,无,无,标准版
示例2：
输入：300ml黑色便携榨汁杯
输出：电器|黑色,无,300ml,无
标题：{title}
""".format(title=title)
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type":"application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role":"user","content":prompt}],
        "temperature":0.1
    }
    try:
        resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=20)
        if resp.status_code == 200:
            res = resp.json()["choices"][0]["message"]["content"].strip()
            parts = res.split("|")
            if len(parts) == 2:
                cat, attr = parts
                cat = cat.strip()
                if cat not in ALLOW_CATEGORY:
                    cat = ""
                return cat, attr.strip()
            else:
                return "", "抽取失败"
    except Exception as e:
        print(f"LLM调用异常：{e}")
    return "", "抽取失败"

def check_row(sku, title, category, price, stock, forbidden_hit, img_err):
    err_msg = []
    if not sku or pd.isna(sku):
        err_msg.append("SKU为空")
    if not title or pd.isna(title) or title.lower()=="nan":
        err_msg.append("商品标题为空")
    try:
        p = float(price)
        if p < 0:
            err_msg.append("价格负数")
    except Exception:
        err_msg.append("价格格式非法")
    try:
        s = int(stock)
        if s < 0:
            err_msg.append("库存负数")
    except Exception:
        err_msg.append("库存格式非法")
    if category and category not in ALLOW_CATEGORY:
        err_msg.append("类目不在标准枚举内")
    if forbidden_hit:
        err_msg.append(f"命中违禁词:{forbidden_hit}")
    if img_err:
        err_msg.append(f"图片链接异常:{img_err}")
    if len(err_msg) == 0:
        return True, ""
    return False, ";".join(err_msg)

# ===================== 主流程 =====================
df = pd.read_excel("goods.xlsx")
clean_rows = []
error_rows = []

for idx, row in df.iterrows():
    sku = str(row.get("SKU","")).strip()
    raw_title = str(row.get("商品标题","")).strip()
    category = str(row.get("类目","")).strip()
    price = row.get("价格","")
    stock = row.get("库存","")
    img_url = str(row.get("图片链接","")).strip()
    spec = str(row.get("规格","")).strip()

    clean_t = clean_title(raw_title)
    forbidden_hit = check_forbidden_word(clean_t)
    img_err = check_img_url_available(img_url)

    print(f"\n-----第{idx+1}行-----")
    print(f"原始标题：{raw_title}")
    print(f"清洗后：{clean_t}")
    if forbidden_hit:
        print(f"⚠️ 命中违禁词：{forbidden_hit}")
    if img_err:
        print(f"🖼️ 图片异常：{img_err}")

    if not category:
        print(f"🚀发起LLM调用")
        category, attr_str = llm_category_and_attr(clean_t)
    else:
        _, attr_str = llm_category_and_attr(clean_t)

    ok, msg = check_row(sku, clean_t, category, price, stock, forbidden_hit, img_err)

    new_row = {
        "SKU": sku,
        "原始标题": raw_title,
        "清洗后标题": clean_t,
        "类目": category,
        "价格": price,
        "库存": stock,
        "图片链接": img_url,
        "图片链接校验结果": img_err,
        "规格": spec,
        "提取属性": attr_str,
        "命中违禁词": forbidden_hit,
        "error_msg": msg
    }
    if ok:
        clean_rows.append(new_row)
    else:
        error_rows.append(new_row)

clean_df = pd.DataFrame(clean_rows)
error_df = pd.DataFrame(error_rows)
summary_df = pd.DataFrame([
    {"指标":"总条数","数值":len(df)},
    {"指标":"校验通过","数值":len(clean_df)},
    {"指标":"异常数据","数值":len(error_df)}
])

with pd.ExcelWriter("output_goods.xlsx", engine="openpyxl") as writer:
    clean_df.to_excel(writer, sheet_name="clean_data", index=False)
    error_df.to_excel(writer, sheet_name="error_data", index=False)
    summary_df.to_excel(writer, sheet_name="summary", index=False)

print(f"\n========== 全部处理完成 ==========")
print(f"✅ 合格数据：{len(clean_rows)} 条")
print(f"❌ 异常数据：{len(error_rows)} 条")