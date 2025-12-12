import streamlit as st
import pandas as pd
import plotly.express as px
from jira_loader import fetch_jira_issues
from data_loading import save_data, load_data
from styles import CUSTOM_CSS
from datetime import datetime, timezone, timedelta, time
import pytz
from data_transformation import load_issues
from plotting import apply_font
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(layout="wide")

# Apply custom CSS styles
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Sidebar
# add logo in sidebar
st.sidebar.image("data/evex_logo.png", width=200)
st.sidebar.header("\n\nJIRA Data Analysis")

st.sidebar.subheader("Data Controls")

# Optional global filters in sidebar
start_date = datetime.now(timezone.utc) - timedelta(days=7)
end_date = datetime.now(timezone.utc)
start_date, end_date = st.sidebar.date_input("Select date range", value=(start_date, end_date))

tz = pytz.UTC

start_dt = tz.localize(datetime.combine(start_date, time.min))
end_dt   = tz.localize(datetime.combine(end_date,   time.max))

st.sidebar.write("Use the button below to refresh JIRA data.")

if st.sidebar.button("🔄 Refresh JIRA Data"):
    st.sidebar.success("Fetch triggered!")
    issues = fetch_jira_issues(start_dt, end_dt, max_issues=10000)
    if issues is None:
        st.sidebar.warning("No JIRA data found — please refresh using sidebar.")
        st.stop()
    else:
        st.sidebar.success(f"JIRA data fetched successfully! {len(issues)} tickets fetched.")
    df = load_issues(issues)
    st.sidebar.success(f"Data transformed successfully! {len(df)} tickets loaded.")
    save_data(df)

df = load_data()
if df is None:
    st.warning("No JIRA data found — please refresh using sidebar.")
    st.stop()
else:
    # Filter dataframe by date range
    df = df[(df['created'] >= start_dt) & (df['created'] <= end_dt)]
    st.sidebar.success(f"Data loaded successfully! {len(df)} tickets loaded.")

df_raw = df.copy()


plot_height = 900
plot_width = 1500
# Tabs
tab_overview, tab_categories, tab_sources, tab_status, tab_cycle_time, tab_resolution_time, tab_customer_tickets, tab_raw = st.tabs([
    "📊 Overview",
    "📊 Aufteilung Kategorien",
    "📊 Aufteilung Quellen",
    "📊 Offene Tickets nach Status",
    "⏱️ Ticketbearbeitungszeit",
    "📈 Erstlösequote",
    "📚 Anzahl Tickets pro Kunde",
    "📄 Rohdaten"
])


# -------------------------------
# Tab 1 – Overview
# -------------------------------
with tab_overview:
    st.header("📊 Overview")
    result = df[['created_string','status','key']].groupby(['created_string','status']).count().reset_index()
    print(result['key'].mean())
    # result['status_key'] = result['status'] + ' (' + result['key'].astype(str) + ')'
    result['status_key'] = result['key'].astype(str) 
    # plot using plotly, show status and key values inside of bars
    fig = px.bar(result, x='created_string', y='key', text='status_key', color='status')
    # add x label
    fig.update_xaxes(title_text='Datum')
    # add y label
    fig.update_yaxes(title_text='Anzahl Tickets')
    fig = apply_font(fig)
    st.plotly_chart(fig, use_container_width=False, height=plot_height, width=plot_width)

# -------------------------------
# Tab 2 – Categories Breakdown
# -------------------------------
with tab_categories:
    st.header("📊 Aufteilung Kategorien")
    result = df[['Hauptkategorie','resolution','key']].groupby(['Hauptkategorie','resolution']).count().reset_index()
    result = result.rename(columns={'key': 'Anzahl'})
    # sort by overall count
    result = result.sort_values('Anzahl', ascending=False)

    fig = px.bar(result, x='Hauptkategorie', y='Anzahl', color='resolution')
    fig = apply_font(fig)
    st.plotly_chart(fig, use_container_width=False, height=plot_height, width=plot_width)


# -------------------------------
# Tab 3 – Sources Breakdown
# -------------------------------
with tab_sources:
    st.header("📊 Aufteilung Quellen")
    # Plot request_type in bar chart
    result = df[df['request_type']!=''][['request_type','created_string','key']].groupby(['request_type','created_string']).count().reset_index()
    fig = px.bar(result, x='created_string', y='key', text='key', color='request_type')
    # set width of plot
    # add share as labels inside of bars, as percentage
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle'
    )
    # add y axis label  
    fig.update_yaxes(title_text='Anzahl Tickets')
    fig = apply_font(fig)
    st.plotly_chart(fig, use_container_width=False, height=plot_height, width=plot_width)

# -------------------------------
# Tab 4 – Status Breakdown
# -------------------------------
with tab_status:
    st.header("📊 Offene Tickets nach Status")
    result = df[df['status_category']!='Fertig'][['status_category','status','key']].groupby(['status_category','status']).count().reset_index().sort_values('key', ascending=False)
    result['status_key'] = result['status'] + ' (' + result['key'].astype(str) + ')'
    # plot using plotly with status_category on x axis and status on y axis, show status and key values inside of bars
    fig = px.bar(result, x='status_category', y='key', color='status', text='status_key')
    # add labels inside of bars
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle'
    )
    # add y axis label
    fig.update_yaxes(title_text='Anzahl Tickets')
    fig.update_xaxes(title_text='Statuskategorie')
    #remove legend
    fig.update_layout(showlegend=False)
    # set fontsize of plot to 24
    fig = apply_font(fig)

    st.plotly_chart(fig, use_container_width=False, height=plot_height, width=plot_width)
    

# -------------------------------
# Tab 5 – Backlog Health
# -------------------------------
with tab_cycle_time:
    st.header("⏱️ Ticketbearbeitungszeit (Fertige Tickets)")



    # plot time to resolution bin counts using plotly
# sort by midpoint of intervals/bins
    result = df[df['currentstatus_name'] == 'Fertig'][['time_to_resolution_bin','key']].groupby('time_to_resolution_bin').count().reset_index()
    fig = px.bar(result,x='time_to_resolution_bin', y='key')
    # add x axis label

    fig.update_layout(
        title='Anzahl Fertige Tickets nach Bearbeitungszeit',
    )
    fig.update_xaxes(title_text='Bearbeitungszeit in Stunden')
    # add y axis label
    fig.update_yaxes(title_text='Anzahl Fertige Tickets')
    # set width of plot
    fig.update_layout(width=1000)
    fig = apply_font(fig)
    st.plotly_chart(fig, use_container_width=False, height=plot_height, width=plot_width)

# -------------------------------
# Tab 6 – Resolution Time
# -------------------------------
with tab_resolution_time:
    st.header("📈 Erstlösequote")
    result = df[df['status_category']=='Fertig'][['created_string','resolution','key']].groupby(['created_string','resolution']).count().reset_index()
    result = result.rename(columns={'key': 'Anzahl'})
    fig = px.bar(result, x='created_string', y='Anzahl', text='Anzahl', color='resolution')
    fig.update_xaxes(title_text='Erstellungsdatum')
    fig.update_yaxes(title_text='Anzahl Fertige Tickets')
    fig = apply_font(fig)
    st.plotly_chart(fig, use_container_width=False, height=plot_height, width=plot_width)


# -------------------------------
# Tab 7 – Customer Tickets
# -------------------------------
with tab_customer_tickets:
    st.header("📚 Anzahl Tickets pro Kunde")
    result = df[df['status_category']=='Fertig'][['zentrale','key']].groupby(['zentrale']).count().reset_index()
    result = result.rename(columns={'key': 'Anzahl'})
    result = result.sort_values('Anzahl', ascending=False)
    result = result.head(25)
    fig = px.bar(result, x='zentrale', y='Anzahl', text='Anzahl')
    fig = apply_font(fig)
    st.plotly_chart(fig, use_container_width=False, height=plot_height, width=plot_width)

# -------------------------------
# Tab 8 – Raw Data
# -------------------------------
with tab_raw:
    df = df[['Link', *[col for col in df.columns if col != 'Link']]]
    st.header("📄 Rohdaten")

    st.dataframe(df,
        column_config={
        "Link": st.column_config.LinkColumn(
            "JIRA Link",
            display_text="Open in JIRA"
        )
    },#
    hide_index=True,
    height=plot_height,
    )

#    st.header("📄 Raw Data")
#    gb = GridOptionsBuilder.from_dataframe(df)
#    gb.configure_default_column(filter=True, sortable=True)
#    grid_options = gb.build()#

#    AgGrid(df, gridOptions=grid_options, height=plot_height, width=plot_width)

