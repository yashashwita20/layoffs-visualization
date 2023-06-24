import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# !pip install pipreqsnb

# ! pipreqsnb . --force

# +
import json

# Read the world.geojson file
with open('world.geojson', 'r') as f:
    geo_json = json.load(f)
    
st.set_page_config(layout="wide")
# -

data = pd.read_json('Layoffs - Preprocessed.json')
data['Country'] = data['Country'].replace('United States', 'United States of America')
data['Month'] = data['Date'].dt.to_period('M').astype(str)
data['Year'] = data['Date'].dt.to_period('Y').astype(str)
data['Quarter'] = data['Date'].dt.to_period('Q').astype(str)
data['Day'] = data['Date'].dt.to_period('D').astype(str)


def time_layoff(data, time_form):
    
    time_layoff = data.groupby([time_form]).agg({'# Laid Off':'sum','Company':'count'}).reset_index()
    
    fig = go.Figure()

    # Add line for # Laid Off
    fig.add_trace(go.Scatter(x=time_layoff[time_form], y=time_layoff['# Laid Off'], name='# Laid Off', mode='lines',line_color='red'))

    # Add line for Company
    fig.add_trace(go.Bar(x=time_layoff[time_form], y=time_layoff['Company'], name='Company',marker_color='rgba(0, 0, 255, 0.3)',yaxis='y2'))

    # Set plot layout
    fig.update_layout(
        title='# Laid Off and # Company over '+time_form,
        xaxis=dict(title=time_form),
        yaxis=dict(title='# Laid Off'),
        yaxis2=dict(title='Company', side='right', overlaying='y', showgrid=False),
    )

    # Display the plot
    #fig.show()
    st.plotly_chart(fig)


def country_layoff(data,geo_json):
    country_laid_off = data.groupby('Country')['# Laid Off'].sum().reset_index()
    country_laid_off['sqrt Laid Off'] = np.sqrt(country_laid_off['# Laid Off']).fillna(0)
    
    
    token = open(".mapbox_token").read()

    px.set_mapbox_access_token(token)

    fig = px.choropleth_mapbox(
        country_laid_off,
        geojson=geo_json,#'world.geojson',
        locations='Country',
        color='sqrt Laid Off',
        mapbox_style="light",
        opacity=1,
        featureidkey="properties.name",  # Specify the key to match country names in GeoJSON
        color_continuous_scale='Reds',
        hover_data={'Country': True, '# Laid Off': True,'sqrt Laid Off':False}
    )
    
    fig.update_layout(coloraxis_showscale=False)

    # Set the layout
    fig.update_layout(hovermode='closest',
        title={
            'text': 'Across the World',
            'x': 0.5,  # Set the title's horizontal alignment to the center
            'font': {'size': 24, 'family': 'Monospace, bold'}
        },
        mapbox=dict(
            zoom=0,
            center=dict(lat=40, lon=10),
        ),
    )

    # Show the map
    #fig.show()
    st.plotly_chart(fig,config={'scrollZoom': False})

st.markdown(
    """
    <div style='text-align: center;'>
        <h1>Visualizing the Impact of Layoffs</h1>
        <p>Data Source: <a href="https://layoffs.fyi/">layoffs.fyi</a> Last Updated: June 21 2023</p>
    </div>
    """,
    unsafe_allow_html=True
)

# +
latest_layoff = data[['Day','Company','# Laid Off']].dropna().groupby(['Day','Company'])['# Laid Off'].sum().reset_index().sort_values(by=['Day','# Laid Off'],ascending=False).dropna().head(10)

box_style = "background-color: lightgray; padding: 1px; margin-bottom: 1px;"

st.sidebar.title(" ")
st.sidebar.title("Latest LayOffs")
with st.sidebar:

    # Iterate over the data and display in boxes
    for _, row in latest_layoff.iterrows():
        col1, col2 = st.columns(2)
        col1.write(row['Company'])
        col2.write(str(round(row['# Laid Off']))+' People')

# +
# st.write(
#     """
#     <div style='text-align: Center;'>
#         <h4>Across the World</h4>
#     </div>
#     """,
#     unsafe_allow_html=True
# )

country_layoff(data,geo_json)
# -

st.write(
    """
    <div style='text-align: Center;'>
        <p style='font-size: 24px; '>Over Time</p>
    </div>
    """,
    unsafe_allow_html=True
)
time_form = st.selectbox("Layoffs over ",['Month','Year','Quarter'])
time_layoff(data, time_form)
