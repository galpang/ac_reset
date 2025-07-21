import pdb
import os
import argparse
import sys
import time
import yaml
import logging
from pathlib import Path
from pysnmp.hlapi import *
import collections.abc
collections.Hashable = collections.abc.Hashable
from datetime import datetime


APC_SERVER = '172.20.0.5'
OID = "1.3.6.1.4.1.318.1.1.12.3.3.1.1.4."
COMMUNITY = "private"


def timestamp():
    return "[{}]".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


class APC(object):
    def __init__(self, config):
        ip = config['ip']
        community = config['community']
        self.oid = config['OID']

        self.transport = UdpTransportTarget((ip, 161))

        self.engine = SnmpEngine()
        self.context = ContextData()
        self.community_data = CommunityData(community)

        self.state = {
            '1': "On",
            '2': "Off",
            '3': "Reboot Delayed"
        }

    def power_switch(self, on=True, reset=False):
        if reset:
            val = Integer(3)
        elif on:
            val = Integer(1)
        else:
            val = Integer(2)
        type = ObjectType(ObjectIdentity(self.oid), val)
        print('test')

        g = setCmd(self.engine,
                   self.community_data,
                   self.transport,
                   self.context,
                   type,
                   lookupMib=False)
        errorIndication, errorStatus, errorIndex, varBinds = next(g)
        print("{} SET - oid: {}, value: {}[{}]".format(timestamp(),
                                                 varBinds[0][0].prettyPrint(),
                                                 varBinds[0][1].prettyPrint(),
                                                 self.state[varBinds[0][1].prettyPrint()]))

    def power_check(self, log=False):
        type = ObjectType(ObjectIdentity(self.oid))

        g = getCmd(self.engine,
                   self.community_data,
                   self.transport,
                   self.context,
                   type,
                   lookupMib=False)
        errorIndication, errorStatus, errorIndex, varBinds = next(g)
        state = self.state[varBinds[0][1].prettyPrint()]
        if log:
            print("{} oid: {}, value: {}({})".format(timestamp(),
                                                     varBinds[0][0].prettyPrint(),
                                                     varBinds[0][1].prettyPrint(),
                                                     state))

        return state

    def run_aging(self, interval, delay):
        print("start aging")
        flag = True
        now = time.time
        cnt = 1

        while flag:
            print(f'{cnt}th reboot')
            try:
                self.power_switch()
                time.sleep(3)
                start = now()
                while now() - start < interval:
                    if self.power_check() == "Off":
                        raise Exception("Abnormal power off!!!")
                    time.sleep(1)
                self.power_switch(on=False)
                time.sleep(delay)
            except Exception as err:
                print(err)
                flag = False
            except KeyboardInterrupt as err:
                print(err)
                flag = False


def main():
    main_logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="HW Reboot Aging Tool")
    parser.add_argument('-i', '--index',
                        required=True,
                        help='DUT index',
                        type=str, default=None)
    parser.add_argument('-t', '--interval',
                        required=False,
                        help='Reboot interval',
                        type=int, default=300)
    parser.add_argument('-d', '--delay',
                        required=False,
                        help='Power Off On delay',
                        type=int, default=5)

    args = parser.parse_args()
    delay = args.delay
    interval = args.interval

    oid = OID + args.index
    print(oid)
    config = {
        'ip': APC_SERVER,
        'community': COMMUNITY,
        'OID': oid,
	}

    apc = APC(config)
    apc.run_aging(interval, delay)

    return 0


if __package__ == '' or __package__ is None:
    path = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    sys.path.insert(0, path)


if __name__ == "__main__":
    sys.exit(main())

