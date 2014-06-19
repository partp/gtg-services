# -*- coding: utf-8 -*-
#
# Copyright (c) 2014 - Parth Panchal <parthpanchl@gmail.com>
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
"""
Remember The Milk Service Plug-in
"""

import json
import requests
from hashlib import md5
from urllib.parse import urlencode
from subprocess import Popen

from GTG.core.service.service import Service

class service_rtm(Service):
    """
    """
    
    BASE_URL = r"http://api.rememberthemilk.com/services/rest/"
    AUTH_BASE_URL = r"http://www.rememberthemilk.com/services/auth/?"
    API_KEY = "826fda34b65df82ccfa279efdaf50ee7"
    SHARED_SECRET = "9a645af7022c325f"

    def __init__(self):
        self.frob = ""
        self.token = ""
        self.timeline = ""
        self.tasklists = []
        self.tasks = {}

    def init_authorization(self):
        """
        Initiate retrieval of authorization_code
        """
        self._get_frob()
        params = {
            "api_key": self.API_KEY,
            "perms": "delete",
            "frob": self.frob
            }
        params['api_sig'] = self._sign(params)
        url = self.AUTH_BASE_URL + urlencode(params)
        Popen(["xdg-open", url])
        return True

    def set_credentials(self, **credentials):
        params = {
            "method": "rtm.auth.getToken",
            "api_key": self.API_KEY,
            "frob": self.frob,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            self.token = resp['auth']['token']
            return True
        else:
            return False

    def init_sync(self):
        """
        Called before requesting any changes for sync
        """
        self._get_token()
        self._create_timeline()
        self.tasklists = self._fetch_all_tasklists()
        for tasklist_id in self.get_all_tasklist_ids():
            self.tasks[tasklist_id] = self._fetch_all_tasks(tasklist_id)

    def get_all_tasklist_ids(self):
        """
        Returns a dictionary of all tasklists with key as remote_id
        & value as tasklist's modified_time
        """
        tasklist_ids = []
        for tasklist in self.tasklists:
            if tasklist["name"] != "All Tasks":
                tasklist_ids.append(tasklist["id"])
        return tasklist_ids

    def insert_tasklist(self, **tasklist):
        """
        Inserts new tasklist & returns its remote_id
        """
        params = {
            "method": "rtm.lists.add",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "name": tasklist["title"],
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            return resp["list"]["id"]

    def delete_tasklist(self, tasklist_id):
        """
        Deletes the tasklist with given remote_id
        """
        params = {
            "method": "rtm.lists.delete",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "list_id": tasklist_id,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            return resp["list"]["deleted"] == "1"

    def update_tasklist(self, **tasklist):
        """
        Updates the tasklist with given remote_id
        """
        params = {
            "method": "rtm.lists.setName",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "list_id": tasklist["id"],
            "name": tasklist["title"],
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        return bool(resp)

    def get_all_task_ids(self, tasklist_id):
        """
        Returns a dictionary of all tasks in the tasklist with given remote_id
        with key as remote_id & value as updated time
        """
        task_ids = []
        for task in self.tasks[tasklist_id]:
            taskseries_id = task["id"]
            task_id = get_last_element(task["task"])["id"]
            note = get_last_element(task["notes"])
            if note:
                note_id = get_last_element(note["note"])["id"]
            else:
                note_id = ""
            task_ids.append(taskseries_id + "#" + task_id + "#" + note_id)
        return task_ids

    def insert_task(self, tasklist_id, **task):
        """
        Inserts new task to the tasklist with given remote_id & returns its remote_id
        """
        task_id = self._add_task(tasklist_id, **task)
        if task_id is not None:
            task["id"] = task_id
            if task["tags"] != "":
                self._set_tags(tasklist_id, **task)
            if task["duedate"] != "":
                self._set_duedate(tasklist_id, **task)
            if task["content"] != "":
                note_id = self._add_note(tasklist_id, **task)
                if note_id:
                    task_id += note_id
            return task_id

    def delete_task(self, tasklist_id, **task):
        """
        Deletes the task with given remote_id
        """
        taskseries_id, task_id, note_id = task["id"].split("#")
        params = {
            "method": "rtm.tasks.delete",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "list_id": tasklist_id,
            "taskseries_id": taskseries_id,
            "task_id": task_id,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        return bool(resp)

    def update_task(self, tasklist_id, **task):
        """
        Updates the task with given remote_id
        """
        taskseries_id, task_id, note_id = task["id"].split("#")
        title = self._set_task_name(tasklist_id, **task)
        tags = self._set_tags(tasklist_id, **task)
        duedate = self._set_duedate(tasklist_id, **task)
        if task["content"] != "":
            if note_id != "":
                content = self._edit_note(**task)
            else:
                content = self._add_note(tasklist_id, **task)
        else:
            content = True
        return title and tags and duedate and content

    def _sign(self, params):
        "Sign the parameters with MD5 hash"
        pairs = ''.join(['%s%s' % (k, v) for k, v in sorted_items(params)])
        return md5((self.SHARED_SECRET + pairs).encode('utf-8')).hexdigest()

    def _get_frob(self):
        params = {
            "method": "rtm.auth.getFrob",
            "api_key": self.API_KEY,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            self.frob = resp["frob"]
            return self.frob

    def _check_token(self):
        params = {
            "method": "rtm.auth.checkToken",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        return bool(response(req))

    def _get_token(self):
        """
        Returns a validated token or initiates authorization if token invalid.
        """
        if self.token == "" or not self._check_token():
            self.init_authorization()
            self.set_credentials()
        return self.token

    def _create_timeline(self):
        params = {
            "method": "rtm.timelines.create",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            self.timeline = resp["timeline"]
            return True
        else:
            return False

    def _fetch_all_tasklists(self):
        """
        Fetches all the tasklists & sets self.tasklists
        """
        params = {
            "method": "rtm.lists.getList",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            return resp["lists"]["list"]

    def _fetch_all_tasks(self, tasklist_id):
        """
        Fetches all the tasks & sets self.tasks
        """
        params = {
            "method": "rtm.tasks.getList",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "list_id": tasklist_id,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            if "taskseries" in resp["tasks"]["list"]:
                return resp["tasks"]["list"]["taskseries"]
            else:
                return []

    def _add_task(self, tasklist_id, **task):
        params = {
            "method": "rtm.tasks.add",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "list_id": tasklist_id,
            "name": task["title"],
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            taskseries = resp["list"]["taskseries"]
            return taskseries["id"] + "#" + taskseries["task"]["id"] + "#"

    def _set_tags(self, tasklist_id, **task):
        taskseries_id, task_id, note_id = task["id"].split("#")
        params = {
            "method": "rtm.tasks.setTags",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "list_id": tasklist_id,
            "taskseries_id": taskseries_id,
            "task_id": task_id,
            "format": "json"
            }
        if "tags" in task:
            params["tags"] = task["tags"],
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        return bool(resp)

    def _set_duedate(self, tasklist_id, **task):
        taskseries_id, task_id, note_id = task["id"].split("#")
        params = {
            "method": "rtm.tasks.setDueDate",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "list_id": tasklist_id,
            "taskseries_id": taskseries_id,
            "task_id": task_id,
            "format": "json"
            }
        if "duedate" in task:
            params["due"] = task["duedate"]
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        return bool(resp)

    def _add_note(self, tasklist_id, **task):
        taskseries_id, task_id, note_id = task["id"].split("#")
        note_title, note_text = split_content(task["content"])
        params = {
            "method": "rtm.tasks.notes.add",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "list_id": tasklist_id,
            "taskseries_id": taskseries_id,
            "task_id": task_id,
            "note_title": note_title,
            "note_text": note_text,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        if resp:
            return resp["note"]["id"]

    def _set_task_name(self, tasklist_id, **task):
        taskseries_id, task_id, note_id = task["id"].split("#")
        params = {
            "method": "rtm.tasks.setName",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "list_id": tasklist_id,
            "taskseries_id": taskseries_id,
            "task_id": task_id,
            "name": task["title"],
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        return bool(resp)

    def _edit_note(self, **task):
        taskseries_id, task_id, note_id = task["id"].split("#")
        note_title, note_text = split_content(task["content"])
        params = {
            "method": "rtm.tasks.notes.edit",
            "auth_token": self.token,
            "api_key": self.API_KEY,
            "timeline": self.timeline,
            "note_id": note_id,
            "note_title": note_title,
            "note_text": note_text,
            "format": "json"
            }
        params["api_sig"] = self._sign(params)
        req = requests.get(self.BASE_URL, params=params)
        resp = response(req)
        return bool(resp)

# Utility functions
def response(req):
    if req.status_code == 200:
        resp = json.loads(req.text)
        if resp["rsp"]["stat"] == "ok":
            return resp["rsp"]
    return False

def get_last_element(data):
    # Data is a dictionary
    if type(data) is dict:
        return data
    # Data is a list of dictionary elements
    elif type(data) is list and len(data) > 0:
        return data[-1]
    else:
        return False

def split_content(content):
    note = content.split("\n", 1)
    if len(note) == 2:
        return note[0], note[1]
    else:
        return note[0], ""

def sorted_items(dictionary):
    "Return a list of (key, value) sorted based on keys"
    keys = list(dictionary.keys())
    keys.sort()
    for key in keys:
        yield key, dictionary[key]