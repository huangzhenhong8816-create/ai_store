import pandas as pd
from functools import lru_cache

@lru_cache(maxsize=128)
def load_stores():
    return pd.read_csv('data/stores.csv', encoding='gbk')

@lru_cache(maxsize=128)
def load_category_benchmark():
    return pd.read_csv('data/category_benchmark.csv', encoding='gbk')

@lru_cache(maxsize=128)
def load_product_pool():
    return pd.read_csv('data/product_pool.csv', encoding='gbk')

@lru_cache(maxsize=128)
def load_store_sales():
    df = pd.read_csv('data/store_sales.csv', encoding='gbk')
    # 处理inventory_days列，将其转换为数值类型，错误的格式设为NaN然后填充值
    df['inventory_days'] = pd.to_numeric(df['inventory_days'], errors='coerce')
    # 将NaN值替换为合理的默认值，或者删除这些行
    df = df.dropna(subset=['inventory_days'])
    return df

@lru_cache(maxsize=128)
def load_customer_profile():
    return pd.read_csv('data/customer_profile.csv', encoding='gbk')

# @lru_cache(maxsize=128)
# def load_headquarter_template():
#     return pd.read_csv('data/headquarter_template.csv', encoding='gbk')

def get_store_info(store_id):
    stores = load_stores()
    store_data = stores[stores['store_id'] == store_id]
    if store_data.empty:
        return {}
    return store_data.iloc[0].to_dict()

def get_store_sales_data(store_id):
    sales = load_store_sales()
    return sales[sales['store_id'] == store_id]

def get_customer_insights(store_id):
    customers = load_customer_profile()
    return customers[customers['store_id'] == store_id]