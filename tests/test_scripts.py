from base.database import db
from conftest import path_playbooks, path_scripts
from os.path import join
from scripts.models import (
    AnsibleScript,
    NapalmConfigScript,
    NapalmGettersScript,
    NetmikoConfigScript,
    FileTransferScript,
    Script
)
from test_base import check_blueprints
from werkzeug.datastructures import ImmutableMultiDict

# test the creation of configuration script (netmiko / napalm)
# test the creation of file transfer script (netmiko via SCP)
# test the creation of ansible script

## Netmiko configuration

netmiko_ping = ImmutableMultiDict([
    ('name', 'netmiko_ping'),
    ('content_type', 'simple'),
    ('create_script', 'netmiko_config'),
    ('content', 'ping 1.1.1.1'),
    ('netmiko_type', 'show_commands'),
    ('driver', 'cisco_xr_ssh'),
    ('global_delay_factor', '1.0'),
])

template = '''
{% for interface, properties in subinterfaces.items() %}
interface FastEthernet0/0.{{ interface }}
description {{ properties.aire }}
encapsulation dot1Q {{ properties.dot1Q }}
ip address {{ properties.address }} 255.255.255.248
no ip redirects
ip ospf cost {{ properties.cost }}
{% endfor %}
'''

result = '''
interface FastEthernet0/0.420
description 262
encapsulation dot1Q 420
ip address 10.124.33.250 255.255.255.248
no ip redirects
ip ospf cost 320

interface FastEthernet0/0.418
description 252
encapsulation dot1Q 418
ip address 10.124.33.234 255.255.255.248
no ip redirects
ip ospf cost 520

interface FastEthernet0/0.419
description 261
encapsulation dot1Q 419
ip address 10.124.33.242 255.255.255.248
no ip redirects
ip ospf cost 620
'''

netmiko_jinja2_script = dict([
    ('name', 'netmiko_subif'),
    ('content_type', 'j2_template'),
    ('create_script', 'netmiko_config'),
    ('content', template),
    ('netmiko_type', 'configuration'),
    ('driver', 'cisco_xr_ssh'),
    ('global_delay_factor', '1.0'),
])

napalm_jinja2_script = dict([
    ('name', 'napalm_subif'),
    ('content_type', 'j2_template'),
    ('create_script', 'napalm_config'),
    ('content', template),
    ('script_type', 'napalm_configuration'),
    ('action', 'load_merge_candidate')
])

file_transfer_script = ImmutableMultiDict([
    ('name', 'test'),
    ('driver', 'cisco_ios'),
    ('source_file', 'path/to/source'),
    ('destination_file', 'path/to/destination'),
    ('file_system', 'flash:'),
    ('direction', 'put'),
    ('create_script', 'file_transfer'),
])


@check_blueprints('/scripts')
def test_base_scripts(user_client):
    user_client.post('/scripts/script_creation', data=netmiko_ping)
    assert len(NetmikoConfigScript.query.all()) == 1
    path_yaml = join(path_scripts, 'interfaces', 'parameters.yaml')
    with open(path_yaml, 'rb') as f:
        netmiko_jinja2_script['file'] = f
        user_client.post('/scripts/script_creation', data=netmiko_jinja2_script)
    with open(path_yaml, 'rb') as f:
        napalm_jinja2_script['file'] = f
        user_client.post('/scripts/script_creation', data=napalm_jinja2_script)
    assert len(NapalmConfigScript.query.all()) == 1
    assert len(Script.query.all()) == 6
    netmiko_j2_script = db.session.query(Script).filter_by(name='netmiko_subif').first()
    napalm_j2_script = db.session.query(Script).filter_by(name='napalm_subif').first()
    # simply removing the space does not work as yaml relies on dict, which
    # are not ordered, we use set instead for the test to pass on python 2 and 3
    assert set(netmiko_j2_script.content.split('\n')) == set(result.split('\n'))
    assert set(napalm_j2_script.content.split('\n')) == set(result.split('\n'))
    ## file transfer script
    user_client.post('scripts/script_creation', data=file_transfer_script)
    assert len(FileTransferScript.query.all()) == 1
    assert len(Script.query.all()) == 7

## NAPALM getters


getters_dict = ImmutableMultiDict([
    ('name', 'napalm_getters_script'),
    ('getters', 'get_interfaces'),
    ('getters', 'get_interfaces_ip'),
    ('getters', 'get_lldp_neighbors'),
    ('create_script', 'napalm_getters')
])


@check_blueprints('/scripts')
def test_getters_script(user_client):
    user_client.post('/scripts/script_creation', data=getters_dict)
    assert len(NapalmGettersScript.query.all()) == 1


## Ansible script

ansible_script = {
    'create_script': 'ansible_playbook',
    'name': 'ansible_test',
    'listtags': 'False',
    'listtasks': 'False',
    'listhosts': 'False',
    'syntax': 'False',
    'connection': 'ssh',
    'module_path': '',
    'forks': '100',
    'remote_user': '',
    'private_key_file': '',
    'ssh_common_args': '',
    'ssh_extra_args': '',
    'sftp_extra_args': '',
    'scp_extra_args': '',
    'become': 'False',
    'become_method': '',
    'become_user': '',
    'verbosity': '',
    'check': 'False',
    'diff': 'False'
}


@check_blueprints('/scripts')
def test_ansible_scripts(user_client):
    path_yaml = join(path_playbooks, 'save_running_config.yml')
    with open(path_yaml, 'rb') as f:
        ansible_script['file'] = f
        user_client.post('/scripts/script_creation', data=ansible_script)
    assert len(AnsibleScript.query.all()) == 1
    assert len(Script.query.all()) == 4
