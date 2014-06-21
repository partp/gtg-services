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
Todoist Service Plug-in
"""

import json
import requests
from urllib.parse import urlencode
from subprocess import Popen

from GTG.core.service.service import Service

class service_todoist(Service):
    """
    """
    
    BASE_URL = r"https://api.todoist.com/API/"
    AUTH_BASE_URL = ''

    def __init__(self):
        self.token = ""
        self.tasklists = []
        self.tasks = {}
        self.completed_tasks = {}

    def init_authorization(self):
        """
        Initiate retrieval of authorization_code
        """
        pass

    def set_credentials(self, **credentials):
        """
        Sets the credentials after user input in service configuration dialog
        """
        url = self.BASE_URL + 'login'
        params = {
            'email': credentials['email'],
            'password': credentials['password']
            }
        req = requests.get(url, params = params)
        if req.status_code == 200:
            resp = json.loads(req.text)
            self.token = resp["token"]
            return True
        return False

    def init_sync(self):
        """
        Called before requesting any changes for sync
        """
        if self._check_token():
            self.tasklists = self._fetch_all_tasklists()
            for tasklist_id in self.get_all_tasklist_ids():
                self.tasks[tasklist_id] = self._fetch_all_tasks(tasklist_id)
                self.completed_tasks[tasklist_id] = self._fetch_all_tasks(tasklist_id, True)
            return True
        else:
            return False

    def get_all_tasklist_ids(self):
        """
        Returns a dictionary of all tasklists with key as remote_id
        & value as tasklist's modified_time
        """
        tasklist_ids = []
        for tasklist in self.tasklists:
            tasklist_ids.append(tasklist["id"])
        return tasklist_ids

    def insert_tasklist(self, **tasklist):
        """
        Inserts new tasklist & returns its remote_id
        """
        url = self.BASE_URL + 'addProject'
        params = {
            "token": self.token,
            "name": tasklist["title"] 
            }
        req = requests.get(url, params = params)
        if req.status_code == 200:
            return json.loads(req.text)["id"]

    def delete_tasklist(self, tasklist_id):
        """
        Deletes the tasklist with given remote_id
        """
        url = self.BASE_URL + 'deleteProject'
        params = {
            "token": self.token,
            "project_id": tasklist_id
            }
        req = requests.get(url, params = params)
        return req.status_code == 200

    def update_tasklist(self, **tasklist):
        """
        Updates the tasklist with given remote_id
        """
        url = self.BASE_URL + 'updateProject'
        params = {
            "token": self.token,
            "project_id": tasklist["id"],
            "name": tasklist["title"] 
            }
        req = requests.get(url, params = params)
        return req.status_code == 200

    def get_all_task_ids(self, tasklist_id):
        """
        Returns a dictionary of all tasks in the tasklist with given remote_id
        with key as remote_id & value as updated time
        """
        task_ids = []
        for task in self.tasks[tasklist_id]:
            task_ids.append(task["id"])
        return task_ids

    def insert_task(self, tasklist_id, **task):
        """
        Inserts new task to the tasklist with given remote_id & returns its remote_id
        """
        url = self.BASE_URL + 'addItem'
        params = {
            "token": self.token,
            "content": sanitize_tags_from(task["title"]) + \
                create_tag_string_from(task["tags"]),
            "project_id": tasklist_id,
            "date_string": task["duedate"],
            "ident": task["indent"],
            "notes": task["content"]
            }
        req = requests.get(url, params = params)
        if req.status_code == 200:
            return json.loads(req.text)["id"]

    def delete_task(self, tasklist_id, **task):
        """
        Deletes the task with given remote_id
        """
        url = self.BASE_URL + 'deleteItems'
        params = {
            "token": self.token,
            "ids": [task["id"]]
            }
        req = requests.get(url, params = params)
        return req.status_code == 200

    def update_task(self, tasklist_id, **task):
        """
        Updates the task with given remote_id
        """
        url = self.BASE_URL + 'updateItem'
        params = {
            "token": self.token,
            "id": task["id"],
            "content": sanitize_tags_from(task["title"]) + \
                create_tag_string_from(task["tags"]),
            "date_string": task["duedate"],
            "ident": task["indent"],
            }
        req = requests.get(url, params = params)
        return req.status_code == 200

    def _check_token(self):
        url = self.BASE_URL + 'ping'
        params = {
            "token": self.token
            }
        req = requests.get(url, params = params)
        return req.status_code == 200

    def _get_token(self):
        """
        Returns a validated token.
        """
        if self.token != "" and self._check_token():
            return self.token

    def _fetch_all_tasklists(self):
        """
        Fetches all the tasklists & sets self.tasklists
        """
        url = self.BASE_URL + 'getProjects'
        params = {
            "token": self.token
            }
        req = requests.get(url, params = params)
        if req.status_code == 200:
            return json.loads(req.text)

    def _fetch_all_tasks(self, tasklist_id, completed=False):
        """
        Fetches all the tasks & sets self.tasks
        """
        if completed:
            api_call = "getAllCompletedItems"
        else:
            api_call = "getUncompletedItems"
        url = self.BASE_URL + api_call
        params = {
            "token": self.token,
            "project_id": tasklist_id
            }
        req = requests.get(url, params = params)
        if req.status_code == 200:
            return json.loads(req.text)

    def _get_labels(self):
        url = self.BASE_URL + 'getLabels'
        params = {
            "token": self.token
            }
        req = requests.get(url, params = params)
        if req.status_code == 200:
            return json.loads(req.text)

# Utility functions
def sanitize_tags_from(title):
    return " ".join([word[1:] if word.startswith("@") else word for word in title.split()])

def create_tag_string_from(tags):
    return " @" + " @".join(tags.split(","))