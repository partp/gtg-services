# -*- coding: utf-8 -*-
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
import os
import configparser

class Service(object):
    """A class to represent a service."""

    def init_authorization(self):
        """
        Initiate retrieval of authorization_code
        """
        raise NotImplementedError

    def set_credentials(self, **credentials):
        """
        Sets the credentials after user input in service configuration dialog
        """
        raise NotImplementedError

    def init_sync(self):
        """
        Called before requesting any changes for sync
        """
        raise NotImplementedError

    def get_all_tasklist_ids(self):
        """
        Returns a dictionary of all tasklists with key as remote_id
        & value as tasklist's modified_time
        """
        raise NotImplementedError

    def insert_tasklist(self, **tasklist):
        """
        Inserts new tasklist & returns its remote_id
        """
        raise NotImplementedError

    def delete_tasklist(self, tasklist_id):
        """
        Deletes the tasklist with given remote_id
        """
        raise NotImplementedError

    def update_tasklist(self, **tasklist):
        """
        Updates the tasklist with given remote_id
        """
        raise NotImplementedError

    def get_all_task_ids(self, tasklist_id):
        """
        Returns a dictionary of all tasks in the tasklist with given remote_id
        with key as remote_id & value as updated time
        """
        raise NotImplementedError

    def insert_task(self, tasklist_id, **task):
        """
        Inserts new task to the tasklist with given remote_id & returns its remote_id
        """
        raise NotImplementedError

    def delete_task(self, tasklist_id, **task):
        """
        Deletes the task with given remote_id
        """
        raise NotImplementedError

    def update_task(self, tasklist_id, **task):
        """
        Updates the task with given remote_id
        """
        raise NotImplementedError

###############################################################################
###### You don't need to reimplement the functions below this line ############
###############################################################################

    # A reference to an instance of the service class
    instance = None
    # True if some error prevents the service from being activated.
    error = False
    # True if the service is actually loaded and running.
    _active = False
    missing_modules = []

    def __init__(self, info, module_path):
        """Initialize the Service using a ConfigParser."""
        info_fields = {
            'module_name': 'module',
            'full_name': 'name',
            'version': 'version',
            'authors': 'authors',
            'short_description': 'short-description',
            'description': 'description',
            'module_depends': 'dependencies',
        }
        for attr, field in info_fields.items():
            try:
                setattr(self, attr, info[field])
            except KeyError:
                setattr(self, attr, [])
        # ensure the module dependencies are a list
        if isinstance(self.module_depends, str):
            self.module_depends = self.module_depends.split(',')
            if not self.module_depends[-1]:
                self.module_depends = self.module_depends[:-1]
        self._load_module(module_path)

    # 'active' property
    def _get_active(self):
        return self._active

    def _set_active(self, value):
        if value:
            self.instance = self.service_class()
        else:
            self.instance = None
        self._active = value

    active = property(_get_active, _set_active)

    def _check_module_depends(self):
        """Check the availability of modules this service depends on."""
        self.missing_modules = []
        for mod_name in self.module_depends:
            try:
                __import__(mod_name)
            except:
                self.missing_modules.append(mod_name)
                self.error = True

    def _load_module(self, module_path):
        """Load the module containing this service."""
        try:
            # import the module containing the service
            f, pathname, desc = imp.find_module(self.module_name, module_path)
            module = imp.load_module(self.module_name, f, pathname, desc)
            # find the class object for the actual service
            for key, item in module.__dict__.items():
                if isinstance(item, type):
                    self.service_class = item
                    self.class_name = item.__dict__['__module__'].split('.')[1]
                    break
        except ImportError as e:
            # load_module() failed, probably because of a module dependency
            if len(self.module_depends) > 0:
                self._check_module_depends()
            else:
                # no dependencies in info file; use the ImportError instead
                self.missing_modules.append(str(e).split(" ")[3])
            self.error = True
        except Exception as e:
            # load_module() failed for some other reason
            Log.error(e)
            self.error = True

    def reload(self, module_path):
        if not self.active:
            self._load_module(module_path)