import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from io import BytesIO


st.set_page_config(
    page_title="Library Management Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff6b6b;
    }
    .stAlert > div {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def get_book_summary(df):
    """Calculate comprehensive book statistics"""
    if df.empty:
        return {
            "Total Books": 0,
            "Available": 0,
            "Issued": 0,
            "Returned": 0,
            "Damaged": 0,
            "Lost": 0,
            "To Be Replaced": 0,
        }

    return {
        "Total Books": len(df),
        "Available": df[df['Status'] == 'Available'].shape[0] if 'Status' in df.columns else 0,
        "Issued": df[df['Status'] == 'Issued'].shape[0] if 'Status' in df.columns else 0,
        "Returned": df[df['Status'] == 'Returned'].shape[0] if 'Status' in df.columns else 0,
        "Damaged": df[df['Condition'] == 'Damaged'].shape[0] if 'Condition' in df.columns else 0,
        "Lost": df[df['Condition'] == 'Lost'].shape[0] if 'Condition' in df.columns else 0,
        "To Be Replaced": df[df['Condition'] == 'To Be Replaced'].shape[0] if 'Condition' in df.columns else 0,
    }


def get_flagged_books(df):
    """Identify books that need attention (damaged, lost, or to be replaced)"""
    if df.empty or 'Condition' not in df.columns:
        return pd.DataFrame()

    flagged_conditions = ['Damaged', 'Lost', 'To Be Replaced']
    return df[df['Condition'].isin(flagged_conditions)]


def get_overdue_books(df):
    """Detect overdue books (issued more than 30 days ago without return)"""
    if df.empty or 'Status' not in df.columns or 'Issue_Date' not in df.columns:
        return pd.DataFrame()

    today = pd.Timestamp.now()
    issued_books = df[df['Status'] == 'Issued'].copy()

    if issued_books.empty:
        return pd.DataFrame()

    if 'Return_Date' in df.columns:
        overdue = issued_books[
            (issued_books['Return_Date'].isna()) &
            ((today - issued_books['Issue_Date']).dt.days > 30)
        ]
    else:
        overdue = issued_books[
            (today - issued_books['Issue_Date']).dt.days > 30
        ]

    return overdue


def get_underrepresented_genres(df, threshold=5):
    """Find genres with fewer books than the threshold"""
    if df.empty or 'Category' not in df.columns:
        return pd.Series(dtype='int64')

    genre_counts = df['Category'].value_counts()
    return genre_counts[genre_counts < threshold]


def convert_df_to_excel(df):
    """Convert DataFrame to Excel format for download"""
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Library_Books')
        return output.getvalue()
    except Exception as e:
        st.error(f"Error converting to Excel: {str(e)}")
        return None

def main():
    st.title("📚 Library Management Dashboard")
    st.markdown("---")


    st.header("📁 Data Upload")
    uploaded_file = st.file_uploader(
        "Upload your library book dataset (.csv)",
        type="csv",
        help="Upload a CSV file containing your library book data"
    )

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)

            # Parse dates if available
            date_columns = ['Issue_Date', 'Return_Date']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            st.success(f"✅ Successfully loaded {len(df)} records")


            st.sidebar.header("🔍 Search & Filter")


            search_columns = [col for col in ['Title', 'Authors'] if col in df.columns]
            if search_columns:
                search_field = st.sidebar.selectbox("Search by", search_columns)
                search_query = st.sidebar.text_input("Enter search query:").lower()

                if search_query:
                    mask = df[search_field].astype(str).str.lower().str.contains(search_query, na=False)
                    filtered_df = df[mask]
                    st.sidebar.success(f"Found {len(filtered_df)} matches")
                else:
                    filtered_df = df
            else:
                filtered_df = df


            stats = get_book_summary(filtered_df)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📚 Total Books", stats['Total Books'])
                st.metric("✅ Available", stats['Available'])
            with col2:
                st.metric("📤 Issued", stats['Issued'])
                st.metric("📥 Returned", stats['Returned'])
            with col3:
                st.metric("🔧 Damaged", stats['Damaged'])
                st.metric("❌ Lost", stats['Lost'])
            with col4:
                st.metric("🔄 To Replace", stats['To Be Replaced'])


            flagged_books = get_flagged_books(filtered_df)
            if not flagged_books.empty:
                st.subheader("🚨 Flagged Books")
                st.dataframe(flagged_books, use_container_width=True)

            # Show overdue books
            overdue_books = get_overdue_books(filtered_df)
            if not overdue_books.empty:
                st.subheader("⏰ Overdue Books")
                st.dataframe(overdue_books, use_container_width=True)

            # Show underrepresented genres
            underrep_genres = get_underrepresented_genres(filtered_df)
            if not underrep_genres.empty:
                st.subheader("📉 Underrepresented Genres")
                st.write(underrep_genres)

            # Visualizations
            st.subheader("📊 Visualizations")

            if 'Status' in df.columns:
                fig1, ax1 = plt.subplots()
                df['Status'].value_counts().plot(kind='bar', ax=ax1)
                st.pyplot(fig1)

            if 'Category' in df.columns:
                fig2, ax2 = plt.subplots()
                df['Category'].value_counts().head(10).plot(kind='pie', autopct='%1.1f%%', ax=ax2)
                st.pyplot(fig2)

            # Excel export
            excel_data = convert_df_to_excel(filtered_df)
            if excel_data:
                st.download_button(
                    label="📊 Download as Excel",
                    data=excel_data,
                    file_name=f'library_books_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

    else:
        st.info("Please upload a CSV file to begin using the dashboard")

        # Show expected format
        st.subheader("Expected CSV Format")
        sample_data = pd.DataFrame({
            'Title': ['The Great Gatsby', 'To Kill a Mockingbird', '1984'],
            'Authors': ['F. Scott Fitzgerald', 'Harper Lee', 'George Orwell'],
            'Status': ['Available', 'Issued', 'Available'],
            'Condition': ['Good', 'Good', 'Damaged'],
            'Category': ['Fiction', 'Fiction', 'Dystopian'],
            'Issue_Date': ['2024-01-15', '2024-02-01', ''],
            'Return_Date': ['', '', ''],
            'Year': [2020, 2019, 2021]
        })
        st.dataframe(sample_data, use_container_width=True)

if __name__ == "__main__":
    main()