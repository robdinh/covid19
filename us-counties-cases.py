# -*- coding: utf-8 -*-

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from urllib.request import urlopen
from datetime import datetime, timedelta

import dash
import dash_core_components as dcc
import dash_html_components as html

import json
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

today = datetime.today() - timedelta(days=1)
today = today.strftime('%Y-%m-%d')

last_week = datetime.today() - timedelta(days=8)
last_week = last_week.strftime('%Y-%m-%d')

# Read CSV's
us_counties = pd.read_csv('https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv')
census = pd.read_csv("https://raw.githubusercontent.com/robdinh/covid19/master/census.csv")
bed_util = pd.read_csv("https://raw.githubusercontent.com/robdinh/covid19/master/bed_util.csv")
current_states = pd.read_csv("https://raw.githubusercontent.com/COVID19Tracking/covid-tracking-data/master/data/states_current.csv")

# Filter dates
us_counties_today = us_counties[us_counties['date'].isin([today])]
us_counties_last_week = us_counties[us_counties['date'].isin([last_week])].rename(columns={'cases': 'cases_lw', 'deaths': 'deaths_lw'})

# Add hospitalized rate
current_states['hospitalized_rate'] = current_states['hospitalizedCurrently'] / current_states['positive']
current_states['hospitalized_rate'].fillna(value=current_states['hospitalized_rate'].mean(), inplace=True)

# Build CSV's
df = pd.merge(census[['fips','county_name','state_abbrev','pop']], bed_util, how='left')
df = pd.merge(df, us_counties_today[['fips','cases','deaths']], how='left')
df = pd.merge(df, us_counties_last_week[['fips','cases_lw','deaths_lw']], how='left')
df = pd.merge(df, current_states[['state','hospitalized_rate']], how='left', left_on='state_abbrev', right_on='state').drop('state_abbrev', axis=1)

df['cases_xincease'] = df['cases'] / df['cases_lw']
df['cases_increase'] = df['cases'] - df['cases_lw']
df['cases_increase_gdp'] = df['cases_increase'] / df['pop'] * 10000 # Per 10K Capita

df.loc[df['cases_increase'] < 1, 'cases_increase'] = 1
df.loc[df['cases_increase'].isnull(), 'cases_increase'] = 1
df.loc[df['cases_increase_gdp'].isnull(), 'cases_increase_gdp'] = 1
df.loc[df['pop'] < 50000, 'cases_increase_gdp'] = None # FIltering metro areas

df['hospitalized'] = df['cases'] * df['hospitalized_rate']
df['bed_load'] = df['bed_util'] + df['hospitalized'] / df['num_beds']
df.loc[df['bed_load'] > 1, 'bed_load'] = 1
df.loc[df['bed_load'] < 0.4, 'bed_load'] = 0.4

def current_cases(data, z, color, title):

	# If statement to switch from reg vs log scale
	if z == 'bed_load':
		z_value=data[z] * 100
		color_scheme=dict(
			tickfont_size=14,
			ticksuffix='%'
		)
	elif z == 'cases_increase':
		z_value=np.log10(data[z])
		color_scheme=dict(
			tickfont_size=14,
			tickmode='array',
			tickvals=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5],
			ticktext=['1', '3', '10', '32', '100', '320', '1000', '3200', '10K', '100K']
		)
	elif z == 'cases_increase_gdp':
		z_value=np.log10(data[z])
		color_scheme=dict(
			tickfont_size=14,
			tickmode='array',
			tickvals=[-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5],
			ticktext=['0.01','0.03','0.1','0.3','1', '3', '10', '32', '100', '320', '1000', '3200', '10K', '100K']
		)

	fig = go.Figure(
		go.Choropleth(
			locations=data['fips'].apply('{:0>5}'.format),
		    locationmode='geojson-id',
		    geojson=counties,
		    colorscale=color,
		    z=z_value,
		    colorbar=color_scheme,
		    marker = dict(line_width=0, opacity=0.8)
		)
	)

	# Style states
	fig.update_geos(visible=True, showsubunits=True, subunitcolor='black')

	fig.update_layout(
		title=title,
		geo_scope='usa',
		autosize=False, width=850, height=500,
		font_size=14,
		margin=dict(l=0, r=0, t=50, b=50),
		coloraxis_colorbar=dict(
			ticks='outside',
			thicknessmode="pixels",
			thickness=50,
			lenmode="pixels", len=200
		)
	)

	return fig

cases_increase = current_cases(df, 'cases_increase', 'electric', 'Case increase since last week')
cases_density = current_cases(df, 'cases_increase_gdp', 'armyrose', 'Cases increase per 10K capita since last week*')

# App Layout
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

markdown_text = '''
[*] Non-metropolitan areas excluded (pop < 50,000)
- Twitter: @rob_dinh
- Source: NY Times
'''

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
	dcc.Graph(id='cases_increase', figure=cases_increase),
	dcc.Graph(id='cases_density', figure=cases_density),
	dcc.Markdown(children=markdown_text)
])

if __name__ == '__main__':
	app.run_server(debug=True, use_reloader=True)  # Turn off reloader if inside Jupyter