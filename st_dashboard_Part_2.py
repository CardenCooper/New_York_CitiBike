################################################ CITI BIKE DASHBOARD ##########################################################################

import streamlit as st
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from datetime import datetime as dt
from numerize.numerize import numerize
from PIL import Image

# --- Try importing KeplerGL safely ---
try:
    from streamlit_keplergl import keplergl_static
    from keplergl import KeplerGl
    kepler_available = True
except ModuleNotFoundError:
    kepler_available = False

########################################### Initial settings for the dashboard ##################################################################

st.set_page_config(page_title='Citi Bike Strategy Dashboard', layout='wide')
st.title("Citi Bike Strategy Dashboard")

# Define side bar
st.sidebar.title("Aspect Selector")
page = st.sidebar.selectbox(
    'Select an aspect of the analysis',
    [
        "Intro page",
        "Weather component and bike usage",
        "Most popular stations",
        "Interactive map with aggregated bike trips",
        "Recommendations"
    ]
)

########################################### Import data ###########################################################################################

# Primary dataset used by the dashboard
try:
    df = pd.read_csv('reduced_data_to_plot_7.csv', index_col=0)
except FileNotFoundError:
    st.error("Could not find 'reduced_data_to_plot_7.csv' in working directory.")
    st.stop()

# Optional precomputed top20 CSV (we will prefer computing top20 from df for filters)
try:
    top20_csv = pd.read_csv('top20.csv', index_col=0)
except Exception:
    top20_csv = None

######################################### DEFINE THE PAGES #####################################################################

## Intro page
if page == "Intro page":
    st.markdown("#### This dashboard aims to provide helpful insights on the expansion problems CitiBike currently faces.")
    st.markdown(
        "Right now, CitiBike runs into a situation where customers complain about bikes not being available at certain times. "
        "This analysis will look at the potential reasons behind this. The dashboard is separated into 4 sections:"
    )
    st.markdown("- Most popular stations")
    st.markdown("- Weather component and bike usage")
    st.markdown("- Interactive map with aggregated bike trips")
    st.markdown("- Recommendations")
    st.markdown("The dropdown menu on the left 'Aspect Selector' will take you to the different aspects of the analysis our team looked at.")

    try:
        myImage = Image.open("CitiBike.jpg")
        st.image(myImage)
    except Exception as e:
        st.warning(f"Could not load image 'CitiBike.jpg': {e}")

### Create the dual-axis line chart page ###
elif page == 'Weather component and bike usage':

    # Ensure date column is datetime
    if 'date' in df.columns:
        try:
            df['date'] = pd.to_datetime(df['date'])
        except Exception:
            pass

    # Make sure temperature is daily (not cumulative)
    if 'avgTemp' in df.columns:
        if df['avgTemp'].max() > 100:  # crude check for cumulative data
            df['avgTemp_daily'] = df['avgTemp'].diff().fillna(df['avgTemp'])
        else:
            df['avgTemp_daily'] = df['avgTemp']
    
    # Create figure with secondary y-axis
    fig_2 = make_subplots(specs=[[{"secondary_y": True}]])

    # Daily Bike Rides (left axis)
    fig_2.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['bike_rides_daily'],
            name='Daily Bike Rides',
            line=dict(color='royalblue', width=3)
        ),
        secondary_y=False
    )

    # Daily Temperature (right axis)
    fig_2.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['avgTemp_daily'],
            name='Daily Temperature',
            line=dict(color='firebrick', width=3)
        ),
        secondary_y=True
    )

    # Layout customization
    fig_2.update_layout(
        title='Daily Bike Rides vs Average Temperature',
        xaxis_title='Date',
        yaxis_title='Number of Bike Rides',
        width=1000,
        height=600,
        plot_bgcolor='white',
        legend=dict(
            title='',
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        font=dict(size=13)
    )

    # Label secondary y-axis
    fig_2.update_yaxes(title_text='Average Temperature (°C)', secondary_y=True)

    # Show chart
    st.plotly_chart(fig_2, use_container_width=True)

    # Explanatory markdown
    st.markdown(
        "This chart shows there is a clear correlation between bike trips and the temperature. "
        "As temperature increases, so do bike rides; the rise starts around the end of May and doesn't begin to fall until around the start of October."
    )
    st.markdown(
        "Using this information we can assume a majority of bike shortages occur during this time period."
    )

### Most Popular Stations Page ###
elif page == 'Most popular stations':

    # Sidebar season filter
    with st.sidebar:
        season_filter = st.multiselect(
            label='Select the Season',
            options=df['season'].unique(),
            default=list(df['season'].unique())
        )

    # Filter dataframe by selected seasons (copy to avoid SettingWithCopyWarning)
    df1 = df.query('season == @season_filter').copy()

    if df1.empty:
        st.error("No data for the selected season(s). Please choose different season(s).")
    else:
        # Metric
        total_rides = float(df1['bike_rides_daily'].count())
        st.metric(label='Total Bike Rides', value=numerize(total_rides))

        # Compute counts per start station and take top 20
        df1['value'] = 1
        # Find station column robustly (fallback detection)
        station_candidates = [c for c in df1.columns if ('start' in c and 'station' in c) or ('station' in c and 'start' in c)]
        if station_candidates:
            station_col_df = station_candidates[0]
        else:
            station_col_df = next((c for c in df1.columns if 'station' in c or 'name' in c), None)

        if station_col_df is None:
            st.error("Could not find a station column in the main dataframe (df).")
            st.stop()

        df_groupby_bar = df1.groupby(station_col_df, as_index=False).agg({'value': 'sum'})
        top20_local = df_groupby_bar.nlargest(20, 'value').copy()

        # Prepare x labels: shorten long station names for ticks to avoid clutter
        def shorten(name, n=28):
            return name if len(name) <= n else name[:n-1].rstrip() + '…'

        top20_local['tick_label'] = top20_local[station_col_df].astype(str).apply(lambda x: shorten(x, n=28))

        # Ensure numeric
        top20_local['value'] = pd.to_numeric(top20_local['value'], errors='coerce').fillna(0)

        # Plot (clean layout)
        fig = go.Figure(
            go.Bar(
                x=top20_local['tick_label'],
                y=top20_local['value'],
                text=top20_local['value'],
                textposition='outside',
                marker={'color': top20_local['value'], 'colorscale': 'Blues'},
                hovertemplate=
                    '<b>%{customdata[0]}</b><br>' +
                    'Trips: %{y}<extra></extra>',
                customdata=np.stack((top20_local[station_col_df].astype(str),), axis=-1)
            )
        )

        fig.update_layout(
            title='Top 20 Most Popular Bike Stations',
            xaxis_title='Start Stations',
            yaxis_title='Sum of Trips',
            template='plotly_dark',
            width=1000,
            height=520,
            bargap=0.18,
            margin=dict(l=40, r=40, t=80, b=140),
        )

        # Tidy x-axis ticks (smaller font, angled, and centered)
        fig.update_xaxes(tickangle=-35, tickfont=dict(size=10), tickmode='linear', ticklabelmode='period')
        # Make y-axis clearer
        fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.05)')

        # Show chart
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("This bar chart shows us that Grove St PATH is far and away the most popular station with the next 3 in South Waterfront Walkway - Sinatra Dr & 1 St, Hoboken Terminal - River St & Hudson Pl, and Hoboken Terminal - Hudson St & Hudson Pl all being close in terms of trips.") 
        st.markdown("After those top 4 there is a sizeable dropoff to number 5 showing that those 4 are big favorites when it comes to starting stations")
        
elif page == 'Interactive map with aggregated bike trips':

    ### Create the map ###
    st.write("Interactive map showing aggregated bike trips in New York")

    path_to_html = "CitiBike_Trips.html"

    # Read file and keep in variable
    try:
        with open(path_to_html, 'r', encoding='utf-8') as f:
            html_data = f.read()

        # Show in webpage
        st.header("Aggregated Bike Trips in New York")
        st.components.v1.html(html_data, height=1000)
        st.markdown("Yes")
    except FileNotFoundError:
        st.error(f"Map HTML file not found at: {path_to_html}")
    except Exception as e:
        st.error(f"Error loading map HTML: {e}")
        st.markdown("We can see that South Waterfront Walkway - Sinatra Dr & 1 St and ending back at the same location is the most popular trip with Hoboken Terminal - Hudson St & Hudson Pl to Hoboken Ave at Monmouth St being the next most popular followed by Marin Light Rail to Grove St PATH.")
        st.markdown("Despite the fact that Grove St PATH was far and away the most popular starting station it actually doesn't appear as a starting station within the top 3 most popular trips.")
        st.markdown("Another thing we can see from this map is that basically all of the most popular trips take place in either Jersey City or Hoboken.")

elif page == 'Recommendations':
    st.header("Conclusions and recommendations")
    bikes = Image.open("recs_page.jpg")  #source: https://www.freepik.com/free-photo/shadows-made-by-daylight-city-with-architecture_27830346.htm#fromView=search&page=1&position=12&uuid=c0c9642f-53c2-4dc3-ab28-20c8c4d57dc2&query=bike+rack+in+city
    st.image(bikes)
    st.markdown("This analysis shows that CitiBike should follow these recommendations.")
    st.markdown("- Add extra bikes during peak months (May to October) and decrease bikes in colder months to save cost.")
    st.markdown("- Add extra bikes in all of the top 20 most popular starting stations but mainly focus on the top 5 especially Grove St PATH.")
    st.markdown("- Add extra bikes to stations in the Jersey City and Hoboken areas as those seems to be hotspots for trips.")

else:
    # Friendly fallback — shouldn't normally happen
    st.write("Please select a page from the sidebar.")
