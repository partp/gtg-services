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
Google Tasks Service Plug-in
"""

import json
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta
from subprocess import Popen

from GTG.core.service.service import Service

class service_gtask(Service):
    """
    """
    
    BASE_URL = r"https://www.googleapis.com/tasks/v1/"
    AUTH_BASE_URL = r"https://accounts.google.com/o/oauth2/"
    CLIENT_ID = "362778520156-v39jobt9ltb69hbrine4k49tpdplc05t.apps.googleusercontent.com"
    CLIENT_SECRET = "VOESkYrhqhDpfn1X1pFsTotY"
    REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

    def __init__(self):
        self.authorization_code = ""
        self.access_token = ""
        self.refresh_token = ""
        self.token_expiry_datetime = None
        self.tasklists = []
        self.tasks = {}

    def init_authorization(self):
        """
        Initiate retrieval of authorization_code from authorization API.
        """
        params = {
            "response_type": "code",
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "scope": (r"https://www.googleapis.com/auth/tasks")
            }
        req = requests.get(self.AUTH_BASE_URL + "auth?%s" % urlencode(params),
            allow_redirects=False)
        url = req.headers.get('location')
        Popen(["xdg-open", url])
        return True

    def set_credentials(self, **credentials):
        self.authorization_code = credentials["authorization_code"]
        return True

    def init_sync(self):
        self.tasklists = self._fetch_all_tasklists()
        for tasklist_id in self.get_all_tasklist_ids():
            self.tasks[tasklist_id] = self._fetch_all_tasks(tasklist_id)

    def get_all_tasklist_ids(self):
        tasklist_ids = []
        for tasklist in self.tasklists:
            tasklist_ids.append(tasklist["id"])
        return tasklist_ids

    def insert_tasklist(self, **tasklist):
        url = self.BASE_URL + r"users/@me/lists"
        header = {
            "Authorization": "Bearer %s" % self._get_access_token(),
            "Content-Type": "application/json"
            }
        data = {
            "title": tasklist["title"]
            }
        req = requests.post(url, headers=header, data=json.dumps(data))
        if req.status_code == 200:
            resp = json.loads(req.text)
            return resp["id"]

    def delete_tasklist(self, tasklist_id):
        url = self.BASE_URL + r"users/@me/lists/%s" % tasklist_id
        authorization_header = {"Authorization": "Bearer %s" % self._get_access_token()}
        req = requests.delete(url, headers=authorization_header)
        return req.status_code == 204

    def update_tasklist(self, **tasklist):
        url = self.BASE_URL + r"users/@me/lists/%s" % tasklist["id"]
        header = {
            "Authorization": "Bearer %s" % self._get_access_token(),
            "Content-Type": "application/json"
            }
        data = {
            "title": tasklist["title"]
            }
        req = requests.put(url, headers=header, data=json.dumps(data))
        if req.status_code == 200:
            resp = json.loads(req.text)
            return resp["id"]

    def get_all_task_ids(self, tasklist_id):
        task_ids = []
        for task in self.tasks[tasklist_id]:
            task_ids.append(task["id"])
        return task_ids

    def insert_task(self, tasklist_id, **task):
        url = self.BASE_URL + r"lists/%s/tasks" % tasklist_id
        header = {
            "Authorization": "Bearer %s" % self._get_access_token(),
            "Content-Type": "application/json"
            }
        params = {
            "tasklist": tasklist_id
            }
        if "parent_id" in task:
            params["parent"] = task["parent_id"]
        data = {
            "title": task["title"],
            "notes": task["content"],
            }
        if "duedate" in task:
            data["due"] = task["duedate"]
        req = requests.post(url, headers=header, params=params, data=json.dumps(data))
        if req.status_code == 200:
            resp = json.loads(req.text)
            return resp["id"]

    def delete_task(self, tasklist_id, task_id):
        url = self.BASE_URL + r"lists/%s/tasks/%s" % (tasklist_id, task_id)
        header = {
            "Authorization": "Bearer %s" % self._get_access_token(),
            "Content-Type": "application/json"
            }
        params = {
            "task": task_id,
            "tasklist": tasklist_id,
            }
        req = requests.delete(url, headers=header, params=params)
        return req.status_code == 204

    def update_task(self, tasklist_id, **task):
        url = self.BASE_URL + r"lists/%s/tasks/%s" % (tasklist_id, task["task_id"])
        header = {
            "Authorization": "Bearer %s" % self._get_access_token(),
            "Content-Type": "application/json"
            }
        params = {
            "task": task["task_id"],
            "tasklist": tasklist_id,
            }
        data = {
            "id": task["task_id"],
            "title": task["title"],
            "notes": task["content"],
            }
        if "duedate" in task:
            data["due"] = task["duedate"]
        req = requests.put(url, headers=header, params=params, data=json.dumps(data))
        if req.status_code == 200:
            resp = json.loads(req.text)
            return resp["id"]

    def _get_access_token(self):
        """
        Retrieving access_token and refresh_token from Token API.
        """
        if self.access_token == "":
            return self._retrieve_tokens()
        elif datetime.now() > self.token_expiry_datetime:
            return self._refresh_token()
        else:
            return self.access_token

    def _retrieve_tokens(self):
        """
        Retrieving access_token and refresh_token from Token API.
        """
        params = {
                "code" : self.authorization_code,
                "client_id" : self.CLIENT_ID,
                "client_secret" : self.CLIENT_SECRET,
                "redirect_uri" : self.REDIRECT_URI,
                "grant_type": "authorization_code",
                }
        params["content-length"] = str(len(urlencode(params)))
        req = requests.post(self.AUTH_BASE_URL + "token", data=params)
        resp = json.loads(req.text)
        self.token_expiry_datetime = datetime.now() + timedelta(seconds=resp["expires_in"])
        self.refresh_token = resp["refresh_token"]
        self.access_token = resp["access_token"]
        return self.access_token

    def _refresh_token(self):
        """
        Refresh access_token using refresh_token from Token API.
        """
        params = {
                "refresh_token" : self.refresh_token,
                "client_id" : self.CLIENT_ID,
                "client_secret" : self.CLIENT_SECRET,
                "grant_type": "refresh_token",
                }
        params["content-length"] = str(len(urlencode(params)))
        req = requests.post(self.AUTH_BASE_URL + "token", data=params)
        resp = json.loads(req.text)
        self.token_expiry_datetime = datetime.now() + timedelta(seconds=resp["expires_in"])
        self.access_token = resp["access_token"]
        return self.access_token

    def _fetch_all_tasklists(self):
        """
        """
        req_url = self.BASE_URL + r"users/@me/lists"
        authorization_header = {"Authorization": "Bearer %s" % self._get_access_token()}
        req = requests.get(req_url, headers=authorization_header)
        return json.loads(req.text)["items"]

    def _fetch_all_tasks(self, tasklist_id):
        """
        """
        req_url = self.BASE_URL + "lists/%s/tasks" % tasklist_id
        authorization_header = {"Authorization": "Bearer %s" % self._get_access_token()}
        req = requests.get(req_url, headers=authorization_header)
        return json.loads(req.text)["items"]