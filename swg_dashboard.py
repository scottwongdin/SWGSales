import streamlit as st
import sqlite3
import pandas as pd
import os

# ── Config ──────────────────────────────────────────────────────────────────
DB_PATH = r"C:\Users\scott\OneDrive\Documents\SWGSales\swg.db"

st.set_page_config(
    page_title="SWG Vendor Dashboard",
    page_icon="🪙",
    layout="wide"
)

# ── Helpers ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def query(sql, params=None):
    conn = get_connection()
    return pd.read_sql_query(sql, conn, params=params)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🪙 SWG Vendor")
st.sidebar.markdown("---")
vendor_options = ["All Vendors", "Cafe Eponine", "Brasserie Eponine"]
selected_vendor = st.sidebar.selectbox("Filter by Vendor", vendor_options)

vendor_filter = "" if selected_vendor == "All Vendors" else f"WHERE vendor = '{selected_vendor}'"
vendor_filter_and = "" if selected_vendor == "All Vendors" else f"AND vendor = '{selected_vendor}'"

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_resource.clear()
    st.rerun()

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("🪙 SWG Vendor Dashboard")
st.markdown("---")

# ── KPI Metrics ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

total_revenue = query(f"SELECT COALESCE(SUM(price), 0) as total FROM sales {vendor_filter}")
total_sales   = query(f"SELECT COUNT(*) as total FROM sales {vendor_filter}")
unique_products = query(f"SELECT COUNT(DISTINCT product) as total FROM sales {vendor_filter}")
unique_customers = query(f"SELECT COUNT(DISTINCT customer) as total FROM sales {vendor_filter}")

col1.metric("💰 Total Revenue",    f"{total_revenue['total'][0]:,} credits")
col2.metric("🧾 Total Sales",       f"{total_sales['total'][0]:,}")
col3.metric("📦 Unique Products",   f"{unique_products['total'][0]:,}")
col4.metric("👥 Unique Customers",  f"{unique_customers['total'][0]:,}")

st.markdown("---")

# ── Sales Over Time ───────────────────────────────────────────────────────────
st.subheader("📈 Revenue Over Time")
sales_over_time = query(f"""
    SELECT sold_date, SUM(price) as revenue, COUNT(*) as num_sales
    FROM sales
    WHERE sold_date IS NOT NULL {vendor_filter_and}
    GROUP BY sold_date
    ORDER BY sold_date
""")

if not sales_over_time.empty:
    st.line_chart(sales_over_time.set_index("sold_date")["revenue"])
else:
    st.info("No sales data available.")

st.markdown("---")

# ── Top Products & Top Customers ──────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🏆 Top Products by Revenue")
    top_products = query(f"""
        SELECT product, SUM(price) as total_revenue, SUM(crate_size) as units_sold
        FROM sales
        WHERE product IS NOT NULL {vendor_filter_and}
        GROUP BY product
        ORDER BY total_revenue DESC
        LIMIT 10
    """)
    if not top_products.empty:
        top_products["total_revenue"] = top_products["total_revenue"].apply(lambda x: f"{x:,}")
        top_products.columns = ["Product", "Revenue (credits)", "Units Sold"]
        st.dataframe(top_products, width="stretch", hide_index=True)
    else:
        st.info("No product data available.")

with col_right:
    st.subheader("👥 Top Customers by Spend")
    top_customers = query(f"""
        SELECT customer, SUM(price) as total_spent, COUNT(*) as num_purchases
        FROM sales
        WHERE customer IS NOT NULL {vendor_filter_and}
        GROUP BY customer
        ORDER BY total_spent DESC
        LIMIT 10
    """)
    if not top_customers.empty:
        top_customers["total_spent"] = top_customers["total_spent"].apply(lambda x: f"{x:,}")
        top_customers.columns = ["Customer", "Total Spent (credits)", "Purchases"]
        st.dataframe(top_customers, width="stretch", hide_index=True)
    else:
        st.info("No customer data available.")

st.markdown("---")

# ── Revenue by Vendor ─────────────────────────────────────────────────────────
st.subheader("🏪 Revenue by Vendor")
vendor_revenue = query("""
    SELECT vendor, SUM(price) as total_revenue, COUNT(*) as num_sales
    FROM sales
    WHERE vendor IS NOT NULL
    GROUP BY vendor
    ORDER BY total_revenue DESC
""")
if not vendor_revenue.empty:
    vendor_revenue["total_revenue"] = vendor_revenue["total_revenue"].apply(lambda x: f"{x:,}")
    vendor_revenue.columns = ["Vendor", "Total Revenue (credits)", "Sales Count"]
    st.dataframe(vendor_revenue, width="stretch", hide_index=True)
else:
    st.info("No vendor data available.")

st.markdown("---")

# ── Inventory Summary ─────────────────────────────────────────────────────────
st.subheader("📦 Inventory Summary")
inventory = query(f"""
    SELECT product, total_units,
        ROUND(CAST(total_units AS FLOAT) / 25, 1) as total_crates,
        restock,
        CASE WHEN restock = -1 THEN NULL
             ELSE ROUND(CAST(restock AS FLOAT) / 25, 1)
        END as maintain_crates,
        vendor,
        CASE WHEN restock = -1 THEN NULL
             ELSE CAST(total_units - restock AS INTEGER)
        END as replenish,
        CASE WHEN restock = -1 THEN NULL
             ELSE ROUND(CAST(total_units - restock AS FLOAT) / 25, 1)
        END as replenish_crates
    FROM inventory
    {"WHERE vendor = '" + selected_vendor + "'" if selected_vendor != "All Vendors" else ""}
    ORDER BY
        CASE WHEN total_units <= 0 THEN 0
             WHEN restock != -1 AND total_units < restock THEN 1
             ELSE 2
        END ASC,
        replenish ASC
""")

if not inventory.empty:
    # Highlight based on restock threshold and zero/negative stock
    def highlight_low(row):
        if row["Total Units"] <= 0:
            return ["background-color: #ffcccc; color: black"] * len(row)
        elif row["Maintain"] != -1 and row["Total Units"] < row["Maintain"]:
            return ["background-color: #fff3cc; color: black"] * len(row)
        return [""] * len(row)

    inventory.columns = ["Product", "Total Units", "Total Crates", "Maintain", "Maintain Crates", "Vendor", "Replenish", "Replenish Crates"]
    inventory["Replenish"] = inventory["Replenish"].apply(lambda x: int(x) if pd.notna(x) else None)
    skip_crates = ["supplement", "substitute", "sample"]

    def format_crates(row, col):
        product_lower = str(row["Product"]).lower()
        if any(x in product_lower for x in skip_crates):
            return ""
        val = row[col]
        if pd.isna(val):
            return ""
        return f"{val:.1f}".rstrip('0').rstrip('.')

    inventory["Total Crates"] = inventory.apply(lambda row: format_crates(row, "Total Crates"), axis=1)
    inventory["Maintain Crates"] = inventory.apply(lambda row: format_crates(row, "Maintain Crates"), axis=1)
    inventory["Replenish Crates"] = inventory.apply(lambda row: format_crates(row, "Replenish Crates"), axis=1)
    st.dataframe(
        inventory.style.apply(highlight_low, axis=1),
        width="stretch",
        hide_index=True
    )
    st.caption("🔴 Red = out of stock or negative  |  🟡 Yellow = below restock threshold")
else:
    st.info("No inventory data available.")

st.markdown("---")

# ── Recent Sales ──────────────────────────────────────────────────────────────
st.subheader("🕐 Recent Sales")
recent_sales = query(f"""
    SELECT sold_date, sold_time, product, crate_size, price, customer, vendor
    FROM sales
    WHERE sold_date IS NOT NULL {vendor_filter_and}
    ORDER BY sold_date DESC, sold_time DESC
    LIMIT 25
""")

if not recent_sales.empty:
    recent_sales["price"] = recent_sales["price"].apply(lambda x: f"{x:,}" if x else "")
    recent_sales.columns = ["Date", "Time", "Product", "Crate Size", "Price (credits)", "Customer", "Vendor"]
    st.dataframe(recent_sales, width="stretch", hide_index=True)
else:
    st.info("No recent sales data available.")

st.markdown("---")

# ── Product Drilldown ─────────────────────────────────────────────────────────
st.subheader("🔍 Product Drilldown")

products_list = query(f"""
    SELECT DISTINCT product FROM sales
    WHERE product IS NOT NULL {vendor_filter_and}
    ORDER BY product
""")

if not products_list.empty:
    col_product, col_range = st.columns([3, 1])
    with col_product:
        selected_product = st.selectbox("Select a Product", products_list["product"].tolist())
    with col_range:
        time_range = st.selectbox("Time Range", ["All Time", "Last Month", "Last Week"])

    # Build date filter based on time range selection
    if time_range == "Last Week":
        date_filter = "AND sold_date >= date('now', '-7 days')"
    elif time_range == "Last Month":
        date_filter = "AND sold_date >= date('now', '-1 month')"
    else:
        date_filter = ""

    if selected_product:
        col1, col2, col3 = st.columns(3)

        product_revenue = query(f"""
            SELECT COALESCE(SUM(price), 0) as total FROM sales
            WHERE product = ? {date_filter}
        """, params=(selected_product,))
        product_units = query(f"""
            SELECT COALESCE(SUM(crate_size), 0) as total FROM sales
            WHERE product = ? {date_filter}
        """, params=(selected_product,))
        product_sales = query(f"""
            SELECT COUNT(*) as total FROM sales
            WHERE product = ? {date_filter}
        """, params=(selected_product,))

        col1.metric("💰 Total Revenue",  f"{product_revenue['total'][0]:,} credits")
        col2.metric("🧾 Number of Sales", f"{product_sales['total'][0]:,}")
        col3.metric("📦 Units Sold",      f"{product_units['total'][0]:,}")

        # Revenue over time for this product
        st.markdown("**Revenue Over Time**")
        product_over_time = query(f"""
            SELECT sold_date, SUM(price) as revenue
            FROM sales
            WHERE product = ? AND sold_date IS NOT NULL {date_filter}
            GROUP BY sold_date
            ORDER BY sold_date
        """, params=(selected_product,))
        if not product_over_time.empty:
            st.line_chart(product_over_time.set_index("sold_date")["revenue"])

        col_left, col_right = st.columns(2)

        # Top customers for this product
        with col_left:
            st.markdown("**Top Customers**")
            product_customers = query(f"""
                SELECT customer, COUNT(*) as purchases, SUM(price) as total_spent
                FROM sales
                WHERE product = ? AND customer IS NOT NULL {date_filter}
                GROUP BY customer
                ORDER BY total_spent DESC
                LIMIT 10
            """, params=(selected_product,))
            if not product_customers.empty:
                product_customers["total_spent"] = product_customers["total_spent"].apply(lambda x: f"{x:,}")
                product_customers.columns = ["Customer", "Purchases", "Total Spent (credits)"]
                st.dataframe(product_customers, width="stretch", hide_index=True)

        # Sales by vendor for this product
        with col_right:
            st.markdown("**Sales by Vendor**")
            product_vendors = query(f"""
                SELECT vendor, COUNT(*) as sales, SUM(price) as revenue
                FROM sales
                WHERE product = ? AND vendor IS NOT NULL {date_filter}
                GROUP BY vendor
                ORDER BY revenue DESC
            """, params=(selected_product,))
            if not product_vendors.empty:
                product_vendors["revenue"] = product_vendors["revenue"].apply(lambda x: f"{x:,}")
                product_vendors.columns = ["Vendor", "Sales", "Revenue (credits)"]
                st.dataframe(product_vendors, width="stretch", hide_index=True)

        # Full sales history for this product
        st.markdown("**Full Sales History**")
        product_history = query(f"""
            SELECT sold_date, sold_time, crate_size, price, customer, vendor
            FROM sales
            WHERE product = ? {date_filter}
            ORDER BY sold_date DESC, sold_time DESC
        """, params=(selected_product,))
        if not product_history.empty:
            product_history["price"] = product_history["price"].apply(lambda x: f"{x:,}" if x else "")
            product_history.columns = ["Date", "Time", "Crate Size", "Price (credits)", "Customer", "Vendor"]
            st.dataframe(product_history, width="stretch", hide_index=True)
else:
    st.info("No product data available.")