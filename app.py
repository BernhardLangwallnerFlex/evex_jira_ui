import streamlit as st
import pandas as pd
import plotly.express as px
from jira_loader import fetch_jira_issues
from data_loading import save_data, load_data
from styles import CUSTOM_CSS
from datetime import datetime, timezone, timedelta, time
import pytz
from data_transformation import load_issues, upsert_jira_data, load_issues_Amparex
from plotting import apply_font
from st_aggrid import AgGrid, GridOptionsBuilder
import pygwalker as pg
from pygwalker.api.streamlit import StreamlitRenderer, init_streamlit_comm
import os
import hmac

# set to dark mode
st.set_page_config(layout="wide")
# Apply custom CSS styles
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def require_password() -> None:
    """
    Simple password gate for the Streamlit UI.

    - Set `UI_PASSWORD` (recommended via Render env var) to enable.
    - If `UI_PASSWORD` is not set, the UI will be accessible without a password.
    """
    configured_password = os.getenv("UI_PASSWORD")
    if not configured_password:
        return

    if st.session_state.get("_ui_authed", False):
        if st.sidebar.button("🔒 Logout"):
            st.session_state["_ui_authed"] = False
            st.rerun()
        return

    st.sidebar.markdown("### 🔐 Login")
    entered = st.sidebar.text_input("Passwort", type="password")
    if entered:
        if hmac.compare_digest(entered, configured_password):
            st.session_state["_ui_authed"] = True
            st.rerun()
        else:
            st.sidebar.error("Falsches Passwort.")

    st.stop()

# Sidebar
# add logo in sidebar
st.sidebar.image("data/evex_logo.png", width=200)
st.sidebar.header("\n\nJIRA Data Analysis")

# Require password before showing any data/controls (set UI_PASSWORD to enable).
require_password()

st.sidebar.subheader("Data Controls")
# add horizontal radio buttons to toggle between Ipro, Amparex and both
firma = st.sidebar.radio("Firma", ["Ipro", "Amparex", "Beide"], horizontal=True)

try:
    df_old = load_data()
    df = df_old.copy()
except:
    df = pd.DataFrame()
    df_old = pd.DataFrame()

# Optional global filters in sidebar
start_date = datetime.now(timezone.utc) - timedelta(days=7)
end_date = datetime.now(timezone.utc)
start_date, end_date = st.sidebar.date_input("Zeitraum", value=(start_date, end_date))

tz = pytz.UTC

start_dt = tz.localize(datetime.combine(start_date, time.min))
end_dt   = tz.localize(datetime.combine(end_date,   time.max))

# toggle to switch between week_string and created_string
if st.sidebar.toggle("Auf Wochenbasis"):
    x_axis = 'week_string'
    x_axis_label = 'Kalenderwoche'
else:
    x_axis = 'created_string'
    x_axis_label = 'Datum'

st.sidebar.write("JIRA Daten aktualisieren.")

if st.sidebar.button("🔄 aktualisieren"):
    st.sidebar.success("Fetch triggered!")
    issues_ipro = fetch_jira_issues(start_dt, end_dt, max_issues=10000, project="SDIPR")
    issues_amparex = fetch_jira_issues(start_dt, end_dt, max_issues=10000, project="SDAX")
    if issues_ipro is None or issues_amparex is None:
        st.sidebar.warning("No JIRA data found — please refresh using sidebar.")
        st.stop()
    else:
        st.sidebar.success(f"JIRA data fetched successfully! {len(issues_ipro)+len(issues_amparex)} tickets fetched.")
    df_new_ipro = load_issues(issues_ipro)
    df_new_amparex = load_issues_Amparex(issues_amparex)
    # st.sidebar.success(f"Data transformed successfully! New {len(df_new_ipro)} tickets loaded for Ipro and {len(df_new_amparex)} tickets loaded for Amparex.")
    df_combined = pd.concat([df_new_ipro, df_new_amparex])
    df = upsert_jira_data(df_old, df_combined)
    save_data(df)
    st.sidebar.success(f"Data upserted successfully! Overall {len(df)} tickets loaded.")

if df is None:
    st.warning("No JIRA data found — please refresh using sidebar.")
    st.stop()
else:
    # Filter dataframe by date range
    df = df[(df['created'] >= start_dt) & (df['created'] <= end_dt)]
    st.sidebar.success(f"Data filtered successfully! {len(df)} tickets loaded.")



if firma == "Ipro":
    df = df[df['firma'] == "IPRO"]
elif firma == "Amparex":
    df = df[df['firma'] == "Amparex"]
else:
    pass
df_raw = df.copy()

plot_height = 900
plot_width = 1500
# Tabs
tab_overview, tab_categories, tab_subcategories, tab_sources, tab_status, tab_cycle_time, tab_resolution_time, tab_customer_tickets, tab_raw, tab_interactive = st.tabs([
    "📊 Überblick",
    "📊 Kategorien",
    "📊 Unterkategorien",
    "📊 Quellen",
    "📊 Offene Tickets nach Status",
    "⏱️ Ticketbearbeitungszeit",
    "📈 Erstlösequote",
    "📚 Tickets pro Kunde",
    "📄 Rohdaten",
    "📄 Interaktiv"
])


# -------------------------------
# Tab 1 – Overview
# -------------------------------
with tab_overview:
    st.header("📊 Überblick")

    result = df[[x_axis,'status','key']].groupby([x_axis,'status']).count().reset_index()
    print(result['key'].mean())
    # result['status_key'] = result['status'] + ' (' + result['key'].astype(str) + ')'
    result['status_key'] = result['key'].astype(str) 
    # plot using plotly, show status and key values inside of bars
    fig = px.bar(result, x=x_axis, y='key', text='status_key', color='status')
    # add x label
    fig.update_xaxes(title_text=x_axis_label)
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
# Tab 3 – Categories Breakdown
# -------------------------------
with tab_subcategories:
    st.header("📊 Aufteilung Unterkategorien")
    result = df[['Hauptkategorie','Unterkategorie','key']].groupby(['Hauptkategorie','Unterkategorie']).count().reset_index()
    result = result.rename(columns={'key': 'Anzahl'})
    # sort by overall count
    result = result.sort_values('Anzahl', ascending=False)

    fig = px.bar(result, x='Hauptkategorie', y='Anzahl', color='Unterkategorie')
    fig = apply_font(fig)
    st.plotly_chart(fig, use_container_width=False, height=plot_height, width=plot_width)


# -------------------------------
# Tab 3 – Sources Breakdown
# -------------------------------
with tab_sources:
    st.header("📊 Aufteilung Quellen")
    # toggle to switch between week_string and created_string

    # Plot request_type in bar chart
    result = df[df['request_type']!=''][['request_type',x_axis,'key']].groupby(['request_type',x_axis]).count().reset_index()
    fig = px.bar(result, x=x_axis, y='key', text='key', color='request_type')
    # set width of plot
    # add share as labels inside of bars, as percentage
    fig.update_traces(
        textposition='inside',
        insidetextanchor='middle'
    )
    # add y axis label  
    fig.update_yaxes(title_text='Anzahl Tickets')
    fig.update_xaxes(title_text=x_axis_label)
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
    result = df[df['status_category']=='Fertig'][[x_axis,'resolution','key']].groupby([x_axis,'resolution']).count().reset_index()
    result = result.rename(columns={'key': 'Anzahl'})
    fig = px.bar(result, x=x_axis, y='Anzahl', text='Anzahl', color='resolution')
    fig.update_xaxes(title_text=x_axis_label)
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


# -------------------------------
# Tab 9 – Interactive Data
# -------------------------------
with tab_interactive:
    st.header("📄 Interaktiv")
    problem_cols = [
    col for col in df.columns
    if df[col].apply(lambda x: isinstance(x, (list, dict, set))).any()
    ]
    df = df.drop(columns=problem_cols)
    # display dataframe with pygwalker
    renderer = StreamlitRenderer(df)
    renderer.explorer()

    st.write("\n\n\n\n\n\n")

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(filter=True, sortable=True)
    grid_options = gb.build()

    AgGrid(df, gridOptions=grid_options, height=plot_height, width=plot_width)

