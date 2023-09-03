#!/usr/bin/env python3
# https://github.com/maldex/TimedTrafficLight
# pip3 install mcrcon flask apscheduler requests

import ast, json, logging, datetime, threading, requests, os, socket, os, sys
from flask import Flask, request, render_template, redirect, send_file
from mcrcon import MCRcon
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

mcserver = "server.camp" #socket.gethostname()
mcpass = "changeme_iam_a_password"

class OurRcon():
    def __init__(self, server="server.camp", passwd="a_password"):
        self.mcr = MCRcon(server, passwd)
        self.mcr.connect()

    def get_time(self):
        return int(self.send_cmd(F"time query daytime").split('is ')[-1])

    def send_cmd(self, cmd):
        logging.debug(F"RCON: sending '{cmd}'")
        try:
           ret = self.mcr.command(F"{cmd}")
        except Exception as e:
           logging.warn(e)
           quit()
        logging.debug(F"RCON: receivd '{ret}")
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
            p['Pos'] = [ int(c) for c in p['Pos'] ]

            p['Dim'] = (
                self.send_cmd(F"data get entity @p[name={p['name']}] Dimension").split('data: ')[-1]
            )[+1: -1].replace('"','').split(':')[-1]

            try:
                LastDeath = self.send_cmd(F"data get entity @p[name={p['name']}] LastDeathLocation").split('data: ')[
                    -1].replace('I; ', '')
                p['LastDeath'] = [int(c.strip()) for c in LastDeath[LastDeath.find("[") + 1:LastDeath.find("]")].split(',')]
                p['LastDim'] = LastDeath.split('dimension:')[-1].replace('"','').replace('}','').split(':')[-1]
            except Exception as e:
                p['LastDeath'] = None
                p['lastDim'] = None

            p['Health'] = int(float(
                self.send_cmd(F"data get entity @p[name={p['name']}] Health").split('data: ')[-1].replace('f','')
            ) /2 )

            ret.append(p)

        return ret

# very nasty way of peristing a string in flask :(
def set_server_message(msg, file="./McServerCompanion.last_msg"):
    with open(file, 'w') as f:
        f.write(msg)

def get_server_message(file="./McServerCompanion.last_msg"):
    try:
        with open(file, 'r') as f:
            msg = f.read()
        os.remove(file)
        logging.info(F"SERVER SAID: {msg}")
        return msg
    except Exception as e:
        return None

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

@app.route("/announce", methods=["GET", "POST"])
def url_announce():
    if request.environ['REQUEST_METHOD'] == "POST":
        form_data = request.form.to_dict(flat=True)
        server.send_cmd(F"/say {form_data['text']}")
        return redirect("/", code=302)
    return render_template("announce.html")

@app.route("/oppanel", methods=["GET", "POST"])
def url_oppannel():
    current_players = server.get_players()
    # try:
    #     current_players = server.get_players()
    # except Exception as e:
    #     return "<title>no user</title><h1><p>seems noone is logged in!</p></h1>"
    return render_template("oppanel.html",
                           current = server.get_time(),
                           players = current_players,
                           server_message = get_server_message() )

@app.route("/time", methods=["GET", "POST"])
def url_settime():
    if request.environ['REQUEST_METHOD'] == "POST":
        form_data = request.form.to_dict(flat=True)
        if 'desired_time' in form_data:
            new_time =  form_data['desired_time'][1:] # without the first character
            logging.debug(F"WE WANT {new_time}")
            set_server_message( server.send_cmd(F"/time set {new_time}") )
    return redirect("/oppanel", code=302)

@app.route("/weather", methods=["GET", "POST"])
def url_weather():
    if request.environ['REQUEST_METHOD'] == "POST":
        form_data = request.form.to_dict(flat=True)
        if 'desired_weather' in form_data:
            new_weather = form_data['desired_weather'][1:] # without the first character
            logging.debug(F"WE WANT {new_weather}")
            # server.set_weather(new_time)
            set_server_message( server.send_cmd(F"/weather {new_weather}") )
    return redirect("/oppanel", code=302)

@app.route("/player/<string:player>", methods=["GET", "POST"])
def url_player(player):
    form_data = request.form.to_dict(flat=True)
    mode = form_data['mode'][1:].strip()    # remove first unicode character
    logging.debug(form_data)
    if 'DEOP' in mode:
        set_server_message( server.send_cmd(F"deop {player}") )
    elif 'OP' in mode:
        set_server_message( server.send_cmd(F"op {player}") )
    elif "creative" in mode:
        set_server_message( server.send_cmd(F"gamemode creative {player}") )
    elif "survival" in mode :
        set_server_message( server.send_cmd(F"gamemode survival {player}") )
    elif "kick" in mode:
        set_server_message( server.send_cmd(F"kick {player}") )
    elif "teleport to" in mode:
        dst = form_data['tp_to']
        logging.debug(F"to to:  {form_data['tp_to']}")
        dst, dim = form_data['tp_to'].split(';')
        dst = ' '.join([ str(d) for d in ast.literal_eval(dst)])
        set_server_message( server.send_cmd(F"execute in {dim} run tp {player} {dst}") )
    return redirect("/oppanel", code=302)

# /execute in the_end run tp <player> <location>   #https://gaming.stackexchange.com/questions/292340/teleporting-a-player-from-the-overworld-to-the-end
# /execute in the_end run tp Poseidon 0 0 0

sched = BlockingScheduler()
@sched.scheduled_job('interval', minutes=15)
def timed_job():
    msg = datetime.datetime.now().strftime("in the real world, it's currently %Y-%m-%d %H:%M:%S")
    logging.info(msg)
    requests.post("http://127.0.0.1:25564/announce", data={'text': msg} )

if __name__ == "__main__":
    server = OurRcon(server = mcserver, passwd = mcpass)

    timer = threading.Thread(target = sched.start)
    timer.start()

    app.run(debug=False, host='0.0.0.0', port=25564)

