# AI Data Analyst Agent

An AI-powered data analysis agent that allows users to upload a CSV dataset and ask business questions using natural language.

The application uses an LLM to dynamically generate SQL queries, validates them for safety, executes them against SQLite, automatically handles SQL errors, generates visualizations, and provides a concise explanation of the results.

---

## 🚀 Project Overview

Traditional data analysis often requires users to know SQL or depend on an analyst to answer simple business questions.

This project provides a natural-language interface for data analysis.

A user can upload a CSV file and ask questions such as:

> What is the total net revenue?

> Show the top 5 products by net revenue.

> What is the average quantity sold for each product?

The agent understands the question, checks the available dataset schema, generates SQL, validates the query, executes it, and presents the result as a table, visualization, and short explanation.

---

## ✨ Features

- Upload CSV datasets
- Automatically inspect the uploaded dataset schema
- Ask questions using natural language
- Generate SQL dynamically using an LLM
- Validate generated SQL before execution
- Allow only read-only `SELECT` queries
- Automatically fix SQL queries when execution fails
- Retry failed SQL queries up to 2 times
- Display query results in a table
- Automatically generate suitable visualizations
- Provide a concise AI-generated explanation
- View the generated SQL query
- Interactive Streamlit interface

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │       User          │
                    │ Upload CSV + Query  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Streamlit UI     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     LangGraph       │
                    │   Agent Workflow    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Request Validation  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Schema Validation  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    SQL Generation   │
                    │      using LLM      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    SQL Validation   │
                    │  Read-only checks   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   SQLite Execution  │
                    └──────────┬──────────┘
                               │
                         ┌─────┴─────┐
                         │           │
                       Error       Success
                         │           │
                         ▼           ▼
                ┌──────────────┐  ┌──────────────┐
                │  Fix SQL     │  │   DataFrame  │
                │   using LLM  │  └──────┬───────┘
                └──────┬───────┘         │
                       │                 ▼
                       │        ┌─────────────────┐
                       └───────►│ Visualization  │
                                └────────┬────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │ AI Explanation  │
                                └─────────────────┘