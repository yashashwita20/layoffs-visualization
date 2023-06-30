import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp

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


def time_layoff(data):
    
    year = data.groupby(['Year']).agg({'# Laid Off':'sum','Company':'count'}).reset_index()
    month = data.groupby(['Month']).agg({'# Laid Off':'sum','Company':'count'}).reset_index()
    quarter = data.groupby(['Quarter']).agg({'# Laid Off':'sum','Company':'count'}).reset_index()
    
    buttons = [
        dict(
            label="Month",
            method="update",
            args=[
                {"x": [month["Month"]], "y": [month["# Laid Off"]], "y1":[month['Company']]},
                {"xaxis.title.text": "Month", "yaxis.title.text": "# Laid Off"}
            ],
        ),
        dict(
            label="Year",
            method="update",
            args=[
                {"x": [year["Year"]], "y": [year["# Laid Off"]], "y1":[year['Company']]},
                {"xaxis.title.text": "Year", "yaxis.title.text": "# Laid Off"}
            ],
        ),
        dict(
            label="Quarter",
            method="update",
            args=[
                {"x": [quarter["Quarter"]], "y": [quarter["# Laid Off"]], "y1":[quarter['Company']]},
                {"xaxis.title.text": "Quarter", "yaxis.title.text": "# Laid Off"}
            ],
        ),
    ]
    
    fig = go.Figure()

    # Add line for # Laid Off
    fig.add_trace(go.Scatter(x=month['Month'], y=month['# Laid Off'], name='# Laid Off', mode='lines',line_color='red'))

    # Add line for Company
    fig.add_trace(go.Bar(x=month['Month'], y=month['Company'], name='# Companies',marker_color='rgba(0, 0, 255, 0.3)',yaxis='y2'))

    # Set plot layout
    fig.update_layout(
        title={
            'text': 'Layoffs over Time',
            'x': 0.5,  # Set the title's horizontal alignment to the center
            'font': {'size': 24, 'family': 'Monospace, bold'}
        },
        xaxis=dict(title=''),
        yaxis=dict(title='# Laid Off'),
        yaxis2=dict(title='# Companies', side='right', overlaying='y', showgrid=False),
        updatemenus=[dict(buttons=buttons)],
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    # Display the plot
    #fig.show()
    st.plotly_chart(fig)


def country_layoff(data,geo_json,title):
    
    geo_df = pd.DataFrame(geo_json['features'])
    geo_df['Country'] = geo_df['properties'].apply(lambda x: x['name'])

    country_laid_off = data.groupby('Country')['# Laid Off'].sum().reset_index()
    country_laid_off = geo_df.merge(country_laid_off,on='Country',how='left')
    country_laid_off['sqrt Laid Off'] = np.sqrt(country_laid_off['# Laid Off'])
    
    colorscale = ["#B4C0DC","#969BF4","#686FEF","#3A43EA"]
    
    fig = px.choropleth(country_laid_off,
                       geojson=country_laid_off.geometry,
                       locations=country_laid_off.id,
                       color="sqrt Laid Off",
                       projection="equirectangular",
                        color_continuous_scale=colorscale,
                    color_continuous_midpoint=0,
                    range_color=(0, 500),
                       #color_continuous_scale='Reds',
                       hover_data={'Country': True, '# Laid Off': True,'id':False,"sqrt Laid Off":False})
    
    fig.update_geos(#fitbounds="locations", 
                    visible=True,
                    showocean=True,oceancolor="LightGray",
                    showland=True, landcolor="White",
                    showcoastlines=True, coastlinecolor="White",countrycolor="White",framecolor="LightGray")

    # Set the layout
    fig.update_layout(hovermode='closest',
        title={
            'text': title,
            'x': 0.5,  # Set the title's horizontal alignment to the center
            'font': {'size': 24, 'family': 'Monospace, bold'}
        },coloraxis_showscale=False
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

st.markdown(" ")
st.markdown(" ")
m1,m2,m3,m4,m5,m6,m7 = st.columns(7)
m2.metric("Total Reports", data.shape[0])
m4.metric("Total Laid Off", str(int(data['# Laid Off'].sum()/1000))+"K+")
m6.metric("Total Companies", int(data['Company'].nunique()))

country_layoff(data,geo_json,"Across the World So Far")

st.markdown(
    """
    <div style='text-align: center;'>
        <h2>Exploring the Depths</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# +
filter1, filter2, filter3, filter4 = st.columns(4)

year_filter = filter1.selectbox("", ['Select Year']+list(data['Year'].unique()))
industry_filter = filter2.selectbox("", ['Select Industry']+sorted(list(data['Industry'].unique())))
country_filter = filter3.selectbox("", ['Select Country']+list(data['Country'].unique()))
company_filter = filter4.selectbox("", ['Select Company']+list(data['Company'].unique()))

# +
data['dum'] = True

mask = (data['dum'] == True)

# Update the mask based on the selected filters
if year_filter != 'Select Year':
    mask &= (data['Year'] == year_filter)
if industry_filter != 'Select Industry':
    mask &= (data['Industry'] == industry_filter)
if country_filter != 'Select Country':
    mask &= (data['Country'] == country_filter)
if company_filter != 'Select Company':
    mask &= (data['Company'] == company_filter)

# Filter the data DataFrame based on the selected filters
filtered_data = data[mask]


# -

def top_layoffs(data,n):
    top = data[['Day','Company','# Laid Off']].dropna().groupby(['Company']).sum().reset_index().sort_values(by=['# Laid Off'],ascending=False).dropna().head(n)
    
    fig = go.Figure(data=[go.Table(
        columnwidth = [1000,600],
        header=dict(values=[top['Company'].iloc[0], top['# Laid Off'].iloc[0]],
                    line_color='#F5F1F1',
                    fill_color='#D7DDEC',
                    align='left',
                   height=40,
                   font_size=16),
        cells=dict(values=[top['Company'].to_list()[1:], # 1st column
                           top['# Laid Off'].to_list()[1:]], # 2nd column
                   line_color='#F5F1F1',
                   fill_color='#D7DDEC',
                   align='left',
                  height=40,
                  font_size=16))
    ])
    
    fig.update_layout(hovermode='closest',
        title={
            'text': "Top Layoffs",
            'x': 0.5,  # Set the title's horizontal alignment to the center
            'font': {'size': 24, 'family': 'Monospace, bold'}
        },coloraxis_showscale=False,width=2400
    )
    
    st.plotly_chart(fig)


# +
t1,t2 = st.columns([4,10])

with t1:
    top_layoffs(filtered_data,7)
    
with t2:
    time_layoff(filtered_data)


# -

def industry_layoff(data):
    industry_group = data.groupby('Industry')['# Laid Off'].sum().reset_index()
    
    threshold = 15000

    # Filter out smaller categories
    large_categories = industry_group[industry_group['# Laid Off'] > threshold]
    small_categories = industry_group[industry_group['# Laid Off'] <= threshold]
    
    large_categories.loc[large_categories[large_categories['Industry'] == 'Other'].index, '# Laid Off'] += small_categories['# Laid Off'].sum()
    
    fig = px.pie(large_categories, values='# Laid Off', names='Industry',hole=0.6)
    
    fig.update_layout(
        title={
            'text': 'Layoffs by Industry',
            'x': 0.5,  # Set the title's horizontal alignment to the center
            'font': {'size': 24, 'family': 'Monospace, bold'}
        }
    )
    
    # Display the chart
    st.plotly_chart(fig)


def stage_layoff(data):
    stage_group = data.groupby('Stage')['# Laid Off'].sum().reset_index()
    
    threshold = 5000

    # Filter out smaller categories
    large_categories = stage_group[stage_group['# Laid Off'] > threshold]
    small_categories = stage_group[stage_group['# Laid Off'] <= threshold]
    
    large_categories.loc[len(large_categories.index)] = ['Other', small_categories['# Laid Off'].sum() ] 
    
    fig = px.pie(large_categories, values='# Laid Off', names='Stage',hole=.6)
    
    fig.update_layout(
        title={
            'text': 'Layoffs by Stage',
            'x': 0.5,  # Set the title's horizontal alignment to the center
            'font': {'size': 24, 'family': 'Monospace, bold'}
        }, legend_traceorder="reversed"
    )
    
    # Display the chart
    st.plotly_chart(fig)


# +
plot1, plot2 = st.columns(2)

with plot1:
    industry_layoff(filtered_data)
with plot2:
    stage_layoff(filtered_data)


# -

def location_layoff(data):
    
    data['City'] = data['Location HQ'].apply(lambda x:x[0]+" ("+x[1]+")" if len(x)>1 else x[0])
    location_group  = data.groupby('City')['# Laid Off'].sum().reset_index().sort_values('# Laid Off').tail(10)
    
    fig = px.bar(location_group, y="City", x="# Laid Off",orientation='h')
    
    fig.update_layout(
        title={
            'text': 'Layoffs in Top 10 Cities',
            'x': 0.5,  # Set the title's horizontal alignment to the center
            'font': {'size': 24, 'family': 'Monospace, bold'}
        },
        xaxis=dict(title=''),
        yaxis=dict(title='')
    )
    
    st.plotly_chart(fig)


# +
l1,l2 = st.columns(2)

with l1:
    country_layoff(filtered_data,geo_json,"Layoffs by Country")
with l2:
    location_layoff(filtered_data)
# -

st.markdown(
    """
    <div style='text-align: center; font-size:24px;'>
        LayOff Reports<br>
    </div>
    """,
    unsafe_allow_html=True
)

st.dataframe(filtered_data[['Day','Company','Location HQ','Industry','Country','Stage','# Laid Off','Source']])
