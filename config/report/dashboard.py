import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import mysql.connector
import os

st.set_page_config(page_title="POS Reports", layout="wide", page_icon="📊")


def get_db_connection():
    connection = mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'pos_mysql'),   # use 'pos_mysql' as default
        user=os.environ.get('DB_USER', 'pos_user'),
        password=os.environ.get('DB_PASSWORD', 'pos_pass'),
        database=os.environ.get('DB_NAME', 'pos_db')
    )
    return connection

def load_query(query, params=()):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()

st.sidebar.title("📅 Filters")
today = datetime.today()
start_date = st.sidebar.date_input("From", today - timedelta(days=30))
end_date = st.sidebar.date_input("To", today)
category = st.sidebar.text_input("Category (optional)", "")

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

sale_query = """
   SELECT
        s.sale_pid,
        s.trans_id,              
        s.product_id,           
        s.user_id,
        s.quantity,
        th.trans_date AS sale_date,
        s.unit_cost_sale,
        s.unit_price_sale,
        s.subtotal,
        i.name,
        i.category,
        u.username
    FROM sales s
    JOIN inventory i 
        ON s.product_id = i.product_id
    JOIN users u 
        ON s.user_id = u.user_id
    JOIN transaction_header th 
        ON s.trans_id = th.trans_id
    WHERE DATE(th.trans_date) BETWEEN %s AND %s 
    AND (%s = '' OR i.category = %s)
"""
df_sales = load_query(sale_query, params=(start_str, end_str, category, category))
if df_sales.empty:
    st.warning("No sales data in selected period.")
    st.stop()

pur_query = """
    SELECT
        pi.purchase_item_id,
        pi.purchase_id,
        ph.supplier_name,
        ph.purchase_date AS purchase_date_header,
        pi.product_id,
        i.name,
        i.category,
        pi.quantity,
        pi.unit_cost,
        pi.subtotal,
        ph.purchase_date
    FROM purchase_items pi
    JOIN purchase_header ph
        ON pi.purchase_id = ph.purchase_id
    JOIN inventory i
        ON pi.product_id = i.product_id
    WHERE DATE(ph.purchase_date) BETWEEN %s AND %s 
     AND (%s = '' OR i.category = %s)
"""
df_pur = load_query(pur_query, params=(start_str, end_str, category, category))
if df_pur.empty:
    st.warning("No purchase data in selected period.")
    st.stop()

st.markdown("Key KPIs")
c1,c2,c3,c4 = st.columns(4)
total_revenue = df_sales['subtotal'].sum()
total_profit = (df_sales['subtotal'] - (df_sales['unit_cost_sale'] * df_sales['quantity'])).sum()
total_purchase = df_pur['subtotal'].sum()
total_items = df_sales['product_id'].nunique()

c1.metric("Total Revenue", f"{total_revenue:,.0f}K")
c2.metric("Total Profit", f"{total_profit:,.0f}K")
c3.metric("Total Purchase", f"{total_purchase:,.0f}K")
c4.metric("Total Items", f"{total_items:,.0f}")

st.markdown("Daily Sale")
df_sales['date'] = pd.to_datetime(df_sales['sale_date']).dt.date
daily_sales = df_sales.groupby('date')['subtotal'].sum().reset_index()

fig_daily = px.line(
    daily_sales, 
    x='date', 
    y='subtotal',
    title="Daily Sales Revenue",
    markers=True,
    labels={'subtotal': f'Revenue (K)', 'date': 'Date'}
)
fig_daily.update_traces(hovertemplate=f"Date: %{{x}}<br>Revenue:%{{y:,.2f}}K")
st.plotly_chart(fig_daily, use_container_width=True)

st.markdown("## 📊 Category & Product Analysis")

# Create two columns
col_left, col_right = st.columns(2)

# ----- LEFT COLUMN: Donut Chart (Sales by Category) -----
with col_left:
    category_sales = df_sales.groupby('category')['subtotal'].sum().reset_index()
    
    fig_donut = px.pie(
        category_sales,
        values='subtotal',
        names='category',
        title="Revenue by Category",
        hole=0.4,  # donut style
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_donut.update_traces(
        hovertemplate=f"Category: %{{label}}<br>Revenue: K%{{value:,.2f}}<br>Share: %{{percent}}"
    )
    st.plotly_chart(fig_donut, use_container_width=True)

# ----- RIGHT COLUMN: Top 10 Products (Bar Chart) -----
with col_right:
    # Use the correct product name column (adjust if 'product_name' or 'name')
    product_sales = df_sales.groupby('name')['quantity'].sum().reset_index()
    top_products = product_sales.sort_values('quantity', ascending=False).head(10)
    
    fig_products = px.bar(
        top_products,
        x='quantity',
        y='name',
        orientation='h',
        title="Top 10 Products by Quantity Sold",
        labels={'quantity': 'Quantity Sold', 'name': 'Product'},
        color='quantity',
        color_continuous_scale='Viridis'
    )
    fig_products.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Quantity Sold",
        yaxis_title=""
    )
    st.plotly_chart(fig_products, use_container_width=True)

st.markdown("## 📈 Weekly Sales & Profit")

# Compute profit per transaction row
df_sales['profit'] = df_sales['subtotal'] - (df_sales['unit_cost_sale'] * df_sales['quantity'])

# Convert sale_date to datetime (already done but ensure)
df_sales['sale_date'] = pd.to_datetime(df_sales['sale_date'])

# Create week-start date (Monday of each week)
df_sales['week_start'] = df_sales['sale_date'].dt.to_period('W-MON').dt.start_time

# Aggregate weekly revenue and profit
weekly_agg = df_sales.groupby('week_start')[['subtotal', 'profit']].sum().reset_index()

# Plot both metrics as lines
fig_weekly = px.line(
    weekly_agg,
    x='week_start',
    y=['subtotal', 'profit'],
    title="Weekly Revenue and Profit",
    markers=True,
    labels={'value': 'Amount (K)', 'week_start': 'Week Starting', 'variable': 'Metric'}
)
fig_weekly.update_traces(hovertemplate="Week: %{x}<br>Amount: %{y:,.2f}K")
st.plotly_chart(fig_weekly, use_container_width=True)

# Add after the donut & top products
df_sales['profit'] = df_sales['subtotal'] - (df_sales['unit_cost_sale'] * df_sales['quantity'])
cat_profit = df_sales.groupby('category').agg({
    'subtotal': 'sum',
    'profit': 'sum'
}).reset_index()
cat_profit['margin_pct'] = (cat_profit['profit'] / cat_profit['subtotal']) * 100

fig_margin = px.bar(
    cat_profit,
    x='category',
    y='margin_pct',
    title="Profit Margin % by Category",
    labels={'margin_pct': 'Margin (%)', 'category': ''},
    color='margin_pct',
    color_continuous_scale='RdYlGn',
    text_auto='.1f'
)
st.plotly_chart(fig_margin, key="margin_by_category", width='stretch')

user_sales = df_sales.groupby('username')['subtotal'].sum().reset_index()
fig_user = px.bar(
    user_sales.sort_values('subtotal', ascending=False),
    x='subtotal',
    y='username',
    orientation='h',
    title="Revenue by User",
    labels={'subtotal': 'Revenue', 'username': ''},
    color='subtotal'
)
st.plotly_chart(fig_user, key="sales_by_user", width='stretch')

df_sales['hour'] = pd.to_datetime(df_sales['sale_date']).dt.hour
hourly_sales = df_sales.groupby('hour')['subtotal'].sum().reset_index()
fig_hour = px.bar(
    hourly_sales,
    x='hour',
    y='subtotal',
    title="Revenue by Hour of Day",
    labels={'subtotal': 'Revenue', 'hour': 'Hour (0-23)'}
)
st.plotly_chart(fig_hour, key="hourly_sales", width='stretch')

df_sales['month'] = pd.to_datetime(df_sales['sale_date']).dt.to_period('M')
monthly = df_sales.groupby('month')['subtotal'].sum().reset_index()
monthly['month'] = monthly['month'].astype(str)  # for plotting
fig_month = px.line(monthly, x='month', y='subtotal', title="Monthly Revenue", markers=True)
st.plotly_chart(fig_month, key="monthly_revenue", width='stretch')

# ---------- BUBBLE CHART: Quantity vs. Profit per Product ----------
st.markdown("## 🫧 Product Performance: Quantity vs. Profit")

# Compute needed metrics per product
product_perf = df_sales.groupby('name').agg(
    total_quantity=('quantity', 'sum'),
    total_revenue=('subtotal', 'sum'),
    total_profit=('profit', 'sum')   # profit already computed earlier
).reset_index()

# Profit margin percentage
product_perf['margin_pct'] = (product_perf['total_profit'] / product_perf['total_revenue']) * 100

fig_bubble = px.scatter(
    product_perf,
    x='total_quantity',
    y='total_profit',
    size='total_revenue',
    color='margin_pct',
    hover_name='name',
    text='name',
    size_max=60,
    title="Quantity Sold vs. Total Profit (Bubble size = Revenue)",
    labels={
        'total_quantity': 'Quantity Sold',
        'total_profit': 'Total Profit (K)',
        'margin_pct': 'Margin (%)'
    },
    color_continuous_scale='RdYlGn',
    range_color=[0, 100]
)
fig_bubble.update_traces(
    textposition='top center',
    hovertemplate="<b>%{hovertext}</b><br>Quantity: %{x}<br>Profit: %{y:,.0f}K<br>Margin: %{marker.color:.1f}%<br>Revenue: %{marker.size:,.0f}K"
)
st.plotly_chart(fig_bubble, key="bubble_performance", width='stretch')

# ---------- TREEMAP: Revenue by Category & Product ----------
st.markdown("## 🌳 Revenue Treemap (Category → Product)")

# Prepare data: aggregate revenue per product within each category
treemap_data = df_sales.groupby(['category', 'name'])['subtotal'].sum().reset_index()

fig_treemap = px.treemap(
    treemap_data,
    path=['category', 'name'],       # hierarchy
    values='subtotal',
    title="Revenue Distribution by Category and Product",
    color='subtotal',
    color_continuous_scale='Blues',
    hover_data={'subtotal': ':,.0f'}
)
fig_treemap.update_traces(
    textinfo="label+value",
    hovertemplate="<b>%{label}</b><br>Revenue: %{value:,.0f}K<br>%{percentRoot:.1%} of total"
)
st.plotly_chart(fig_treemap, key="treemap_revenue", width='stretch')

# ---------- CURRENT MONTH: Sales vs. Purchase Cost (Grouped Bar) ----------
st.markdown("## 📆 Current Month: Daily Sales vs. Purchase Cost")

# Get current month range
today = datetime.today()
first_day_this_month = today.replace(day=1).strftime("%Y-%m-%d")
current_month_end = today.strftime("%Y-%m-%d")

# Sales query for current month (respect category filter)
sales_current_query = """
   SELECT
        DATE(th.trans_date) AS sale_date,
        SUM(s.subtotal) AS total_sales
    FROM sales s
    JOIN transaction_header th ON s.trans_id = th.trans_id
    JOIN inventory i ON s.product_id = i.product_id
    WHERE DATE(th.trans_date) BETWEEN %s AND %s
      AND (%s = '' OR i.category = %s)
    GROUP BY DATE(th.trans_date)
"""
df_sales_current = load_query(sales_current_query, 
                              params=(first_day_this_month, current_month_end, category, category))

# Purchase query for current month
purchase_current_query = """
   SELECT
        DATE(ph.purchase_date) AS purchase_date,
        SUM(pi.subtotal) AS total_purchase
    FROM purchase_items pi
    JOIN purchase_header ph ON pi.purchase_id = ph.purchase_id
    JOIN inventory i ON pi.product_id = i.product_id
    WHERE DATE(ph.purchase_date) BETWEEN %s AND %s
      AND (%s = '' OR i.category = %s)
    GROUP BY DATE(ph.purchase_date)
"""
df_purchase_current = load_query(purchase_current_query,
                                 params=(first_day_this_month, current_month_end, category, category))

# Merge on date (full outer join) - NO fillna(0) here yet
df_compare = pd.merge(df_sales_current, df_purchase_current,
                      left_on='sale_date', right_on='purchase_date',
                      how='outer')

# Create a proper date column from whichever side has a value
df_compare['date'] = df_compare['sale_date'].fillna(df_compare['purchase_date'])
df_compare['date'] = pd.to_datetime(df_compare['date'])

# Now fill missing numeric values with 0
df_compare['total_sales'] = df_compare['total_sales'].fillna(0)
df_compare['total_purchase'] = df_compare['total_purchase'].fillna(0)

# Sort by date
df_compare = df_compare.sort_values('date')

# Melt for grouped bar
df_melted = df_compare.melt(id_vars='date', 
                            value_vars=['total_sales', 'total_purchase'],
                            var_name='Type', 
                            value_name='Amount')

# Fancy grouped bar with custom colors
fig_month = px.bar(df_melted, x='date', y='Amount', color='Type',
                   barmode='group',
                   title=f"Current Month ({first_day_this_month} to {current_month_end})",
                   labels={'Amount': 'Amount (K)', 'date': 'Date'},
                   color_discrete_map={'total_sales': '#2E86AB', 'total_purchase': '#A23B72'})
fig_month.update_layout(
    xaxis_title="Date",
    yaxis_title="Amount",
    legend_title="",
    hovermode='x unified'
)
fig_month.update_traces(hovertemplate="%{y:,.0f}K")
st.plotly_chart(fig_month, key="current_month_compare", width='stretch')

