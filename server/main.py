import os
import time
import sqlite3
import zoneinfo
from datetime import datetime

import numpy as np

import bokeh.embed
import bokeh.resources
import bokeh.layouts
import bokeh.plotting
import bokeh.models

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseSettings, FilePath

class Settings(BaseSettings):
    pi_ir_db_path: FilePath = '../power_mon.sqlite3'
    dollars_per_kwh: float = 0 # 0 means don't show the cost info


settings = Settings()
app = FastAPI()

def get_connection():
    return sqlite3.connect(settings.pi_ir_db_path)


def get_bokeh_html(samples, cumulative_plot=True, mean_plot=True):
    figs = []

    utcoffset = np.timedelta64(get_system_zoneinfo().utcoffset(datetime.now()))

    if cumulative_plot:
        fig = bokeh.plotting.figure(x_axis_type="datetime", width=800, height=500)

        fig.circle(x=samples.astype('datetime64[ns]') + utcoffset,
                   y=np.arange(len(samples))/1000)

        fig.xaxis.axis_label = 'Time'
        fig.yaxis.axis_label = 'Cumulative kwh'

        figs.append(fig)

    if mean_plot:
        figkwargs = dict(x_axis_type="datetime", width=800, height=500)
        if len(figs) > 0:
            figkwargs['x_range'] = figs[-1].x_range
        fig = bokeh.plotting.figure(**figkwargs)


        dns = np.diff(samples)
        ts = ((samples[1:] + samples[:-1]) / 2).astype('datetime64[ns]')
        kw = 3.6e9/dns
        fig.circle(x=ts + utcoffset, y=kw)

        avg_kw = np.average(kw, weights=samples[1:] - samples[:-1])

        average_span = bokeh.models.Span(location=avg_kw,
                              dimension='width', line_color='#E30B5C',
                              line_dash='dashed', line_width=2)
        fig.add_layout(average_span)

        fig.xaxis.axis_label = 'Time'
        fig.yaxis.axis_label = 'Mean kw during 1 wh'

        figs.append(fig)

    plot = bokeh.layouts.column(*figs)

    return  bokeh.embed.components(plot), avg_kw

def get_system_zoneinfo():
    with open('/etc/timezone') as f:
        return zoneinfo.ZoneInfo(f.read().strip())


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def index(minutes_last: float = 60*24):
    con = get_connection()
    try:
        cur = con.cursor()
        currtime_ns = time.time()*1e9
        backtime_ns = currtime_ns - minutes_last*6.e10

        cur.execute(f'select tstampunixns from wh_pulses where tstampunixns > {backtime_ns} order by tstampunixns ASC')

        samples = np.array(cur.fetchall()).ravel()
    finally:
        con.close()

    latest_kw = 3.6e9/(samples[-1] - samples[-2])

    bokeh_cdn = bokeh.resources.CDN.render()
    (plot_script, plot_div), avg_kw = get_bokeh_html(samples, True, True)

    if settings.dollars_per_kwh == 0:
        moneyinfo = lambda kw: ''
    else:
        def moneyinfo(kw):
            dollars = kw * settings.dollars_per_kwh
            return f' which is ${dollars:.2f} over an hour or ${dollars*24.:.2f} over a day or ${dollars*730.5:.2f} over a month'

    return f"""
    <html>
        <head>
            <title>Electricity usage</title>

            {bokeh_cdn}
            {plot_script}
        </head>
        <body>
            <h1>Latest Power Usage</h1>
            {latest_kw:.3f} kw{moneyinfo(latest_kw)}

            <h1>History</h1>
            {plot_div}
            <h3> Average Power Usage</h3>
            {avg_kw:.3f} kw{moneyinfo(avg_kw)}
        </body>
    </html>
    """


@app.get("/kw")
async def kw():
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute('select tstampunixns from wh_pulses order by tstampunixns DESC LIMIT 2')
        r1, r2 = cur.fetchall()
        dns = r1[0] - r2[0]
        return {'value': 3.6e9/dns}
    finally:
        con.close()


@app.get("/kw_smoothed")
async def kw_smoothed(nsamples: int = 10):
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute(f'select tstampunixns from wh_pulses order by tstampunixns DESC LIMIT {nsamples}')
        samples = np.array(cur.fetchall()).ravel()[::-1]
        dns = np.diff(samples)
        return {'value': np.mean(3.6e9/dns), 'nsamples':len(samples), 'minutes_span':(samples[-1] - samples[0])/6.e10}
    finally:
        con.close()



@app.get("/kw_time_smoothed")
async def kw_time_smoothed(minutes_last: float = 1):
    con = get_connection()
    try:
        cur = con.cursor()
        currtime_ns = time.time()*1e9
        backtime_ns = currtime_ns - minutes_last*6.e10

        cur.execute(f'select tstampunixns from wh_pulses where tstampunixns > {backtime_ns} order by tstampunixns ASC')

        samples = np.array(cur.fetchall()).ravel()

        # always need at least two samples
        if len(samples) < 2:

            cur.execute('select tstampunixns from wh_pulses order by tstampunixns ASC LIMIT 2')
            samples = np.array(cur.fetchall()).ravel()

        dns = np.diff(samples)
        return {'value': np.mean(3.6e9/dns), 'nsamples':len(samples), 'minutes_span':(samples[-1] - samples[0])/6.e10}
    finally:
        con.close()



@app.get("/kwh_since")
async def kwh_since(minutes_back: float = 60):
    currtime_ns = time.time()*1e9
    backtime_ns = currtime_ns - minutes_back*6.e10

    con = get_connection()
    try:
        cur = con.execute(f'select count(tstampunixns) from wh_pulses where tstampunixns > {backtime_ns}')
        count = cur.fetchone()[0]

        return {'value': count/1000, 'nsamples':count}

    finally:
        con.close()

