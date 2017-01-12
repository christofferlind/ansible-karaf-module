#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import *

"""
Ansible module to manage karaf features
(c) 2017, Matthieu Rémy <remy.matthieu@gmail.com>
"""

DOCUMENTATION = '''
---
module: karaf_feature
'''

EXAMPLES = '''
# Install karaf feature
- karaf_feature: state=present name="camel-jms"

# Uninstall karaf feature
- karaf_feature: state=absent name="camel-jms"

# Install karaf feature versioned
- karaf_feature: state=present name="camel-jms" version="2.18.1"

# Force install
- karaf_feature: state=present name="camel-jms" version="2.18.1" force=true
'''

PACKAGE_STATE_MAP = dict(
    present="install",
    absent="uninstall"
)

FEATURE_STATE_UNINSTALLED = 'Uninstalled'
CLIENT_KARAF_COMMAND = "{0} 'feature:{1}'"
CLIENT_KARAF_COMMAND_WITH_ARGS = "{0} 'feature:{1} {2}'"


def install_feature(client_bin, module, feature_name):
    """Call karaf client command to install a feature

    :param client_bin: karaf client command bin
    :param module: ansible module
    :param feature_name: name of feature to install
    :return: command, ouput command message, error command message
    """
    cmd = CLIENT_KARAF_COMMAND_WITH_ARGS.format(client_bin, PACKAGE_STATE_MAP["present"], feature_name)
    rc, out, err = module.run_command(cmd)

    if rc != 0:
        reason = parse_error(out)
        module.fail_json(msg=reason)

    return True, cmd, out, err


def uninstall_feature(client_bin, module, feature_name):
    """Call karaf client command to uninstall a feature

    :param client_bin: karaf client command bin
    :param module: ansible module
    :param feature_name: name of feature to install
    :return: command, ouput command message, error command message
    """
    cmd = CLIENT_KARAF_COMMAND_WITH_ARGS.format(client_bin, PACKAGE_STATE_MAP["absent"], feature_name)
    rc, out, err = module.run_command(cmd)

    if rc != 0:
        reason = parse_error(out)
        module.fail_json(msg=reason)

    return True, cmd, out, err


def is_feature_installed(client_bin, module, feature_name, feature_version):
    """ Check if a feature with given version is installed.

    :param client_bin: karaf client command bin
    :param module: ansible module
    :param feature_name: name of feature to install
    :param feature_version: version of feature to install. Optional.
    :return: True if feature is installed, False if not
    """

    cmd = CLIENT_KARAF_COMMAND.format(client_bin, 'list')
    rc, out, err = module.run_command(cmd)
    lines = out.split('\n')

    is_installed = False
    for line in lines:
        feature_data = line.split('|')
        if len(feature_data) > 2:
            name = feature_data[0].strip()
            version = feature_data[1].strip()
            state = feature_data[3].strip()

            if state != FEATURE_STATE_UNINSTALLED:
                if feature_version:
                    if name == feature_name and version == feature_version:
                        is_installed = True
                else:
                    if name == feature_name:
                        is_installed = True

    return is_installed


def parse_error(string):
    reason = "reason: "
    try:
        return string[string.index(reason) + len(reason):].strip()
    except ValueError:
        return string


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True),
            version=dict(default=None),
            state=dict(default="present", choices=PACKAGE_STATE_MAP.keys()),
            force=dict(default=False),
            client_bin=dict(default="/opt/karaf/bin/client", type="path")
        )
    )

    name = module.params["name"]
    version = module.params["version"]
    state = module.params["state"]
    force = module.params["force"]
    client_bin = module.params["client_bin"]

    full_qualified_name = name
    if version:
        full_qualified_name = full_qualified_name + "/" + version

    changed = False
    cmd = ''
    out = ''
    err = ''
    if force == True and state == "present":
        module.fail_json(msg=force)
        uninstall_feature(client_bin, module, full_qualified_name)
        changed, cmd, out, err = install_feature(client_bin, module, full_qualified_name)
    else:
        is_installed = is_feature_installed(client_bin, module, name, version)
        # skip if the state is correct
        if (is_installed and state == "present") or (state == "absent" and not is_installed):
            module.exit_json(changed=False, name=full_qualified_name, state=state)

        if state == "present":
            changed, cmd, out, err = install_feature(client_bin, module, full_qualified_name)
        elif state == "absent":
            changed, cmd, out, err = uninstall_feature(client_bin, module, full_qualified_name)

    module.exit_json(changed=changed, cmd=cmd, name=full_qualified_name, state=state, stdout=out, stderr=err)

if __name__ == '__main__':
    main()
