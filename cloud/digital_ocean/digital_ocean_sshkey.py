#!/usr/bin/python
# -*- coding: utf-8 -*-

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
DOCUMENTATION = '''
---
module: digital_ocean_sshkey
short_description: Create/delete an SSH key in DigitalOcean
description:
     - Create/delete an SSH key.
version_added: "1.6"
author: "Michael Gregson (@mgregson)"
options:
  state:
    description:
     - Indicate desired state of the target.
    default: present
    choices: ['present', 'absent']
  api_token:
    description:
     - DigitalOcean api token.
  id:
    description:
     - Numeric, the SSH key id you want to operate on.
  name:
    description:
     - String, this is the name of an SSH key to create or destroy.
  ssh_pub_key:
    description:
     - The public SSH key you want to add to your account.

notes:
  - Two environment variables can be used, DO_API_KEY and DO_API_TOKEN. They both refer to the v2 token.
  - As of Ansible 2.0, Version 2 of the DigitalOcean API is used.
  - As of Ansible 2.0, the above parameters were changed significantly. If you are running 1.9.x or earlier, please use C(ansible-doc digital_ocean_v2) to view the correct parameters for your version. Dedicated web docs will be available in the near future for the stable branch.
requirements:
  - "python >= 2.6"
  - dopy
'''


EXAMPLES = '''
# Ensure a SSH key is present
# If a key matches this name, will return the ssh key id and changed = False
# If no existing key matches this name, a new key is created, the ssh key id is returned and changed = False

- digital_ocean_sshkey: >
      state=present
      name=my_ssh_key
      ssh_pub_key='ssh-rsa AAAA...'
      api_token=XXX

'''

import os
import time
from distutils.version import LooseVersion

HAS_DOPY = True
try:
    import dopy
    from dopy.manager import DoError, DoManager
    if LooseVersion(dopy.__version__) < LooseVersion('0.3.2'):
        HAS_DOPY = False
except ImportError:
    HAS_DOPY = False

class TimeoutError(DoError):
    def __init__(self, msg, id):
        super(TimeoutError, self).__init__(msg)
        self.id = id

class JsonfyMixIn(object):
    def to_json(self):
        return self.__dict__

class SSH(JsonfyMixIn):
    manager = None

    def __init__(self, ssh_key_json):
        self.__dict__.update(ssh_key_json)
    update_attr = __init__

    def destroy(self):
        self.manager.destroy_ssh_key(self.id)
        return True

    @classmethod
    def setup(cls, api_token):
        cls.manager = DoManager(None, api_token, api_version=2)

    @classmethod
    def find(cls, name):
        if not name:
            return False
        keys = cls.list_all()
        for key in keys:
            if key.name == name:
                return key
        return False

    @classmethod
    def list_all(cls):
        json = cls.manager.all_ssh_keys()
        return map(cls, json)

    @classmethod
    def add(cls, name, key_pub):
        json = cls.manager.new_ssh_key(name, key_pub)
        return cls(json)

def core(module):
    def getkeyordie(k):
        v = module.params[k]
        if v is None:
            module.fail_json(msg='Unable to load %s' % k)
        return v

    try:
        api_token = module.params['api_token'] or os.environ['DO_API_TOKEN'] or os.environ['DO_API_KEY']
    except KeyError, e:
        module.fail_json(msg='Unable to load %s' % e.message)

    changed = True
    state = module.params['state']

    SSH.setup(api_token)
    name = getkeyordie('name')
    if state in ('present'):
        key = SSH.find(name)
        if key:
            module.exit_json(changed=False, ssh_key=key.to_json())
        key = SSH.add(name, getkeyordie('ssh_pub_key'))
        module.exit_json(changed=True, ssh_key=key.to_json())

    elif state in ('absent'):
        key = SSH.find(name)
        if not key:
            module.exit_json(changed=False, msg='SSH key with the name of %s is not found.' % name)
        key.destroy()
        module.exit_json(changed=True)

def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(choices=['present', 'absent'], default='present'),
            api_token = dict(aliases=['API_TOKEN'], no_log=True),
            name = dict(type='str'),
            id = dict(aliases=['droplet_id'], type='int'),
            ssh_pub_key = dict(type='str'),
        ),
        required_one_of = (
            ['id', 'name'],
        ),
    )
    if not HAS_DOPY:
        module.fail_json(msg='dopy required for this module')

    try:
        core(module)
    except TimeoutError as e:
        module.fail_json(msg=str(e), id=e.id)
    except (DoError, Exception) as e:
        module.fail_json(msg=str(e))

# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
