import streamlit as st
import pandas as pd


def apply_font(fig, base=20):
    fig.update_layout(font=dict(size=base))
    fig.update_xaxes(title_font=dict(size=base), tickfont=dict(size=base-2))
    fig.update_yaxes(title_font=dict(size=base), tickfont=dict(size=base-2))

    fig.update_traces(
        textfont_size=base-2,
        textposition="inside",
        insidetextanchor="middle",
        textangle=0         
    )
    fig.update_layout(
        uniformtext_minsize=base-2,   # minimum label size
        uniformtext_mode='show'   # do NOT hide or shrink
    )
    fig.update_layout(
    legend=dict(
        title=dict(font=dict(size=base)),
        font=dict(size=base-2)
    )
    )
    fig.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
    )
    return fig


def apply_filters(df):
    with st.sidebar:
        status = st.multiselect("Status", df.status.unique())
        assignee = st.multiselect("Assignee", df.assignee.unique())

    if status:
        df = df[df.status.isin(status)]
    if assignee:
        df = df[df.assignee.isin(assignee)]

    return df