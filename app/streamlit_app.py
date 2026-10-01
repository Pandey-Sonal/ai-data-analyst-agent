import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

from graph.graph import graph
from graph.nodes import SCHEMA
from database.upload_data import (
    load_csv_to_database,
    get_uploaded_schema
)


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown(
    """
<style>

/* Hide Streamlit settings menu */
span[data-testid="stMainMenu"] {
    visibility: hidden;
}

.stApp {
    background-color: #f7f9fc;
}

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}


/* ================================================
   HEADER
   ================================================ */

.app-title {
    font-size: 2.3rem;
    font-weight: 700;
    color: #0B1F3A;
    margin-bottom: 0.2rem;
}

.app-tagline {
    font-size: 1.25rem;
    font-weight: 600;
    font-style: italic;
    color: #0B1F3A;
    margin-bottom: 0.35rem;
}

.app-subtitle {
    color: #667085;
    font-size: 0.95rem;
    margin-bottom: 2rem;
}


/* ================================================
   SECTION TITLES
   ================================================ */

.section-title {
    font-size: 1.15rem;
    font-weight: 650;
    color: #1d2939;
    margin-top: 1.5rem;
    margin-bottom: 0.8rem;
}


/* ================================================
   ANSWER LABEL
   ================================================ */

.answer-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #667085;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
}


/* ================================================
   SIDEBAR
   ================================================ */

section[data-testid="stSidebar"] {
    background-color: white;
    border-right: 1px solid #e5e7eb;
}


/* ================================================
   BUTTON
   ================================================ */

.stButton > button {
    background-color: #0B1F3A;
    color: white;
    border: none;
    border-radius: 8px;
    min-height: 42px;
    font-weight: 600;
}

.stButton > button:hover {
    background-color: #162F52;
    color: white;
}

.stButton > button:focus {
    color: white;
}


/* ================================================
   TEXT AREA
   ================================================ */

div[data-testid="stTextArea"] textarea {
    border-radius: 10px;
}


/* ================================================
   METRIC
   ================================================ */

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e5e7eb;
    padding: 1rem;
    border-radius: 12px;
}


/* ================================================
   DATAFRAME
   ================================================ */

[data-testid="stDataFrame"] {
    border-radius: 10px;
}

</style>
""",
    unsafe_allow_html=True
)


# ==================================================
# HEADER
# ==================================================

st.markdown(
    """
<div class="app-title">
    AI Data Analyst
</div>

<div class="app-tagline">
    Ask. Analyze. Understand.
</div>

<div class="app-subtitle">
    An intelligent data analysis agent that converts
    natural-language questions into SQL and actionable insights.
</div>
""",
    unsafe_allow_html=True
)


# ==================================================
# DEFAULT DATABASE
# ==================================================

db_path = "database/olist.db"
schema = SCHEMA


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.markdown("## Dataset")

    uploaded_file = st.file_uploader(
        "Upload a CSV file",
        type=["csv"],
        help="Upload any CSV dataset."
    )

    if uploaded_file is not None:

        try:

            uploaded_db_path = load_csv_to_database(
                uploaded_file
            )

            db_path = str(
                Path(uploaded_db_path).resolve()
            )

            schema = get_uploaded_schema()

            st.success(
                f"{uploaded_file.name} loaded"
            )

            # ------------------------------------------
            # Dataset information
            # ------------------------------------------

            schema_lines = schema.splitlines()

            column_count = sum(
                1
                for line in schema_lines
                if line.strip().startswith("- ")
            )

            st.caption(
                f"{column_count} columns • Dataset ready"
            )

            # ------------------------------------------
            # Dataset columns
            # ------------------------------------------

            with st.expander("View columns"):

                st.code(
                    schema,
                    language="text"
                )

        except Exception as e:

            st.error(
                "Could not load the CSV."
            )

            with st.expander("Technical details"):

                st.write(
                    f"{type(e).__name__}: {str(e)}"
                )

    else:

        st.caption(
            "Upload a CSV to analyze your own data."
        )

    st.divider()

    # ----------------------------------------------
    # Example questions
    # ----------------------------------------------

    st.markdown("### Try asking")

    st.caption(
        "What is the total revenue?"
    )

    st.caption(
        "What is the average quantity sold?"
    )

    st.caption(
        "Show the top 5 products by revenue."
    )

    st.caption(
        "Show the relationship between quantity sold and profit."
    )


# ==================================================
# QUESTION AREA
# ==================================================

st.markdown(
    '<div class="section-title">Ask your data</div>',
    unsafe_allow_html=True
)

question = st.text_area(
    "",
    placeholder=(
        "Example: Show the top 5 products by net revenue."
    ),
    height=90,
    label_visibility="collapsed"
)


# ==================================================
# ANALYZE BUTTON
# ==================================================

analyze_clicked = st.button(
    "Analyze Data",
    type="primary"
)


# ==================================================
# RUN ANALYSIS
# ==================================================

if analyze_clicked:

    # ----------------------------------------------
    # Empty question
    # ----------------------------------------------

    if not question.strip():

        st.warning(
            "Please enter a question first."
        )

        st.stop()


    # ----------------------------------------------
    # Run LangGraph
    # ----------------------------------------------

    with st.spinner(
        "Analyzing your data..."
    ):

        initial_state = {
            "question": question,
            "schema": schema,
            "db_path": db_path,
            "retry_count": 0
        }

        try:

            result = graph.invoke(
                initial_state
            )

        except Exception as e:

            st.error(
                "Something went wrong while analyzing the data."
            )

            with st.expander("Technical details"):

                st.write(
                    f"{type(e).__name__}: {str(e)}"
                )

            st.stop()


    # ==================================================
    # SAFETY REJECTION
    # ==================================================

    if result.get("rejection_message"):

        st.warning(
            result["rejection_message"]
        )

        st.stop()


    # ==================================================
    # SCHEMA REJECTION
    # ==================================================

    if result.get("schema_valid") is False:

        st.warning(
            result.get(
                "schema_message",
                "The uploaded dataset does not contain "
                "the data required to answer this question."
            )
        )

        st.stop()


    # ==================================================
    # SUCCESS
    # ==================================================

    if result.get("explanation"):

        df = result["dataframe"]


        # ==============================================
        # AI ANSWER
        # ==============================================

        st.markdown(
            '<div class="answer-label">AI ANSWER</div>',
            unsafe_allow_html=True
        )

        st.write(
            result["explanation"]
        )


        # ==============================================
        # SINGLE VALUE RESULT
        # ==============================================

        if df.shape == (1, 1):

            value = df.iloc[0, 0]

            if isinstance(value, float):

                value = round(
                    value,
                    2
                )

            label = (
                df.columns[0]
                .replace("_", " ")
                .title()
            )

            col1, col2, col3 = st.columns(
                [1, 2, 1]
            )

            with col2:

                st.metric(
                    label=label,
                    value=value
                )


        # ==============================================
        # MULTI-ROW RESULT
        # ==============================================

        else:

            st.markdown(
                '<div class="section-title">Results</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"{len(df):,} rows returned"
            )


            # ==========================================
            # VISUALIZATION
            # ==========================================

            if result.get("visualization") is not None:

                st.markdown(
                    '<div class="section-title">Visualization</div>',
                    unsafe_allow_html=True
                )

                st.plotly_chart(
                    result["visualization"],
                    use_container_width=True
                )


        # ==============================================
        # SQL
        # ==============================================

        with st.expander("View generated SQL"):

            st.code(
                result["sql"],
                language="sql"
            )


    # ==================================================
    # UNEXPECTED RESULT
    # ==================================================

    else:

        st.warning(
            "The agent could not answer this question."
        )