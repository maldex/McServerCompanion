#!/usr/bin/env python3
# https://github.com/maldex/TimedTrafficLight
# pip3 install mcrcon flask apscheduler requests

import ast, json, logging, datetime, threading, requests, os, socket
from flask import Flask, request, render_template, redirect, send_file
from mcrcon import MCRcon
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)



class OurRcon():
    def __init__(self, server="server.camp", passwd="a_password"):
        self.mcr = MCRcon(server, passwd)
        self.mcr.connect()

    def get_time(self):
        return int(self.send_cmd(F"time query daytime").split('is ')[-1])

    def send_cmd(self, cmd):
        logging.debug(F"send to rcon: '{cmd}'")
        try:
           ret = self.mcr.command(F"{cmd}")
        except Exception as e:
           logging.warn(e)
           quit()
        logging.debug(F"received from rcon: '{ret}")
        return ret

    def get_players(self):
        ret = []
        for p in self.send_cmd("/list uuids").split(':')[-1].split(','):
            p = { 'name': p.split(' ')[1],
                  'uuid': p[p.find("(")+1:p.find(")")]
            }

            p['Pos'] = json.loads(
                self.send_cmd(F"data get entity @p[name={p['name']}] Pos").split('data: ')[-1].replace('d','')
            )
            p['Pos'] = [ int(d) for d in p['Pos'] ]

            LastDeath = self.send_cmd(F"data get entity @p[name={p['name']}] LastDeathLocation").split('data: ')[
                -1].replace('I; ', '')
            p['LastDeath'] = [c.strip() for c in LastDeath[LastDeath.find("[") + 1:LastDeath.find("]")].split(',')]
            ret.append(p)
        return ret

app = Flask(__name__)

@app.route('/favicon.ico')
def url_favicon():
    return send_file('templates/favicon.png')

@app.route('/server-icon.png')
def url_servericon():
    return send_file('templates/server-icon.png')

@app.route("/")
def url_root():
    return redirect("/oppanel", code=302)


@app.route("/oppanel", methods=["GET", "POST"])
def url_oppannel():
    try:
        current_players = server.get_players()
    except Exception as e:
        return "<p>seems noone is logged in!</p>"
    return render_template("oppanel.html",
                           current = server.get_time(),
                           players = current_players,)



@app.route("/time", methods=["GET", "POST"])
def url_settime():
    if request.environ['REQUEST_METHOD'] == "POST":
        form_data = request.form.to_dict(flat=True)
        if 'desired_time' in form_data:
            new_time =  form_data['desired_time'][1:] # without the first character
            print(F"WE WANT {new_time}")
            server.send_cmd(F"/time set {new_time}")
    return redirect("/oppanel", code=302)

@app.route("/weather", methods=["GET", "POST"])
def url_weather():
    if request.environ['REQUEST_METHOD'] == "POST":
        form_data = request.form.to_dict(flat=True)
        if 'desired_weather' in form_data:
            new_weather =  form_data['desired_weather'][1:] # without the first character
            print(F"WE WANT {new_weather}")
            # server.set_weather(new_time)
            server.send_cmd(F"/weather {new_weather}")
    return redirect("/oppanel", code=302)

@app.route("/player/<string:player>", methods=["GET", "POST"])
def url_player(player):
    form_data = request.form.to_dict(flat=True)
    mode = form_data['mode'][1:].strip()    # remove first unicode character
    if 'DEOP' in mode:
        server.send_cmd(F"/deop {player}")
    elif 'OP' in mode:
        server.send_cmd(F"/op {player}")
    elif "creative" in mode:
        server.send_cmd(F"/gamemode creative {player}")
    elif "survival" in mode :
        server.send_cmd(F"/gamemode survival {player}")
    elif "kick" in mode:
        server.send_cmd(F"/kick {player}")
    elif "teleport to" in mode:
        dst = form_data['tp_to']
        if dst == "LastDeath":
            logging.debug(F"Last Death:  {form_data['LastDeath']}")
            dst = ' '.join(ast.literal_eval(form_data['LastDeath']))
        server.send_cmd(F"/tp {player} {dst}")
    return redirect("/oppanel", code=302)

@app.route("/announce", methods=["GET", "POST"])
def url_announce():
    if request.environ['REQUEST_METHOD'] == "POST":
        form_data = request.form.to_dict(flat=True)
        server.send_cmd(F"/say {form_data['text']}")
        return redirect("/", code=302)
    return render_template("announce.html")

sched = BlockingScheduler()
@sched.scheduled_job('interval', minutes=15)
def timed_job():
    msg = datetime.datetime.now().strftime("in the outside (real) world, it's currently %Y-%m-%d %H:%M:%S")
    logging.info(msg)
    requests.post("http://127.0.0.1:25564/announce", data={'text': msg} )

if __name__ == "__main__":
    server = OurRcon(server = socket.gethostname(), passwd = "changeme_iam_a_password")

    x = threading.Thread(target = sched.start)
    x.start()


    app.run(debug=False, host='0.0.0.0', port=25564)

