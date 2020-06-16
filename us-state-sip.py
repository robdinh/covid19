# -*- coding: utf-8 -*-

import plotly.graph_objects as go
import plotly.express as px
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

# Read and build CSV's
census = pd.read_csv("https://raw.githubusercontent.com/robdinh/covid19/master/census.csv")
states_current = pd.read_csv("https://raw.githubusercontent.com/COVID19Tracking/covid-tracking-data/master/data/states_current.csv")
states_daily = pd.read_csv("https://raw.githubusercontent.com/COVID19Tracking/covid-tracking-data/master/data/states_daily_4pm_et.csv")
us_sip = pd.read_csv('https://raw.githubusercontent.com/robdinh/covid19/master/sip_dates.csv')
state_pop = census[['state_abbrev', 'pop']].groupby(['state_abbrev']).sum()
states_current = pd.merge(states_current[['state','positive','death']], us_sip[['state_abbrev','effective_date','end_date']], left_on='state', right_on='state_abbrev').drop('state_abbrev', axis=1)

def state_peak(df, status, title):
	df_pivot = df.pivot(index='date', columns='state', values='positiveIncrease')

	# Build DF for rolling average
	df_rolling = pd.DataFrame(columns=df_pivot.columns.values.tolist())

	for i in range(len(df_pivot.columns.values.tolist())):
	    state = df_rolling.columns[i]
	    df_rolling[state] = df_pivot[state].rolling(7).mean()

	df_rolling = df_rolling.transpose().reset_index()
	df_rolling['max'] = df_rolling.max(axis=1, skipna=True)
	df_rolling['peak_ratio'] = df_rolling.iloc[:,-2] / df_rolling['max']

	df_rolling.loc[df_rolling['peak_ratio'].isna(), 'peak_ratio'] = 0
	df_rolling.loc[df_rolling['peak_ratio'] > 0.8, 'status'] = 'high risk'
	df_rolling.loc[df_rolling['peak_ratio'] > 0.95, 'status'] = 'peaking'
	df_rolling.loc[df_rolling['peak_ratio'] < 0.8, 'status'] = 'past peak'	

	fig = px.choropleth(
		df_rolling,
		locations=df_rolling['index'],
	    locationmode='USA-states',
		color=status,
		color_discrete_map={
			'past peak': '#d1e5f0',
			'high risk': '#fddbc7',
			'peaking': '#ef8a62'
		},
		category_orders={
			'status': [
				'peaking',
				'high risk',
				'past peak'
			]
		}
	)

	# Style states
	fig.update_geos(visible=True, showsubunits=True, subunitcolor='white')

	# Textbox
	annotations = []
	annotations.append(
		dict(
			xref='paper', yref='paper',
			x=0.95, y=0.6,
			xanchor='left', yanchor='top',
			align='left',
			text='Current 7 day rolling<br>average of daily new<br>cases compared to max<br>rolling average since Jan<br><br>Peaking: >0.95x of max<br>Flattening: >0.8x of max<br>Past Peak: <0.8x of max',
			font=dict(size=14, color='Silver'),
			showarrow=False)
		)

	fig.update_layout(
		title=title,
		geo_scope='usa',
		geo_projection=go.layout.geo.Projection(type = 'albers usa'),
		autosize=False, width=850, height=500,
		font_size=18,
		margin=dict(l=0, r=200, t=50, b=50),
		annotations=annotations	
	)

	return fig

def state_sip(data, status, title):
	this_week = datetime.today().isocalendar()[1]

	# Build DF for SIP dates
	data['end_date_week'] = pd.to_datetime(data['end_date'], format='%m/%d/%y', errors='ignore').dt.week
	data['week_diff'] = data['end_date_week'] - this_week
	data.sort_values(by=['week_diff', 'effective_date'], axis=0, inplace=True)

	# Change data['week_diff']=NaN to 1000 to convert float to int 
	data.loc[data['effective_date'].notna() & data['end_date'].isna(), 'week_diff'] = 1000
	data.loc[data['effective_date'].isna() & data['end_date'].isna(), 'week_diff'] = -1000

	data.loc[data['week_diff'] < 0, 'status'] = 'open'
	data.loc[data['week_diff'] == 0, 'status'] = 'this week'
	data.loc[data['week_diff'] == 1, 'status'] = 'next week'
	data.loc[data['week_diff'] > 1, 'status'] = data['week_diff'].astype('int').astype('str') + ' weeks'
	data.loc[data['week_diff'] > 3, 'status'] = '1+ month'
	data.loc[data['week_diff'] == 1000, 'status'] = 'TBD'

	fig = px.choropleth(
		data,
		locations=data['state'],
	    locationmode='USA-states',
		color=status,
		color_discrete_map={
			'open': 'rgb(246,232,195)',
			'this week': 'rgb(245,245,245)',
			'next week': 'rgb(199,234,229)',
			'2 weeks': 'rgb(128,205,193)',
			'3 weeks': 'rgb(53,151,143)',
			'1+ month': 'rgb(1,102,94)',
			'TBD': 'rgb(231,212,232)'
		},
		category_orders={
			'status': [
				'open',
				'this week',
				'next week',
				'2 weeks',
				'3 weeks',
				'1+ month',
				'TBD'
			]
		}
	)

	# Style states
	fig.update_geos(visible=True, showsubunits=True, subunitcolor='white')

	fig.update_layout(
		title=title,
		geo_scope='usa',
		geo_projection=go.layout.geo.Projection(type = 'albers usa'),
		autosize=False, width=850, height=500,
		font_size=18,
		margin=dict(l=0, r=200, t=50, b=50)
	)

	return fig

state_sip = state_sip(states_current, 'status', 'Scheduled State level SIP rollback*')
state_peak = state_peak(states_daily, 'status', 'States peak status')

# App Layout
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

markdown_text = '''
[*] Updated as of 5/21
- Twitter: @rob_dinh
- Source: Kaiser Family Foundation, The COVID Tracking Project
'''

app.layout = html.Div(children=[
	dcc.Graph(id='state_sip', figure=state_sip),
	dcc.Graph(id='state_peak', figure=state_peak),
	dcc.Markdown(children=markdown_text)
])

if __name__ == '__main__':
	app.run_server(debug=True, use_reloader=True)