'''
Copyright (C) 2015 sprd.net AG

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
from sqlite3 import dbapi2 as sqlite3
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from flask import Flask, request, make_response, g, render_template, jsonify, json, abort, redirect
from calendar import Calendar
from datetime import date
import requests

# configuration
app = Flask(__name__)
app.config.from_object('config')

def connect_to_database():
    if not hasattr(g, 'db'):
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_database(error):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
def releases():
    entries = []
    db = connect_to_database()
    cur = db.execute('select id,name from releases')
    releases = cur.fetchall()
    for release in releases:
        cur = db.execute('select checklist_type,checklist_id,status from checklist_to_release where release_id=?', (release["id"],))
        checklists = cur.fetchall()
        notrun = 0
        notneeded = 0
        passed = 0
        failed = 0
        checks = 0
        for checklist in checklists:
            checks += 1
            if checklist["status"] == "notrun":
                notrun += 1
            if checklist["status"] == "notneeded":
                notneeded += 1
            if checklist["status"] == "passed":
                passed += 1
            if checklist["status"] == "failed":
                failed += 1
        entry = {}
        entry["id"] = release["id"]
        entry["name"] = release["name"]
        if checks > 0:
            entry["notrun"] = (notrun*100/checks)
            entry["notneeded"] = (notneeded*100/checks)
            entry["passed"] = (passed*100/checks)
            entry["failed"] = (failed*100/checks)
        entries.append(entry)
    return render_template('releases.html', entries=entries)

@app.route('/release', methods=['GET', 'POST'])
def release():
    if request.method == 'GET':
        db = connect_to_database()
        cur = db.execute('select id,name from components')
        components = cur.fetchall()
        cur = db.execute('select id,name,default_value from placeholders')
        placeholders = cur.fetchall()
        return render_template('release_new.html', components=components, placeholders=placeholders);
    else:
        steps = []
        release = {}
        release["name"] = request.form["name"]
        db = connect_to_database()
        cur = db.execute('select id,name from placeholders')
        rows = cur.fetchall()
        placeholders = []
        for placeholder in rows:
            placeholders.append(placeholder["name"] + "=" + request.form[placeholder["name"]])
        components = request.form.getlist("components")

        steps.append("Setup new release {} in database...".format(release["name"]))
        cur = db.execute('insert into releases (name,placeholders) values (?,?)', (release["name"], ",".join(placeholders)))
        db.commit()
        release["id"] = cur.lastrowid

        steps.append("Add checklists of components to release {} in database...".format(release["name"]))
        for component_id in components:
            cur = db.execute('select checklist_type,checklist_id from checklist_to_component where component_id=?', (component_id,))
            checklists = cur.fetchall()
            for checklist in checklists:
                cur = db.execute('insert into checklist_to_release(release_id,checklist_type,checklist_id,status) values (?,?,?,?)',
                        (release['id'],checklist['checklist_type'],checklist['checklist_id'],'notrun'))
                db.commit()

        steps.append("Check which checklists need configuration...")
        cur = db.execute('select checklist_type,checklist_id from checklist_to_release where release_id=?', (release["id"],))
        checklists = cur.fetchall()

        for checklist in checklists:
            if checklist["checklist_type"] == 'jenkins':
                cur = db.execute('select name,url,login,password,job,xml from jenkins_checklists where id=?', (checklist["checklist_id"],))
                jenkins = cur.fetchone()
                job = replace(jenkins['job'], placeholders)
                steps.append("Create jenkins job {} on <a href=\"{}\">{}</a>...".format(job,jenkins['url'],jenkins['url']))
                headers = {'content-type': 'application/xml'}
                data = replace(jenkins['xml'], placeholders)
                try:
                    response = requests.post(jenkins['url'] + "/createItem?name=" + job,
                            auth=(jenkins['login'], jenkins['password']), data=data, headers=headers)
                except requests.exceptions.ConnectionError:
                    steps.append("Job creation failed")

        return render_template('release_new_success.html', release=release, steps=steps);

@app.route('/release/<int:id>')
def release_overview(id=None):
    release = None
    entries = []
    db = connect_to_database()
    cur = db.execute('select id,name from releases where id=?', (id,))
    release = cur.fetchone()
    if release == None:
        abort(404)
    cur = db.execute('select checklist_type,checklist_id,status from checklist_to_release where release_id=?', (id,))
    checklists = cur.fetchall()
    for checklist in checklists:
        sql = "select * from {}_checklists where id=?".format(checklist['checklist_type'])
        cur = db.execute(sql, (checklist['checklist_id'],))
        row = cur.fetchone()
        entry = {}
        entry['name'] = row['name']
        entry['status'] = checklist['status']
        entry['id'] = checklist['checklist_id']
        entry['type'] = checklist['checklist_type']
        entries.append(entry)
    return render_template('release_overview.html', release=release, entries=entries)

@app.route('/release/<int:release_id>/checklist/<type>/<id>/status', methods=['GET', 'POST'])
def checklist_status(release_id=None, type=None, id=None):
    db = connect_to_database()
    if request.method == 'POST':
        db.execute('update checklist_to_release set status=? where release_id = ? and checklist_type=? and checklist_id=?', (request.form['status'], release_id, type, id))
        db.commit()
        status = {}
        status['status'] = request.form['status']
        return jsonify(status)
    else:
        cur = db.execute("select status from checklist_to_release as cor inner join releases on cor.release_id = releases.id where releases.id=? and cor.checklist_type=? and cor.checklist_id=?", (release_id, type,id))
        release = cur.fetchone()
        status = {}
        status['status'] = release['status']
        return jsonify(status)

@app.route('/release/<int:release_id>/checklist/<type>/<int:id>')
def checklist(release_id=None, type=None, id=None):
    release = None
    db = connect_to_database()
    cur = db.execute('select id,name,placeholders from releases where id=?', (release_id,))
    release = cur.fetchone()
    if release == None:
        abort(404)
 
    if type == 'screenshots':
        name = None
        actual_urls = None
        expected_urls = None
        cur = db.execute('select id,name,grid,browser,actual_urls,expected_urls from screenshots_checklists where id=?', (id,))
        row = cur.fetchone()
        name = row['name']
        grid = row['grid']
        actual_urls = []
        for url in row['actual_urls'].split(','):
            actual_urls.append(replace(url, release["placeholders"].split(",")))
        expected_urls = []
        for url in row['expected_urls'].split(','):
            expected_urls.append(replace(url, release["placeholders"].split(",")))
        return render_template('screenshots_checklist.html', release=release, id=id, name=name, grid=grid,
                browser=row['browser'],actual_urls=actual_urls, expected_urls=expected_urls)
    else:
        plain = None
        cur = db.execute('select id,name,description from plain_checklists where id=?', (id,))
        plain = cur.fetchone()        
        return render_template('plain_checklist.html', release=release, plain=plain)


@app.route('/archive/<int:release_id>/status', methods=['POST'])
def archive_or_delete_release(release_id=None):
    action_on_release = request.form['status']
    db = connect_to_database()
    if action_on_release == 'delete':
        db.execute('delete from checklist_to_release where release_id = ?', (release_id,))
        db.execute('delete from releases where id=?', (release_id,))
        db.commit()

    if action_on_release == 'archive':
        db.execute('insert into checklist_to_release_archived select *, datetime() from checklist_to_release where release_id=?', (release_id,))
        db.execute('delete from checklist_to_release where release_id=?', (release_id,))
        db.execute('insert into releases_archived select *, datetime() from releases where id=?', (release_id,))
        db.execute('delete from releases where id=?', (release_id,))
        db.commit()

    return redirect('/')

@app.route('/archive')
def archive():
    cal = Calendar(0)
    year = date.today().year
    cal_list = [cal.monthdatescalendar(year, i+1) for i in range(12)]
    db = connect_to_database()
    cur = db.execute('select id, name, strftime(\'%d\', date_archived) as day, strftime(\'%m\', date_archived) as month, strftime(\'%Y\', date_archived) as year from releases_archived')
    archived_releases = cur.fetchall()
    return render_template('archive.html', year=year, cal=cal_list, archived_releases=archived_releases)

@app.route('/configuration/components')
def configuration_components():
    db = connect_to_database()
    cur = db.execute('select id,name from components')
    components = cur.fetchall()
    return render_template('configuration_components.html', components=components)

@app.route('/configuration/component', strict_slashes=False, methods=['GET', 'POST'])
@app.route('/configuration/component/<int:id>', strict_slashes=False, methods=['GET', 'POST', 'DELETE'])
def configuration_component(id=None):
    db = connect_to_database()
    marked_jenkins_checklists = []
    marked_screenshots_checklists = []
    marked_plain_checklists = []
    if request.method == 'GET':
        if id == None:
            class component: pass
            component.id = ''
            component.name = ''
        else:
            cur = db.execute('select id,name from components where id=?', (id,))
            component = cur.fetchone()
            # mark checkboxes of all used checklists
            cur = db.execute('select checklist_id from checklist_to_component where component_id=? and checklist_type="jenkins"', (id,))
            for checklist in cur.fetchall():
                marked_jenkins_checklists.append(checklist["checklist_id"])
            cur = db.execute('select checklist_id from checklist_to_component where component_id=? and checklist_type="screenshots"', (id,))
            for checklist in cur.fetchall():
                marked_screenshots_checklists.append(checklist["checklist_id"])
            cur = db.execute('select checklist_id from checklist_to_component where component_id=? and checklist_type="plain"', (id,))
            for checklist in cur.fetchall():
                marked_plain_checklists.append(checklist["checklist_id"])
        cur = db.execute('select id,name from jenkins_checklists')
        jenkins_checklists = cur.fetchall()
        cur = db.execute('select id,name from screenshots_checklists')
        screenshots_checklists = cur.fetchall()
        cur = db.execute('select id,name from plain_checklists')
        plain_checklists = cur.fetchall()
        return render_template('configuration_component.html', component=component, jenkins_checklists=jenkins_checklists,
                marked_jenkins_checklists=marked_jenkins_checklists,
                marked_screenshots_checklists=marked_screenshots_checklists,
                marked_plain_checklists=marked_plain_checklists,
                screenshots_checklists=screenshots_checklists, plain_checklists=plain_checklists)
    elif request.method == 'POST':
        name = request.form["name"]
        jenkins_checklists = request.form.getlist("jenkins_checklists")
        screenshots_checklists = request.form.getlist("screenshots_checklists")
        plain_checklists = request.form.getlist("plain_checklists")
        if id == None:
            cur = db.execute('insert into components(name) values (?)', (name,))
            component_id = cur.lastrowid
        else:
            cur = db.execute('delete from checklist_to_component where component_id=?', (id,))
            component_id = id

        for checklist_id in jenkins_checklists:
            cur = db.execute('insert into checklist_to_component(component_id,checklist_type,checklist_id) values (?,"jenkins",?)',
                    (component_id,checklist_id))
        for checklist_id in screenshots_checklists:
            cur = db.execute('insert into checklist_to_component(component_id,checklist_type,checklist_id) values (?,"screenshots",?)',
                    (component_id,checklist_id))
        for checklist_id in plain_checklists:
            cur = db.execute('insert into checklist_to_component(component_id,checklist_type,checklist_id) values (?,"plain",?)',
                    (component_id,checklist_id))
        db.commit()
        return redirect('/configuration/components')
    else:
         cur = db.execute('delete from checklist_to_component where component_id=?', (id,))
         cur = db.execute('delete from components where id=?', (id,))
         db.commit()
         return make_response("", 200)

@app.route('/configuration/checklists')
def configuration_checklists():
    db = connect_to_database()
    cur = db.execute('select id,name from jenkins_checklists')
    jenkins_checklists = cur.fetchall()
    cur = db.execute('select id,name from screenshots_checklists')
    screenshots_checklists = cur.fetchall()
    cur = db.execute('select id,name from plain_checklists')
    plain_checklists = cur.fetchall()
    return render_template('configuration_checklists.html', jenkins_checklists=jenkins_checklists,
            screenshots_checklists=screenshots_checklists, plain_checklists=plain_checklists)

@app.route('/configuration/checklist')
def configuration_checklist():
    return render_template('configuration_checklist.html')

@app.route('/configuration/checklist/jenkins_first_step', strict_slashes=False, methods=['GET'])
@app.route('/configuration/checklist/jenkins_first_step/<int:id>', strict_slashes=False, methods=['GET'])
def configuration_checklist_jenkins_first_step(id=None):
    if id == None:
        return render_template('configuration_checklist_jenkins_first_step.html', id='', job='')
    else:
        db = connect_to_database()
        cur = db.execute('select id,name,url,login,password,job from jenkins_checklists where id=?', (id,))
        jenkins = cur.fetchone()
        return render_template('configuration_checklist_jenkins_first_step.html', id=id, name=jenkins['name'], url=jenkins['url'],
                login=jenkins['login'],password=jenkins['password'],job=jenkins['job'])

@app.route('/configuration/checklist/jenkins_second_step', strict_slashes=False, methods=['POST'])
@app.route('/configuration/checklist/jenkins_second_step/<int:id>', strict_slashes=False, methods=['POST'])
def configuration_checklist_jenkins_second_step(id='',job=''):
    name = request.form["name"]
    url = request.form["url"]
    login = request.form["login"]
    password = request.form["password"]
    try:
        response = requests.get(url + "/api/json?tree=jobs[name]", auth=(login, password))
        data = json.loads(response.text)
    except requests.exceptions.RequestException:
        abort(500)
    return render_template('configuration_checklist_jenkins_second_step.html', id=id,name=name,url=url,login=login,
            password=password,job=job,jobs=data['jobs'])
 
@app.route('/configuration/checklist/jenkins_third_step', strict_slashes=False, methods=['POST'])
@app.route('/configuration/checklist/jenkins_third_step/<int:id>', strict_slashes=False, methods=['POST'])
def configuration_checklist_jenkins_third_step(id=''):
    db = connect_to_database()
    name = request.form["name"]
    url = request.form["url"]
    login = request.form["login"]
    password = request.form["password"]
    chooseJob = request.form["chooseJob"]
    if chooseJob == "existing":
        job = request.form["existingJob"]
        response = requests.get(url + "/job/" + job + "/config.xml", auth=(login, password))
        xml = response.text
    else:
        if id == '':
            job = ""
            xml = ""
        else:
            cur = db.execute('select xml,job from jenkins_checklists where id=?', (id,))
            jenkins = cur.fetchone()
            job = jenkins["job"]
            xml = jenkins["xml"]
    cur = db.execute('select name from placeholders')
    placeholders = cur.fetchall()
    job = job.replace('checker_','')

    return render_template('configuration_checklist_jenkins_third_step.html', id=id,name=name,url=url,login=login,
            password=password,job=job,xml=xml,placeholders=placeholders)

@app.route('/configuration/checklist/jenkins_finish', strict_slashes=False, methods=['POST'])
@app.route('/configuration/checklist/jenkins_finish/<int:id>', strict_slashes=False, methods=['POST','DELETE'])
def configuration_checklist_jenkins_finish(id=None):
    db = connect_to_database()
    if request.method == 'POST':
        name = request.form["name"]
        url = request.form["url"]
        login = request.form["login"]
        password = request.form["password"]
        job = "checker_" + request.form["job"]
        xml = request.form["xml"]

        if id == None:
            cur = db.execute('insert into jenkins_checklists(name,url,login,password,job,xml) values (?,?,?,?,?,?)',
                    (name,url,login,password,job,xml))
            db.commit()
        else:
            db.execute('update jenkins_checklists set name=?,url=?,login=?,password=?,job=?,xml=? where id=?',
                    (name,url,login,password,job,xml,id))
            db.commit()
        return redirect('/configuration/checklists')
    else:
        cur = db.execute('delete from checklist_to_component where checklist_type="jenkins" and checklist_id=?', (id,))
        cur = db.execute('delete from checklist_to_release where checklist_type="jenkins" and checklist_id=?', (id,))
        cur = db.execute('delete from jenkins_checklists where id=?', (id,))
        db.commit()
        return make_response("", 200)

@app.route('/configuration/checklist/screenshots', strict_slashes=False, methods=['GET', 'POST'])
@app.route('/configuration/checklist/screenshots/<int:id>', strict_slashes=False, methods=['GET', 'POST', 'DELETE'])
def configuration_checklist_screenshots(id=None):
    db = connect_to_database()
    if request.method == 'GET':
        if id == None:
            cur = db.execute('select name from placeholders')
            placeholders = cur.fetchall()
            return render_template('configuration_checklist_screenshots.html', id='', name='', actual_urls=[],
                    expected_urls=[], placeholders=placeholders)
        else:
            cur = db.execute('select id,name,grid,browser,actual_urls,expected_urls from screenshots_checklists where id=?', (id,))
            screenshots = cur.fetchone()
            actual_urls = screenshots['actual_urls'].split(',')
            expected_urls = screenshots['expected_urls'].split(',')
            cur = db.execute('select name from placeholders')
            placeholders = cur.fetchall()
            return render_template('configuration_checklist_screenshots.html', id=id, name=screenshots['name'],
                    grid=screenshots['grid'], browser=screenshots['browser'], actual_urls=actual_urls, expected_urls=expected_urls, placeholders=placeholders)
    elif request.method == 'POST':
        name = request.form["name"]
        grid = request.form["grid"]
        browser = request.form["browser"]
        actual_urls = request.form["actual_urls"].rstrip("\n\r").replace("\n",",")
        expected_urls = request.form["expected_urls"].rstrip("\n\r").replace("\n",",")
        if id == None:
            cur = db.execute('insert into screenshots_checklists(name,grid,browser,actual_urls,expected_urls) values (?,?,?,?,?)',
                    (name,grid,browser,actual_urls,expected_urls))
            db.commit()
        else:
            db.execute('update screenshots_checklists set name=?,grid=?,browser=?,actual_urls=?,expected_urls=? where id=?',
                    (name,grid,browser,actual_urls,expected_urls,id))
            db.commit()
        return redirect('/configuration/checklists')
    else:
        cur = db.execute('delete from checklist_to_component where checklist_type="screenshots" and checklist_id=?', (id,))
        cur = db.execute('delete from checklist_to_release where checklist_type="screenshots" and checklist_id=?', (id,))
        cur = db.execute('delete from screenshots_checklists where id=?', (id,))
        db.commit()
        return make_response("", 200)

@app.route('/configuration/checklist/plain', strict_slashes=False, methods=['GET', 'POST'])
@app.route('/configuration/checklist/plain/<int:id>', strict_slashes=False, methods=['GET', 'POST', 'DELETE'])
def configuration_checklist_plain(id=None):
    if request.method == 'GET':
        if id == None:
            class plain: pass
            plain.id = ''
            plain.name = ''
            plain.description = ''
            return render_template('configuration_checklist_plain.html', plain=plain)
        else:
            db = connect_to_database()
            cur = db.execute('select id,name,description from plain_checklists where id=?', (id,))
            plain = cur.fetchone()
            return render_template('configuration_checklist_plain.html', plain=plain)
    elif request.method == 'POST':
        name = request.form["name"]
        description = request.form["description"]
        db = connect_to_database()
        if id == None:
            cur = db.execute('insert into plain_checklists(name,description) values (?,?)', (name,description))
            db.commit()
        else:
            db.execute('update plain_checklists set name=?,description=? where id=?', (name,description,id))
            db.commit()
        return redirect('/configuration/checklists')
    else:
        db = connect_to_database()
        cur = db.execute('delete from checklist_to_component where checklist_type="plain" and checklist_id=?', (id,))
        cur = db.execute('delete from checklist_to_release where checklist_type="plain" and checklist_id=?', (id,))
        cur = db.execute('delete from plain_checklists where id=?', (id,))
        db.commit()
        return make_response("", 200)
 
@app.route('/configuration/placeholders')
def configuration_placeholders():
    db = connect_to_database()
    cur = db.execute('select id,name from placeholders')
    placeholders = cur.fetchall()
    return render_template('configuration_placeholders.html', placeholders=placeholders)

@app.route('/configuration/placeholder', strict_slashes=False, methods=['GET', 'POST'])
@app.route('/configuration/placeholder/<int:id>', strict_slashes=False, methods=['GET', 'POST', 'DELETE'])
def configuration_placeholder(id=None):
    db = connect_to_database()
    if request.method == 'GET':
        if id == None:
            class placeholder: pass
            placeholder.id = ''
            placeholder.name = ''
            placeholder.default_value = ''
        else:
            cur = db.execute('select id,name,default_value from placeholders where id=?', (id,))
            placeholder = cur.fetchone()
        return render_template('configuration_placeholder.html', placeholder=placeholder)
    elif request.method == 'POST':
        name = request.form["name"]
        default_value = request.form["default_value"]
        if id == None:
            cur = db.execute('insert into placeholders(name,default_value) values (?,?)', (name,default_value))
            db.commit()
            placeholder_id = cur.lastrowid
        else:
            cur = db.execute('update placeholders set name=?, default_value=? where id=?', (name,default_value,id))
            db.commit()
        return redirect('/configuration/placeholders')
    else:
        cur = db.execute('delete from placeholders where id=?', (id,))
        db.commit()
        return make_response("", 200)

@app.route('/release/<int:release_id>/jenkins')
def jenkins(release_id=None):
    release = None
    db = connect_to_database()
    cur = db.execute('select id,name,placeholders from releases where id=?', (release_id,))
    release = cur.fetchone()
    if release == None:
        abort(404)

    checklist_type = request.args.get('type')
    checklist_id = request.args.get('id')
    db = connect_to_database()
    sql = "select url,name,login,password,job from {}_checklists where id=?".format(checklist_type)
    cur = db.execute(sql, (checklist_id,))
    rows = cur.fetchall()
    for row in rows:
        name = row['name']
        job = replace(row['job'], release["placeholders"].split(","))
        url = row['url']
        login = row['login']
        password = row['password']
        response = requests.get(url + "/job/" + job + "/api/json", auth=(login, password))
        if response.status_code != 200:
            abort(response.status_code)
        data = json.loads(response.text)
        entry = {}
        entry['name'] = row['name']
        entry['job'] = job
        entry['url'] = row['url']
        entry['status'] = 'notrun'
        entry['color'] = data['color']
        if len(data['healthReport']) > 0:
            entry['healthReport'] = data['healthReport'][0]['description']
        else:
            entry['healthReport'] = "Not built yet"
    return jsonify(entry)

@app.route('/screenshot', methods=['GET'])
def screenshot():
    url = request.args.get('url', '')
    grid = request.args.get('grid', '')
    browser = request.args.get('browser', '')
    if browser == "FIREFOX":
        capabilities = DesiredCapabilities.FIREFOX
    elif browser == "INTERNETEXPLORER":
        capabilities = {'browserName': 'internet explorer',
                'ignoreProtectedModeSettings': True,
                'initialBrowserUrl': '',
                'ignoreProtectedModeSettings': True,
                'acceptSslCerts': True,
                'requireWindowFocus': True,
                'enablePersistentHover': False,
                'javascriptEnabled': True}
    else:
        capabilities = DesiredCapabilities.CHROME
    driver = webdriver.Remote(
               command_executor=grid,
               desired_capabilities=capabilities)
    driver.get(url)
    screenshot = driver.get_screenshot_as_png();
    driver.quit()
    response=make_response(screenshot)
    response.headers['Content-Type'] = 'image/png'
    return response 

def replace(text, placeholders):
    for placeholder in placeholders:
        key = placeholder.split('=')[0]
        value = placeholder.split('=')[1]
        text = text.replace("{{" + key + "}}", value)
    return text

if __name__ == "__main__":
    app.run(threaded=True)
