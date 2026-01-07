import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Finance Tracker", page_icon="💰", layout="wide")

category_file = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": [],
    }
    
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)
        
def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        
        for idx, row in df.iterrows():
            details = row["Details"].lower().strip()
            # Use substring matching instead of exact match
            if any(keyword in details for keyword in lowered_keywords):
                df.at[idx, "Category"] = category
                
    return df  

def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns]
        
        # Handle amount formatting
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        
        # Parse dates
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
        
        # Filter only settled transactions if Status column exists
        if "Status" in df.columns:
            df = df[df["Status"] == "SETTLED"]
        
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    
    return False

def main():
    st.title("💰 Finance Dashboard")
    st.markdown("Upload your bank statement CSV to analyze spending patterns")
    
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])
    
    if uploaded_file is not None:
        df = load_transactions(uploaded_file)
        
        if df is not None and not df.empty:
            # Separate debits and credits
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()
            
            st.session_state.debits_df = debits_df.copy()
            
            # Overview metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Spending", f"{debits_df['Amount'].sum():,.2f} AED", delta=None)
            with col2:
                st.metric("Total Payments", f"{credits_df['Amount'].sum():,.2f} AED", delta=None)
            with col3:
                st.metric("Transactions", len(debits_df))
            
            st.divider()
            
            # Tabs for expenses and payments
            tab1, tab2, tab3 = st.tabs(["📊 Expenses", "💳 Payments", "⚙️ Settings"])
            
            with tab1:
                st.subheader("Expense Breakdown")
                
                # Category summary
                category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                category_totals = category_totals.sort_values("Amount", ascending=False)
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.dataframe(
                        category_totals, 
                        column_config={
                         "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED")   
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                
                with col2:
                    fig = px.pie(
                        category_totals,
                        values="Amount",
                        names="Category",
                        title="Expenses by Category",
                        hole=0.3
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
                
                # Spending over time
                st.subheader("Spending Over Time")
                spending_over_time = st.session_state.debits_df.groupby("Date")["Amount"].sum().reset_index()
                fig2 = px.line(
                    spending_over_time, 
                    x="Date", 
                    y="Amount", 
                    title="Daily Spending Trend",
                    markers=True
                )
                fig2.update_layout(yaxis_title="Amount (AED)", xaxis_title="Date")
                st.plotly_chart(fig2, use_container_width=True)
                
                st.divider()
                
                # Transaction details
                st.subheader("Transaction Details")
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )
                
                if st.button("💾 Save Category Changes", type="primary"):
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        
                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)
                    
                    st.success("Categories saved successfully!")
                        
            with tab2:
                st.subheader("Payment History")
                st.dataframe(
                    credits_df[["Date", "Details", "Amount"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED")
                    },
                    use_container_width=True,
                    hide_index=True
                )
            
            with tab3:
                st.subheader("Category Management")
                
                # Add new category
                new_category = st.text_input("Create New Category")
                if st.button("Add Category"):
                    if new_category and new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.success(f"Category '{new_category}' added!")
                        st.rerun()
                    elif new_category in st.session_state.categories:
                        st.warning("Category already exists!")
                
                st.divider()
                
                # Show existing categories and keywords
                st.subheader("Existing Categories")
                for category, keywords in st.session_state.categories.items():
                    with st.expander(f"📁 {category} ({len(keywords)} keywords)"):
                        if keywords:
                            st.write(", ".join(keywords))
                        else:
                            st.write("No keywords yet")
        
        elif df is not None and df.empty:
            st.warning("No settled transactions found in the file")
    
    else:
        st.info("👆 Upload a CSV file to get started")
        
        with st.expander("ℹ️ CSV Format Requirements"):
            st.markdown("""
            Your CSV file should have these columns:
            - **Date** (format: DD MMM YYYY, e.g., "28 Feb 2025")
            - **Details** (merchant name)
            - **Amount** (can include commas)
            - **Currency** (e.g., AED)
            - **Debit/Credit** (transaction type)
            - **Status** (SETTLED, REVERSED, etc.)
            """)

if __name__ == "__main__":
    main()
