# +
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp
import json

from layoffs_data import (
    Target,
    load_target,
    load_page_url,
    discover_picked_url,
    fetch_json,
)

# +
# Read the world.geojson file
with open('world.geojson', 'r') as f:
    geo_json = json.load(f)
    
st.set_page_config(layout="wide")
# -

# ## Loading Data

PAGE_URL = load_page_url()


@st.cache_data(ttl=10 * 24 * 60 * 60, show_spinner=True)
def get_latest_json_cached(page_url: str, view_id: str, share_id: str):
    # Cache-friendly: only primitives as inputs
    target = Target(view_id=view_id, share_id=share_id)
    picked_url, all_urls, matching_urls = discover_picked_url(
        page_url=page_url,
        target=target,
        settle_ms=12_000,
    )
    data = fetch_json(picked_url)
    return picked_url, all_urls, matching_urls, data


target = load_target()

picked_url, all_urls, matching_urls, json_data = get_latest_json_cached(
    PAGE_URL, target.view_id, target.share_id
)

# +
# Only for Jupyter

# from layoffs_data import Target, discover_all_and_pick_readsharedviewdata_url_async, fetch_json 

# picked_url, all_urls, matching_urls = await discover_all_and_pick_readsharedviewdata_url_async( page_url=PAGE_URL, target=target, settle_ms=12_000, log=print ) 
# json_data = fetch_json(picked_url)
# -

# ### Data Preprocessing

# +
key_map = {}
            
for item in json_data['data']['table']['columns']:
    id_ = item['id']
    name_ = item['name']
    key_map[id_] = name_

# +
key_map_switch = { key_map[k]:k for k in key_map}

#Location HQ
for item in json_data['data']['table']['columns']:
    if item['id']==key_map_switch['Location HQ']:
        for i in item['typeOptions']['choices'].values():
            id_ = i['id']
            name_ = i['name']
            key_map[id_] = name_
    
#Industry
for item in json_data['data']['table']['columns']:
    if item['id']==key_map_switch['Industry']:
        for i in item['typeOptions']['choices'].values():
            id_ = i['id']
            name_ = i['name']
            key_map[id_] = name_

#Country
for item in json_data['data']['table']['columns']:
    if item['id']==key_map_switch['Country']:
        for i in item['typeOptions']['choices'].values():
            id_ = i['id']
            name_ = i['name']
            key_map[id_] = name_

#Stage
for item in json_data['data']['table']['columns']:
    if item['id']==key_map_switch['Stage']:
        for i in item['typeOptions']['choices'].values():
            id_ = i['id']
            name_ = i['name']
            key_map[id_] = name_

# -

row_data = []
for item in json_data['data']['table']['rows']:
    item['cellValuesByColumnId']['id'] = item['id']
    row_data.append(item['cellValuesByColumnId'])


# +
def replace_values(data, replacements):
    for item in data:
        for key, value in item.items():
            if key in [key_map_switch[i] for i in key_map_switch if i in ['Location HQ', 'Industry', 'Stage', 'Country']]:
                if isinstance(value, list):
                    item[key] = [replacements[item] for item in value]
                else:
                    item[key] = replacements[value]

replace_values(row_data, key_map)


# +
def replace_keys(data, replacements):
    for item in data:
        item_copy = item.copy()
        for key, value in item_copy.items():
            item[replacements.get(key, key)] = item.pop(key, None)

replace_keys(row_data, key_map)
# -

data = pd.DataFrame(row_data)
data['Date'] = pd.to_datetime(data['Date'])
data['Date Added'] = pd.to_datetime(data['Date Added'])

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
                {"x": [month["Month"]], "y2": [month["# Laid Off"]], "y1":[month['Company']]},
            ],
        ),
        dict(
            label="Year",
            method="update",
            args=[
                {"x": [year["Year"]], "y2": [year["# Laid Off"]], "y1":[year['Company']]},
            ],
        ),
        dict(
            label="Quarter",
            method="update",
            args=[
                {"x": [quarter["Quarter"]], "y2": [quarter["# Laid Off"]], "y1":[quarter['Company']]},
            ],
        ),
    ]
    
    fig = go.Figure()

    # Add line for Company
    fig.add_trace(go.Bar(x=month['Month'], y=month['Company'], name='Companies with Layoffs',marker_color='rgba(254,206,186,255)',yaxis='y1'))
    
    # Add line for # Laid Off
    fig.add_trace(go.Scatter(x=month['Month'], y=month['# Laid Off'], name='Employees Laid Off', mode='lines',line_color='#67000d',yaxis='y2'))

    # Set plot layout
    fig.update_layout(
#         title={
#             'text': 'Layoffs over Time',
#             'x': 0.5,  # Set the title's horizontal alignment to the center
#             'font': {'size': 24, 'family': 'Monospace, bold'}
#         },
        xaxis=dict(title=''),
        yaxis=dict(title='Companies with Layoffs'),
        yaxis2=dict(title='Employees Laid Off', side='right', overlaying='y', showgrid=False),
        updatemenus=[dict(buttons=buttons)],
        legend=dict(orientation='h',
            yanchor="bottom",
            y=1,
            xanchor="left",
            x=0.20
        )
    )

    # Display the plot
    #fig.show()
    st.plotly_chart(fig,use_container_width=True)


def country_layoff(data,geo_json,title):
    
    geo_df = pd.DataFrame(geo_json['features'])
    geo_df['Country'] = geo_df['properties'].apply(lambda x: x['name'])

    country_laid_off = data.groupby('Country').agg({'# Laid Off':'sum',
                                                   'Company':'nunique'}).reset_index()
    shutdown = data[data['%']==1].groupby('Country')['Company'].nunique().reset_index()
    
    country_laid_off = country_laid_off.merge(shutdown,on='Country',how='left').fillna(0)
    
    country_laid_off.columns = ['Country','# Laid Off','Total Companies','# Companies Shutdown']
    
    country_laid_off = geo_df.merge(country_laid_off,on='Country',how='left')
    country_laid_off['sqrt Laid Off'] = np.sqrt(country_laid_off['# Laid Off'])
    
    colorscale = ["#B4C0DC","#969BF4","#686FEF","#3A43EA"]
    
    fig = px.choropleth(country_laid_off,
                       geojson=country_laid_off.geometry,
                       locations=country_laid_off.id,
                       color="sqrt Laid Off",
                       projection="equirectangular",
                        #color_continuous_scale=colorscale,
                    #color_continuous_midpoint=0,
                    #range_color=(0, 500),
                       color_continuous_scale='Reds',
                       hover_data={'Country': True, '# Laid Off': True,'id':False,"sqrt Laid Off":False,'# Companies Shutdown':True,'Total Companies':True})
    
    fig.update_geos(#fitbounds="locations", 
                    visible=True,
                    showocean=True,oceancolor="LightGray",
                    showland=True, landcolor="White",
                    showcoastlines=True, coastlinecolor="White",countrycolor="White",framecolor="LightGray")

    # Set the layout
    fig.update_layout(hovermode='closest',
#         title={
#             'text': title,
#             'x': 0.5,  # Set the title's horizontal alignment to the center
#             'font': {'size': 24, 'family': 'Monospace, bold'}
#         },
        coloraxis_showscale=False,
        width=1500,
        height=500,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    # Show the map
    #fig.show()
    st.plotly_chart(fig,config={'scrollZoom': False},use_container_width=True)


# ## Streamlit

st.markdown(
    """
    <div style='text-align: center;'>
        <h1>Visualizing the Impact of Layoffs</h1>
        <p>Data Source: <a href="https://layoffs.fyi/">layoffs.fyi</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style='text-align: center;'>
        <h2>Across the World So Far</h2>
    </div>
    """,
    unsafe_allow_html=True
)

country_layoff(data,geo_json,"Across the World So Far")


# +
def centered_metric(label, value):
    st.markdown(f"""
        
        <div style="
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 15px;
                text-align: center;
                box-shadow: 0 2px 6px rgba(0,0,0,0.05);
                font-family: monospace;
            ">
            <div style='font-size: 16px; color: gray;'>{label}</div>
            <div style='font-size: 28px;'>{value}</div>
        </div>
    """, unsafe_allow_html=True)

m1,m2,m3,m4,m5,m6 = st.columns([3,2,2,2,2,3])
with m2:
    centered_metric("Total Reports", data.shape[0])
with m3:
    centered_metric("Total Laid Off", str(int(data['# Laid Off'].sum()/1000))+"K+")
with m4:
    centered_metric("Total Companies", int(data['Company'].nunique()))
with m5:
    centered_metric("Companies Shutdown", int(data[data['%']==1]['Company'].nunique()))
# -

st.markdown(
    """
    <div style='text-align: center;'>
        <br>
        <h2>Exploring the Depths</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# +
filter1, filter2, filter3, filter4 = st.columns(4)

year_filter = filter1.selectbox("", ['Select Year (All)']+list(data['Year'].dropna().unique()))
industry_filter = filter2.selectbox("", ['Select Industry (All)']+sorted(data['Industry'].dropna().astype(str).unique()))
country_filter = filter3.selectbox("", ['Select Country (All)']+list(data['Country'].dropna().astype(str).unique()))
company_filter = filter4.selectbox("", ['Select Company (All)']+list(data[data['# Laid Off'].notnull()]['Company'].astype(str).unique()))

try:
    # +
    data['dum'] = True

    mask = (data['dum'] == True)

    # Update the mask based on the selected filters
    if year_filter != 'Select Year (All)':
        mask &= (data['Year'] == year_filter)
    if industry_filter != 'Select Industry (All)':
        mask &= (data['Industry'] == industry_filter)
    if country_filter != 'Select Country (All)':
        mask &= (data['Country'] == country_filter)
    if company_filter != 'Select Company (All)':
        mask &= (data['Company'] == company_filter)

    # Filter the data DataFrame based on the selected filters
    filtered_data = data[mask]


    # -
    def custom_metric(label, value, delta):
        st.markdown(f"""
            <div style="
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 15px;
                text-align: center;
                box-shadow: 0 2px 6px rgba(0,0,0,0.05);
                font-family: monospace;
            ">
                <div style="font-size: 24px; color: #212529;">{value}</div>
                <div style="font-size: 16px; color: #e03131;">{delta}</div>
                <div style="font-size: 16px; color: #6c757d;">{label}</div>
            </div>
        """, unsafe_allow_html=True)



    def top_layoffs(data,n):
        top = data[['Day','Company','# Laid Off']].dropna().sort_values(by=['# Laid Off'],ascending=False).head(n)
        top = top.rename(columns={'# Laid Off': 'Laid_Off'})
        top['Day'] = pd.to_datetime(top['Day']).dt.strftime('%b %Y')

        for i in range(0, len(top), 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < len(top):
                    row = top.iloc[i + j]
                    with cols[j]:
                        custom_metric(
                            label=row.Day,
                            value=row.Company,
                            delta=f"{int(row.Laid_Off):,} employees"
                        )
            st.markdown("<h6> </h6>", unsafe_allow_html=True)



    #+
    st.markdown("<h1> </h1>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center;'>Top Layoffs</h3>", unsafe_allow_html=True)
    top_layoffs(filtered_data,10)
    
    st.markdown("<h1> </h1>", unsafe_allow_html=True)
        
    st.markdown("<h3 style='text-align: center;'>Layoffs over Time</h3>", unsafe_allow_html=True)
    time_layoff(filtered_data)


    # -

    def industry_layoff(data):
        industry_group = data.groupby('Industry')['# Laid Off'].sum().sort_values(ascending=False).reset_index()

        if len(industry_group[industry_group['Industry']!='Other'])>=8:
            large_categories = industry_group[industry_group['Industry']!='Other'].head(8)
            other_categories = industry_group[~industry_group['Industry'].isin(large_categories['Industry'].unique())]['# Laid Off'].sum()
            large_categories.loc[len(large_categories)] = {'Industry': 'Other', '# Laid Off': other_categories}
            
        else:
            large_categories = industry_group.copy()
        
        fig = px.pie(large_categories, values='# Laid Off', names='Industry',hole=0.6,
                    color_discrete_sequence= px.colors.sequential.Reds_r)
        
#         fig.update_layout(
#             title={
#                 'text': 'Layoffs by Industry',
#                 'x': 0.5,  # Set the title's horizontal alignment to the center
#                 'font': {'size': 24, 'family': 'Monospace, bold'}
#             }
#         )
        
        # Display the chart
        st.plotly_chart(fig,use_container_width=True)


    def stage_layoff(data):
        stage_group = data.groupby('Stage')['# Laid Off'].sum().reset_index()

        if len(stage_group[stage_group['Stage']!='Other'])>=8:
            large_categories = stage_group[stage_group['Stage']!='Other'].head(8)
            other_categories = stage_group[~stage_group['Stage'].isin(large_categories['Stage'].unique())]['# Laid Off'].sum()
            large_categories.loc[len(large_categories)] = {'Stage': 'Other', '# Laid Off': other_categories}
        else:
            large_categories = stage_group.copy()
        
        fig = px.pie(large_categories, values='# Laid Off', names='Stage',hole=.6,
                    color_discrete_sequence= px.colors.sequential.Reds_r)
        
        fig.update_layout(
#             title={
#                 'text': 'Layoffs by Stage',
#                 'x': 0.5,  # Set the title's horizontal alignment to the center
#                 'font': {'size': 24, 'family': 'Monospace, bold'}
#             }, 
            legend_traceorder="reversed"
        )
        
        # Display the chart
        st.plotly_chart(fig,use_container_width=True)


    # +
    plot1, plot2 = st.columns(2)

    with plot1:
        st.markdown("<h3 style='text-align: center;'>Layoffs by Industry</h3>", unsafe_allow_html=True)
        industry_layoff(filtered_data)
    with plot2:
        st.markdown("<h3 style='text-align: center;'>Layoffs by Company Stage</h3>", unsafe_allow_html=True)
        stage_layoff(filtered_data)


    # -

    def location_layoff(data):
        
#         data['City'] = data['Location HQ'].apply(lambda x:x[0]+" ("+x[1]+")" if len(x)>1 else x[0])
        data['City'] = data['Location HQ'].dropna().apply(lambda x:x[0])
        location_group  = data.groupby('City')['# Laid Off'].sum().reset_index().sort_values('# Laid Off').tail(10)
        
        fig = px.bar(location_group, y="City", x="# Laid Off",orientation='h')
        
        fig.update_layout(
#             title={
#                 'text': 'Top 10 Cities with Layoffs',
#                 'x': 0.5,  # Set the title's horizontal alignment to the center
#                 'font': {'size': 24, 'family': 'Monospace, bold'}
#             },
            xaxis=dict(title=''),
            yaxis=dict(title=''),
            width=1500,
            height=500,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        fig.update_traces(marker_color='rgba(254,206,186,255)')
        
        st.plotly_chart(fig,use_container_width=True)


    # +
    l1,l2 = st.columns(2)

    with l1:
        st.markdown("<h3 style='text-align: center;'>Layoffs by Country</h3>", unsafe_allow_html=True)
        country_layoff(filtered_data,geo_json,"Layoffs by Country")
    with l2:
        st.markdown("<h3 style='text-align: center;'>Layoffs by Cities</h3>", unsafe_allow_html=True)
        location_layoff(filtered_data)
    # -

    st.markdown(
        """
        <h3 style='text-align: center; font-size:24px;'>
            LayOff Reports<br>
        </h3>
        """,
        unsafe_allow_html=True
    )

    st.dataframe(filtered_data[['Day','Company','Location HQ','Industry','Country','Stage','# Laid Off','Source']],use_container_width=True)

except Exception as e:
    st.error(e)
    st.error('Try another combination of filters')
